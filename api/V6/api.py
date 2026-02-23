import os
import sys
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

from schemas import ScrapeRequest, JobResponse, JobResult, ContentResponse, JobStatus
from services import job_manager

# ---------------------------------------------------------------------------
# Configuração de caminhos e ambiente
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LANGCHAIN_DIR = ROOT_DIR / "langchain"
UPLOAD_DIR = LANGCHAIN_DIR / "uploads"
INGEST_SCRIPT = LANGCHAIN_DIR / "Agente_FAQ.py"
PYTHON_BIN = sys.executable

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Carrega variáveis do .env do langchain
load_dotenv(dotenv_path=str(LANGCHAIN_DIR / ".env"))

WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL",
    "https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional",
)
SUPABASE_URL = os.getenv("SUPABASE_URL") or ""
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or ""

PORT = int(os.getenv("PORT", "3000"))

# Origens permitidas: inclui o Vite dev (5173), o antigo front (8080)
# e qualquer origem extra definida via FRONT_ORIGIN no .env
_extra_origin = os.getenv("FRONT_ORIGIN", "")
ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite/React (dev)
    "http://localhost:5174",   # Vite fallback
    "http://localhost:8080",   # front legado
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]
if _extra_origin and _extra_origin not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(_extra_origin)


class ChatRequest(BaseModel):
    message: str
    ID_Conta: str


class ChatResponse(BaseModel):
    success: bool
    data: dict


class IngestResponse(BaseModel):
    success: bool
    message: str
    data: dict


app = FastAPI(
    title="API de Raspagem de Dados",
    description="API para realizar raspagem de páginas web de forma assíncrona, ingestão de markdown e chat via webhook.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def sanitize_id_conta(name: str) -> str:
    """
    Deriva um ID_Conta seguro a partir de um nome de arquivo ou slug.
    """
    stem = Path(name).stem
    sanitized = (
        stem.replace(" ", "_")
        .replace("-", "_")
        .strip()
    )
    sanitized = "".join(ch for ch in sanitized if ch.isalnum() or ch in {"_", "-"})
    if not sanitized:
        raise ValueError("Nome inválido para derivar ID_Conta.")
    return sanitized


def executar_ingestao(input_path: str, table: str, clear: bool) -> dict:
    """
    Executa o script Agente_FAQ.py e captura o resultado.
    """
    if not INGEST_SCRIPT.exists():
        raise RuntimeError(f"Script de ingestão não encontrado: {INGEST_SCRIPT}")

    args = [
        PYTHON_BIN,
        str(INGEST_SCRIPT),
        "--input",
        str(input_path),
        "--table",
        table,
    ]
    if clear:
        args.append("--clear")

    # Garante UTF-8 no subprocess independente do locale do Windows (evita UnicodeEncodeError)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        args,
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Ingestão falhou com código {result.returncode}. "
            f"Detalhes: {result.stderr or result.stdout}"
        )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def extrair_reply(data) -> str:
    """
    Tenta extrair texto útil de resposta JSON do webhook.
    """
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return "\n".join(extrair_reply(item) for item in data).strip()
    if not isinstance(data, dict):
        return str(data)

    for key in ["reply", "response", "answer", "message", "output", "text"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return str(data)


# ---------------------------------------------------------------------------
# Endpoints de scraping (mantidos)
# ---------------------------------------------------------------------------

@app.post("/scrape/single", response_model=JobResponse, status_code=202)
def scrape_single(request: ScrapeRequest):
    """
    Inicia o processo de raspagem de uma única página.
    """
    job_id = job_manager.start_single_scrape_job(request.url)
    return JobResponse(job_id=job_id, status=JobStatus.PENDING)


@app.post("/scrape/multi", response_model=JobResponse, status_code=202)
def scrape_multi(request: ScrapeRequest):
    """
    Inicia o processo de raspagem de múltiplas páginas a partir de uma URL inicial.
    """
    job_id = job_manager.start_multi_scrape_job(request.url)
    return JobResponse(job_id=job_id, status=JobStatus.PENDING)


@app.get("/job/{job_id}", response_model=JobResult)
def get_job_status(job_id: str):
    """
    Retorna o status atual de um job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@app.get("/job/{job_id}/content", response_model=ContentResponse)
def get_job_content(job_id: str):
    """
    Retorna o conteúdo extraído pelo job (se concluído).
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Job ainda não foi concluído ou falhou.",
        )

    if not job.result:
        raise HTTPException(
            status_code=500,
            detail="Job concluído mas sem resultado.",
        )

    # Para scrape único, retornamos markdown e metadados
    if "markdown" in job.result:
        return ContentResponse(
            job_id=job_id,
            content={
                "markdown": job.result["markdown"],
                "metadata": job.result.get("metadata"),
            },
        )
    # Para scrape múltiplo, retornamos a lista de conteúdos
    if "content" in job.result:
        return ContentResponse(job_id=job_id, content=job.result["content"])

    # Fallback
    return ContentResponse(job_id=job_id, content=job.result)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "scrape_api_v6",
    }


