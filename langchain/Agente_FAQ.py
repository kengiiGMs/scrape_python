"""
Script de Ingestão Agêntica de FAQs.
Processa arquivos Markdown scraped usando LLM para gerar FAQs estruturados
e carrega no banco vetorial Supabase.
"""

import os
import json
import argparse
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.callbacks import BaseCallbackHandler
from supabase.client import Client, create_client
from pydantic import ValidationError

from models import FAQResponse, FAQItem


# Carrega variáveis de ambiente
load_dotenv()


# Classe para rastrear uso de tokens
class TokenUsageTracker(BaseCallbackHandler):
    """Callback para rastrear uso de tokens do LLM e embeddings."""
    
    def __init__(self):
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
        self.llm_total_tokens = 0
        self.embedding_tokens = 0
        
    def on_llm_end(self, response: Any, **kwargs) -> None:
        """Captura tokens usados pelo LLM."""
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            self.llm_input_tokens += token_usage.get('prompt_tokens', 0)
            self.llm_output_tokens += token_usage.get('completion_tokens', 0)
            self.llm_total_tokens += token_usage.get('total_tokens', 0)
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna um resumo do uso de tokens."""
        return {
            'llm': {
                'input_tokens': self.llm_input_tokens,
                'output_tokens': self.llm_output_tokens,
                'total_tokens': self.llm_total_tokens
            },
            'embeddings': {
                'tokens': self.embedding_tokens
            },
            'total_all': self.llm_total_tokens + self.embedding_tokens
        }
    
    def print_summary(self):
        """Imprime um resumo formatado do uso de tokens."""
        summary = self.get_summary()
        print("\n" + "=" * 80)
        print("RESUMO DE USO DE TOKENS")
        print("=" * 80)
        print(f"\nLLM (Gemini 2.5 Flash):")
        print(f"   - Tokens de entrada: {summary['llm']['input_tokens']:,}")
        print(f"   - Tokens de saida: {summary['llm']['output_tokens']:,}")
        print(f"   - Total LLM: {summary['llm']['total_tokens']:,}")
        
        if summary['embeddings']['tokens'] > 0:
            print(f"\nEmbeddings (Gemini Embedding):")
            print(f"   - Tokens processados: {summary['embeddings']['tokens']:,}")
        
        print(f"\nTOTAL GERAL: {summary['total_all']:,} tokens")
        print("=" * 80)


# System Prompt extraído do doc.md
INGESTION_SYSTEM_PROMPT = """
SYSTEM PROMPT: AGENTE DE INGESTÃO E ESTRUTURAÇÃO

1. OBJETIVO
Você receberá um texto em formato Markdown bruto, extraído de um site corporativo ou documentação técnica. Sua tarefa é analisar este conteúdo, identificar informações valiosas e transformá-las em uma lista estruturada de objetos FAQ (Pergunta/Resposta) em formato JSON.

2. REGRAS DE LIMPEZA E EXTRAÇÃO (CRÍTICO)
Você deve agir como um filtro inteligente. Siga estas diretrizes rigorosamente:

O Que Ignorar (Negative Constraints):
- Navegação: Ignore menus, breadcrumbs ("Home > Ajuda..."), rodapés, sitemaps e links de "Voltar ao topo".
- Marketing e CTA: Ignore frases puramente promocionais ("A melhor solução para você", "Assine agora"), banners de newsletter e botões de compartilhamento social.
- Conteúdo Dinâmico: Ignore listas de "Posts Recentes", "Notícias" datadas ou informações que se tornam obsoletas rapidamente.
- Boilerplate Legal: Ignore avisos de copyright ou termos de uso genéricos que aparecem no rodapé de todas as páginas (exceto se o documento for especificamente sobre Termos de Uso).

Como Processar o Texto (Transformation Rules):
- Single-Topic Chunking: Se um parágrafo trata de múltiplos tópicos (ex: "Como instalar" E "Como configurar"), divida-o em dois itens FAQ separados. Cada item deve conter apenas uma "verdade" atômica.
- Contextualização (De-referencing): Substitua pronomes e referências relativas.
  - Ruim: "Clique nele para salvar."
  - Bom: "Clique no botão 'Salvar' no painel de configurações."
  - Se o texto original perder o sentido fora da página, injete o contexto do título da seção ou da página no corpo da resposta.
