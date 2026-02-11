# EXPLICACAO DETALHADA: ID_Conta + Upload + Chat N8N

Este documento descreve, em detalhes, todas as alteracoes realizadas para:

1. Introduzir `ID_Conta` no fluxo de ingestao RAG.
2. Vincular cada arquivo Markdown a uma conta.
3. Criar uma pagina HTML simples para upload/processamento.
4. Integrar chat com webhook N8N.

---

## 1) Objetivo de arquitetura

Antes:
- O pipeline processava Markdown e inseria FAQs vetorizados no Supabase sem um identificador explicito por conta.

Depois:
- Cada ingestao passa a carregar `ID_Conta`, derivado do nome do arquivo `.md`.
- O backend expoe endpoints para upload + execucao da ingestao.
- O backend expoe endpoint de chat que envia `{ message, ID_Conta }` ao webhook N8N.
- Frontend HTML unico para operacao basica.

---

## 2) Arquivos alterados/criados

## `langchain/Agente_FAQ.py`

### O que foi adicionado

1. Nova importacao:
- `from pathlib import Path`

2. Nova funcao:
- `derive_id_conta(file_path: str) -> str`
- Extrai o `stem` do arquivo Markdown (nome sem extensao), que vira o `ID_Conta`.

3. Alteracao de assinatura:
- `generate_embeddings_for_faqs(..., id_conta: str, ...)`

4. Inclusao de `ID_Conta` em todas as rows:
- Campo dedicado no nivel da row: `"ID_Conta": id_conta`
- Campo em metadata para compatibilidade e rastreabilidade: `"ID_Conta": id_conta`

5. Logs operacionais:
- Exibe no terminal: `ID_Conta derivado do arquivo: ...`
- Inclui `ID_Conta` no resumo final de estatisticas.

6. Tratamento de erro de schema no Supabase:
- Ao falhar insercao envolvendo `ID_Conta`, retorna erro claro orientando a garantir a coluna literal `ID_Conta`.

### Resultado funcional
- Todas as linhas geradas para o mesmo `.md` ficam associadas ao mesmo `ID_Conta`.

---

## `index.ts`

### O que foi adicionado

1. Novas importacoes:
- `multer`, `path`, `fs`, `spawn` de `child_process`.

2. Constantes de runtime:
- `WEBHOOK_URL` com o endpoint informado.
- Caminhos de projeto: `PUBLIC_DIR`, `LANGCHAIN_DIR`, `UPLOAD_DIR`, `INGEST_SCRIPT_PATH`.
- `PYTHON_BIN` configuravel por `PYTHON_BIN` no ambiente (fallback `python`).

3. Servir frontend estatico:
- `app.use(express.static(PUBLIC_DIR))`
- `GET /` retorna `public/index.html`.

4. Upload de Markdown:
- Configuracao `multer` com `diskStorage`.
- Restricao de extensao para `.md`.
- Sanitizacao do nome para gerar `ID_Conta`.
- Nome final salvo em `langchain/uploads/<ID_Conta>.md`.

5. Endpoint de ingestao:
- `POST /api/ingest-markdown`
- Campo esperado de upload: `markdownFile`
- Parametros adicionais: `table` (default `marketing_rag`) e `clear` (`true/false`)
- Executa script Python:
  - `python langchain/Agente_FAQ.py --input <arquivo> --table <table> [--clear]`
- Retorna JSON padronizado com `ID_Conta`, caminho, output e status.

6. Endpoint de chat:
- `POST /api/chat`
- Valida payload com Zod: `{ message, ID_Conta }`
- Repassa para webhook N8N com o mesmo formato.
- Faz parse de resposta JSON/texto e tenta extrair uma mensagem util (`reply/response/answer/message/output/text`).

7. Atualizacao de logs de boot:
- Lista os novos endpoints no startup do servidor.

### Resultado funcional
- O backend vira ponto unico de integracao (frontend nao chama webhook diretamente).

---

## `public/index.html` (novo)

### O que foi criado

Pagina unica com duas areas:

