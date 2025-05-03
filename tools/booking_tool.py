# booking_tool.py
import streamlit as st

def handle_booking_flow(query: str) -> str:
    print("DEBUG: handle_booking_flow called!")
    st.session_state.booking_mode = True
    print(f"DEBUG: booking_mode set to {st.session_state.booking_mode}")
    return "Okay, let's proceed with your booking."

if __name__ == '__main__':
    st.title("Booking Tool Test")
    if st.button("Trigger Booking Mode"):
        result = handle_booking_flow("Initiate booking")
        st.write(result)
        st.write(f"Current booking_mode in session state: {st.session_state.get('booking_mode', False)}")