- Formatação da Resposta: Use Markdown limpo dentro do campo de resposta (answer). Utilize listas (- ou 1.) para instruções passo-a-passo. Use negrito (**texto**) para elementos de interface (botões, menus). Mantenha a resposta concisa e direta.

3. TAXONOMIA DE CATEGORIAS
Classifique cada item extraído em APENAS UMA das seguintes categorias:
- Troubleshooting: Solução de erros, falhas, problemas técnicos e bugs.
- How-To & Configuration: Tutoriais, guias de instalação, configuração de funcionalidades, passo-a-passo.
- Billing & Account: Faturas, pagamentos, planos, gestão de assinatura, login, senhas.
- Product Info: Definições de funcionalidades, requisitos de sistema, integrações, limites.
- Policies & Compliance: Termos de uso, privacidade, segurança, garantias, jurídico.
- General: Informações de contato, horário de atendimento, sobre a empresa.

4. GERAÇÃO DE PERGUNTAS SINTÉTICAS (QUERY EXPANSION)
Para cada item extraído, você deve gerar o campo synthetic_variations contendo 2 a 4 variações da pergunta principal:
- Variação de Usuário Leigo: Use termos menos técnicos, gírias ou descrições vagas.
- Variação baseada em Sintoma/Dor: Foque no problema, não na solução (ex: "Não consigo acessar" vs "Erro de login").
- Variação de Palavras-Chave: Uma string curta focada em keywords principais para busca híbrida.

5. FORMATO DE SAÍDA (JSON SCHEMA)
Retorne APENAS um objeto JSON válido contendo uma lista de itens sob a chave "faq_items". Não inclua texto introdutório ou conclusivo fora do JSON.

Estrutura do JSON:
{
  "faq_items": [
    {
      "question": "A pergunta principal clara e direta (Ex: Como resetar a senha?)",
      "synthetic_variations": [
        "Variação 1 (Ex: esqueci minha senha o que fazer)",
        "Variação 2 (Ex: recuperar acesso conta)",
        "Variação 3 (Ex: problema login senha incorreta)"
      ],
      "answer": "A resposta completa, limpa e contextualizada em Markdown.",
      "category": "Uma das categorias definidas na seção 3 (Ex: Billing & Account)",
      "tags": ["lista", "de", "palavras-chave", "relevantes", "para", "filtro"],
      "audience": "Público alvo inferido (Ex: 'End-User', 'Admin', 'Developer')",
      "confidence_score": 1.0
    }
  ]
}

6. EXEMPLO FEW-SHOT (Para guiar seu raciocínio)

Entrada Bruta:
"Home > Suporte > Financeiro.
Se você precisa ver suas notas fiscais, o caminho mudou. Agora fica no menu superior direito, sob o ícone de engrenagem. Clique lá e selecione 'Faturamento'.
Ah, e se tiver o erro 500, tente limpar o cache.
Copyright 2024."

Saída Esperada:
{
  "faq_items": [
    {
      "question": "Como acessar e visualizar as notas fiscais?",
      "synthetic_variations": [
        "Onde baixo meus boletos?",
        "Caminho para faturamento",
        "Ver histórico de pagamentos"
      ],
      "answer": "Para visualizar suas notas fiscais, acesse o menu superior direito (ícone de engrenagem) e selecione a opção **Faturamento**.",
      "category": "Billing & Account",
      "tags": ["notas fiscais", "faturamento", "boletos", "menu"],
      "audience": "End-User",
      "confidence_score": 1.0
    },
    {
      "question": "Como resolver o Erro 500?",
      "synthetic_variations": [
        "tá dando erro 500",
        "site não carrega erro 500",
        "problema servidor erro 500"
      ],
      "answer": "Se você encontrar o **Erro 500**, a recomendação inicial é realizar a limpeza do cache do seu navegador e tentar novamente.",
      "category": "Troubleshooting",
      "tags": ["erro 500", "cache", "navegador"],
      "audience": "End-User",
      "confidence_score": 0.9
    }
  ]
}
"""


def load_markdown_file(file_path: str) -> str:
    """Carrega o conteúdo de um arquivo Markdown."""
    print(f"Carregando arquivo: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    
    if not documents:
        raise ValueError(f"Nenhum conteúdo encontrado em: {file_path}")
    
    content = documents[0].page_content
    print(f"Arquivo carregado com sucesso! ({len(content)} caracteres)")
    return content


def derive_id_conta(file_path: str) -> str:
    """Deriva o ID_Conta usando literalmente o nome do arquivo Markdown."""
    id_conta = Path(file_path).stem.strip()
    if not id_conta:
        raise ValueError("Nao foi possivel derivar ID_Conta do nome do arquivo Markdown.")
    return id_conta


def process_with_llm(content: str, llm: ChatGoogleGenerativeAI, tracker: TokenUsageTracker = None) -> FAQResponse:
    """Processa o conteúdo Markdown usando o LLM para gerar FAQs estruturados."""
    print("\nEnviando para o LLM processar...")
    
    user_message = f"""Analise o seguinte conteúdo Markdown e extraia FAQs estruturados seguindo as instruções do system prompt:

