# Last updated: 2025-05-12
from langchain.agents import Tool
import streamlit as st
from booking.calendar import render_booking_form


def handle_booking_flow(query: str) -> str:
    # Check if the user wants to cancel or exit the booking flow
    cancel_keywords = ["cancel", "exit", "quit", "remove", "stop", "back", "reset"]

    if any(keyword in query.lower() for keyword in cancel_keywords):
        if st.session_state.get("booking_mode", False) or st.session_state.get("show_calendar", False):
            # Clear booking-related session states
            for key in ['booking_mode', 'show_calendar', 'pre_selected_room_id',
                        'pre_selected_check_in', 'pre_selected_check_out']:
                if key in st.session_state:
                    del st.session_state[key]
            return "I've canceled the booking process. How else can I help you today?"
        return "You're not currently in a booking flow. How can I assist you?"

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
        st.session_state.show_calendar = False
        return "I'll help you book a room at our hotel. Please fill out the booking form with your details."


booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out. Also handles requests to view the availability calendar."
)