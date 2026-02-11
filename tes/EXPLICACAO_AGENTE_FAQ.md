# 📚 Documentação: Agente_FAQ.py

## 🎯 Visão Geral

O `Agente_FAQ.py` é um **sistema de ingestão agêntica** que utiliza Inteligência Artificial para processar documentação em formato Markdown e transformá-la automaticamente em uma base de conhecimento estruturada de FAQs (Perguntas Frequentes).

### O que o script faz?

1. **Lê** arquivos Markdown brutos (scraped de sites, documentações, etc)
2. **Processa** o conteúdo usando LLM (Gemini 2.5 Flash) para extrair informações relevantes
3. **Estrutura** as informações em formato FAQ com perguntas, respostas, categorias e metadados
4. **Gera embeddings** vetoriais dos FAQs usando Gemini Embedding
5. **Armazena** tudo no banco vetorial Supabase para consulta por similaridade
6. **Rastreia** o consumo de tokens da operação

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────┐
│ Arquivo .md     │
│ (Markdown bruto)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ 1. load_markdown_file() │
│    - Carrega arquivo    │
│    - Valida conteúdo    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 2. process_with_llm()       │
│    - Envia para Gemini      │
│    - System Prompt inteli.  │
│    - Extrai FAQs estrut.    │
│    - Rastreia tokens        │
└────────┬────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ 3. generate_embeddings()     │
│    - Cria vetores semânticos │
│    - Concatena Q+A+variações │
│    - Estima tokens usado     │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ 4. insert_into_supabase()    │
│    - Insere no banco vetorial│
│    - Opção de limpar tabela  │
└──────────────────────────────┘
```

---

## 🧩 Componentes Principais

### 1. TokenUsageTracker (Classe)

**Propósito**: Rastrear o consumo de tokens durante a operação.

**Atributos**:
- `llm_input_tokens`: Tokens de entrada do LLM
- `llm_output_tokens`: Tokens de saída do LLM
- `llm_total_tokens`: Total de tokens do LLM
- `embedding_tokens`: Tokens usados nos embeddings

**Métodos**:
- `on_llm_end()`: Callback para capturar tokens (não usado diretamente no Gemini)
- `get_summary()`: Retorna dicionário com resumo de uso
- `print_summary()`: Imprime resumo formatado no terminal

**Exemplo de uso**:
```python
tracker = TokenUsageTracker()
faq_response = process_with_llm(content, llm, tracker)
tracker.print_summary()  # Exibe: 15,986 tokens (6,311 entrada + 9,675 saída)
```

---

### 2. INGESTION_SYSTEM_PROMPT (Constante)

**Propósito**: System prompt que instrui o LLM sobre como processar o conteúdo.

**Principais Diretrizes**:

#### 2.1 O que Ignorar
- ❌ Elementos de navegação (menus, breadcrumbs, rodapés)
- ❌ Conteúdo promocional e CTAs
- ❌ Listas dinâmicas (posts recentes, notícias)
- ❌ Boilerplate legal genérico

#### 2.2 Como Processar
- ✅ **Single-Topic Chunking**: Um tópico por FAQ
- ✅ **Contextualização**: Substituir pronomes vagos por referências explícitas
- ✅ **Formatação Markdown**: Usar negrito, listas, instruções claras

#### 2.3 Taxonomia de Categorias
1. `Troubleshooting` - Solução de problemas e erros
2. `How-To & Configuration` - Tutoriais e configurações
3. `Billing & Account` - Faturas, pagamentos, login
4. `Product Info` - Funcionalidades e requisitos
5. `Policies & Compliance` - Termos, privacidade, jurídico
6. `General` - Informações gerais da empresa

#### 2.4 Query Expansion (Variações Sintéticas)
Para cada FAQ, o LLM gera 2-4 variações de pergunta:
- **Variação Leiga**: Termos menos técnicos
- **Variação Sintoma**: Foco no problema, não na solução
- **Variação Keywords**: String curta com palavras-chave

**Exemplo**:
```json
{
  "question": "Como resetar a senha?",
  "synthetic_variations": [
    "esqueci minha senha o que fazer",
    "recuperar acesso conta",
    "problema login senha incorreta"
  ]
}
```

---

### 3. load_markdown_file(file_path: str)

**Propósito**: Carrega arquivo Markdown e retorna seu conteúdo.

**Parâmetros**:
- `file_path`: Caminho do arquivo .md

**Retorno**: String com o conteúdo completo

**Validações**:
- ✅ Arquivo existe
- ✅ Conteúdo não está vazio
- ✅ Encoding UTF-8

**Exemplo de saída**:
```
Carregando arquivo: plantie.md
Arquivo carregado com sucesso! (20608 caracteres)
```

---

### 4. process_with_llm(content, llm, tracker)

**Propósito**: Envia conteúdo para o LLM e extrai FAQs estruturados.

**Parâmetros**:
- `content`: String com o conteúdo Markdown
- `llm`: Instância do ChatGoogleGenerativeAI
- `tracker`: (Opcional) TokenUsageTracker para rastrear tokens

**Retorno**: Objeto `FAQResponse` (validado com Pydantic)

**Fluxo de Processamento**:

1. **Monta mensagens** (system + user prompt)
2. **Invoca LLM** (Gemini 2.5 Flash)
3. **Captura tokens** do `usage_metadata` da resposta
4. **Extrai JSON** (remove markdown se presente)
5. **Valida** estrutura com Pydantic
6. **Retorna** objeto FAQResponse

**Tratamento de Erros**:
- `JSONDecodeError`: JSON malformado
- `ValidationError`: Estrutura inválida do FAQ

**Exemplo de saída**:
```
Enviando para o LLM processar...
   (LLM usou 15,986 tokens: 6,311 entrada + 9,675 saída)
