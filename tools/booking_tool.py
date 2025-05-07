# Last updated: 2025-05-07 14:45:57
from langchain.agents import Tool
import streamlit as st
from booking.calendar import render_booking_form

def handle_booking_flow(query: str) -> str:
    st.session_state.booking_mode = True
    return ""  # 👈 Do not return a long message that LLM could treat as "final answer"

booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)