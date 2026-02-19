# EXPLICAÇÃO COMPLETA: API Python Scrape V3 + Pipeline FAQ + Chat

Este documento detalha a migração do fluxo de scraping e ingestão FAQ de Node/TypeScript para uma API 100% Python, usando o `scrape_python/V3/scraper.py` como base.

---

## 1) Visão geral da arquitetura

### Antes
- Backend Node/TypeScript (`index.ts`) com scraper Puppeteer
- Upload manual de markdown para processamento
- Frontend HTML chamando endpoints Node

### Depois
- **API Python única** (`scrape_python/api.py`) usando FastAPI
- **Pipeline automático**: URL → Scrape V3 → Markdown → Ingestão FAQ
- **Frontend HTML** consumindo API Python
- **Chat integrado** com proxy para webhook N8N

---

## 2) Arquivos modificados e criados

### `scrape_python/V3/scraper.py` (modificado)

**Alterações aplicadas:**

1. **Novas importações**:
```python
from urllib.parse import urlparse
import re
import uuid
```

2. **Nova função `sanitizar_dominio(url)`**:
- Extrai domínio da URL
- Remove `www.` e sanitiza caracteres especiais
- Retorna string segura para nome de arquivo

3. **Nova função `salvar_markdown_nomeado(markdown, url, pasta_destino=None)`**:
- Formato padrão: `dominio_YYYY-MM-DD_sufixo.md`
- Sufixo único (8 primeiros caracteres de UUID)
- Retorna tupla: `(caminho_completo, nome_arquivo_sem_extensao)`
- O `nome_arquivo_sem_extensao` vira o `ID_Conta`

4. **Função `salvar_markdown()` mantida**:
- Formato legado com timestamp mantido para compatibilidade

**Resultado funcional**:
- O scraper agora pode ser importado como módulo Python
- Não depende mais de `input()` CLI quando chamado programaticamente
- Gera nomes de arquivo consistentes e rastreáveis

---

### `scrape_python/api.py` (novo)

API FastAPI completa com 4 endpoints principais.

**Estrutura da API:**

#### Endpoint: `GET /`
- Serve o frontend HTML estático
- Retorna `public/index.html`

#### Endpoint: `GET /health`
- Health check básico
- Retorna status e timestamp

#### Endpoint: `POST /api/scrape`
**Payload:**
```json
{
  "url": "https://exemplo.com.br"
}
```

**Resposta:**
```json
{
  "success": true,
  "url": "https://exemplo.com.br",
  "markdown_preview": "# Título...",
  "length": 15234
}
```

**Comportamento:**
- Executa scraping de página única
- Retorna preview do markdown
- **NÃO salva** arquivo (apenas para teste)

#### Endpoint: `POST /api/pipeline`
**Payload:**
```json
{
  "url": "https://exemplo.com.br",
  "table": "marketing_rag",
  "clear": false
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Pipeline completo executado com sucesso",
  "data": {
    "url": "https://exemplo.com.br",
    "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4",
    "markdown_file": ".../langchain/uploads/exemplo-com-br_2026-02-11_a1b2c3d4.md",
    "markdown_length": 15234,
    "table": "marketing_rag",
    "clear": false,
    "ingest_output": {
      "returncode": 0,
      "stdout": "...",
      "stderr": ""
    }
  }
}
```

**Comportamento (pipeline completo):**
1. Scraping da URL com `processar()` do V3
2. Conversão para markdown com `html_para_markdown()`
3. Salvamento em `langchain/uploads/` com nome padronizado
4. Derivação automática do `ID_Conta` (nome do arquivo sem `.md`)
5. Execução do `Agente_FAQ.py` com subprocess:
   - `python langchain/Agente_FAQ.py --input <arquivo> --table marketing_rag [--clear]`
6. Captura de `stdout/stderr` e retorno estruturado

#### Endpoint: `POST /api/chat`
**Payload:**
```json
{
  "message": "Como funciona o sistema?",
  "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "reply": "Resposta do webhook N8N",
    "raw": { ... },
    "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4"
  }
}
```