LLM retornou resposta (27094 caracteres)
JSON validado com sucesso! 30 FAQs encontrados.
```

---

### 5. generate_embeddings_for_faqs(faq_items, embeddings, tracker)

**Propósito**: Gera embeddings vetoriais para cada FAQ.

**Parâmetros**:
- `faq_items`: Lista de objetos FAQItem
- `embeddings`: Instância do GoogleGenerativeAIEmbeddings
- `tracker`: (Opcional) TokenUsageTracker

**Retorno**: Lista de dicionários prontos para inserção no Supabase

**Processo**:

1. **Concatena** para cada FAQ:
   ```python
   text_to_embed = f"{question}\n\n{answer}\n\n{' '.join(synthetic_variations)}"
   ```

2. **Gera embeddings em batch** (todos de uma vez para eficiência)

3. **Estima tokens**: `total_chars / 4` (aproximação)

4. **Monta estrutura final**:
   ```python
   {
       "content": answer,           # Texto retornado ao chatbot
       "metadata": {
           "question": question,
           "synthetic_variations": [...],
           "category": category,
           "tags": [...],
           "audience": audience,
           "confidence_score": 0.9
       },
       "embedding": [0.123, -0.456, ...]  # Vetor de 768 dimensões
   }
   ```

**Exemplo de saída**:
```
Gerando embeddings para os FAQs...
   (Estimativa: ~4,276 tokens de embeddings)
30 embeddings gerados com sucesso!
```

---

### 6. clear_table(supabase, table_name)

**Propósito**: Limpa todos os registros da tabela no Supabase.

**Parâmetros**:
- `supabase`: Cliente Supabase
- `table_name`: Nome da tabela

**Comportamento**:
- Usa filtro `.neq('id', 0)` (sempre verdadeiro) para deletar tudo
- Captura exceções e continua se falhar

**Exemplo de saída**:
```
Limpando tabela 'marketing_rag'...
Tabela 'marketing_rag' limpa com sucesso!
```

---

### 7. insert_into_supabase(supabase, table_name, rows, clear_before)

**Propósito**: Insere FAQs processados no banco vetorial.

**Parâmetros**:
- `supabase`: Cliente Supabase
- `table_name`: Nome da tabela destino
- `rows`: Lista de registros para inserir
- `clear_before`: Se `True`, limpa tabela antes

**Fluxo**:
1. (Opcional) Limpa tabela
2. Insere todos os registros em batch
3. Retorna resultado da operação

**Exemplo de saída**:
```
Inserindo 30 FAQs na tabela 'marketing_rag'...
30 FAQs inseridos com sucesso no Supabase!
```

---

### 8. main()

**Propósito**: Função principal que orquestra todo o pipeline.

**Argumentos de Linha de Comando**:

| Argumento | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `--input` | string | ✅ Sim | - | Caminho do arquivo .md |
| `--table` | string | ❌ Não | `marketing_rag` | Nome da tabela Supabase |
| `--clear` | flag | ❌ Não | `False` | Limpar tabela antes de inserir |

**Pipeline Completo**:

```python
# 1. Configuração
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
supabase = create_client(supabase_url, supabase_key)
tracker = TokenUsageTracker()

# 2. Carrega arquivo
content = load_markdown_file(args.input)

# 3. Processa com LLM
faq_response = process_with_llm(content, llm, tracker)

# 4. Gera embeddings
rows = generate_embeddings_for_faqs(faq_response.faq_items, embeddings, tracker)

