# Trigger redeploy
# Last updated: 2025-04-24 22:11:38
import streamlit as st
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool  # 👈 This line should remain as is

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
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],  # 👈 This line should remain as is
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Handle user input
user_input = st.chat_input("Ask about availability, bookings, or anything else...")
if user_input:
    st.session_state.history.append(("user", user_input))
    with st.spinner("George is replying..."):
        response = agent.run(user_input)
    st.session_state.history.append(("bot", response))

    # 👈 ADD THIS DEBUGGING CODE
    st.write(f"DEBUG: After agent run, booking_mode = {st.session_state.booking_mode}")

# Chat history UI
render_chat_bubbles(st.session_state.history)

# 👈 ADD THIS DEBUGGING CODE
st.write(f"DEBUG: Before conditional render, booking_mode = {st.session_state.booking_mode}")

# ✅ Render booking form if booking_mode was triggered
if st.session_state.booking_mode:
    render_booking_form()