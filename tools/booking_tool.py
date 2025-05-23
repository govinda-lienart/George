
#booking_tool
# Last updated: 2025-05-19 18:26:37

from langchain.agents import Tool
import streamlit as st
from booking.calendar import render_booking_form
from logger import logger

# ========================================
# 🤖 Booking Handler
# ========================================
def handle_booking_flow(query: str) -> str:
    logger.info(f"📅 Booking flow triggered by user query: {query}")
    st.session_state.booking_mode = True
    return ""  # Don't return text — the form will take over the UI

# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)