# 5. Insere no banco
insert_into_supabase(supabase, args.table, rows, clear_before=args.clear)

# 6. Estatísticas
tracker.print_summary()
```

---

## 🚀 Como Usar

### Pré-requisitos

**1. Variáveis de Ambiente** (`.env`):
```env
GOOGLE_API_KEY=sua_chave_api_google
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=sua_chave_service
```

**2. Dependências Python**:
```bash
pip install langchain-google-genai langchain-community supabase python-dotenv pydantic
```

**3. Arquivo `models.py`** com as classes Pydantic:
```python
from pydantic import BaseModel
from typing import List

class FAQItem(BaseModel):
    question: str
    synthetic_variations: List[str]
    answer: str
    category: str
    tags: List[str]
    audience: str
    confidence_score: float

class FAQResponse(BaseModel):
    faq_items: List[FAQItem]
```

### Execução Básica

```bash
python Agente_FAQ.py --input documento.md --table marketing_rag
```

### Execução com Limpeza de Tabela

```bash
python Agente_FAQ.py --input documento.md --table marketing_rag --clear
```

### Exemplo de Saída Completa

```
================================================================================
SISTEMA DE INGESTAO AGENTICA DE FAQs
================================================================================

Configurando sistema...
Sistema configurado!
Carregando arquivo: plantie.md
Arquivo carregado com sucesso! (20608 caracteres)

Enviando para o LLM processar...
   (LLM usou 15,986 tokens: 6,311 entrada + 9,675 saída)
LLM retornou resposta (27094 caracteres)
JSON validado com sucesso! 30 FAQs encontrados.

Gerando embeddings para os FAQs...
   (Estimativa: ~4,276 tokens de embeddings)
30 embeddings gerados com sucesso!

Inserindo 30 FAQs na tabela 'marketing_rag'...

Limpando tabela 'marketing_rag'...
Tabela 'marketing_rag' limpa com sucesso!
30 FAQs inseridos com sucesso no Supabase!

================================================================================
INGESTAO CONCLUIDA COM SUCESSO!
================================================================================

Estatisticas:
   - Arquivo processado: plantie.md
   - FAQs gerados: 30
   - Tabela: marketing_rag
   - Modo clear: Sim

FAQs por categoria:
   - Policies & Compliance: 17
   - Billing & Account: 4
   - Product Info: 3
   - How-To & Configuration: 3
   - General: 2
   - Troubleshooting: 1

================================================================================
RESUMO DE USO DE TOKENS
================================================================================

LLM (Gemini 2.5 Flash):
   - Tokens de entrada: 6,311
   - Tokens de saida: 9,675
   - Total LLM: 15,986

Embeddings (Gemini Embedding):
   - Tokens processados: 4,276

TOTAL GERAL: 20,262 tokens
================================================================================
```

---

## 📊 Estrutura dos Dados no Supabase

### Esquema da Tabela

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | ID único (auto-gerado) |
| `content` | TEXT | Resposta do FAQ (o que será retornado) |
| `metadata` | JSONB | Metadados estruturados |
| `embedding` | VECTOR(768) | Vetor semântico |

### Exemplo de Registro

```json
{
  "id": "a1b2c3d4-...",
  "content": "Para visualizar suas notas fiscais, acesse o menu superior direito...",
  "metadata": {
    "question": "Como acessar e visualizar as notas fiscais?",
    "synthetic_variations": [
      "Onde baixo meus boletos?",
      "Caminho para faturamento",
      "Ver histórico de pagamentos"
    ],
    "category": "Billing & Account",
    "tags": ["notas fiscais", "faturamento", "boletos", "menu"],
    "audience": "End-User",
    "confidence_score": 1.0
  },
  "embedding": [0.123, -0.456, 0.789, ...]
}
```

---

## 🔍 Casos de Uso

### 1. Ingestão de Documentação Técnica

```bash
python Agente_FAQ.py --input docs/api-reference.md --table tech_docs_faq
```

**Entrada**: Documentação técnica bruta com explicações de endpoints, parâmetros, etc.

**Saída**: FAQs estruturados como:
- "Como autenticar na API?"
- "Quais são os limites de rate limit?"
- "Como fazer paginação nos resultados?"

### 2. Base de Conhecimento de Suporte

```bash
python Agente_FAQ.py --input support/troubleshooting.md --table support_kb --clear
```

**Entrada**: Artigos de troubleshooting do site de suporte

**Saída**: FAQs categorizados como `Troubleshooting` com soluções para erros comuns

### 3. Políticas e Compliance

```bash
python Agente_FAQ.py --input legal/terms-of-service.md --table legal_kb
```

**Entrada**: Termos de uso, política de privacidade

**Saída**: FAQs em linguagem simples sobre políticas da empresa

---

## ⚙️ Configurações e Otimizações

### Modelos Utilizados

**LLM: Gemini 2.5 Flash**
- **Propósito**: Extração estruturada de FAQs
- **Temperature**: 0 (determinístico)
- **Vantagens**: Rápido, custo-efetivo, boa qualidade

**Embeddings: Gemini Embedding-001**
- **Dimensões**: 3072 (default), mas pode usar 768 ou 1536
- **Suporta**: 100+ idiomas
- **Vantagens**: SOTA em multilingual, 2048 tokens de entrada

### Estimativa de Custos

**Preço Gemini Embedding-001**: $0.15 por 1M tokens

**Exemplo de cálculo** (baseado na execução de teste):
- LLM: 15.986 tokens
- Embeddings: 4.276 tokens
- **Total**: 20.262 tokens

**Custo estimado para embeddings**: 
```
4.276 tokens × ($0.15 / 1.000.000) = $0.00064 (~R$ 0,0036)
```

Para processar 100 documentos similares:
```
20.262 tokens × 100 = ~2M tokens
Custo embeddings: ~$0.30
```

### Otimizações Possíveis

**1. Batch Processing**: Processar múltiplos arquivos em uma execução
```python
for file in glob.glob("docs/*.md"):
    content = load_markdown_file(file)
    # ... processo
