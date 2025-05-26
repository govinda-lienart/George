# ========================================
# 📋 ROLE OF THIS SCRIPT - chat_ui.py
# ========================================

"""
Chat UI module for the George AI Hotel Receptionist app.
- Provides user interface components for chat conversation display
- Handles message rendering with proper styling for user and assistant messages
- Manages user input collection through Streamlit's chat interface
- Supports HTML rendering for rich message formatting
- Creates intuitive chat bubble experience for guest interactions
- Essential UI component for George's conversational interface
"""

# chat_ui.py
import streamlit as st

# ========================================
# 💬 Display Chat Messages
# ========================================
def render_chat_bubbles(history):
    for sender, msg in history:
        with st.chat_message("user" if sender == "user" else "assistant"):
            if sender == "user":
                st.markdown(f"{msg}")
            else:
                st.markdown(msg, unsafe_allow_html=True)

# ========================================
# 🎙️ Get User Input
# ========================================
def get_user_input():
    return st.chat_input("Ask about our hotel, booking, ...")