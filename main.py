import os
import re
import mysql.connector
import streamlit as st
import datetime
from dotenv import load_dotenv

from langchain_community.chat_models import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType

from chat_ui import inject_custom_css
from calendar_app import render_booking_form

# Load environment variables
load_dotenv()

# LLM setup
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1"
)

# Load FAISS vector store
faiss_index_dir = os.path.join(os.getcwd(), "hotel_description_vectordb1")
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorstore = FAISS.load_local(
    folder_path=faiss_index_dir,
    embeddings=embeddings,
    allow_dangerous_deserialization=True
)

# SQL Prompt
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

- Dates are stored as 'YYYY-MM-DD'.
- Use raw SQL only.
- Do not explain anything.

User: "{input}"
"""
)

def run_sql_query(query):
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD") or '',
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        return []

def format_result_naturally(user_question, sql_result):
    if not sql_result:
        return "No data found."
    rows_text = "\n".join([str(row) for row in sql_result])
    response_prompt = PromptTemplate(
        input_variables=["question", "result"],
        template="""
You are a hotel assistant. Summarize the following SQL result in natural, friendly language.

User's question: {question}
SQL result:
{result}

Your response:
"""
    )
    chain = response_prompt | llm
    response = chain.invoke({"question": user_question, "result": rows_text})
    return response.content.strip()

def run_vector_search(query):
    k = 5 if len(query.split()) < 6 else 3
    docs = vectorstore.similarity_search(query, k=k)
    if not docs:
        return "I couldn't find anything relevant in the hotel information."
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are George, the friendly receptionist at Chez Govinda.

Use this hotel context to answer the guest's question clearly and warmly:

{context}

Question: {question}

George's reply:
"""
    )
    chain = prompt | llm
    response = chain.invoke({"context": context, "question": query})
    return response.content.strip()

# Tools
def react_sql_tool(q):
    sql_query = (sql_prompt | llm).invoke({"summary": st.session_state.chat_summary, "input": q}).content.strip()
    sql_query = sql_query.removeprefix("```sql").removesuffix("```").strip()
    return format_result_naturally(q, run_sql_query(sql_query))

def memory_tool(q):
    return st.session_state.chat_summary or "No memory yet."

def chat_tool(q):
    return llm.invoke(q).content.strip()

tools = [
    Tool(name="sql", func=react_sql_tool, description="Bookings, availability, prices, listing rooms."),
    Tool(name="vector", func=run_vector_search, description="Hotel descriptions, policies."),
    Tool(name="memory", func=memory_tool, description="Conversation summary."),
    Tool(name="chat", func=chat_tool, description="General or chit-chat.")
]

react_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Streamlit App
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
st.title("🏨 Chez Govinda – AI Hotel Assistant")
inject_custom_css()

# Session State
if "history" not in st.session_state: st.session_state.history = []
if "chat_memory" not in st.session_state: st.session_state.chat_memory = []
if "chat_summary" not in st.session_state: st.session_state.chat_summary = ""

def update_chat_summary():
    full = "\n".join(f"User: {u}\nAssistant: {a}" for u, a in st.session_state.chat_memory)
    prompt = PromptTemplate(input_variables=["history"], template="Summarize the conversation:\n{history}\n\nSummary:")
    chain = prompt | llm
    result = chain.invoke({"history": full})
    st.session_state.chat_summary = result.content.strip()

# Show chat history
for sender, msg in st.session_state.history:
    st.chat_message(sender.lower()).markdown(msg)

# User input
user_question = st.chat_input("Ask about availability, bookings, or anything else...")

if user_question:
    # Show user message right away
    st.session_state.history.append(("User", user_question))
    st.chat_message("user").markdown(user_question)

    # Show George typing
    with st.chat_message("assistant"):
        with st.spinner("George is replying..."):
            reply = react_agent.run(user_question)
        st.markdown(reply)

    # Save reply
    st.session_state.history.append(("Assistant", reply))
    st.session_state.chat_memory.append((user_question, reply))
    update_chat_summary()

# Debug info
with st.expander("🛠️ Debug"):
    st.json({"summary": st.session_state.get("chat_summary")})

# ✅ Safe booking form check
if user_question and "book now" in user_question.lower():
    render_booking_form()