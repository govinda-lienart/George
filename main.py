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
from booking.calendar import render_booking_form  # 👈 Form rendering

# Load environment variables
load_dotenv()

# Streamlit page setup
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# Initialize session state
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

# Chat input and response
user_input = st.chat_input("Ask about availability, bookings, or anything else...")
if user_input:
    st.session_state.history.append(("user", user_input))

    with st.spinner("George is replying..."):
        response = agent.run(user_input)

    st.session_state.history.append(("bot", response))

    # ✅ Force rerun to display form immediately after booking intent
    if st.session_state.get("booking_mode"):
        st.rerun()

# Display chat history
render_chat_bubbles(st.session_state.history)

# ✅ If booking flag is set, render form
if st.session_state.booking_mode:
    st.markdown("### 📝 Booking Form")
    render_booking_form()