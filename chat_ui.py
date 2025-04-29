# Last updated: 2025-04-29 14:26:23
# Last updatted: 2025-04-24 22:11:38
# chat_ui.py

import streamlit as st

def render_header():
    st.markdown(
        """
        <h1 style='font-size: 2.4rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;'>
            🏨 Chez Govinda – AI Hotel Assistant
        </h1>
        """,
        unsafe_allow_html=True
    )

def render_chat_bubbles(history):
    for sender, msg in history:
        with st.chat_message("user" if sender == "user" else "assistant"):
            st.write(msg)