```

**2. Cache de Embeddings**: Não regerar embeddings se conteúdo não mudou
```python
# Usar hash do conteúdo como chave
content_hash = hashlib.md5(content.encode()).hexdigest()
```

**3. Chunking de Documentos Grandes**: Dividir docs >100k chars
```python
if len(content) > 100000:
    chunks = split_text(content, max_size=50000)
```

---

## 🐛 Tratamento de Erros

### Erros Comuns

**1. `FileNotFoundError`**
```
Arquivo não encontrado: documento.md
```
**Solução**: Verificar caminho do arquivo

**2. `JSONDecodeError`**
```
Erro ao fazer parse do JSON: Expecting value: line 1 column 1 (char 0)
```
**Solução**: LLM retornou resposta inválida. Verificar system prompt ou tentar novamente.

**3. `ValidationError`**
```
Erro de validacao Pydantic: field required
```
**Solução**: JSON não segue estrutura esperada. Revisar models.py.

**4. `GoogleGenerativeAIError`**
```
Error embedding content (NOT_FOUND): 404 NOT_FOUND
```
**Solução**: Modelo de embedding incorreto. Usar `models/gemini-embedding-001`.

**5. `ValueError` (Variáveis de ambiente)**
```
SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar definidos no .env
```
**Solução**: Criar arquivo `.env` com as credenciais.

---

## 🔐 Segurança

### Boas Práticas

✅ **Usar variáveis de ambiente** para credenciais (nunca commitar `.env`)

✅ **Service Key do Supabase** apenas em servidor (não expor no frontend)

✅ **Validação de entrada** com Pydantic para prevenir dados malformados

✅ **Rate limiting** se processar muitos arquivos (evitar throttling da API)

### Permissões Necessárias

**Google AI**:
- Acesso à API Gemini (chave válida)
- Quota suficiente para tokens

**Supabase**:
- Permissão de INSERT na tabela
- Permissão de DELETE se usar `--clear`
- Service Key com privilégios adequados

---

## 📈 Métricas e Monitoramento

### O que Rastrear

1. **Tokens por documento**: Verificar se está dentro do esperado
2. **Número de FAQs extraídos**: Avaliar qualidade da extração
3. **Distribuição por categoria**: Verificar balanceamento
4. **Tempo de execução**: Identificar gargalos
5. **Taxa de erros**: JSON parsing, validação

### Exemplo de Log

```python
{
    "timestamp": "2026-02-10T16:26:46Z",
    "arquivo": "plantie.md",
    "chars_input": 20608,
    "faqs_gerados": 30,
    "tokens_llm": 15986,
    "tokens_embeddings": 4276,
    "tokens_total": 20262,
    "tempo_execucao_ms": 69358,
    "categorias": {
        "Policies & Compliance": 17,
        "Billing & Account": 4,
        "Product Info": 3
    }
}
```

---

## 🧪 Testes e Validação

### Testes Recomendados

**1. Teste com Documento Pequeno**
```bash
echo "# FAQ\n\nComo fazer login?\n\nAcesse o site e clique em Entrar." > test.md
python Agente_FAQ.py --input test.md --table test_table --clear
```

**2. Teste de Categorização**
- Verificar se FAQs estão nas categorias corretas
- Validar que synthetic_variations fazem sentido

**3. Teste de Busca Semântica** (após ingestão)
```python
# Usar agent_rag.py para buscar
result = buscar_faq("preciso redefinir minha senha")
# Deve retornar FAQ sobre reset de senha
```

---

## 🎓 Conceitos Técnicos

### RAG (Retrieval-Augmented Generation)

Este script é a **parte de INGESTÃO** de um sistema RAG:

1. **Ingestão** (Agente_FAQ.py) ← Você está aqui
   - Processa documentos
   - Gera embeddings
   - Armazena no banco vetorial

2. **Retrieval** (agent_rag.py)
   - Recebe pergunta do usuário
   - Busca FAQs similares no banco
   - Retorna as melhores respostas

3. **Generation** (chatbot)
   - Usa contexto recuperado
   - Gera resposta personalizada

### Embeddings Vetoriais

**O que são**: Representações numéricas de texto que capturam significado semântico.

**Como funcionam**:
```
Texto: "Como resetar senha?"
       ↓ (Gemini Embedding)
