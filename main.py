import os
import time
import streamlit as st
from dotenv import load_dotenv
from chat_ui import render_header, render_chat_bubbles
from tools import agent  # Import the agent from tools.py

# Load environment variables
load_dotenv()

# Streamlit UI setup
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""

# User input
user_input = st.chat_input("Ask about availability, bookings, or anything else...")
if user_input:
    st.session_state.history.append(("user", user_input))
    with st.spinner("George is replying..."):
        start_time = time.time()
        response = agent.run(user_input)
        end_time = time.time()
        duration = end_time - start_time
    st.session_state.history.append(("bot", response))
    st.write(f"⏱️ Response time: {duration:.2f} seconds")

render_chat_bubbles(st.session_state.history)