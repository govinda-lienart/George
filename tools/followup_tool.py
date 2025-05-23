# followup_tool.py

import os
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import streamlit as st

# --- Path to your static hotel info file ---
HOTEL_FACTS_FILE = "static/hotel_facts.txt"

# --- Load static content once ---
def load_activities() -> str:
    try:
        with open(HOTEL_FACTS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load hotel facts: {e}", exc_info=True)
        return "I'm sorry, I couldn't load the activity suggestions at this time."

# --- Intent detection prompt ---
intent_prompt = PromptTemplate.from_template("""
You are a polite hotel assistant. The user was asked:
"Would you like suggestions for things to do during your stay?"

Their reply was:
"{user_reply}"

Please classify the user's intent as one of these:
- yes
- maybe
- no

Respond with just the label (yes, maybe, or no) — nothing else.
""")

# --- Main follow-up handler ---
def handle_followup_response(user_input: str, session_state) -> str:
    try:
        intent = (intent_prompt | llm).invoke({"user_reply": user_input}).content.strip().lower()
        logger.info(f"🎯 Follow-up intent detected: {intent}")
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}", exc_info=True)
        return "I'm sorry, I had trouble understanding that. Could you say that again?"

    if intent == "yes" or intent == "maybe":
        activities = load_activities()
        return (
            "🌟 Wonderful! Here are some activities you might enjoy during your stay:\n\n"
            f"{activities}"
        )
    elif intent == "no":
        return "No problem at all! I hope you have a relaxing and enjoyable trip. 😊"
    else:
        return "Got it! If you'd like activity suggestions later, just let me know."

# --- Tool wrapper (optional if you use router, or use this directly in main.py) ---
followup_tool = Tool(
    name="followup_tool",
    func=lambda q: handle_followup_response(q, st.session_state),
    description="Handles guest replies to post-booking follow-up messages about local activity suggestions."
)
