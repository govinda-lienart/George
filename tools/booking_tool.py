# Last updated: 2025-04-29 14:26:23
from langchain.agents import Tool
import streamlit as st
from booking.calendar import render_booking_form

def handle_booking_flow(query: str) -> str:
    print("DEBUG: handle_booking_flow called!")  # 👈 ADD THIS
    st.session_state.booking_mode = True
    print(f"DEBUG: booking_mode set to {st.session_state.booking_mode}")  # 👈 ADD THIS
    return ""  # 👈 Do not return a long message that LLM could treat as "final answer"

booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)