**Comportamento:**
- Recebe mensagem + ID_Conta do frontend
- Envia para webhook N8N: `https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional`
- Payload forward: `{ "message": "...", "ID_Conta": "..." }`
- Extrai resposta útil (tenta chaves: `reply`, `response`, `answer`, `message`, `output`, `text`)
- Retorna resposta + dados brutos

**Funções auxiliares:**

1. `executar_ingestao(input_path, table, clear)`:
- Executa `Agente_FAQ.py` com `subprocess.run()`
- Timeout de 5 minutos
- Captura `stdout/stderr`
- Levanta erro se `returncode != 0`

2. `extrair_reply(data)`:
- Tenta extrair texto útil de resposta JSON do webhook
- Suporta dict, list, str
- Busca em chaves comuns de resposta

**Configurações importantes:**
```python
ROOT_DIR = Path(__file__).parent.parent
LANGCHAIN_DIR = ROOT_DIR / 'langchain'
UPLOAD_DIR = LANGCHAIN_DIR / 'uploads'  # Onde markdowns são salvos
INGEST_SCRIPT = LANGCHAIN_DIR / 'Agente_FAQ.py'
PUBLIC_DIR = Path(__file__).parent / 'public'
WEBHOOK_URL = 'https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional'
PYTHON_BIN = sys.executable  # Python do ambiente atual
```

---

### `scrape_python/public/index.html` (novo)

Frontend SPA (Single Page Application) sem frameworks.

**Seções principais:**

#### 1. Seção de Pipeline
- **Input URL**: Campo para URL do site
- **Checkbox Clear**: Opção para limpar tabela antes da ingestão
- **Botão Pipeline**: Executa `POST /api/pipeline`
- **Status**: Exibe estado (idle/processing/success/error)
- **Info Box**: Mostra `ID_Conta`, arquivo gerado e tabela após sucesso

#### 2. Seção de Chat
- **Chat Log**: Histórico de mensagens (user/bot/system)
- **Input Mensagem**: Textarea para pergunta
- **Botão Enviar**: Executa `POST /api/chat`
- **Botão Limpar**: Limpa histórico visual

**Fluxo de UX:**

1. Usuário digita URL
2. Clica "Executar Pipeline Completo"
3. Frontend desabilita botão e exibe "Executando pipeline..."
4. Chama `POST /api/pipeline`
5. Se sucesso:
   - Exibe `ID_Conta` e arquivo gerado
   - Habilita seção de chat
   - Armazena `ID_Conta` em variável local
6. Usuário pode enviar mensagens no chat
7. Cada mensagem envia `{ message, ID_Conta }` para `/api/chat`
8. Resposta do webhook aparece no chat

**Recursos de UI:**
- Design dark mode moderno
- Status visual com cores (azul=processing, verde=success, vermelho=error)
- Scroll automático do chat
- Tecla Enter envia mensagem (Shift+Enter quebra linha)
- Chat desabilitado até pipeline gerar `ID_Conta`

---

### `scrape_python/requirements.txt` (modificado)

**Dependências adicionadas:**

```txt
playwright==1.50.0       # Já existia (scraping fallback)
fastapi==0.115.6         # Framework web
uvicorn[standard]==0.34.0  # Servidor ASGI
httpx==0.28.1            # Cliente HTTP async para webhook
pydantic==2.12.5         # Validação de schemas
python-dotenv==1.2.1     # Gerenciamento de .env
```

**Dependências mantidas:**
- `beautifulsoup4`, `markdownify`, `requests` (scraping)

---

### `langchain/Agente_FAQ.py` (já alterado anteriormente)

**Modificação relevante para este fluxo:**

O script já foi atualizado para derivar `ID_Conta` do nome do arquivo markdown:

```python
def derive_id_conta(file_path: str) -> str:
    id_conta = Path(file_path).stem.strip()
    if not id_conta:
        raise ValueError("Não foi possível derivar ID_Conta do nome do arquivo.")
    return id_conta
```

**Compatibilidade perfeita:**
- Arquivo gerado: `exemplo-com-br_2026-02-11_a1b2c3d4.md`
- `ID_Conta` derivado: `exemplo-com-br_2026-02-11_a1b2c3d4`
- Inserido em **todas as rows** no Supabase (coluna `ID_Conta` + metadata)

