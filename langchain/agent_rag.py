from dotenv import load_dotenv
import os
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages


# LangChain & LangGraph Imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client
from langchain_core.tools import tool


# Carrega variáveis de ambiente
load_dotenv()


# --- CONFIGURAÇÃO INICIAL ---


# Configuração do LLM (Usando Gemini 1.5 Flash para velocidade/custo)
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)


# Configuração dos embeddings (Fixando 768 para bater com o banco)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)


# Configuração do Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")


if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar definidos no.env")


supabase: Client = create_client(supabase_url, supabase_key)


# --- INGESTÃO DE DADOS (Markdown) ---
# Nota: Em produção, isso seria um script separado para não re-inserir dados a cada execução.


markdown_path = "plantie.md"


if not os.path.exists(markdown_path):
    # Cria um arquivo dummy se não existir para o código não quebrar
    print(f"⚠️ Aviso: {markdown_path} não encontrado. Criando arquivo de exemplo...")
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write("# Plantie Platform\n\nA Plantie é uma solução de IoT para monitoramento de plantas...")


markdown_loader = TextLoader(markdown_path, encoding="utf-8")


try:
    documents = markdown_loader.load()
    print(f"📄 Markdown carregado! {len(documents)} documento(s).")
except Exception as e:
    print(f"❌ Erro ao carregar Markdown: {e}")
    raise


# Chunking (Estratégia Otimizada para FAQs)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n## ", "\n### ", "\n", " ", ""] # Tenta quebrar por cabeçalhos primeiro
)


pages_split = text_splitter.split_documents(documents)


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
    
    vectorstore = SupabaseVectorStore(
        embedding=embeddings,
        client=supabase,
        table_name="marketing_rag",
        query_name="match_documents"
    )
except Exception as e:
    print(f"⚠️ Aviso: Erro na inserção ou dados já existentes: {str(e)}")
    vectorstore = SupabaseVectorStore(
        embedding=embeddings,
        client=supabase,
        table_name="marketing_rag",
        query_name="match_documents",        
        chunk_size=3072
    )


retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4} # Retorna os top 4 chunks mais relevantes
)


# --- DEFINIÇÃO DAS FERRAMENTAS ---


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


tools = [retriever_tool]
llm_with_tools = llm.bind_tools(tools)


# --- O SYSTEM PROMPT (ADAPTADO DO META-AGENTE) ---


# Aqui aplicamos a lógica que pesquisamos: Persona + Regras de RAG + Tom de Voz
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


# --- GRAFO DO AGENTE (LANGGRAPH) ---


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def call_llm(state: AgentState):
    """Nó que chama o LLM"""
    messages = state['messages']
    # Injeta o System Prompt no início, mas mantendo o histórico
    # Nota: Em modelos de chat, o SystemMessage deve ser o primeiro.
    if not isinstance(messages, SystemMessage):
        messages = + messages
   
    response = llm_with_tools.invoke(messages)
    return {'messages': [response]}


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


def should_continue(state: AgentState):
    """Decide se para ou continua para as ferramentas"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "retriever_agent"
    return END


# Construção do Grafo
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


# --- INTERFACE DE TERMINAL ---


def running_agent():
    print("\n🌱 === PLANTIE AI AGENT (RAG SYSTEM) ===")
    print("Digite 'exit' para sair.\n")
   
    # Histórico local simples para o loop do terminal
    chat_history = []


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


if __name__ == "__main__":
    running_agent()

