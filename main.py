import streamlit as st
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType
from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from utils.config import llm
from chat_ui import render_header, render_chat_bubbles

# Load .env
load_dotenv()

# Streamlit page
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# Session state
if "history" not in st.session_state: st.session_state.history = []
if "chat_summary" not in st.session_state: st.session_state.chat_summary = ""

# Initialize agent
agent = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Chat input
user_input = st.chat_input("Ask about availability, bookings, or anything else...")
if user_input:
    st.session_state.history.append(("user", user_input))
    with st.spinner("George is replying..."):
        response = agent.run(user_input)
    st.session_state.history.append(("bot", response))

render_chat_bubbles(st.session_state.history)