---

## 3) Fluxo completo ponta a ponta

### Passo 1: Usuário digita URL no frontend

```
Frontend: https://exemplo.com.br
```

### Passo 2: Frontend chama API pipeline

```http
POST http://localhost:8000/api/pipeline
Content-Type: application/json

{
  "url": "https://exemplo.com.br",
  "table": "marketing_rag",
  "clear": false
}
```

### Passo 3: API executa scraping

```python
# api.py chama:
from scraper import processar, html_para_markdown

status, html = processar("https://exemplo.com.br")
# -> Tenta requests primeiro, fallback para playwright
```

**O que acontece no V3:**
- Tenta `scrape_request()` (rápido)
- Se falhar ou pouco conteúdo: usa `scrape_playwright()` (SPA support)
- Retorna HTML renderizado

### Passo 4: Conversão para markdown

```python
markdown = html_para_markdown(html)
```

### Passo 5: Salvamento com nome padronizado

```python
from scraper import salvar_markdown_nomeado

caminho_md, id_conta = salvar_markdown_nomeado(
    markdown, 
    "https://exemplo.com.br",
    pasta_destino="/langchain/uploads"
)

# Resultado:
# caminho_md = ".../langchain/uploads/exemplo-com-br_2026-02-11_a1b2c3d4.md"
# id_conta = "exemplo-com-br_2026-02-11_a1b2c3d4"
```

### Passo 6: Execução da ingestão FAQ

```python
import subprocess

result = subprocess.run([
    sys.executable,
    ".../langchain/Agente_FAQ.py",
    "--input", caminho_md,
    "--table", "marketing_rag"
], capture_output=True, text=True, timeout=300)
```

**O que acontece no `Agente_FAQ.py`:**
1. Deriva `ID_Conta` do nome do arquivo
2. Carrega markdown
3. Processa com LLM (Gemini 2.5 Flash) → FAQs estruturados
4. Gera embeddings (Gemini Embedding-001)
5. Insere no Supabase com `ID_Conta` em todas as rows

### Passo 7: API retorna sucesso ao frontend

```json
{
  "success": true,
  "message": "Pipeline completo executado com sucesso",
  "data": {
    "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4",
    "markdown_file": ".../exemplo-com-br_2026-02-11_a1b2c3d4.md",
    ...
  }
}
```

### Passo 8: Frontend habilita chat e armazena ID_Conta

```javascript
currentIdConta = data.data.ID_Conta;
chatInput.disabled = false;
sendChatButton.disabled = false;
```

### Passo 9: Usuário envia mensagem no chat

```
User: "Como funciona o sistema?"
```

### Passo 10: Frontend chama API chat

```http
POST http://localhost:8000/api/chat
Content-Type: application/json

{
  "message": "Como funciona o sistema?",
  "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4"
}
```

### Passo 11: API faz proxy para webhook N8N

```python
import httpx

response = await httpx.AsyncClient().post(
    "https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional",
    json={
        "message": "Como funciona o sistema?",
        "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4"
    }
)
```

### Passo 12: Webhook N8N processa e retorna

**O webhook N8N deve:**
1. Receber `{ message, ID_Conta }`
2. Fazer busca vetorial no Supabase **filtrando por `ID_Conta`**
3. Usar RAG com contexto filtrado
4. Gerar resposta com LLM
5. Retornar JSON (ex.: `{ "reply": "..." }`)

### Passo 13: API extrai resposta e retorna ao frontend

```python
reply = extrair_reply(response.json())
return {"success": True, "data": {"reply": reply, ...}}
```

### Passo 14: Frontend exibe no chat

```javascript
appendChatMessage('bot', reply);
```

---

## 4) Comandos para execução

### Instalar dependências

```bash
cd scrape_python
pip install -r requirements.txt
playwright install chromium  # Baixa navegador Chromium
```

### Rodar API

```bash
cd scrape_python
python api.py
```

Ou com uvicorn direto:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Acessar frontend

Abrir navegador em: `http://localhost:8000`

