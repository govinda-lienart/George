# booking_tool.py
# Last updated: 2025-05-23

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

    # Return a friendly message before showing the form
    return "Perfect! I'd be happy to help you book a room. Please fill out the booking form below with your details and preferences."


# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
booking_tool = Tool(
    name="booking_tool",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)