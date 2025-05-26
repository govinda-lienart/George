# ========================================
# 📋 ROLE OF THIS SCRIPT - followup_tool.py
# ========================================

"""
Follow-up tool module for the George AI Hotel Receptionist app.
- Manages post-booking guest engagement and activity recommendations
- Processes guest responses to activity suggestion offers after booking completion
- Uses LLM-based intent classification to understand guest preferences
- Provides personalized local attraction and activity recommendations
- Handles booking confirmation messaging with guest-specific details
- Creates seamless post-booking experience to enhance guest satisfaction
- Integrates with static content files for consistent activity information
"""

# ========================================
# 🤖 FOLLOW-UP TOOL MODULE (LLM-BASED POST-BOOKING SYSTEM)
# ========================================

# ────────────────────────────────────────────────
# 🧠 LANGCHAIN, CONFIG, STREAMLIT & LOGGER IMPORTS
# ────────────────────────────────────────────────
import os
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import streamlit as st

# ────────────────────────────────────────────────
# 📁 STATIC FILE PATHS
# ────────────────────────────────────────────────
HOTEL_FACTS_FILE = "static/hotel_facts.txt"

# ────────────────────────────────────────────────
# 📄 STATIC BOOKING CONFIRMATION TEMPLATE
# ────────────────────────────────────────────────
BOOKING_CONFIRMATION_TEMPLATE = """Dear {first_name}, This is your booking confirmation #**{booking_number}**. A confirmation email has been sent to your provided email address. Thank you for choosing Chez Govinda for your upcoming stay! We're thrilled to welcome you and want to ensure everything is perfect for your visit.

Would you like recommendations for things to see and do during your stay? """

# ========================================
# 📄 LOAD STATIC ACTIVITY CONTENT
# ========================================
# ┌─────────────────────────────────────────┐
# │  LOAD ATTRACTIONS FROM FILE             │
# └─────────────────────────────────────────┘
def load_activities() -> str:
    """Load activities and local attractions from static file"""
    try:
        with open(HOTEL_FACTS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load hotel facts: {e}", exc_info=True)
        return "I'm sorry, I couldn't load the activity suggestions at this time."

# ========================================
# 🎯 LLM PROMPTS FOR INTENT & RESPONSE
# ========================================
# ────────────────────────────────────────────────
# 🧠 INTENT CLASSIFICATION PROMPT
# ────────────────────────────────────────────────
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

# ────────────────────────────────────────────────
# 💡 ACTIVITY RESPONSE GENERATION PROMPT
# ────────────────────────────────────────────────
activity_response_prompt = PromptTemplate.from_template("""
You are providing activity suggestions to a hotel guest. Be warm and helpful.

Activities information:
{activities_info}

CRITICAL REQUIREMENTS - FOLLOW EXACTLY:
1. Start directly with your response (NO "George:" or any names)
2. Provide the activity information in a friendly way
3. END immediately after giving the information
4. DO NOT mention reception, assistance, help, or further services
5. DO NOT ask questions or invite more interaction
6. DO NOT use phrases like "Need anything", "happy to assist", "enjoy your stay"
7. Just give the info and STOP

Guest said: {user_input}

Your response (end after providing activities - NO additional offers):""")

# ========================================
# 💬 FOLLOW-UP RESPONSE HANDLER
# ========================================
# ┌─────────────────────────────────────────┐
# │  PROCESS GUEST REPLY TO FOLLOW-UP       │
# └─────────────────────────────────────────┘
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
            # Use LLM to generate a clean response (rules are in the prompt)
            response = (activity_response_prompt | llm).invoke({
                "activities_info": activities_info,
                "user_input": user_input
            }).content.strip()

            return response
        except Exception as e:
            logger.error(f"Failed to generate activity response: {e}")
            return (
                "Great! Here are some wonderful things to do in the area:\n\n"
                f"{activities_info}"
            )
    elif intent == "NEGATIVE":
        return "No problem at all! Have a wonderful and relaxing stay with us! 😊"
    else:  # UNCLEAR
        return (
            "Would you like some suggestions for local attractions and activities? "
            "Just let me know!"
        )

# ========================================
# 📝 HARDCODED FAST FOLLOW-UP MESSAGE
# ========================================
# ┌─────────────────────────────────────────┐
# │  INSTANT CONFIRMATION MESSAGE TEMPLATE  │
# └─────────────────────────────────────────┘
def create_followup_message() -> dict:
    """
    Create a follow-up message using hardcoded template - FAST execution.
    """
    booking_info = st.session_state.get("latest_booking_info", {})
    first_name = booking_info.get("first_name", "valued guest") if booking_info else "valued guest"
    booking_number = booking_info.get("booking_number", "your booking") if booking_info else "your booking"

    message = f"Dear {first_name}, This is your booking number #{booking_number}. A confirmation email has been sent to your provided email address. Thank you for choosing Chez Govinda for your upcoming stay!\n\nWould you like recommendations for things to see and do during your stay?"

    logger.info("Hardcoded booking confirmation message created (fast)")
    return {"message": message, "awaiting_activity_consent": True}

# ========================================
# 🧰 LANGCHAIN TOOL WRAPPER
# ========================================
# ┌─────────────────────────────────────────┐
# │  WRAP FOLLOW-UP LOGIC INTO TOOL OBJECT  │
# └─────────────────────────────────────────┘
followup_tool = Tool(
    name="followup_tool",
    func=lambda q: handle_followup_response(q, st.session_state),
    description="Handles guest replies to post-booking follow-up messages about local activity suggestions."
)