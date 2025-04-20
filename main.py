# looking_good_v18.py (cleaned version without booking form)

import os
import re
import mysql.connector
import streamlit as st
from dotenv import load_dotenv
import datetime

from langchain_community.chat_models import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType

# --- Load environment variables ---
load_dotenv()

# --- LLM Setup ---
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1"
)

# --- Load FAISS Vector Store ---
faiss_index_dir = os.path.join(os.getcwd(), "hotel_description_vectordb6")
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
vectorstore = FAISS.load_local(
    folder_path=faiss_index_dir,
    embeddings=embeddings,
    allow_dangerous_deserialization=True
)

# --- SQL Prompt ---
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

Additional context:
- Examples of room types include: "Economy Room", "Family Room", "Suite Room", "Romantic Room", "Double Room", "Single Room"
- Dates are stored as 'YYYY-MM-DD'.
- Room availability is marked with 1 for available, 0 for not available.

Rules:
- If the user asks for availability between two dates, return rooms from `room_availability` that are available on **all** dates in the range.
- If the user asks for total price for a stay, calculate it as `price * number_of_nights`, using `DATEDIFF(check_out, check_in)`.
- Always match rooms using `room_type`.
- **If the user asks for a listing of room types, generate a query to select distinct room_type from the rooms table.**
- **Crucial Rule:** You MUST ONLY return the raw MySQL query. Do not include any explanations, markdown formatting, or extra text.

User: "{input}"
"""
)

# --- SQL Utilities ---
def run_sql_query(query):
    print(f"DEBUG: Executing SQL Query: {query}")
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
        print(f"DEBUG: SQL Query Result: {rows}")
        return rows
    except Exception as e:
        print("DEBUG SQL ERROR:", e)
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

# --- Vector Search ---
def run_vector_search(query):
    k = 5 if len(query.split()) < 6 else 3
    docs = vectorstore.similarity_search(query, k=k)
    if not docs:
        return "I couldn't find anything relevant in the hotel information."
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are George, the friendly and professional receptionist at Chez Govinda, a boutique hotel in Brussels.

Use the context below to answer the guest's question. If the answer can be found word-for-word in the context (like the hotel's address, phone number, or email), include it exactly as it appears.

Be warm, concise, and helpful — just like a real receptionist would be.

Context:
{context}

Question: {question}

George's reply:
"""
    )
    chain = prompt | llm
    response = chain.invoke({"context": context, "question": query})
    return response.content.strip()

# --- ReAct Tools ---
def react_sql_tool(q):
    sql_text = (sql_prompt | llm).invoke({"summary": st.session_state.chat_summary, "input": q}).content.strip()
    sql_query = sql_text.removeprefix("```sql").removesuffix("```").strip()
    print(f"DEBUG: Generated SQL Query: {sql_query}")
    return format_result_naturally(q, run_sql_query(sql_query))

def memory_tool(q):
    return st.session_state.chat_summary or "No memory yet."

def chat_tool(q):
    return llm.invoke(q).content.strip()

tools = [
    Tool(name="sql", func=react_sql_tool, description="Use for bookings, availability, prices, and listing room types."),
    Tool(name="vector", func=run_vector_search, description="Use for hotel policies, descriptions."),
    Tool(name="memory", func=memory_tool, description="Conversation summary."),
    Tool(name="chat", func=chat_tool, description="Small talk and greetings."),
]

react_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# --- Streamlit UI ---
st.set_page_config(page_title="Chez Govinda - AI Hotel Assistant", page_icon="🏨")
st.title("🏨 Chez Govinda — AI Hotel Assistant")

if "history" not in st.session_state: st.session_state.history = []
if "chat_memory" not in st.session_state: st.session_state.chat_memory = []
if "chat_summary" not in st.session_state: st.session_state.chat_summary = ""

def update_chat_summary():
    full = "\n".join(f"User: {u}\nAssistant: {a}" for u, a in st.session_state.chat_memory)
    prompt = PromptTemplate(input_variables=["history"], template="Summarize the conversation:\n{history}\n\nSummary:")
    chain = prompt | llm
    result = chain.invoke({"history": full})
    st.session_state.chat_summary = result.content.strip()

def handle_user_input(user_question):
    with st.spinner("Thinking..."):
        reply = react_agent.run(user_question)
    return reply

user_question = st.chat_input("Ask about availability, policies, or anything else...")

if user_question:
    chatbot_response = handle_user_input(user_question)
    if chatbot_response:
        st.session_state.history.append(("You", user_question))
        st.session_state.history.append(("Assistant", chatbot_response))
        st.session_state.chat_memory.append((user_question, chatbot_response))
        update_chat_summary()

for sender, msg in st.session_state.history:
    st.chat_message(sender.lower()).write(msg)

# --- Debug Info ---
with st.expander("🧠 Debug"):
    st.json({
        "summary": st.session_state.get("chat_summary"),
    })