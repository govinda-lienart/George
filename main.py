import os
import streamlit as st
from dotenv import load_dotenv
from langchain.agents import Tool, initialize_agent, AgentType
from langchain_community.chat_models import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from chat_ui import render_header, render_chat_bubbles

# Load environment variables
load_dotenv()

# LLM setup
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1"
)

# Load Pinecone vector store
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
)

# Prompt to convert user queries to SQL
sql_prompt = PromptTemplate(
    input_variables=["summary", "input"],
    template="""
You are an SQL assistant for a hotel booking system.

Conversation summary so far:
{summary}

Translate the user's question into a MySQL query using this schema:

rooms(room_id, room_type, price, guest_capacity, description)
room_availability(id, room_id, date, is_available)
bookings(booking_id, first_name, last_name, email, phone, room_id, check_in, check_out, num_guests, total_price, special_requests)

Rules:
- Use raw MySQL.
- Do NOT explain anything. Only return the raw SQL query.

User: "{input}"
"""
)

# SQL runner
def run_sql(query):
    import mysql.connector
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        return f"SQL ERROR: {e}"
    finally:
        cursor.close()
        conn.close()

# SQL result explainer
def explain_sql(user_question, result):
    prompt = PromptTemplate(
        input_variables=["question", "result"],
        template="""
You are a hotel assistant.

Summarize this SQL result for the guest:
User Question: {question}
SQL Result: {result}
Response:
"""
    )
    return (prompt | llm).invoke({"question": user_question, "result": str(result)}).content.strip()

# Vector search
def vector_search(query):
    docs = vectorstore.similarity_search(query, k=3)
    if not docs:
        return "I couldn’t find anything relevant."
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are George, the friendly receptionist at Chez Govinda.

Answer based on the context below:
{context}

User: {question}
"""
    )
    return (prompt | llm).invoke({"context": context, "question": query}).content.strip()

# Tools
tools = [
    Tool(name="sql", func=lambda q: explain_sql(q, run_sql((sql_prompt | llm).invoke({"summary": st.session_state.chat_summary, "input": q}).content.strip())), description="Bookings, prices, availability."),
    Tool(name="vector", func=vector_search, description="Hotel details and policies."),
    Tool(name="chat", func=lambda q: llm.invoke(q).content.strip(), description="General chat.")
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Streamlit UI
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")

render_header()

# Session State
if "history" not in st.session_state: st.session_state.history = []
if "chat_summary" not in st.session_state: st.session_state.chat_summary = ""

# Chat logic
user_input = st.chat_input("Ask about availability, bookings, or anything else...")

if user_input:
    st.session_state.history.append(("user", user_input))
    with st.spinner("George is replying..."):
        response = agent.run(user_input)
    st.session_state.history.append(("bot", response))

render_chat_bubbles(st.session_state.history)