# ---------------------------------------------------------------------------
# Chat (proxy para webhook N8N)
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        payload = {"message": request.message, "ID_Conta": request.ID_Conta}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Webhook retornou erro: {response.text}",
            )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            raw_data = response.json()
            reply = extrair_reply(raw_data)
        else:
            raw_data = response.text
            reply = raw_data

        return ChatResponse(
            success=True,
            data={"reply": reply, "raw": raw_data, "ID_Conta": request.ID_Conta},
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Timeout ao contatar webhook N8N",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Pipeline completo: scrape URL → salva markdown → ingere no Supabase
# ---------------------------------------------------------------------------

class PipelineRequest(BaseModel):
    url: str
    table: str = "marketing_rag"
    clear: bool = False


@app.post("/api/pipeline", response_model=IngestResponse)
async def run_pipeline(request: PipelineRequest):
    """
    Pipeline completo chamado pelo frontend:
    1. Dispara o scrape da URL
    2. Aguarda a conclusão do job de scrape
    3. Salva o markdown resultante em disco
    4. Executa a ingestão (Agente_FAQ.py) no Supabase
    """
    try:
        # 1. Inicia o job de scrape (multi para cobrir todo o site)
        job_id = job_manager.start_multi_scrape_job(request.url)

        # 2. Aguarda conclusão (polling com timeout de 5 minutos)
        timeout_s = 300
        poll_interval = 2
        elapsed = 0
        while elapsed < timeout_s:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            job = job_manager.get_job(job_id)
            if job is None:
                raise HTTPException(status_code=500, detail="Job de scrape não encontrado")
            if job.status == JobStatus.FAILED:
                raise HTTPException(
                    status_code=500,
                    detail=f"Scrape falhou: {job.error or 'erro desconhecido'}",
                )
            if job.status == JobStatus.COMPLETED:
                break
        else:
            raise HTTPException(status_code=504, detail="Timeout aguardando scrape")

        # 3. Monta o markdown consolidado a partir do resultado do job
        result = job.result or {}
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc.replace("www.", "").replace(".", "_").replace("-", "_")
        id_conta = domain or "site"
        target_path = UPLOAD_DIR / f"{id_conta}.md"

        if "full_report" in result:
            # Scrape multi já traz o relatório consolidado
            target_path.write_text(result["full_report"], encoding="utf-8")
        elif "markdown" in result:
            # Scrape único
            target_path.write_text(result["markdown"], encoding="utf-8")
        else:
            raise HTTPException(
                status_code=500,
                detail="Scrape concluído mas sem conteúdo Markdown para ingerir",
            )

        # 4. Executa a ingestão
        ingest_result = executar_ingestao(str(target_path), request.table, request.clear)

        return IngestResponse(
            success=True,
            message="Pipeline concluído com sucesso",
            data={
                "ID_Conta": id_conta,
                "filePath": str(target_path),
                "table": request.table,
                "clear": request.clear,
                "scrape_job_id": job_id,
                "output": ingest_result,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Ingestão de Markdown (upload direto de arquivo)
# ---------------------------------------------------------------------------

@app.post("/api/ingest-markdown", response_model=IngestResponse)
async def ingest_markdown(
    markdownFile: UploadFile = File(...),
    clear: Optional[str] = Form("false"),
    table: str = Form("marketing_rag"),
):
    try:
        filename = markdownFile.filename or "arquivo.md"
        id_conta = sanitize_id_conta(filename)
        target_path = UPLOAD_DIR / f"{id_conta}.md"

        content = await markdownFile.read()
        target_path.write_bytes(content)

        clear_flag = str(clear or "").lower() == "true"
        ingest_result = executar_ingestao(str(target_path), table, clear_flag)

        return IngestResponse(
            success=True,
            message="Ingestão concluída com sucesso",
            data={
                "ID_Conta": id_conta,
                "filePath": str(target_path),
                "table": table,
                "clear": clear_flag,
                "output": ingest_result,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Pipelines (Supabase / RAG)
# ---------------------------------------------------------------------------

@app.get("/api/pipelines")
def list_pipelines():
    """
    Lista todos os pipelines já executados (ID_Conta únicos do Supabase).
    """
    try:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise HTTPException(
                status_code=500,
                detail="Credenciais Supabase não configuradas",
            )

        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = (
            supabase.table("marketing_rag")
            .select("ID_Conta, metadata")
            .execute()
        )

        if not result.data:
            return {"success": True, "data": []}

        pipelines_map = {}
        for row in result.data:
            id_conta = row.get("ID_Conta")
            if id_conta and id_conta not in pipelines_map:
                domain_parts = (
                    id_conta.split("_")[0] if "_" in id_conta else id_conta
                )
                url_inferido = domain_parts.replace("-", ".")
                pipelines_map[id_conta] = {
                    "ID_Conta": id_conta,
                    "url_inferido": (
                        f"https://{url_inferido}"
                        if not url_inferido.startswith("http")
                        else url_inferido
                    ),
                    "total_faqs": 0,
                }

        for row in result.data:
            id_conta = row.get("ID_Conta")
            if id_conta in pipelines_map:
                pipelines_map[id_conta]["total_faqs"] += 1

        pipelines_list = list(pipelines_map.values())
        return {"success": True, "data": pipelines_list}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
