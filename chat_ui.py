# Last updated: 2025-05-05 19:29:09
import streamlit as st

# ========================================
# 🏷️ Render Page Config and Title
# ========================================
def render_page_config():
    st.set_page_config(
        page_title="Chez Govinda – AI Hotel Assistant",
        page_icon="🏨",
        layout="centered",
        initial_sidebar_state="auto"
    )

# ========================================
# 🏨 Render Header
# ========================================
def render_header():
    st.markdown(
        """
        <h1 style='font-size: 1.5rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;'>
            🤖 Talk with our AI Hotel Receptionist
        </h1>
        """,
        unsafe_allow_html=True
    )
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
    return st.chat_input("Ask about availability, bookings, or anything else...")