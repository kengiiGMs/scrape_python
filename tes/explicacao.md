Vou ler o arquivo para fornecer uma explicação detalhada sobre o funcionamento desse agente.

[1 tool called]

# Explicação Detalhada do Agente RAG

Vou explicar como funciona esse agente completo, detalhando cada componente e o motivo de usar cada biblioteca:

## 🏗️ Arquitetura Geral

Este é um **agente RAG (Retrieval-Augmented Generation)** conversacional que combina:
- Um LLM (Large Language Model) para geração de respostas
- Um sistema de busca vetorial para recuperar informações de documentos
- Um grafo de estados para orquestrar o fluxo de decisões

## 📚 Bibliotecas Utilizadas e Seus Propósitos

### 1. **LangGraph** (`langgraph`)

```1:8:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
from dotenv import load_dotenv
import os
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages


# LangChain & LangGraph Imports
from langgraph.graph import StateGraph, END
```

**Por quê?** LangGraph permite criar agentes com **fluxos de decisão complexos** usando grafos de estados. É superior a uma simples chamada de LLM porque:
- Permite loops: o agente pode chamar ferramentas múltiplas vezes
- Controla o fluxo baseado em condições (tem ou não tool_calls?)
- Mantém histórico de conversação estruturado

### 2. **LangChain** (vários módulos)

```9:16:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client
from langchain_core.tools import tool
```

**Por quê cada um?**
- **`messages`**: Sistema de tipagem forte para mensagens (Human, System, Tool) - mantém contexto organizado
- **`ChatGoogleGenerativeAI`**: Interface unificada para o Gemini, permite trocar de modelo facilmente
- **`GoogleGenerativeAIEmbeddings`**: Converte texto em vetores numéricos (768 dimensões) para busca semântica
- **`TextLoader`**: Carrega arquivos Markdown preservando encoding UTF-8
- **`RecursiveCharacterTextSplitter`**: Quebra documentos grandes em chunks menores de forma inteligente
- **`SupabaseVectorStore`**: Interface para salvar/buscar vetores no Supabase (banco vetorial)
- **`@tool`**: Decorador que transforma funções Python em ferramentas que o LLM pode chamar

### 3. **Supabase Client**

```15:15:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
from supabase.client import Client, create_client
```

**Por quê?** Supabase é um **PostgreSQL com extensão pgvector**, que permite:
- Busca vetorial performática (similarity search)
- Escalabilidade (cloud-native)
- RLS (Row Level Security) para multi-tenancy
- Alternativa open-source ao Pinecone/Weaviate

## 🔄 Fluxo de Funcionamento

### **Fase 1: Configuração e Ingestão de Dados** (linhas 23-123)

```26:33:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
# Configuração do LLM (Usando Gemini 1.5 Flash para velocidade/custo)
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)


# Configuração dos embeddings (Fixando 768 para bater com o banco)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)
```

1. **LLM com temperatura 0**: Respostas determinísticas (importante para suporte)
2. **Embeddings de 768 dimensões**: Padrão do Gemini Embedding 001

```74:81:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n## ", "\n### ", "\n", " ", ""] # Tenta quebrar por cabeçalhos primeiro
)


pages_split = text_splitter.split_documents(documents)
```

3. **Chunking estratégico**:
   - **1000 caracteres**: Tamanho ideal para contexto focado
   - **200 de overlap**: Evita perder contexto entre chunks
   - **Separators**: Prioriza quebras em cabeçalhos Markdown (mantém contexto semântico)

```84:101:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
# Inserção manual para deixar o Supabase gerar o ID sozinho
try:
    # Gera embeddings para todos os chunks
    texts = [doc.page_content for doc in pages_split]
    metadatas = [doc.metadata for doc in pages_split]
    vectors = embeddings.embed_documents(texts)
    
    rows = []
    for i in range(len(texts)):
        rows.append({
            "content": texts[i],
            "metadata": metadatas[i],
            "embedding": vectors[i]
        })
    
    # Insere no Supabase sem enviar a coluna 'id'
    supabase.table("marketing_rag").insert(rows).execute()
    print(f"✅ Dados inseridos com sucesso! {len(rows)} chunks.")
```

