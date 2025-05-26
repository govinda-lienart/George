# ========================================
# 📋 ROLE OF THIS SCRIPT - booking_tool.py
# ========================================

"""
Booking tool module for the George AI Hotel Receptionist app.
- Provides LangChain tool wrapper for hotel room booking functionality
- Activates booking form interface when users request to make reservations
- Manages session state for booking mode transitions
- Integrates with the calendar booking form for seamless user experience
- Handles booking flow initiation and user guidance
- Essential component of George's booking assistance capabilities
"""

# ========================================
# 🏨 BOOKING TOOL MODULE (FORM ACTIVATION)
# ========================================

# ────────────────────────────────────────────────
# 🔧 LANGCHAIN, STREAMLIT & INTERNAL IMPORTS
# ────────────────────────────────────────────────
from langchain.agents import Tool
import streamlit as st
from booking.calendar import render_booking_form
from logger import logger

# ========================================
# 🤖 BOOKING FLOW HANDLER
# ========================================
# ┌─────────────────────────────────────────┐
# │  SET booking_mode FLAG + RETURN PROMPT  │
# └─────────────────────────────────────────┘
def handle_booking_flow(query: str) -> str:
    logger.info(f"📅 Booking flow triggered by user query: {query}")
    st.session_state.booking_mode = True

    # Return a friendly message before showing the form
    return "Perfect! I'd be happy to help you book a room. Please fill out the booking form below with your details and preferences."

# ========================================
# 🧰 LANGCHAIN TOOL WRAPPER
# ========================================
# ┌─────────────────────────────────────────┐
# │  WRAP BOOKING FLOW INTO TOOL OBJECT     │
# └─────────────────────────────────────────┘
booking_tool = Tool(
    name="booking_tool",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)