import streamlit as st

def apply_chat_styles():
    st.markdown("""
    <style>
    .chat-message {
        padding: 10px 15px;
        border-radius: 12px;
        margin: 5px 0;
        max-width: 75%;
        word-wrap: break-word;
    }
    .user {
        background-color: #DCF8C6;
        align-self: flex-end;
        text-align: right;
        margin-left: auto;
    }
    .assistant {
        background-color: #F1F0F0;
        align-self: flex-start;
        text-align: left;
        margin-right: auto;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

def render_chat_history(history):
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, msg in history:
        css_class = "user" if sender.lower() == "you" else "assistant"
        st.markdown(f'<div class="chat-message {css_class}">{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)