4. **Vetorização em batch**: Converte todos os chunks em vetores de uma vez (eficiente)

### **Fase 2: Ferramenta de Busca** (linhas 126-153)

```129:149:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
@tool
def retriever_tool(query: str) -> str:
    """
    Use esta ferramenta para buscar informações oficiais sobre a Plantie.
    Sempre que o usuário fizer uma pergunta sobre funcionalidades, preços ou suporte,
    você DEVE usar esta ferramenta antes de responder.
    """
    print(f"🔎 Buscando no banco de dados: '{query}'")
    docs = retriever.invoke(query)


    if not docs:
        return "Nenhuma informação relevante encontrada na base de conhecimento."
   
    results = []
    for i, doc in enumerate(docs):
        # Adiciona o conteúdo e a fonte (metadata) para o LLM saber de onde veio
        source = doc.metadata.get('source', 'Desconhecido')
        results.append(f"--- Trecho {i+1} (Fonte: {source}) ---\n{doc.page_content}\n")
   
    return "\n".join(results)
```

**Funcionamento**:
1. LLM decide que precisa buscar informações
2. Chama `retriever_tool(query="como funciona o monitoramento")`
3. A ferramenta busca os 4 chunks mais similares (cosine similarity)
4. Retorna os trechos formatados para o LLM sintetizar

### **Fase 3: Grafo de Estados** (linhas 190-266)

```193:195:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

**Estado do agente**: Lista de mensagens que cresce automaticamente (`add_messages` é um reducer)

```197:206:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
def call_llm(state: AgentState):
    """Nó que chama o LLM"""
    messages = state['messages']
    # Injeta o System Prompt no início, mas mantendo o histórico
    # Nota: Em modelos de chat, o SystemMessage deve ser o primeiro.
    if not isinstance(messages, SystemMessage):
        messages = + messages
   
    response = llm_with_tools.invoke(messages)
    return {'messages': [response]}
```

**Nó 1 (call_llm)**: Envia histórico + system prompt para o LLM

```209:231:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
def take_action(state: AgentState):
    """Nó que executa as ferramentas"""
    last_message = state['messages'][-1]
    tool_calls = last_message.tool_calls
   
    results = []
    tools_dict = {t.name: t for t in tools}


    for t in tool_calls:
        print(f"⚙️ Executando ferramenta: {t['name']}")
        if t['name'] in tools_dict:
            # Executa a tool
            tool_result = tools_dict[t['name']].invoke(t['args'])
           
            # Cria a mensagem de resposta da tool
            results.append(ToolMessage(
                tool_call_id=t['id'],
                name=t['name'],
                content=str(tool_result)
            ))
   
    return {'messages': results}
