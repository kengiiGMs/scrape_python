"""
Script de Ingestão Agêntica de FAQs.
Processa arquivos Markdown scraped usando LLM para gerar FAQs estruturados
e carrega no banco vetorial Supabase.
"""

import os
import sys
import json
import time
import threading
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
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


# ──────────────────────────────────────────────────────────────
class ProgressSpinner:
    """
    Spinner animado que imprime na mesma linha com elapsed time.
    Uso:
        spinner = ProgressSpinner("Enviando para o LLM...")
        spinner.start()
        # ... trabalho demorado ...
        spinner.stop(success=True, msg="Pronto!")
    """
    FRAMES = ['|', '/', '-', '\\']

    def __init__(self, label: str, estimate_s: float = 0):
        self.label = label
        self.estimate_s = estimate_s  # 0 = sem estimativa
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._start_time = 0.0
        self._is_tty = sys.stdout.isatty()

    def start(self):
        self._start_time = time.time()
        self._thread.start()
        return self

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            elapsed = time.time() - self._start_time
            frame = self.FRAMES[idx % len(self.FRAMES)]
            idx += 1
            if self.estimate_s > 0:
                remaining = max(0.0, self.estimate_s - elapsed)
                eta = f" | ~{remaining:.0f}s restantes"
            else:
                eta = ""
            line = f"  {frame} {self.label} ({elapsed:.1f}s{eta})   "
            if self._is_tty:
                sys.stdout.write(f"\r{line}")
                sys.stdout.flush()
            self._stop_event.wait(0.12)

    def stop(self, success: bool = True, msg: str = ""):
        self._stop_event.set()
        self._thread.join(timeout=1)
        elapsed = time.time() - self._start_time
        icon = "[OK]" if success else "[X]"
        label = msg if msg else self.label
        line = f"  {icon} {label} ({elapsed:.1f}s)"
        if self._is_tty:
            sys.stdout.write(f"\r{line}" + " " * 20 + "\n")
        else:
            print(line)
        sys.stdout.flush()
# ──────────────────────────────────────────────────────────────



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


def chunk_content(content: str, max_chars: int = 50_000) -> List[str]:
    """Divide o conteúdo em chunks menores para evitar truncamento do LLM."""
    if len(content) <= max_chars:
        return [content]
    
    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line) + 1  # +1 para o \n
        if current_size + line_size > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks


def derive_id_conta(file_path: str) -> str:
    """Deriva o ID_Conta usando literalmente o nome do arquivo Markdown."""
    id_conta = Path(file_path).stem.strip()
    if not id_conta:
        raise ValueError("Nao foi possivel derivar ID_Conta do nome do arquivo Markdown.")
    return id_conta


