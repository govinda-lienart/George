# Last updated: 2025-05-11
from langchain.agents import Tool
import streamlit as st
from booking.calendar import render_booking_form


def handle_booking_flow(query: str) -> str:
    # Check if query is about seeing availability calendar
    availability_keywords = ["calendar", "availability", "available dates", "which dates",
                             "see when", "visual", "view rooms", "room availability"]

    if any(keyword in query.lower() for keyword in availability_keywords):
        st.session_state.booking_mode = True
        st.session_state.show_calendar = True
        return "I've opened our availability calendar where you can check which dates are available or booked for each room. Available dates are shown in green, while booked dates are in red."
    else:
        # Regular booking request
        st.session_state.booking_mode = True
        return ""  # 👈 Do not return a long message that LLM could treat as "final answer"


booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out. Also handles requests to view the availability calendar."
)