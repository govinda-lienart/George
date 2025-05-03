import streamlit as st
from dotenv import load_dotenv
import os
from langchain.agents import initialize_agent, AgentType

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

from utils.config import llm
from chat_ui import render_header, render_chat_bubbles
from booking.calendar import render_booking_form

# Load .env
load_dotenv()

# Streamlit page setup
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# ================================
# 🛠️ Sidebar Toggle for SQL Panel
# ================================
with st.sidebar:
    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

# ================================
# 🔍 SQL Query Panel (if toggled on)
# ================================
if st.session_state.show_sql_panel:
    st.markdown("### 🔍 SQL Query Panel")

    # SQL query input with label
    sql_input = st.text_area("🔍 Enter SQL query to run:",
                             value="SELECT * FROM bookings LIMIT 10;",
                             height=150,
                             key="sql_input_box")

    # Run Query button
    run_query = st.button("Run Query", key="run_query_button", type="primary")

    # Create result containers
    status_container = st.container()
    result_container = st.container()

    # Import necessary libraries for SQL connection
    import pandas as pd
    import mysql.connector

    if run_query:
        try:
            with status_container:
                st.write("🔐 Connecting to database...")

            # Connect using mysql.connector instead of SQLAlchemy
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=os.getenv("DB_USERNAME"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_DATABASE")
            )

            with status_container:
                st.success("✅ Connected to MySQL!")

            cursor = conn.cursor()
            cursor.execute(sql_input)
            rows = cursor.fetchall()

            # Get column headers
            col_names = [desc[0] for desc in cursor.description]

            # Display results
            with result_container:
                st.dataframe(rows, use_container_width=True)
                st.caption(f"Columns: {col_names}")

        except Exception as e:
            with status_container:
                st.error(f"❌ Connection failed:\n\n{e}")

        finally:
            try:
                if 'conn' in locals() and conn.is_connected():
                    cursor.close()
                    conn.close()
                    with status_container:
                        st.info("🔌 Connection closed.")
            except Exception as close_err:
                with status_container:
                    st.warning(f"⚠️ Error closing connection:\n\n{close_err}")

# ================================
# 🤖 LangChain Agent Setup
# ================================
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""
if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

agent = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# ================================
# 💬 Chatbot (only if SQL panel is off)
# ================================
if not st.session_state.show_sql_panel:
    st.markdown("### 💬 George the Assistant")
    user_input = st.chat_input("Ask about availability, bookings, or anything else...")
    if user_input:
        st.session_state.history.append(("user", user_input))
        with st.spinner("George is replying..."):
            response = agent.run(user_input)
        st.session_state.history.append(("bot", response))

# ================================
# 💬 Chat History UI
# ================================
if not st.session_state.show_sql_panel:
    render_chat_bubbles(st.session_state.history)

# ================================
# 📅 Booking Form if Triggered
# ================================
if st.session_state.booking_mode:
    render_booking_form()