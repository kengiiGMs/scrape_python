# =============================================================
#  INICIAR.ps1 - Inicializa API FastAPI + Frontend React
#  Execute com: .\INICIAR.ps1
# =============================================================

$ROOT = $PSScriptRoot
$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────

function Write-Header { param([string]$t) Write-Host "`n$('=' * 60)" -ForegroundColor Cyan; Write-Host "  $t" -ForegroundColor Cyan; Write-Host "$('=' * 60)`n" -ForegroundColor Cyan }
function Write-Ok { param([string]$m) Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn { param([string]$m) Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Write-Err { param([string]$m) Write-Host "  [X]  $m" -ForegroundColor Red }
function Write-Info { param([string]$m) Write-Host "  >>   $m" -ForegroundColor Gray }

# ── Verificar pré-requisitos ─────────────────────────────────

function Test-Prerequisites {
    Write-Header "Verificando pré-requisitos"

    if (Get-Command node -ErrorAction SilentlyContinue) {
        Write-Ok "Node.js $(node --version)"
    }
    else {
        Write-Err "Node.js não encontrado. Instale em https://nodejs.org"
        exit 1
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Ok "Python $(python --version 2>&1)"
    }
    else {
        Write-Err "Python não encontrado. Instale em https://python.org"
        exit 1
    }

    # .venv
    if (Test-Path "$ROOT\.venv\Scripts\Activate.ps1") {
        Write-Ok "Virtualenv .venv encontrado"
    }
    else {
        Write-Warn "Criando virtualenv .venv..."
        python -m venv "$ROOT\.venv"
        Write-Ok ".venv criado"
    }

    # Ativa .venv e verifica dependências Python
    & "$ROOT\.venv\Scripts\Activate.ps1"
    $pipCheck = pip show fastapi 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Instalando dependências Python..."
        if (Test-Path "$ROOT\api\V6\requirements.txt") {
            pip install -r "$ROOT\api\V6\requirements.txt" -q
        }
        if (Test-Path "$ROOT\langchain\requirements.txt") {
            pip install -r "$ROOT\langchain\requirements.txt" -q
        }
    }
    else {
        Write-Ok "Dependências Python ok"
    }

    # node_modules do front-react
    if (-not (Test-Path "$ROOT\front-react\node_modules")) {
        Write-Warn "Instalando dependências do frontend (npm install)..."
        Push-Location "$ROOT\front-react"
        npm install
        Pop-Location
    }
    else {
        Write-Ok "node_modules (front-react) ok"
    }

    # langchain/.env
    if (Test-Path "$ROOT\langchain\.env") {
        Write-Ok "langchain/.env encontrado (Supabase)"
    }
    else {
        Write-Err "langchain/.env NÃO encontrado! Configure SUPABASE_URL e SUPABASE_SERVICE_KEY."
        exit 1
    }
}

# ── Matar processos anteriores nas portas ────────────────────

function Stop-PortProcess {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if ($conn) {
        $pid = $conn.OwningProcess | Select-Object -First 1
        Write-Warn "Porta $Port ocupada (PID $pid). Encerrando..."
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

# ── Iniciar serviços ─────────────────────────────────────────

function Start-All {
    Write-Header "Liberando portas"
    Stop-PortProcess -Port 3000
    Stop-PortProcess -Port 5173

    Write-Header "Iniciando serviços"

    # API FastAPI (porta 3000)
    Write-Info "Iniciando API FastAPI (porta 3000)..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'API FastAPI - porta 3000'
    cd '$ROOT\api\V6'
    & '$ROOT\.venv\Scripts\Activate.ps1'
    `$env:PYTHONIOENCODING = 'utf-8'
    uvicorn api:app --host 0.0.0.0 --port 3000 --reload
"@ -WorkingDirectory "$ROOT\api\V6"

    Start-Sleep -Seconds 3

    # Frontend React/Vite (porta 5173)
    Write-Info "Iniciando Frontend React (porta 5173)..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'FRONT React - porta 5173'
    cd '$ROOT\front-react'
    npm run dev
"@ -WorkingDirectory "$ROOT\front-react"

    Start-Sleep -Seconds 3

    # Resumo
    Write-Header "Tudo rodando!"

    Write-Host "  API      -> " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Green
    Write-Host "  Frontend -> " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Endpoints:" -ForegroundColor Gray
    Write-Host "    POST /api/pipeline        - Pipeline completo (scrape + ingest)" -ForegroundColor Gray
    Write-Host "    GET  /api/pipelines       - Lista sites processados" -ForegroundColor Gray
    Write-Host "    POST /api/chat            - Chat via N8N" -ForegroundColor Gray
    Write-Host "    POST /api/ingest-markdown - Upload manual de .md" -ForegroundColor Gray
    Write-Host "    GET  /health              - Health check" -ForegroundColor Gray
    Write-Host "    GET  /docs                - Swagger da API" -ForegroundColor Gray
    Write-Host ""

    # Abrir no navegador
    Start-Process "http://localhost:5173"
    Write-Ok "Navegador aberto em http://localhost:5173"
    Write-Host ""
    Write-Host "  Pressione qualquer tecla para encerrar tudo..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

    # Encerrar tudo ao sair
    Write-Header "Encerrando serviços"
    Stop-PortProcess -Port 3000
    Stop-PortProcess -Port 5173
    Write-Ok "Serviços encerrados."
}

# ── Execução ─────────────────────────────────────────────────

Test-Prerequisites
Start-All
