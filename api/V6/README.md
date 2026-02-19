# Documentação da API de Raspagem (V6)

Esta API permite realizar raspagem de dados de páginas web de forma assíncrona. Ela foi construída utilizando **FastAPI**.

## Pré-requisitos e Instalação

1.  **Ativar o Ambiente Virtual**:
    Antes de rodar a API, certifique-se de ativar o ambiente virtual existente:
    ```bash
    .\venv\Scripts\activate
    ```

2.  **Instalar Dependências**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Rodar a API**:
    Para iniciar o servidor, execute o seguinte comando na pasta raiz (`V6`):
    ```bash
    python -m uvicorn api:app --reload
    ```
    Ou simplesmente:
    ```bash
    python api.py
    ```
    A API estará disponível em `http://127.0.0.1:8000`.

## Endpoints

### 1. Iniciar Raspagem de Página Única
- **Rota**: `/scrape/single`
- **Método**: `POST`
- **Corpo da Requisição**:
  ```json
  {
    "url": "https://exemplo.com"
  }
  ```
- **Resposta**: Retorna o ID do Job criado.
  ```json
  {
    "job_id": "uuid-do-job",
    "status": "PENDING"
  }
  ```

### 2. Iniciar Raspagem de Múltiplas Páginas
- **Rota**: `/scrape/multi`
- **Método**: `POST`
- **Corpo da Requisição**:
  ```json
  {
    "url": "https://exemplo.com"
  }
  ```
- **Resposta**: Retorna o ID do Job criado.
  ```json
  {
    "job_id": "uuid-do-job",
    "status": "PENDING"
  }
  ```

### 3. Verificar Status do Job
- **Rota**: `/job/{job_id}`
- **Método**: `GET`
- **Resposta**: Retorna o status atual e informações do job.
  ```json
  {
    "job_id": "uuid-do-job",
    "status": "COMPLETED",
    "created_at": "2024-05-20T10:00:00",
    "completed_at": "2024-05-20T10:05:00",
    "result": { ... },
    "error": null
  }
  ```
  Status possíveis: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`.

### 4. Obter Conteúdo do Job
- **Rota**: `/job/{job_id}/content`
- **Método**: `GET`
- **Resposta**: Retorna o conteúdo extraído.
    - Para **Single Scrape**, retorna um objeto com o markdown e metadados.
    - Para **Multi Scrape**, retorna uma lista com o conteúdo de cada página encontrada.

## Notas Adicionais

- **Arquivos Locais**: Os arquivos gerados pela raspagem continuam sendo salvos localmente na pasta de execução, mantendo o comportamento original dos scripts.
- **Swagger UI**: Você pode testar a API visualmente acessando `http://127.0.0.1:8000/docs`.


## Escopo do projeot
```
scraper_project/
│
├── extratores_informacoes/    # 1 - Extração de dados 
├── ferramentas/               # 2 - Ferramentas
├── modos/                     # 3 - Tipos de scraper 
├── resultados/                # Dados gerados
├── scrapers/                  # 4 - Formas de scrapper 
│
├── main.py                    # Arquivo de execução cmd (executa como script)
├── services.py                # Serviços de raspagem
├── api.py                     # API de raspagem (executa como api)
├── README_API.md              # Documentação da API
└── requirements.txt           # Arquivo de dependências
```
