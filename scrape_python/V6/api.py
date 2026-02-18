from fastapi import FastAPI, HTTPException, BackgroundTasks
from schemas import ScrapeRequest, JobResponse, JobResult, ContentResponse, JobStatus
from services import job_manager

app = FastAPI(
    title="API de Raspagem de Dados",
    description="API para realizar raspagem de páginas web de forma assíncrona.",
    version="1.0.0"
)

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
        raise HTTPException(status_code=400, detail="Job ainda não foi concluído ou falhou.")
    
    if not job.result:
        raise HTTPException(status_code=500, detail="Job concluído mas sem resultado.")

    # Para scrape único, retornamos markdown e metadados
    if "markdown" in job.result:
        return ContentResponse(job_id=job_id, content={
            "markdown": job.result["markdown"],
            "metadata": job.result.get("metadata")
        })
    # Para scrape múltiplo, retornamos a lista de conteúdos
    elif "content" in job.result:
        return ContentResponse(job_id=job_id, content=job.result["content"])
    
    # Fallback
    return ContentResponse(job_id=job_id, content=job.result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
