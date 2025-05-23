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
    return ""  # Don't return text — the form will take over the UI

# ========================================
# 📝 Post Booking Follow-up Message
# ========================================
def post_booking_followup(latest_booking_number: str) -> dict:
    """
    Prepare follow-up message after booking to ask user about interest in hotel activities.
    Args:
        latest_booking_number (str): The booking reference number.
    Returns:
        dict: Contains follow-up message and flag if awaiting user consent.
    """
    if not latest_booking_number:
        logger.warning("No latest booking number found for follow-up.")
        return {"message": "", "awaiting_activity_consent": False}

    message = (
        f"Thank you for your booking (Ref: {latest_booking_number})! "
        "Would you be interested in joining any of our hotel activities during your stay? "
        "Please reply YES or NO."
    )
    logger.info("Post booking follow-up message prepared.")
    return {"message": message, "awaiting_activity_consent": True}

# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)