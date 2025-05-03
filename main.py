# Trigger redeploy
# Last updated: 2025-05-03

import streamlit as st
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

from utils.config import llm
from chat_ui import render_header, render_chat_bubbles
from booking.calendar import render_booking_form  # 👈 Import calendar form renderer

# Load .env
load_dotenv()

# Streamlit page setup
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# Session state
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""
if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

# Initialize LangChain agent
agent = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Handle user input
user_input = st.chat_input("Ask about availability, bookings, or type: sql_query:")
if user_input:
    st.session_state.history.append(("user", user_input))

    # 🧠 Trigger SQL mode if input starts with sql_query:
    if user_input.lower().startswith("sql_query:"):
        st.markdown("### 🧠 SQL Mode Activated – Enter your custom query below")
        query_text = st.text_area("🔍 Enter SQL query to run:", height=150, key="sql_input")

        if st.button("Run Query"):
            full_query = query_text.strip()
            result = execute_manual_sql(f"sql_query: {full_query}")
            if result:
                st.code(result["query"], language="sql")
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.dataframe(result["dataframe"])
    else:
        # 👨‍💼 Normal LLM-based response
        with st.spinner("George is replying..."):
            response = agent.run(user_input)
        st.session_state.history.append(("bot", response))

# Chat history UI
render_chat_bubbles(st.session_state.history)

# ✅ Render booking form if booking_mode was triggered
if st.session_state.booking_mode:
    render_booking_form()
