# tools/booking_tool.py
# Last updated: 2025-05-03 (fixes booking_mode issue for Streamlit Cloud)

from langchain.agents import Tool

# Instead of mutating session state directly (which fails on Streamlit Cloud),
# we return a signal string the main app can catch.
def handle_booking_flow(query: str) -> str:
    return "ACTIVATE_BOOKING_MODE"

booking_tool = Tool(
    name="booking",
    func=handle_booking_flow,
    description="Triggers the hotel booking form for the user to fill out."
)