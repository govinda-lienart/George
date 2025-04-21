import streamlit as st

def inject_custom_css():
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
        }

        .stChatMessage.user {
            background-color: #e0f7fa;
            padding: 0.7rem;
            border-radius: 1rem;
            margin: 0.5rem 0;
            max-width: 80%;
            align-self: flex-end;
        }

        .stChatMessage.assistant {
            background-color: #fff3e0;
            padding: 0.7rem;
            border-radius: 1rem;
            margin: 0.5rem 0;
            max-width: 80%;
            align-self: flex-start;
        }

        .stChatMessage {
            display: flex;
            flex-direction: column;
        }

        .st-emotion-cache-1c7y2kd {
            border: 1px solid #ccc;
            border-radius: 2rem;
            padding: 0.5rem 1rem;
            font-size: 1rem;
        }

        .st-emotion-cache-1c7y2kd:focus {
            outline: none;
            border-color: #f57c00;
        }
        </style>
    """, unsafe_allow_html=True)