```

**Nó 2 (take_action)**: Executa as ferramentas solicitadas pelo LLM

```234:239:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
def should_continue(state: AgentState):
    """Decide se para ou continua para as ferramentas"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "retriever_agent"
    return END
```

**Função de decisão**: Se o LLM pediu ferramentas → vai para `take_action`, senão → termina

```243:264:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
graph = StateGraph(AgentState)


graph.add_node("llm", call_llm)
graph.add_node("retriever_agent", take_action)


graph.set_entry_point("llm")


graph.add_conditional_edges(
    "llm",
    should_continue,
    {
        "retriever_agent": "retriever_agent",
        END: END
    }
)


graph.add_edge("retriever_agent", "llm")


rag_agent = graph.compile()
```

**Fluxo do grafo**:
```
Início → [LLM] → Precisa ferramenta? 
                    ↓ Sim             ↓ Não
               [Executa Tool] → [LLM] → Fim
                    ↑______________|
```

### **Fase 4: Loop de Conversação** (linhas 272-302)

```280:298:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
    while True:
        user_input = input("\nVocê: ")
        if user_input.lower() in ['exit', 'quit']:
            break
       
        # Adiciona mensagem do usuário ao estado
        chat_history.append(HumanMessage(content=user_input))
       
        # Invoca o agente
        print("🤖 Pensando...")
        result = rag_agent.invoke({"messages": chat_history})
       
        # Pega a resposta final
        final_response = result['messages'][-1].content
       
        # Atualiza histórico com a resposta do assistente para manter contexto
        chat_history.append(result['messages'][-1])
       
        print(f"\nPlantie AI: {final_response}")
```

Mantém histórico completo para conversas contextuais (multi-turn).

## 🎯 Pontos-Chave do Design

### **System Prompt Estratégico**

```160:187:c:\Users\bucci\Quaestum\Scrape - Copia\langchain\agent_rag.py
system_prompt = """
# IDENTITY & ROLE
Você é o **Plantie AI Specialist**, o assistente virtual oficial da plataforma Plantie.
Sua missão é ajudar clientes a entenderem, comprarem e utilizarem nossa solução de monitoramento de plantas via IoT.


# KNOWLEDGE BASE & TRUTH (CRÍTICO)
Você NÃO possui conhecimento inato sobre os detalhes técnicos atuais da Plantie.
**REGRA NÚMERO 1:** Para QUALQUER pergunta sobre a plataforma (preços, como funciona, erros, cadastro), você **DEVE** usar a ferramenta `retriever_tool` para buscar a resposta oficial.


# PROTOCOLO DE RESPOSTA
1. **Analise** a pergunta do usuário.
2. **Consulte** a `retriever_tool` com termos de busca relevantes.
3. **Sintetize** a resposta baseada APENAS no texto retornado pela ferramenta.
4. **Cite** as informações implicitamente (ex: "De acordo com nossa documentação...").


# GUARDRAILS (SEGURANÇA)
- Se a `retriever_tool` retornar "Nenhuma informação encontrada" ou informações que não respondem à dúvida, **NÃO INVENTE**. Responda: "Desculpe, não encontrei essa informação específica nos meus manuais. Gostaria de falar com um atendente humano?"
- Se o usuário perguntar sobre código (Python, React) que não seja relacionado à API da Plantie, recuse educadamente.
- Mantenha um tom profissional, entusiasta e focado em soluções sustentáveis.


# INTERACTION STYLE
- Seja conciso. Use listas (bullet points) para instruções passo-a-passo.
- Se for uma objeção de vendas (ex: "está caro"), use as informações recuperadas para destacar o valor/benefício (ex: economia de água).
"""
```

- **Força o uso da ferramenta**: Evita alucinações
- **Guardrails**: Define limites claros do que o agente pode/não pode fazer
- **Tom de voz**: Define personalidade (profissional + sustentável)

## 🚀 Vantagens dessa Arquitetura

1. **Escalabilidade**: Supabase cresce com o negócio
2. **Precisão**: RAG reduz alucinações em ~80% vs LLM puro
3. **Manutenibilidade**: Atualizar conhecimento = atualizar Markdown + re-inserir
4. **Auditabilidade**: Logs mostram exatamente quais documentos foram usados
5. **Multi-turn**: Mantém contexto entre perguntas

## ⚠️ Problemas Atuais no Código

Há um bug na linha 203:

```python
if not isinstance(messages, SystemMessage):
    messages = + messages  # ❌ Sintaxe inválida
```

Deveria ser:

```python
messages = [SystemMessage(content=system_prompt)] + messages
```

Essa é a explicação completa! O agente combina busca vetorial inteligente com um LLM guiado por ferramentas, tudo orquestrado por um grafo de estados que permite decisões complexas e loops de raciocínio.