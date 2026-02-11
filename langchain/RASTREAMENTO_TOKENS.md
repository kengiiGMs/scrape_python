# 📊 Sistema de Rastreamento de Tokens

## 🎯 Funcionalidades Implementadas

O script `ingest_faq.py` agora inclui rastreamento completo de uso de tokens para:

### 1. **Tokens do LLM (Gemini 2.5 Flash)**
- ✅ Tokens de entrada (input/prompt)
- ✅ Tokens de saída (output/completion)
- ✅ Total de tokens do LLM

### 2. **Tokens de Embeddings (Gemini Embedding-001)**
- ✅ Estimativa de tokens processados nos embeddings
- ✅ Cálculo baseado na quantidade de caracteres (1 token ≈ 4 caracteres)

## 📝 Como Funciona

### Classe `TokenUsageTracker`

A classe implementa o callback do LangChain para capturar automaticamente o uso de tokens:

```python
tracker = TokenUsageTracker()

# Usa o tracker nas chamadas do LLM
faq_response = process_with_llm(content, llm, tracker)

# Usa o tracker na geração de embeddings
rows = generate_embeddings_for_faqs(faq_response.faq_items, embeddings, tracker)

# Imprime o resumo ao final
tracker.print_summary()
```

## 📊 Formato da Saída

Ao final da execução, o script exibirá um resumo detalhado:

```
================================================================================
RESUMO DE USO DE TOKENS
================================================================================

📝 LLM (Gemini 2.5 Flash):
   - Tokens de entrada: 12,345
   - Tokens de saída: 3,456
   - Total LLM: 15,801

🔢 Embeddings (Gemini Embedding):
   - Tokens processados: 8,234

💰 TOTAL GERAL: 24,035 tokens
================================================================================
```

## 💡 Informações Úteis

### Preços (referência Google AI, fevereiro 2026)

**Gemini 2.5 Flash:**
- Input: Consultar tabela de preços oficial
- Output: Consultar tabela de preços oficial

**Gemini Embedding-001:**
- $0.15 por 1M tokens de entrada

### Cálculo de Custos

Para calcular o custo estimado da operação:

```python
# Exemplo (valores fictícios)
custo_llm_input = (tokens_input / 1_000_000) * preco_por_milhao
custo_llm_output = (tokens_output / 1_000_000) * preco_por_milhao
custo_embeddings = (tokens_embeddings / 1_000_000) * 0.15

custo_total = custo_llm_input + custo_llm_output + custo_embeddings
```

## 🚀 Uso

Execute o script normalmente. O rastreamento é automático:

```bash
python ingest_faq.py --input seu_arquivo.md --table marketing_rag --clear
```

O resumo de tokens será exibido automaticamente ao final da execução!

## 📌 Observações

1. **Tokens do LLM**: Valores exatos capturados da API do Google
2. **Tokens de Embeddings**: Estimativa calculada (1 token ≈ 4 chars)
3. **Formatação**: Números formatados com separadores de milhar para melhor legibilidade
4. **Zero Configuração**: Funciona automaticamente sem precisar de flags adicionais
