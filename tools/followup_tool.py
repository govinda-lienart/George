# Updated followup_tool.py - SIMPLIFIED VERSION

import os
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import streamlit as st

# --- Path to your static hotel info file ---
HOTEL_FACTS_FILE = "static/hotel_facts.txt"


# ========================================
# 📄 Content Loading
# ========================================
def load_activities() -> str:
    """Load activities and local attractions from static file"""
    try:
        with open(HOTEL_FACTS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load hotel facts: {e}", exc_info=True)
        return "I'm sorry, I couldn't load the activity suggestions at this time."


# ========================================
# 🧠 LLM Intent Detection (Only for user response)
# ========================================
intent_prompt = PromptTemplate.from_template("""
You are analyzing a guest's response to this question:
"Would you like suggestions for things to do in the area during your stay?"

Their reply was: "{user_reply}"

Classify their intent as:
- POSITIVE: They want activity suggestions (yes, sure, sounds good, please, etc.)
- NEGATIVE: They don't want suggestions (no, not interested, no thanks, etc.)
- UNCLEAR: Ambiguous response

Respond with only: POSITIVE, NEGATIVE, or UNCLEAR
""")

# ========================================
# 🧠 LLM Activity Response Generator
# ========================================
activity_response_prompt = PromptTemplate.from_template("""
You are George, a friendly hotel receptionist at Chez Govinda. A guest has asked for activity suggestions during their stay.

Here is the information about local activities and attractions:
{activities_info}

Please create a warm, helpful response that:
- Thanks them for their interest
- Presents the activities in an engaging, personalized way
- Uses a friendly, conversational tone
- Highlights the best options
- Offers to help with more specific questions

Guest's request: {user_input}
""")


# ========================================
# 💬 Follow-up Response Handler
# ========================================
def handle_followup_response(user_input: str, session_state) -> str:
    """Handle user's response to activity suggestions follow-up"""
    try:
        intent = (intent_prompt | llm).invoke({"user_reply": user_input}).content.strip().upper()
        logger.info(f"🎯 Follow-up intent detected: {intent}")
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}", exc_info=True)
        return "I'm sorry, I had trouble understanding that. Could you say that again?"

    if intent == "POSITIVE":
        activities_info = load_activities()
        try:
            # Use LLM to generate a personalized response with the activity info
            response = (activity_response_prompt | llm).invoke({
                "activities_info": activities_info,
                "user_input": user_input
            }).content
            return response
        except Exception as e:
            logger.error(f"Failed to generate activity response: {e}")
            return (
                "🌟 Wonderful! Here are some great things to do in the area during your stay:\n\n"
                f"{activities_info}\n\n"
                "I hope you have an amazing time exploring! Let me know if you need anything else. 😊"
            )
    elif intent == "NEGATIVE":
        return (
            "No problem at all! I completely understand. "
            "If you change your mind later or need any other assistance during your stay, "
            "just let me know. Have a wonderful and relaxing trip! 😊"
        )
    else:  # UNCLEAR
        return (
            "I want to make sure I understand correctly - would you like me to share "
            "some suggestions for activities and attractions in the area during your stay? "
            "Just say yes or no and I'll be happy to help!"
        )


# ========================================
# 📝 Simple Follow-up Message (Hardcoded)
# ========================================
# Replace the create_followup_message function in your followup_tool.py with this:

def create_followup_message() -> dict:
    """
    Create a personalized follow-up message using booking data from session state.
    """
    booking_info = st.session_state.get("latest_booking_info", {})

    if booking_info:
        client_name = booking_info.get("client_name", "valued guest")
        booking_number = booking_info.get("booking_number", "your booking")
        check_in = booking_info.get("check_in", "")
        check_out = booking_info.get("check_out", "")

        if check_in and check_out:
            date_info = f"from {check_in} to {check_out}"
        else:
            date_info = "for your upcoming stay"

        message = (
            f"🎉 Thank you {client_name} for your booking (Ref: {booking_number})! "
            f"I see you'll be staying with us {date_info}. "
            "Would you like suggestions for things to do in the area during your visit? "
            "I'd be happy to share some local attractions and activities!"
        )
    else:
        # Fallback if no booking info available
        message = (
            "🎉 Thank you for your booking! "
            "Would you like suggestions for things to do in the area during your stay? "
            "I'd be happy to share some local attractions and activities!"
        )

    logger.info("Personalized follow-up message created")
    return {"message": message, "awaiting_activity_consent": True}
# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
followup_tool = Tool(
    name="followup_tool",
    func=lambda q: handle_followup_response(q, st.session_state),
    description="Handles guest replies to post-booking follow-up messages about local activity suggestions."
)