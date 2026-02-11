"""
API FastAPI para scraping, ingestão FAQ e chat com webhook N8N
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl, Field
from dotenv import load_dotenv

# Importa funções do scraper V3
sys.path.insert(0, str(Path(__file__).parent / 'V3'))
from scraper import processar, html_para_markdown, salvar_markdown_nomeado

app = FastAPI(title="Scrape & FAQ API", version="1.0.0")

# Configurações
ROOT_DIR = Path(__file__).parent.parent
LANGCHAIN_DIR = ROOT_DIR / 'langchain'
UPLOAD_DIR = LANGCHAIN_DIR / 'uploads'
INGEST_SCRIPT = LANGCHAIN_DIR / 'Agente_FAQ.py'
PUBLIC_DIR = Path(__file__).parent / 'public'
PYTHON_BIN = sys.executable

# Carregar variáveis do .env
load_dotenv(dotenv_path=str(LANGCHAIN_DIR / '.env'))

# URL do webhook N8N (carregada do .env)
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://auto-serv-teste.grupoquaestum.com/webhook/marketing_conversacional')

# Garante que diretórios existem
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# Servir frontend estático
app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")


# Schemas Pydantic
class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL da página para scraping")


class PipelineRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL da página para scraping")
    table: str = Field(default="marketing_rag", description="Nome da tabela Supabase")
    clear: bool = Field(default=False, description="Limpar tabela antes da ingestão")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Mensagem do usuário")
    ID_Conta: str = Field(..., min_length=1, description="Identificador da conta")


class ScrapeResponse(BaseModel):
    success: bool
    url: str
    markdown_preview: str
    length: int


class PipelineResponse(BaseModel):
    success: bool
    message: str
    data: dict


class ChatResponse(BaseModel):
    success: bool
    data: dict


@app.get("/")
async def root():
    """Serve o frontend HTML"""
    return FileResponse(PUBLIC_DIR / 'index.html')


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "Scrape & FAQ API"
    }


@app.get("/api/pipelines")
async def list_pipelines():
    """
    Lista todos os pipelines já executados (ID_Conta únicos do Supabase)
    """
    try:
        from dotenv import load_dotenv
        from supabase import create_client
        
        load_dotenv(dotenv_path=str(LANGCHAIN_DIR / '.env'))
        
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Credenciais Supabase não configuradas"
            )
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Busca ID_Conta únicos e metadados da primeira row de cada
        result = supabase.table("marketing_rag") \
            .select("ID_Conta, metadata") \
            .execute()
        
        if not result.data:
            return {"success": True, "data": []}
        
        # Agrupa por ID_Conta e pega info da primeira row
        pipelines_map = {}
        for row in result.data:
            id_conta = row.get("ID_Conta")
            if id_conta and id_conta not in pipelines_map:
                metadata = row.get("metadata", {})
                # Tenta extrair URL original do ID_Conta
                domain_parts = id_conta.split('_')[0] if '_' in id_conta else id_conta
                url_inferido = domain_parts.replace('-', '.')
                
                pipelines_map[id_conta] = {
                    "ID_Conta": id_conta,
                    "url_inferido": f"https://{url_inferido}" if not url_inferido.startswith('http') else url_inferido,
                    "total_faqs": 0  # Será contado abaixo
                }
        
        # Conta FAQs por ID_Conta
        for row in result.data:
            id_conta = row.get("ID_Conta")
            if id_conta in pipelines_map:
                pipelines_map[id_conta]["total_faqs"] += 1
        
        pipelines_list = list(pipelines_map.values())
        
        return {
            "success": True,
            "data": pipelines_list
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):
    """
    Endpoint para scraping de uma única página
    Retorna o markdown gerado mas NÃO salva ou processa
    """
    try:
        url_str = str(request.url)
        print(f"[SCRAPE] URL: {url_str}")
        
        status, html = processar(url_str)
        
        if not status or not html:
            raise HTTPException(
                status_code=500,
                detail="Falha ao fazer scraping da página. Tente outra URL."
            )
        
        markdown = html_para_markdown(html)
        
        return ScrapeResponse(
            success=True,
            url=url_str,
            markdown_preview=markdown[:500],
            length=len(markdown)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline", response_model=PipelineResponse)
async def pipeline_endpoint(request: PipelineRequest):
    """
    Pipeline completo: scraping -> salvar markdown -> ingestão FAQ
    """
    try:
        url_str = str(request.url)
        print(f"\n{'='*60}")
        print(f"INICIANDO PIPELINE COMPLETO")
        print(f"{'='*60}")
        print(f"URL: {url_str}")
        print(f"Tabela: {request.table}")
        print(f"Clear: {request.clear}")
        
        # 1. Scraping
        print("\n[1/3] Executando scraping...")
        status, html = processar(url_str)
        
        if not status or not html:
            raise HTTPException(
                status_code=500,
                detail="Falha no scraping da página"
            )
        
        print("[OK] Scraping concluido")
        
        # 2. Converter e salvar markdown
        print("\n[2/3] Convertendo para markdown e salvando...")
        markdown = html_para_markdown(html)
        
        caminho_md, id_conta = salvar_markdown_nomeado(
            markdown, 
            url_str, 
            pasta_destino=str(UPLOAD_DIR)
        )
        
        print(f"[OK] Markdown salvo: {caminho_md}")
        print(f"[OK] ID_Conta derivado: {id_conta}")
        
        # 3. Executar ingestão FAQ
        print("\n[3/3] Executando ingestao FAQ...")
        ingest_result = executar_ingestao(
            input_path=caminho_md,
            table=request.table,
            clear=request.clear
        )
        
        print("[OK] Ingestao concluida")
        print(f"{'='*60}\n")
        
        return PipelineResponse(
            success=True,
            message="Pipeline completo executado com sucesso",
            data={
                "url": url_str,
                "ID_Conta": id_conta,
                "markdown_file": caminho_md,
                "markdown_length": len(markdown),
                "table": request.table,
                "clear": request.clear,
                "ingest_output": ingest_result
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERRO] Pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Proxy de chat para webhook N8N
    """
    try:
        payload = {
            "message": request.message,
            "ID_Conta": request.ID_Conta
        }
        
        print(f"\n[CHAT] Msg: {request.message[:50]}...")
        print(f"[CHAT] ID_Conta: {request.ID_Conta}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Webhook retornou erro: {response.text}"
                )
            
            # Tenta extrair resposta útil
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                raw_data = response.json()
                reply = extrair_reply(raw_data)
            else:
                raw_data = response.text
                reply = raw_data
            
            return ChatResponse(
                success=True,
                data={
                    "reply": reply,
                    "raw": raw_data,
                    "ID_Conta": request.ID_Conta
                }
            )
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout ao contatar webhook N8N")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def executar_ingestao(input_path: str, table: str, clear: bool) -> dict:
    """
    Executa o script Agente_FAQ.py e captura o resultado
    """
    if not Path(INGEST_SCRIPT).exists():
        raise FileNotFoundError(f"Script de ingestão não encontrado: {INGEST_SCRIPT}")
    
    args = [
        PYTHON_BIN,
        str(INGEST_SCRIPT),
        '--input', input_path,
        '--table', table
    ]
    
    if clear:
        args.append('--clear')
    
    print(f"   Executando: {' '.join(args)}")
    
    try:
        result = subprocess.run(
            args,
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos max
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Ingestão falhou (código {result.returncode}). "
                f"Detalhes: {result.stderr or result.stdout}"
            )
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    
    except subprocess.TimeoutExpired:
        raise RuntimeError("Ingestão excedeu tempo limite de 5 minutos")


def extrair_reply(data) -> str:
    """
    Tenta extrair texto útil de resposta JSON do webhook
    """
    if isinstance(data, str):
        return data
    
    if isinstance(data, list):
        return '\n'.join(extrair_reply(item) for item in data).strip()
    
    if not isinstance(data, dict):
        return str(data)
    
    # Chaves comuns de resposta
    for key in ['reply', 'response', 'answer', 'message', 'output', 'text']:
        if key in data and isinstance(data[key], str) and data[key].strip():
            return data[key]
    
    return str(data)


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("INICIANDO API SCRAPE & FAQ")
    print("="*60)
    print(f"Diretorio uploads: {UPLOAD_DIR}")
    print(f"Diretorio publico: {PUBLIC_DIR}")
    print(f"Webhook N8N: {WEBHOOK_URL}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