1. **Upload + Ingestao**
- Input de arquivo `.md`
- Campo readonly de `ID_Conta` (derivado do nome)
- Checkbox para `clear`
- Botao para processar ingestao (`POST /api/ingest-markdown`)

2. **Chat**
- Log de mensagens (usuario/bot)
- Textarea para pergunta
- Botao enviar (`POST /api/chat`)
- Envio com payload exato:
  - `{ "message": "...", "ID_Conta": "..." }`

### Resultado funcional
- Operacao basica sem framework, facil de testar e evoluir.

---

## `package.json` e `yarn.lock`

### O que foi alterado

Dependencias adicionadas:
- `multer` (upload multipart/form-data)
- `@types/multer` (tipagem TypeScript)

### Resultado funcional
- Backend suporta upload de arquivo no endpoint de ingestao.

---

## 3) Fluxo ponta a ponta

1. Usuario abre `/`.
2. Usuario seleciona `arquivo.md`.
3. Frontend deriva e exibe `ID_Conta` (nome do arquivo sem extensao).
4. Frontend envia upload para `POST /api/ingest-markdown`.
5. Backend salva arquivo em `langchain/uploads/<ID_Conta>.md`.
6. Backend executa `Agente_FAQ.py`.
7. Script Python:
   - Re-deriva `ID_Conta` pelo nome do arquivo.
   - Gera FAQs e embeddings.
   - Insere rows no Supabase com `ID_Conta`.
8. Usuario envia mensagem no chat.
9. Frontend chama `POST /api/chat` com `message` + `ID_Conta`.
10. Backend encaminha ao webhook N8N.
11. Resposta volta ao frontend e aparece no chat.

---

## 4) Contratos de API

## `POST /api/ingest-markdown`

### Request
- `multipart/form-data`
- Campo de arquivo: `markdownFile` (`.md`)
- Campo opcional: `table` (default `marketing_rag`)
- Campo opcional: `clear` (`"true"` ou `"false"`)

### Response (sucesso)
```json
{
  "success": true,
  "message": "Ingestão concluída com sucesso",
  "data": {
    "ID_Conta": "nome_do_arquivo",
    "filePath": ".../langchain/uploads/nome_do_arquivo.md",
    "table": "marketing_rag",
    "clear": false,
    "output": {
      "stdout": "...",
      "stderr": "..."
    }
  }
}
```

## `POST /api/chat`

### Request
```json
{
  "message": "Pergunta do usuário",
  "ID_Conta": "nome_do_arquivo"
}
```

### Forward para N8N
Mesmo payload:
```json
{
  "message": "Pergunta do usuário",
  "ID_Conta": "nome_do_arquivo"
}
```

### Response (sucesso)
```json
{
  "success": true,
  "data": {
    "reply": "Texto da resposta",
    "raw": {},
    "ID_Conta": "nome_do_arquivo"
  }
}
```

---

## 5) Observacoes operacionais importantes

1. Banco de dados:
- Para persistir `ID_Conta` em coluna dedicada, a tabela deve possuir a coluna literal `ID_Conta`.
- Se a coluna nao existir, o script agora retorna erro orientativo.

2. Multi-cliente:
- O isolamento por conta depende de usar sempre o `.md` correto para cada cliente.
- O mesmo nome de arquivo representa a mesma conta.

3. Sanitizacao:
- O nome do arquivo e sanitizado para manter apenas caracteres seguros (`a-z`, `A-Z`, `0-9`, `_`, `-`).

4. Seguranca:
- O webhook N8N fica protegido pelo backend; evita expor URL e logica sensivel direto no navegador.

---

## 6) Proximos passos recomendados

1. Criar/validar coluna `ID_Conta` na tabela `marketing_rag`.
2. Adicionar filtro por `ID_Conta` no lado de consulta do agente conversacional (n8n/SQL/RPC), para nao misturar clientes.
3. Adicionar autenticacao basica no frontend/backend se for ambiente aberto.
4. Versionar uploads por data, se desejar historico por conta.
