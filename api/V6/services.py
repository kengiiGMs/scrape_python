import uuid
import logging
from datetime import datetime
from threading import Thread
import concurrent.futures
from typing import Dict, Any

# Importações dos módulos existentes
from modos.scrape_unico import processar_scrape_unico
from modos.scrape_completo import processar_scrape_completo
from ferramentas.converter import html_para_markdown
from ferramentas.nome_arquivo import gerar_nome_arquivo_da_url
from ferramentas.limpeza import limpar_markdown
from ferramentas.salvamento import salvar_arquivo_local

from schemas import JobStatus, JobResult

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, JobResult] = {} # Dicionário para armazenar os jobs
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5) # Executor para processar jobs em paralelo

    # Função para criar um novo job (devolve o id do job criado)
    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = JobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        return job_id

    # Função para obter um job (devolve o job encontrado)
    def get_job(self, job_id: str) -> JobResult:
        return self.jobs.get(job_id)

    # Função para atualizar o status de um job
    def update_job_status(self, job_id: str, status: JobStatus, result: Any = None, error: str = None):
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = status
            if result:
                job.result = result
            if error:
                job.error = error
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completed_at = datetime.now().isoformat()

    # Função para executar o scrape único (recebe o id do job e a url)
    def run_scrape_single(self, job_id: str, url: str):
        try:
            self.update_job_status(job_id, JobStatus.PROCESSING)
            logger.info(f"Iniciando scrape único para job {job_id} - URL: {url}")
            
            # Executa a função original
            status, html_processado, informacoes_da_pagina, nome_arquivo_gerado = processar_scrape_unico(url)

            if status and html_processado:
                markdown = html_para_markdown(html_processado)
                
                # Salva os arquivos (mantendo comportamento original de salvar localmente)
                salvar_arquivo_local(conteudo=markdown, nome_arquivo=nome_arquivo_gerado)
                salvar_arquivo_local(conteudo=informacoes_da_pagina, nome_arquivo=f"{nome_arquivo_gerado}_informacoes")

                result_data = {
                    "markdown": markdown,
                    "metadata": informacoes_da_pagina,
                    "saved_files": [
                        f"{nome_arquivo_gerado}.md",
                        f"{nome_arquivo_gerado}_informacoes.json" # Assumindo json ou txt dependendo da impl do salvar_arquivo_local
                    ]
                }
                self.update_job_status(job_id, JobStatus.COMPLETED, result=result_data)
            else:
                self.update_job_status(job_id, JobStatus.FAILED, error="Não foi possível raspar a página.")

        except Exception as e:
            logger.error(f"Erro no job {job_id}: {e}")
            self.update_job_status(job_id, JobStatus.FAILED, error=str(e))

    # Função para executar o scrape múltiplo (recebe o id do job e a url)
    def run_scrape_multi(self, job_id: str, url: str):
        try:
            self.update_job_status(job_id, JobStatus.PROCESSING)
            logger.info(f"Iniciando scrape múltiplo para job {job_id} - URL: {url}")

            status, html_processado = processar_scrape_completo(url)

            if status and html_processado:
                markdown_list = []
                conteudo_completo = ""

                for paginas_html in html_processado:
                    if paginas_html['status'] == True:
                        conteudo_bruto = html_para_markdown(paginas_html['html'])
                        conteudo_pagina = limpar_markdown(conteudo_bruto)
                        
                        item = {
                            "link": paginas_html['link'], 
                            "conteudo": conteudo_pagina, 
                        }
                        markdown_list.append(item)

                        # Monta string pro arquivo completo
                        conteudo_completo += f"\n{'='*40}\n"
                        conteudo_completo += f"TÍTULO: {item['link']['texto']}\n"
                        conteudo_completo += f"{'='*40}\n\n"
                        conteudo_completo += "--- CONTEÚDO PRINCIPAL IDENTIFICADO ---\n\n"
                        conteudo_completo += str(item['conteudo']) + "\n\n"

                # Salva o arquivo consolidado
                nome_arquivo_unico = f"{gerar_nome_arquivo_da_url(url)}_relatorio_completo"
                salvar_arquivo_local(conteudo=conteudo_completo, nome_arquivo=nome_arquivo_unico)

                result_data = {
                    "content": markdown_list, # Lista estruturada
                    "full_report": conteudo_completo, # String única
                    "saved_files": [f"{nome_arquivo_unico}.md"]
                }
                self.update_job_status(job_id, JobStatus.COMPLETED, result=result_data)
            else:
                 self.update_job_status(job_id, JobStatus.FAILED, error="Não foi possível raspar as páginas.")

        except Exception as e:
            logger.error(f"Erro no job {job_id}: {e}")
            self.update_job_status(job_id, JobStatus.FAILED, error=str(e))

    # Função para iniciar o scrape único (recebe a url)
    def start_single_scrape_job(self, url: str) -> str:
        job_id = self.create_job()
        self.executor.submit(self.run_scrape_single, job_id, url)
        return job_id

    # Função para iniciar o scrape múltiplo (recebe a url)
    def start_multi_scrape_job(self, url: str) -> str:
        job_id = self.create_job()
        self.executor.submit(self.run_scrape_multi, job_id, url)
        return job_id

# Instância global do gerenciador (criado apenas uma vez, e no decorrer de toda aplicação é usado apenas seus métodos garantindo um estado absoluto dos jobs)
job_manager = JobManager()
