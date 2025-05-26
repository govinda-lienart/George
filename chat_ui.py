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