---INÍCIO DO CONTEÚDO---
{content}
---FIM DO CONTEÚDO---

Retorne APENAS o JSON estruturado conforme especificado."""
    
    # Envia para o LLM
    messages = [
        {"role": "system", "content": INGESTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    
    response = llm.invoke(messages)
    raw_response = response.content
    
    # Captura tokens da resposta (Google Generative AI retorna em usage_metadata)
    if tracker and hasattr(response, 'usage_metadata') and response.usage_metadata:
        metadata = response.usage_metadata
        input_tokens = metadata.get('input_tokens', 0)
        output_tokens = metadata.get('output_tokens', 0)
        total_tokens = metadata.get('total_tokens', 0)
        
        tracker.llm_input_tokens += input_tokens
        tracker.llm_output_tokens += output_tokens
        tracker.llm_total_tokens += total_tokens
        
        print(f"   (LLM usou {total_tokens:,} tokens: {input_tokens:,} entrada + {output_tokens:,} saída)")
    
    # Tenta extrair JSON da resposta (caso o LLM adicione markdown)
    json_str = raw_response
    if "```json" in raw_response:
        json_str = raw_response.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_response:
        json_str = raw_response.split("```")[1].split("```")[0].strip()
    
    print(f"LLM retornou resposta ({len(json_str)} caracteres)")
    
    # Parse e valida o JSON
    try:
        parsed_json = json.loads(json_str)
        faq_response = FAQResponse(**parsed_json)
        print(f"JSON validado com sucesso! {len(faq_response.faq_items)} FAQs encontrados.")
        return faq_response
    except json.JSONDecodeError as e:
        print(f"Erro ao fazer parse do JSON: {e}")
        print(f"Resposta bruta do LLM:\n{raw_response[:500]}...")
        raise
    except ValidationError as e:
        print(f"Erro de validacao Pydantic: {e}")
        raise


def generate_embeddings_for_faqs(
    faq_items: List[FAQItem], 
    embeddings: GoogleGenerativeAIEmbeddings,
    id_conta: str,
    tracker: TokenUsageTracker = None
) -> List[Dict]:
    """Gera embeddings para cada FAQ concatenando question + answer + synthetic_variations."""
    print("\nGerando embeddings para os FAQs...")
    
    rows = []
    texts_to_embed = []
    
    # Prepara os textos para vetorização
    for faq in faq_items:
        # Concatena question + answer + synthetic_variations para criar um vetor rico
        text_to_embed = (
            f"{faq.question}\n\n"
            f"{faq.answer}\n\n"
            f"{' '.join(faq.synthetic_variations)}"
        )
        texts_to_embed.append(text_to_embed)
    
    # Gera todos os embeddings de uma vez (batch)
    vectors = embeddings.embed_documents(texts_to_embed)
    
    # Estima tokens de embeddings (aproximadamente 1 token por 4 caracteres)
    if tracker:
        total_chars = sum(len(text) for text in texts_to_embed)
        estimated_tokens = total_chars // 4
        tracker.embedding_tokens += estimated_tokens
        print(f"   (Estimativa: ~{estimated_tokens:,} tokens de embeddings)")
    
    # Prepara as linhas para inserção
    for i, faq in enumerate(faq_items):
        rows.append({
            "content": faq.answer,  # O conteúdo retornado ao chatbot
            "ID_Conta": id_conta,
            "metadata": {
                "ID_Conta": id_conta,
                "question": faq.question,
                "synthetic_variations": faq.synthetic_variations,
                "category": faq.category,
                "tags": faq.tags,
                "audience": faq.audience,
                "confidence_score": faq.confidence_score
            },
            "embedding": vectors[i]
        })
    
    print(f"{len(rows)} embeddings gerados com sucesso!")
    return rows


def clear_table(supabase: Client, table_name: str):
    """Limpa todos os dados da tabela."""
    print(f"\nLimpando tabela '{table_name}'...")
    
    try:
        # Deleta todos os registros
        # Nota: Supabase requer um filtro, então usamos um filtro que sempre é verdadeiro
        result = supabase.table(table_name).delete().neq('id', 0).execute()
        print(f"Tabela '{table_name}' limpa com sucesso!")
    except Exception as e:
        print(f"Aviso: Nao foi possivel limpar a tabela: {e}")
        print("Continuando com a insercao...")


def insert_into_supabase(
    supabase: Client, 
    table_name: str, 
    rows: List[Dict],
    clear_before: bool = False
):
    """Insere os FAQs processados no Supabase."""
    print(f"\nInserindo {len(rows)} FAQs na tabela '{table_name}'...")
    
    if clear_before:
        clear_table(supabase, table_name)
    
    try:
        # Insere em batch
        result = supabase.table(table_name).insert(rows).execute()
        print(f"{len(rows)} FAQs inseridos com sucesso no Supabase!")
        return result
    except Exception as e:
        if "ID_Conta" in str(e):
            raise RuntimeError(
                "Falha ao inserir ID_Conta. Garanta que a tabela possua a coluna literal 'ID_Conta' "
                "ou ajuste o schema no Supabase antes da ingestao."
            ) from e
        print(f"Erro ao inserir no Supabase: {e}")
        raise


def main():
    """Função principal do script."""
    # Parse de argumentos
    parser = argparse.ArgumentParser(
        description="Script de Ingestão Agêntica de FAQs"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Caminho do arquivo Markdown a processar"
    )
    parser.add_argument(
        "--table",
        type=str,
        default="marketing_rag",
        help="Nome da tabela no Supabase (padrão: marketing_rag)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Limpar a tabela antes de inserir novos dados"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("SISTEMA DE INGESTAO AGENTICA DE FAQs")
    print("=" * 80)
    
    # Configuração
    print("\nConfigurando sistema...")
    
    # Verifica variáveis de ambiente
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar definidos no .env")
    
    # Inicializa LLM e Embeddings
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,  # Determinístico para extração estruturada
    )
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )
    
    # Conecta ao Supabase
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Inicializa o tracker de tokens
    tracker = TokenUsageTracker()
    
    print("Sistema configurado!")
    
    # Pipeline de ingestão
    try:
        id_conta = derive_id_conta(args.input)
        print(f"\nID_Conta derivado do arquivo: {id_conta}")

        # 1. Carrega o arquivo Markdown
        content = load_markdown_file(args.input)
        
        # 2. Processa com LLM
        faq_response = process_with_llm(content, llm, tracker)
        
        # 3. Gera embeddings
        rows = generate_embeddings_for_faqs(faq_response.faq_items, embeddings, id_conta, tracker)
        
        # 4. Insere no Supabase
        insert_into_supabase(supabase, args.table, rows, clear_before=args.clear)
        
        print("\n" + "=" * 80)
        print("INGESTAO CONCLUIDA COM SUCESSO!")
        print("=" * 80)
        print(f"\nEstatisticas:")
        print(f"   - Arquivo processado: {args.input}")
        print(f"   - ID_Conta: {id_conta}")
        print(f"   - FAQs gerados: {len(faq_response.faq_items)}")
        print(f"   - Tabela: {args.table}")
        print(f"   - Modo clear: {'Sim' if args.clear else 'Nao'}")
        
        # Estatísticas por categoria
        categories = {}
        for faq in faq_response.faq_items:
            categories[faq.category] = categories.get(faq.category, 0) + 1
        
        print(f"\nFAQs por categoria:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {category}: {count}")
        
        # Imprime resumo de uso de tokens
        tracker.print_summary()
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("ERRO NA INGESTAO")
        print("=" * 80)
        print(f"\n{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
