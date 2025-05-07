import os
import streamlit as st
from dotenv import load_dotenv

# ========================================
# 🔁 Load local .env for development
# ========================================
load_dotenv()

# ========================================
# ✅ Safe secret getter: Cloud or local
# ========================================
def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ========================================
# 🧠 Set environment variables before LangChain
# ========================================
os.environ["LANGSMITH_TRACING"] = get_secret("LANGSMITH_TRACING", "false")
os.environ["LANGSMITH_API_KEY"] = get_secret("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_PROJECT"] = get_secret("LANGSMITH_PROJECT", "George")
os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY", "")

# ========================================
# 📦 Imports after env is configured
# ========================================
import pandas as pd
import mysql.connector
from PIL import Image
from langchain.agents import initialize_agent, AgentType
from langsmith import traceable
from langchain_core.tracers.langchain import wait_for_all_tracers
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

from utils.config import llm
from chat_ui import render_header, render_chat_bubbles, get_user_input
from booking.calendar import render_booking_form

# ========================================
# ⚙️ Streamlit page config
# ========================================
st.set_page_config(
    page_title="Chez Govinda – AI Hotel Assistant",
    page_icon="🏨",
    layout="centered",
    initial_sidebar_state="auto"
)
render_header()

# ========================================
# ✅ LangSmith Trace Functions
# ========================================
@traceable(name="streamlit_trace_test", run_type="chain", tags=["manual", "test"])
def trace_test_info():
    return {"status": "✅ Streamlit is tracing properly", "user": "Govinda", "test": True}

@traceable(name="pure_streamlit_trace", run_type="chain")
def streamlit_hello_world():
    return "✅ Hello from Streamlit with LangSmith!"

@traceable(name="langsmith_test_trace", run_type="chain")
def test_langsmith_trace():
    return llm.invoke("Just say hi to LangSmith.", config={"metadata": {"project_name": "George"}})

# ========================================
# 🧠 Router LLM Setup
# ========================================
router_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

router_prompt = PromptTemplate.from_template("""
You are a routing assistant for an AI hotel receptionist.

Choose the correct tool for the user's question.

Available tools:
- sql_tool: check room availability, prices, booking status, or existing reservation details
- vector_tool: room descriptions, hotel policies, breakfast, amenities
- booking_tool: when the user confirms they want to book
- chat_tool: if the question is unrelated to the hotel (e.g. weather, personal questions, general small talk)

Important:
- If the question is not related to the hotel, choose `chat_tool`. The assistant will then respond kindly: 
  “😊 I can only help with questions about our hotel and your stay. Could you ask something about your visit to Chez Govinda?”

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

Question: "{question}"
Tool:
""")

# ========================================
# 🔍 SQL Query Panel
# ========================================
if st.session_state.get("show_sql_panel", False):
    st.markdown("### 🔍 SQL Query Panel")
    sql_input = st.text_area("Enter SQL query:", "SELECT * FROM bookings LIMIT 10;", height=150)
    if st.button("Run Query"):
        try:
            conn = mysql.connector.connect(
                host=get_secret("DB_HOST_READ_ONLY"),
                port=int(get_secret("DB_PORT_READ_ONLY", 3306)),
                user=get_secret("DB_USERNAME_READ_ONLY"),
                password=get_secret("DB_PASSWORD_READ_ONLY"),
                database=get_secret("DB_DATABASE_READ_ONLY")
            )
            cursor = conn.cursor()
            cursor.execute(sql_input)
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=col_names)
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            import traceback
            st.error("❌ Connection failed:")
            st.code(traceback.format_exc())
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

# ========================================
# 🧠 Chatbot Logic
# ========================================
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""
if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

if not st.session_state.show_sql_panel:
    if not st.session_state.history:
        st.session_state.history.append(("bot", "👋 Hello, I’m George. How can I help you today?"))

    render_chat_bubbles(st.session_state.history)
    user_input = get_user_input()

    if user_input:
        st.session_state.history.append(("user", user_input))
        render_chat_bubbles(st.session_state.history)

        with st.chat_message("assistant"):
            with st.spinner("🧠 George is thinking..."):
                selected_tool = router_llm.invoke(router_prompt.format(question=user_input)).content.strip()

                if selected_tool == "chat_tool":
                    response = "😊 I can only help with questions about our hotel and your stay. Could you ask something about your visit to Chez Govinda?"
                elif selected_tool == "sql_tool":
                    response = sql_tool.run(user_input)
                elif selected_tool == "vector_tool":
                    response = vector_tool.run(user_input)
                elif selected_tool == "booking_tool":
                    response = booking_tool.run(user_input)
                else:
                    response = "I'm not sure how to help with that. Could you rephrase your question?"

        st.session_state.history.append(("bot", response))
        st.rerun()

# ========================================
# 🗓️ Booking Form Display
# ========================================
if st.session_state.booking_mode:
    render_booking_form()

# ========================================
# 🪜 Flush LangSmith traces
# ========================================
wait_for_all_tracers()
