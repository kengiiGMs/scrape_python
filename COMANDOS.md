## 🚀 Comandos para rodar o projeto

Este guia assume que você está na pasta raiz do projeto:

```powershell
cd "c:\Users\bucci\Quaestum\Scrape - Copia"
```

---

## 1. Preparar ambiente Python

```powershell
# Criar (se ainda não existir) e ativar o virtualenv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependências da API
pip install -r api\requirements.txt
```

Se você nunca usou o Playwright na máquina, rode também:

```powershell
playwright install
```

---

## 2. Subir a API Python (porta 3000)

A API oficial agora é a V6, que está em `api/V6`.

```powershell
cd "c:\Users\bucci\Quaestum\Scrape - Copia"
.\.venv\Scripts\Activate.ps1

cd api\V6
uvicorn api:app --reload --port 3000
```

A API ficará acessível em:

- `http://localhost:3000/health` – health check  
- `http://localhost:3000/docs` – Swagger UI (se habilitado pelo FastAPI)

---

## 3. Subir o Front (porta 8000)

O front é estático e fica na pasta `front`. Você pode usar o servidor HTTP embutido do Python:

```powershell
cd "c:\Users\bucci\Quaestum\Scrape - Copia"
python -m http.server 8000 --directory front
```

Depois acesse no navegador:

- `http://localhost:8000`

O front, por padrão, aponta para a API em `http://localhost:3000`.  
Se quiser mudar, basta alterar a URL diretamente no código ou (quando implementado) via UI.

---

## 4. Fluxos principais e exemplos de teste

### 4.1. Health check da API

```powershell
curl http://localhost:3000/health
```

Resposta esperada (exemplo):

```json
{
  "status": "ok",
  "timestamp": "2026-02-18T12:00:00",
  "service": "scrape_api_v6"
}
```

### 4.2. Scraping assíncrono (single)

Iniciar job:

```powershell
curl -X POST http://localhost:3000/scrape/single `
  -H "Content-Type: application/json" `
  -d '{ "url": "https://www.buenopolis.mg.gov.br" }'
```

Resposta (exemplo):

```json
{
  "job_id": "UUID",
  "status": "PENDING"
}
```

Consultar status:

```powershell
curl http://localhost:3000/job/SEU_JOB_ID
curl http://localhost:3000/job/SEU_JOB_ID/content
```

### 4.3. Pipeline completo (scrape + salvar markdown + ingestão)

```powershell
curl -X POST http://localhost:3000/api/pipeline `
  -H "Content-Type: application/json" `
  -d '{ "url": "https://www.buenopolis.mg.gov.br", "table": "marketing_rag", "clear": false }'
```

### 4.4. Ingestão via upload de Markdown

```powershell
curl -X POST http://localhost:3000/api/ingest-markdown `
  -F "markdownFile=@langchain\uploads\seu_arquivo.md" `
  -F "clear=false" `
  -F "table=marketing_rag"
```

### 4.5. Chat (via API)

```powershell
curl -X POST http://localhost:3000/api/chat `
  -H "Content-Type: application/json" `
  -d '{ "message": "Sobre o que você pode falar?", "ID_Conta": "buenopolis_web" }'
```

---

## 5. Resumo rápido

- **API (porta 3000)**  
  - `cd api\V6`  
  - `uvicorn api:app --reload --port 3000`

- **Front (porta 8000)**  
  - `python -m http.server 8000 --directory front`

- **Sequência típica de uso**  
  1. Subir a API.  
  2. Subir o front.  
  3. Acessar `http://localhost:8000`, escolher o `ID_Conta` e usar o chat / ingestão.

