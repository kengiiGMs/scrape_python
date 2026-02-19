# ✅ CHECKLIST DE VALIDAÇÃO - API Scrape V3 + FAQ Pipeline

## Pré-requisitos

- [ ] Python 3.11+ instalado
- [ ] Arquivo `.env` com credenciais:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`
  - `GOOGLE_API_KEY`
- [ ] Dependências instaladas: `pip install -r scrape_python/requirements.txt`
- [ ] Playwright configurado: `playwright install chromium`
- [ ] Coluna `ID_Conta` existe na tabela `marketing_rag` do Supabase

## Validações técnicas executadas

- [x] Sintaxe Python válida em `scrape_python/api.py`
- [x] Sintaxe Python válida em `scrape_python/V3/scraper.py`
- [x] Sintaxe Python válida em `langchain/Agente_FAQ.py`
- [x] Estrutura de diretórios criada corretamente
- [x] Frontend HTML criado em `scrape_python/public/index.html`
- [x] Dependências atualizadas em `requirements.txt`
- [x] Documentação completa gerada

## Testes funcionais recomendados

### 1. Teste de scraping isolado

```bash
cd scrape_python/V3
python scraper.py
# Digite uma URL quando solicitado
# Verificar se markdown é gerado em resultados/
```

**Resultado esperado:**
- Arquivo markdown salvo com timestamp
- Conteúdo legível em português

### 2. Teste da API

```bash
cd scrape_python
python api.py
```

**Verificar:**
- API inicia em `http://localhost:8000`
- Logs mostram diretórios configurados
- Não há erros de import

### 3. Teste do health endpoint

```bash
curl http://localhost:8000/health
```

**Resultado esperado:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-11T...",
  "service": "Scrape & FAQ API"
}
```

### 4. Teste do frontend

1. Abrir `http://localhost:8000` no navegador
2. Verificar se página carrega
3. Verificar se campos estão visíveis

### 5. Teste do pipeline completo

**Via frontend:**
1. Digitar URL: `https://www.google.com`
2. Clicar "Executar Pipeline Completo"
3. Aguardar processamento

**Verificações:**
- Status muda para "processing" → "success"
- `ID_Conta` é exibido (ex.: `www-google-com_2026-02-11_a1b2c3d4`)
- Arquivo markdown criado em `langchain/uploads/`
- Chat é habilitado

**Via curl:**
```bash
curl -X POST http://localhost:8000/api/pipeline \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.google.com","table":"marketing_rag","clear":false}'
```

### 6. Teste do chat

**Pré-requisito:** Pipeline executado com sucesso (para ter `ID_Conta`)

**Via frontend:**
1. Digitar mensagem no chat
2. Clicar "Enviar mensagem"
3. Verificar resposta do webhook N8N

**Via curl:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Como funciona?","ID_Conta":"www-google-com_2026-02-11_a1b2c3d4"}'
```

**Resultado esperado:**
- Webhook recebe payload corretamente
- Resposta é exibida no chat
- Sem erros de timeout

### 7. Teste de banco de dados

**Verificar no Supabase:**

```sql
SELECT "ID_Conta", content, metadata 
FROM marketing_rag 
WHERE "ID_Conta" LIKE 'www-google-com%' 
LIMIT 5;
```

**Resultado esperado:**
- Linhas com `ID_Conta` preenchido
- Campo `metadata` contém `ID_Conta` também
- Embeddings gerados corretamente

## Possíveis erros e soluções

### Erro: `ModuleNotFoundError: No module named 'fastapi'`

**Solução:**
```bash
pip install -r requirements.txt
```

### Erro: `playwright._impl._errors.Error: Executable doesn't exist`

**Solução:**
```bash
playwright install chromium
```

### Erro: `ValueError: SUPABASE_URL deve estar definido no .env`

**Solução:**
Criar arquivo `.env` com as variáveis necessárias

### Erro: `column "ID_Conta" does not exist`

**Solução:**
```sql
ALTER TABLE marketing_rag ADD COLUMN "ID_Conta" TEXT;
CREATE INDEX idx_id_conta ON marketing_rag("ID_Conta");
```

### Erro: `Timeout ao contatar webhook N8N`

**Solução:**
1. Verificar se webhook está online
2. Testar manualmente com curl
3. Aumentar timeout em `api.py` se necessário

## Observações finais

1. **Performance**: Pipeline pode levar 30s-2min dependendo do site e quantidade de FAQs
2. **Memória**: LLM usa ~500MB-1GB durante processamento
3. **Concorrência**: API não tem fila, processar 1 site por vez
4. **Produção**: Adicionar autenticação, rate limiting e logs estruturados

## Próximos passos

1. Testar com URL real do cliente
2. Validar filtragem por `ID_Conta` no webhook N8N
3. Configurar deploy (Docker, VM, etc.)
4. Adicionar monitoramento e alertas