---

## 5) Diferenças vs implementação Node anterior

| Aspecto | Node/TypeScript | Python Atual |
|---------|-----------------|--------------|
| **Linguagem** | TypeScript + Express | Python + FastAPI |
| **Scraping** | Puppeteer (TS) | Requests + Playwright (PY) |
| **Upload** | Multipart form (Multer) | URL direta (sem upload) |
| **Nomeação** | Manual ou timestamp | Padrão `dominio_data_sufixo` |
| **Ingestão** | Subprocess Python | Subprocess Python (mesmo) |
| **Frontend** | Servido por Express | Servido por FastAPI |
| **Chat** | Proxy em TS | Proxy em Python (httpx async) |

**Vantagens da nova arquitetura:**
1. **Unificação**: Tudo em Python (scraping + API + ingestão)
2. **Consistência**: Mesmo ambiente para todo pipeline
3. **Manutenibilidade**: Menos tecnologias = menos complexidade
4. **Performance scraping**: V3 otimizado com fallback inteligente

---

## 6) Observações operacionais importantes

### Schema do Supabase

**Obrigatório**: A tabela `marketing_rag` deve ter a coluna literal `ID_Conta`.

```sql
ALTER TABLE marketing_rag ADD COLUMN "ID_Conta" TEXT;
CREATE INDEX idx_id_conta ON marketing_rag("ID_Conta");
```

### Filtragem no webhook N8N

**CRÍTICO**: O webhook N8N **deve filtrar** por `ID_Conta` ao buscar no Supabase:

```sql
SELECT * FROM marketing_rag
WHERE "ID_Conta" = '<id_conta_recebido>'
ORDER BY embedding <-> '<embedding_da_pergunta>'
LIMIT 4;
```

**Sem esse filtro**, o agente misturará contextos de clientes diferentes!

### Limite de scraping

V3 scrape **uma única página**. Para múltiplas páginas:
- Implementar crawler recursivo no V3
- Ou usar V4 se já tiver essa funcionalidade

### Timeout e retry

- **Pipeline**: 5 minutos max (ingestão pode ser lenta)
- **Chat**: 30 segundos max (webhook N8N)
- Sem retry automático (adicionar se necessário)

### Logs e debugging

API FastAPI gera logs automáticos. Para ver detalhes:

```bash
# Modo debug com reload
uvicorn api:app --reload --log-level debug
```

---

## 7) Próximos passos recomendados

1. **Criar coluna `ID_Conta` no Supabase** (se ainda não existir)
2. **Configurar webhook N8N** para filtrar por `ID_Conta`
3. **Testar pipeline completo** com URL real
4. **Validar chat** enviando perguntas e verificando contexto correto
5. **Adicionar autenticação** na API (se expor publicamente)
6. **Implementar rate limiting** para evitar abuso
7. **Adicionar logs estruturados** (ex.: com `structlog`)

---

## 8) Troubleshooting

### Erro: "Script de ingestão não encontrado"

**Causa**: Caminho do `Agente_FAQ.py` incorreto

**Solução**: Verificar constante `INGEST_SCRIPT` em `api.py`

### Erro: "Falha no scraping da página"

**Causa**: Site bloqueando requests ou problema no playwright

**Solução**:
1. Verificar se playwright instalou navegador: `playwright install chromium`
2. Testar URL manualmente: `python V3/scraper.py`

### Erro: "Timeout ao contatar webhook N8N"

**Causa**: Webhook lento ou indisponível

**Solução**:
1. Verificar URL do webhook
2. Testar com curl: `curl -X POST <webhook_url> -d '{"message":"teste","ID_Conta":"teste"}'`
3. Aumentar timeout em `api.py` se necessário

### Erro: "ID_Conta não preenchido no Supabase"

**Causa**: Coluna não existe ou script antigo

**Solução**:
1. Garantir que `Agente_FAQ.py` está atualizado (tem `derive_id_conta`)
2. Criar coluna no banco se necessário

---

**Versão:** 1.0  
**Data:** 11 de fevereiro de 2026  
**Autor:** Sistema de Ingestão FAQ
