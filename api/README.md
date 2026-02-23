# 🕷️ API Python - Scrape & FAQ Agent

Sistema unificado em Python com pipeline automático de scraping, geração de markdown, ingestão FAQ com LangChain e chat via webhook N8N.

## 📋 Funcionalidades

- **Scraping inteligente** (página única) com fallback Requests → Playwright
- **Pipeline automático**: URL → Markdown → Ingestão FAQ → Chat
- **ID_Conta único** por arquivo (formato: `dominio_YYYY-MM-DD_sufixo`)
- **API REST** com FastAPI
- **Frontend HTML** simples e funcional
- **Chat integrado** com proxy para webhook N8N

## 🚀 Início rápido

### 1. Criar e ativar ambiente virtual

```bash
# Criar venv
python -m venv venv

# Ativar no Windowshttps://chacarawanderlust.com.br/
venv\Scripts\activate

# Ativar no Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt

# Baixar navegador Chromium para Playwright
playwright install chromium
```

### 3. Configurar variáveis de ambiente

Criar arquivo `.env` na raiz do projeto com:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=sua_chave_service
GOOGLE_API_KEY=sua_chave_google_ai
```

### 4. Rodar API

```bash
<<<<<<< HEAD
python api.py
```

Ou com uvicorn:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Acessar frontend

Abrir navegador em: `http://localhost:8000`

## 📡 Endpoints da API

### `GET /`
Serve o frontend HTML

### `GET /health`
Health check

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-11T15:30:00",
  "service": "Scrape & FAQ API"
}
```

### `POST /api/scrape`
Scraping de página única (apenas teste, não salva)

**Request:**
```json
{
  "url": "https://exemplo.com.br"
}
```

**Response:**
```json
{
  "success": true,
  "url": "https://exemplo.com.br",
  "markdown_preview": "# Título...",
  "length": 15234
}
```

### `POST /api/pipeline`
Pipeline completo: scraping → markdown → ingestão FAQ

**Request:**
```json
{
  "url": "https://exemplo.com.br",
  "table": "marketing_rag",
  "clear": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Pipeline completo executado com sucesso",
  "data": {
    "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4",
    "markdown_file": ".../exemplo-com-br_2026-02-11_a1b2c3d4.md",
    "table": "marketing_rag",
    "ingest_output": { ... }
  }
}
```

### `POST /api/chat`
Chat com proxy para webhook N8N

**Request:**
```json
{
  "message": "Como funciona?",
  "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reply": "Resposta do webhook",
    "raw": { ... },
    "ID_Conta": "exemplo-com-br_2026-02-11_a1b2c3d4"
  }
}
```

## 📁 Estrutura do projeto

```
scrape_python/
├── api.py                    # API FastAPI principal
├── requirements.txt          # Dependências Python
├── public/
│   └── index.html           # Frontend
├── V3/
│   └── scraper.py           # Motor de scraping
└── V4/
    └── extrair_informacoes.py

langchain/
├── Agente_FAQ.py            # Script de ingestão FAQ
├── models.py                # Schemas Pydantic
└── uploads/                 # Markdowns gerados (com ID_Conta)
```

## ⚙️ Configuração avançada

### Variável de ambiente `PYTHON_BIN`

Se usar Python customizado:

```bash
export PYTHON_BIN=/caminho/para/python3
python api.py
```

### Webhook N8N customizado

Editar em `api.py`:

```python
WEBHOOK_URL = 'https://seu-webhook.com/endpoint'
```

## 🐛 Troubleshooting

Ver documentação completa em: `tes/EXPLICACAO_API_SCRAPE_V3_PIPELINE.md`

## 📚 Documentação adicional

- `tes/EXPLICACAO_API_SCRAPE_V3_PIPELINE.md` - Fluxo completo
- `tes/EXPLICACAO_AGENTE_FAQ.md` - Sistema de ingestão FAQ
- `tes/explicacao_ingest_faq.md` - Detalhes do RAG

## 🔧 Scripts úteis

```bash
# Testar scraper V3 isolado
python V3/scraper.py

# Testar ingestão FAQ direta
python ../langchain/Agente_FAQ.py --input arquivo.md --table marketing_rag
```
=======
playwright codegen https://www.site.com
```



transformar em api

https://www.quaestum.com.br/

remover espaços do scrappe
>>>>>>> 1ee3df8ef389d6de73bc9c246cefd0f5818a0816
