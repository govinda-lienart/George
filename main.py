# main.py

import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import mysql.connector
from langchain.agents import initialize_agent, AgentType

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

from utils.config import llm
from chat_ui import render_header, render_chat_bubbles
from booking.calendar import render_booking_form

# ========================================
# 🔁 Load .env
# ========================================
load_dotenv()

# ========================================
# ✅ Get secret or fallback
# ========================================
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ========================================
# ⚙️ Page setup
# ========================================
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# ========================================
# 🔁 Initialize session state
# ========================================
if "history" not in st.session_state:
    st.session_state.history = [("bot", "👋 How may I assist you today?")]

if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

# ========================================
# 🧠 LangChain agent
# ========================================
agent = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# ========================================
# 🧰 Sidebar Dev Panel
# ========================================
with st.sidebar:
    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

# ========================================
# 🧠 SQL Query Panel
# ========================================
if st.session_state.show_sql_panel:
    st.markdown("### 🔍 SQL Query Panel")

    sql_input = st.text_area("Enter SQL query", "SELECT * FROM bookings LIMIT 10;", height=150)
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
            cols = [desc[0] for desc in cursor.description]
            st.dataframe(pd.DataFrame(rows, columns=cols))
        except Exception as e:
            st.error(str(e))
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

# ========================================
# 💬 Chat Interface
# ========================================
if not st.session_state.show_sql_panel:
    render_chat_bubbles(st.session_state.history)

    user_input = st.chat_input("Ask about availability, bookings, or anything else...")
    if user_input:
        # Add user message to history first so it's displayed
        st.session_state.history.append(("user", user_input))

        # Display assistant is thinking...
        with st.chat_message("assistant"):
            thinking = st.empty()
            thinking.markdown("⏳ George is replying...")

            try:
                response = agent.run(user_input)
            except Exception as e:
                response = f"⚠️ Error: {e}"

            thinking.markdown(response)

        st.session_state.history.append(("bot", response))

# ========================================
# 📅 Booking Form
# ========================================
if st.session_state.booking_mode:
    render_booking_form()
