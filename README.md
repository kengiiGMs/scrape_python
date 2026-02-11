# 🕷️ Web Scraper Institucional

Sistema de scraping inteligente para extrair informações institucionais e de contato de websites, com suporte para SPAs (Single Page Applications) e geração automática de documentação em Markdown.

## 📋 Índice

- [Características](#características)
- [Tecnologias](#tecnologias)
- [Instalação](#instalação)
- [Uso](#uso)
  - [API Server](#api-server)
  - [CLI](#cli)
- [Endpoints da API](#endpoints-da-api)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Configuração](#configuração)
- [Output](#output)
- [Exemplos](#exemplos)

## ✨ Características

- **Scraping Inteligente**: Detecta e navega automaticamente por páginas institucionais (sobre, contato, políticas, etc.)
- **Suporte a SPAs**: Otimizado para React, Vue e outros frameworks modernos usando Puppeteer
- **Extração de Contatos**: Captura emails, telefones, redes sociais e endereços automaticamente
- **Geração de Markdown**: Converte todo o conteúdo extraído em documentos Markdown organizados
- **API Assíncrona**: Processamento em background com sistema de jobs e consulta de status
- **CLI Standalone**: Execute scraping diretamente via linha de comando
- **Filtros Avançados**: Evita páginas de produtos e foca em conteúdo institucional

## 🛠️ Tecnologias

- **Node.js** + **TypeScript**
- **Express** - API REST
- **Puppeteer** - Automação de navegador e scraping de SPAs
- **Cheerio** - Parse e manipulação de HTML
- **Turndown** - Conversão de HTML para Markdown
- **Zod** - Validação de schemas

## 📦 Instalação

```bash
# Clone o repositório
git clone <seu-repositorio>
cd web-scraper

# Instale as dependências
yarn install

# Configure o Chrome/Chromium (se necessário)
# O Puppeteer irá baixar automaticamente, mas você pode configurar o caminho:
export PUPPETEER_CACHE_DIR=/caminho/para/chrome
```

## 🚀 Uso

### API Server

Inicie o servidor da API:

```bash
# Modo desenvolvimento (com hot-reload)
yarn dev

# Modo produção
yarn start
```

O servidor será iniciado em `http://localhost:3000`

### CLI

Execute scraping diretamente via linha de comando:

```bash
yarn tsx cli.ts https://www.exemplo.com.br

```

## 📡 Endpoints da API

### POST /scrape

Inicia um processo de scraping assíncrono.

**Request:**
```json
{
  "url": "https://www.exemplo.com.br",
  "options": {
    "timeout": 30000,
    "waitUntil": "networkidle2"
  }
}
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "statusUrl": "http://localhost:3000/status/550e8400-e29b-41d4-a716-446655440000",
  "message": "Scraping iniciado. Use o statusUrl para acompanhar."
}
```

### GET /status/:jobId

Consulta o status de um job de scraping.

**Response (Processando):**
```json
{
  "status": "processing",
  "url": "https://www.exemplo.com.br",
  "elapsed": "3.45s"
}
```

**Response (Concluído):**
```json
{
  "status": "completed",
  "duration": "12.34s",
  "data": {
    "url": "https://www.exemplo.com.br",
    "markdownFile": "/caminho/para/outputs/exemplo-com-br_2026-02-06_550e8400.md",
    "stats": {
      "pagesScraped": 8,
      "totalInstitutional": 5
    },
    "metadata": {
      "title": "Exemplo Loja",
      "description": "Descrição do site",
      "siteName": "Exemplo"
    },
    "contactInfo": {
      "emails": ["contato@exemplo.com.br"],
      "phones": ["(11) 98765-4321"],
      "socialMedia": {
        "instagram": "https://instagram.com/exemplo",
        "facebook": "https://facebook.com/exemplo"
      },
      "addresses": []
    },
    "storeInfo": {
      "name": "Exemplo Loja Ltda",
      "cnpj": "12.345.678/0001-90"
    }
  }
}
```

**Response (Falhou):**
```json
{
  "status": "failed",
  "error": "Timeout ao acessar a página"
}
```

### GET /health

Health check da API.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-06T17:35:00.000Z",
  "activeJobs": 3
}
```

## 📁 Estrutura do Projeto

```
web-scraper/
├── index.ts                 # API Server Express
├── cli.ts                   # Script CLI standalone
├── scraper.service.ts       # Serviço principal de scraping
├── markdown-generator.ts    # Gerador de documentos Markdown
├── types.ts                 # Interfaces TypeScript
├── outputs/                 # Arquivos Markdown gerados
│   └── exemplo-com-br_2026-02-06_550e8400.md
├── package.json
├── tsconfig.json
└── README.md
```

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# Porta do servidor (padrão: 3000)
PORT=3000

# Caminho do executável do Chrome (opcional)
PUPPETEER_CACHE_DIR=/usr/bin/google-chrome-stable
```

### Opções de Scraping

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `timeout` | number | 30000 | Timeout em ms para cada página |
| `waitUntil` | string | 'networkidle2' | Condição de espera: 'load', 'domcontentloaded', 'networkidle0', 'networkidle2' |

### Limites e Filtros

- **Profundidade máxima**: 12 páginas institucionais por site
- **Timeout de jobs**: Jobs são removidos da fila após 1 hora de conclusão
- **Filtros de conteúdo**: Exclui automaticamente páginas de produtos, carrinho e checkout

## 📄 Output

Os arquivos Markdown gerados seguem esta estrutura:

```markdown
# Nome da Loja

**Site:** https://www.exemplo.com.br
**Descrição:** Descrição do site
**Nome da Empresa:** Exemplo Loja Ltda
**Data da Coleta:** 06/02/2026

---

## 📞 Informações de Contato

**Emails:**
- contato@exemplo.com.br
- vendas@exemplo.com.br

**Telefones:**
- (11) 98765-4321
- (11) 3456-7890

**Redes Sociais:**
- WhatsApp: https://wa.me/5511987654321
- Instagram: https://instagram.com/exemplo
- Facebook: https://facebook.com/exemplo

---

## 🏢 Dados da Empresa

**Nome:** Exemplo Loja Ltda
**CNPJ:** 12.345.678/0001-90

---

## 📄 Conteúdo Institucional

### Sobre Nós

[Conteúdo da página sobre...]

### Política de Privacidade

[Conteúdo da página de política...]
```

## 💡 Exemplos

### Exemplo 1: Uso da API

```bash
# 1. Inicia o scraping
curl -X POST http://localhost:3000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.loja-exemplo.com.br"}'

# Resposta:
# {
#   "jobId": "abc-123",
#   "statusUrl": "http://localhost:3000/status/abc-123"
# }

# 2. Consulta o status
curl http://localhost:3000/status/abc-123

# 3. Quando concluído, o arquivo markdown estará em outputs/
```

### Exemplo 2: Uso do CLI

```bash
# Scraping simples
yarn run cli https://www.loja-exemplo.com.br

# Output no terminal:
# ============================================================
# ✅ SCRAPING CONCLUÍDO EM 15.32s
# ============================================================
# 
# 📊 Resumo:
#    📄 Páginas processadas: 10
#    📋 Páginas institucionais: 6
#    📧 Emails encontrados: 2
#    📞 Telefones encontrados: 3
#    🌐 Redes sociais: 4
#    📄 Markdown salvo em: outputs/loja-exemplo-com-br_2026-02-06_cli-1738869300123.md
# ============================================================
```

### Exemplo 3: Integração com TypeScript

```typescript
import { scraperService } from './scraper.service.js';
import { MarkdownGenerator } from './markdown-generator.js';

async function meuScraper() {
  const result = await scraperService.scrapeUrl('https://exemplo.com', {
    timeout: 30000,
    waitUntil: 'networkidle2'
  });

  const markdownPath = MarkdownGenerator.generateAndSave(result, 'custom-id');

  console.log('Markdown salvo em:', markdownPath);
  console.log('Emails encontrados:', result.contactInfo.emails);
}
```

## 🔧 Scripts Disponíveis

| Script | Comando | Descrição |
|--------|---------|-----------|
| Desenvolvimento | `yarn dev` | Inicia API com hot-reload |
| Produção | `yarn start` | Inicia API em modo produção |
| CLI | `yarn run cli <URL>` | Executa scraping via linha de comando |
| Build | `yarn run build` | Compila TypeScript para JavaScript |

## 🐛 Troubleshooting

### Puppeteer não encontra o Chrome

```bash
# Linux
sudo apt-get install -y chromium-browser

# Mac
brew install chromium

# Ou configure manualmente:
export PUPPETEER_CACHE_DIR=/caminho/para/chrome
```

### Timeout em sites lentos

Aumente o timeout nas opções:

```json
{
  "url": "https://site-lento.com",
  "options": {
    "timeout": 60000,
    "waitUntil": "domcontentloaded"
  }
}
```

### Conteúdo não está sendo capturado

Para SPAs com muito JavaScript, use `networkidle0`:

```json
{
  "options": {
    "waitUntil": "networkidle0"
  }
}
```

## 📝 Licença

MIT

## 👨‍💻 Autor

Desenvolvido com ☕ e 💻