Vetor: [0.123, -0.456, 0.789, ..., 0.234]  (768 dimensões)
```

**Similaridade**:
```python
# Perguntas semanticamente similares têm vetores próximos
pergunta1 = "Como recuperar minha senha?"  → vetor1
pergunta2 = "Esqueci minha senha"          → vetor2
# cosine_similarity(vetor1, vetor2) = 0.92 (muito similar!)
```

### Query Expansion

**Problema**: Usuário pode perguntar de formas diferentes.

**Solução**: Gerar variações sintéticas para capturar mais formas de busca.

**Exemplo**:
```
Pergunta original: "Como resetar a senha?"

Variações geradas:
- "esqueci minha senha o que fazer" (leigo)
- "recuperar acesso conta" (keyword)
- "problema login senha incorreta" (sintoma)
```

Quando o usuário buscar qualquer uma dessas formas, o FAQ será encontrado!

---

## 🔄 Fluxo de Dados Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SISTEMA COMPLETO RAG                          │
└─────────────────────────────────────────────────────────────────────┘

1. INGESTÃO (Agente_FAQ.py) ──────────────────────────────────────────┐
                                                                        │
   docs/*.md ──► LLM ──► FAQs ──► Embeddings ──► Supabase              │
   (scraped)    (Gemini) (JSON)  (vectors)     (pgvector)             │
                                                                        │
2. CONSULTA (agent_rag.py) ───────────────────────────────────────────┤
                                                                        │
   Pergunta ──► Embedding ──► Busca ──► Top-K FAQs ──► Resposta       │
   usuário     (vetor)       (similar)  (relevantes)   (contextual)    │
                                                                        │
3. INTERFACE (Chatbot/API) ───────────────────────────────────────────┘
                                                                        
   Frontend ──► API ──► RAG ──► Resposta ──► Usuário                   
   (React)    (Flask)  (agent) (markdown)   (satisfeito!)              
```

---

## 📝 Notas Finais

### Quando Usar Este Script

✅ **Ideal para**:
- Documentação técnica extensa
- Base de conhecimento de suporte
- FAQs corporativos
- Políticas e compliance
- Manuais de produtos

❌ **Não ideal para**:
- Dados tabulares (usar CSV/database diretamente)
- Código-fonte (usar ferramentas de code search)
- Dados time-sensitive que mudam frequentemente

### Próximos Passos

Após executar este script, você pode:

1. **Consultar os FAQs** usando `agent_rag.py`
2. **Integrar com chatbot** para atendimento automático
3. **Criar API REST** para expor busca de FAQs
4. **Adicionar UI** para gerenciar base de conhecimento
5. **Configurar pipeline CI/CD** para auto-ingestão

---

## 🤝 Contribuindo

Para melhorar este script:

1. **Adicionar suporte a múltiplos arquivos** em uma execução
2. **Implementar cache** de embeddings
3. **Adicionar testes unitários**
4. **Criar CLI mais rica** (progress bars, logs JSON)
5. **Suportar outros formatos** (PDF, HTML, DOCX)

---

## 📚 Referências

- [LangChain Documentation](https://python.langchain.com/)
- [Google AI Gemini API](https://ai.google.dev/)
- [Supabase Vector Search](https://supabase.com/docs/guides/ai)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

**Criado em**: Fevereiro 2026  
**Versão**: 1.0  
**Autor**: Sistema de Ingestão Agêntica