def _call_llm_for_chunk(
    chunk: str,
    chunk_num: int,
    total_chunks: int,
    llm: ChatGoogleGenerativeAI,
    tracker: TokenUsageTracker = None
) -> List:
    """Envia um único chunk para o LLM e retorna a lista de faq_items."""

    estimate_s = 45.0  # média empírica por chunk no Gemini Flash
    spinner = ProgressSpinner(
        f"[Chunk {chunk_num}/{total_chunks}] Enviando {len(chunk):,} chars ao LLM",
        estimate_s=estimate_s
    ).start()

    user_message = f"""Analise o seguinte conteúdo Markdown e extraia FAQs estruturados seguindo as instruções do system prompt:

---INÍCIO DO CONTEÚDO---
{chunk}
---FIM DO CONTEÚDO---

Retorne APENAS o JSON estruturado conforme especificado."""

    messages = [
        {"role": "system", "content": INGESTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    try:
        response = llm.invoke(messages)
    except Exception as e:
        spinner.stop(success=False, msg=f"[Chunk {chunk_num}/{total_chunks}] Erro na chamada ao LLM")
        raise

    raw_response = response.content

    # Captura tokens
    if tracker and hasattr(response, 'usage_metadata') and response.usage_metadata:
        metadata = response.usage_metadata
        if isinstance(metadata, dict):
            input_tokens = metadata.get('input_tokens', 0) or metadata.get('prompt_token_count', 0)
            output_tokens = metadata.get('output_tokens', 0) or metadata.get('candidates_token_count', 0)
            total_tokens = metadata.get('total_tokens', 0) or metadata.get('total_token_count', 0)
        else:
            input_tokens = getattr(metadata, 'input_tokens', None) or getattr(metadata, 'prompt_token_count', 0)
            output_tokens = getattr(metadata, 'output_tokens', None) or getattr(metadata, 'candidates_token_count', 0)
            total_tokens = getattr(metadata, 'total_tokens', None) or getattr(metadata, 'total_token_count', 0)

        if not total_tokens and input_tokens and output_tokens:
            total_tokens = input_tokens + output_tokens

        tracker.llm_input_tokens += input_tokens
        tracker.llm_output_tokens += output_tokens
        tracker.llm_total_tokens += total_tokens

    # Extrai JSON da resposta
    json_str = raw_response
    if "```json" in raw_response:
        json_str = raw_response.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_response:
        json_str = raw_response.split("```")[1].split("```")[0].strip()

    try:
        parsed_json = json.loads(json_str)
        items = parsed_json.get("faq_items", [])

        token_info = ""
        if tracker:
            token_info = f" | {total_tokens:,} tokens"
        spinner.stop(
            success=True,
            msg=f"[Chunk {chunk_num}/{total_chunks}] {len(items)} FAQs extraídos{token_info}"
        )
        return items
    except json.JSONDecodeError as e:
        spinner.stop(success=False, msg=f"[Chunk {chunk_num}/{total_chunks}] Erro JSON: {e}")
        print(f"  Resposta bruta:\n{raw_response[:500]}...")
        raise



def process_with_llm(content: str, llm: ChatGoogleGenerativeAI, tracker: TokenUsageTracker = None) -> FAQResponse:
    """Processa o conteúdo Markdown usando o LLM para gerar FAQs estruturados.
    
    Divide automaticamente arquivos grandes em chunks para evitar truncamento do JSON.
    """
    chunks = chunk_content(content, max_chars=50_000)
    total_chunks = len(chunks)
    
    if total_chunks == 1:
        print("\nEnviando para o LLM processar...")
    else:
        print(f"\nArquivo grande detectado ({len(content):,} chars). Processando em {total_chunks} chunks...")
    
    all_faq_items = []
    
    for i, chunk in enumerate(chunks, start=1):
        items = _call_llm_for_chunk(chunk, i, total_chunks, llm, tracker)
        all_faq_items.extend(items)
    
    try:
        faq_response = FAQResponse(faq_items=all_faq_items)
        print(f"\nJSON validado com sucesso! {len(faq_response.faq_items)} FAQs encontrados no total.")
        return faq_response
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

    spinner = ProgressSpinner(
        f"Gerando embeddings para {len(faq_items)} FAQs",
        estimate_s=max(10.0, len(faq_items) * 0.2)
    ).start()

    rows = []
    texts_to_embed = []

    for faq in faq_items:
        text_to_embed = (
            f"{faq.question}\n\n"
            f"{faq.answer}\n\n"
            f"{' '.join(faq.synthetic_variations)}"
        )
        texts_to_embed.append(text_to_embed)

    try:
        vectors = embeddings.embed_documents(texts_to_embed)
    except Exception as e:
        spinner.stop(success=False, msg=f"Erro ao gerar embeddings")
        raise

    # Estima tokens de embeddings (~1 token por 4 caracteres)
    estimated_tokens = 0
    if tracker:
        total_chars = sum(len(t) for t in texts_to_embed)
        estimated_tokens = total_chars // 4
        tracker.embedding_tokens += estimated_tokens

    for i, faq in enumerate(faq_items):
        rows.append({
            "content": faq.answer,
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

    token_info = f" | ~{estimated_tokens:,} tokens estimados" if estimated_tokens else ""
    spinner.stop(success=True, msg=f"{len(rows)} embeddings gerados{token_info}")
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
    if clear_before:
        print(f"\n  [clear] Limpando tabela '{table_name}'...")
        try:
            supabase.table(table_name).delete().neq('id', 0).execute()
            print(f"  [OK] Tabela '{table_name}' limpa.")
        except Exception as e:
            print(f"  [!] Nao foi possivel limpar a tabela: {e}")
            print("  Continuando com a insercao...")

    spinner = ProgressSpinner(
        f"Inserindo {len(rows)} FAQs no Supabase (tabela: {table_name})",
        estimate_s=5.0
    ).start()
    try:
        result = supabase.table(table_name).insert(rows).execute()
        spinner.stop(success=True, msg=f"{len(rows)} FAQs inseridos com sucesso no Supabase")
        return result
    except Exception as e:
        spinner.stop(success=False, msg=f"Erro ao inserir no Supabase")
        if "ID_Conta" in str(e):
            raise RuntimeError(
                "Falha ao inserir ID_Conta. Garanta que a tabela possua a coluna literal 'ID_Conta' "
                "ou ajuste o schema no Supabase antes da ingestão."
            ) from e
        raise



def export_to_xml(faq_response, id_conta: str, tracker, args_input: str, args_table: str, output_dir=None) -> str:
    """Exporta todos os FAQs gerados para um arquivo XML na pasta Exemplos."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"faq_{id_conta}_{timestamp}.xml"
    
    if output_dir is None:
        # Usa a pasta Exemplos relativa ao script
        script_dir = Path(__file__).parent
        output_dir = script_dir / "Exemplos"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    
    # Cria estrutura XML
    root = ET.Element("IngestaoFAQ")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    
    # Metadados
    meta = ET.SubElement(root, "Metadados")
    ET.SubElement(meta, "ID_Conta").text = id_conta
    ET.SubElement(meta, "ArquivoOrigem").text = str(args_input)
    ET.SubElement(meta, "TabelaDestino").text = args_table
    ET.SubElement(meta, "DataHora").text = datetime.now().isoformat()
    ET.SubElement(meta, "TotalFAQs").text = str(len(faq_response.faq_items))
    
    # Tokens
    summary = tracker.get_summary()
    tokens_el = ET.SubElement(meta, "UsoDeTokens")
    llm_el = ET.SubElement(tokens_el, "LLM")
    ET.SubElement(llm_el, "Entrada").text = str(summary['llm']['input_tokens'])
    ET.SubElement(llm_el, "Saida").text = str(summary['llm']['output_tokens'])
    ET.SubElement(llm_el, "Total").text = str(summary['llm']['total_tokens'])
    emb_el = ET.SubElement(tokens_el, "Embeddings")
    ET.SubElement(emb_el, "Estimativa").text = str(summary['embeddings']['tokens'])
    ET.SubElement(tokens_el, "TotalGeral").text = str(summary['total_all'])
    
    # FAQs
    faqs_el = ET.SubElement(root, "FAQs")
    for i, faq in enumerate(faq_response.faq_items, start=1):
        faq_el = ET.SubElement(faqs_el, "FAQ")
        faq_el.set("id", str(i))
        ET.SubElement(faq_el, "Pergunta").text = faq.question
        ET.SubElement(faq_el, "Resposta").text = faq.answer
        ET.SubElement(faq_el, "Categoria").text = faq.category
        ET.SubElement(faq_el, "Audiencia").text = faq.audience
        ET.SubElement(faq_el, "ConfiancaScore").text = str(faq.confidence_score)
        
        vars_el = ET.SubElement(faq_el, "VariacoesSinteticas")
        for v in faq.synthetic_variations:
            ET.SubElement(vars_el, "Variacao").text = v
        
        tags_el = ET.SubElement(faq_el, "Tags")
        for t in faq.tags:
            ET.SubElement(tags_el, "Tag").text = t
    
    # Grava com indentação bonita
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    tree.write(str(output_path), encoding="utf-8", xml_declaration=True)
    
    print(f"\n[OK] XML exportado: {output_path}")
    return str(output_path)


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
    parser.add_argument(
        "--output-xml",
        type=str,
        default=None,
        help="Pasta de saída para o XML (padrão: Exemplos/ ao lado do script)"
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
        
        # 5. Exporta XML
        xml_path = export_to_xml(
            faq_response, id_conta, tracker,
            args.input, args.table,
            output_dir=args.output_xml
        )
        
        print("\n" + "=" * 80)
        print("INGESTAO CONCLUIDA COM SUCESSO!")
        print("=" * 80)
        print(f"\nEstatisticas:")
        print(f"   - Arquivo processado: {args.input}")
        print(f"   - ID_Conta: {id_conta}")
        print(f"   - FAQs gerados: {len(faq_response.faq_items)}")
        print(f"   - Tabela: {args.table}")
        print(f"   - Modo clear: {'Sim' if args.clear else 'Nao'}")
        print(f"   - XML gerado: {xml_path}")
        
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
