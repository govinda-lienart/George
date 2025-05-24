# Updated followup_tool.py - LLM GENERATED DETAILED FOLLOW-UP

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
# 🧠 LLM Activity Response Generator (More Concise)
# ========================================
activity_response_prompt = PromptTemplate.from_template("""
You are George, a friendly hotel receptionist at Chez Govinda. A guest has asked for activity suggestions during their stay.

Here is the information about local activities and attractions:
{activities_info}

Please create a warm, helpful response that:
- Thanks them briefly
- Presents the activities in a concise, well-organized way
- Uses a friendly, conversational tone
- Highlights the best options
- ONLY mentions what's in the provided information - do not offer additional services like restaurant bookings

Keep the response focused and not too long.

Guest's request: {user_input}
""")

# ========================================
# 🧠 LLM Detailed Follow-up Message Generator
# ========================================
detailed_followup_prompt = PromptTemplate.from_template("""
You are George, a friendly hotel receptionist at Chez Govinda. A guest has just completed their booking and you need to create a warm, detailed follow-up message.

Guest booking details:
- First Name: {first_name}
- Last Name: {last_name}
- Booking Number: {booking_number}
- Email: {email}
- Phone: {phone}
- Room Type: {room_type}
- Check-in: {check_in}
- Check-out: {check_out}
- Number of Guests: {num_guests}
- Total Price: €{total_price}
- Special Requests: {special_requests}

Create a warm, professional follow-up message that:
1. Thanks the guest by their first name
2. Confirms their booking with all the important details in a clear, organized way
3. Mentions that a confirmation email was sent to their email address
4. Asks if they would like suggestions for things to visit and do in the area during their stay
5. Uses a friendly, welcoming tone as a hotel receptionist

Keep it well-organized with emojis and clear formatting.
""")


# ========================================
# 💬 Follow-up Response Handler (Updated for conciseness)
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
            # Use LLM to generate a concise response with the activity info
            response = (activity_response_prompt | llm).invoke({
                "activities_info": activities_info,
                "user_input": user_input
            }).content
            return response
        except Exception as e:
            logger.error(f"Failed to generate activity response: {e}")
            return (
                "🌟 Great! Here are some wonderful things to do in the area:\n\n"
                f"{activities_info}\n\n"
                "Have a fantastic time exploring!"
            )
    elif intent == "NEGATIVE":
        return (
            "No problem at all! Have a wonderful and relaxing stay with us! 😊"
        )
    else:  # UNCLEAR
        return (
            "Would you like some suggestions for local attractions and activities? "
            "Just let me know!"
        )


# ========================================
# 📝 LLM-Generated Detailed Follow-up Message
# ========================================
def create_followup_message() -> dict:
    """
    Create a detailed follow-up message using LLM with all booking information.
    """
    booking_info = st.session_state.get("latest_booking_info", {})

    if booking_info:
        try:
            # Use LLM to generate detailed follow-up message
            message = (detailed_followup_prompt | llm).invoke({
                "first_name": booking_info.get("first_name", "valued guest"),
                "last_name": booking_info.get("last_name", ""),
                "booking_number": booking_info.get("booking_number", ""),
                "email": booking_info.get("email", ""),
                "phone": booking_info.get("phone", ""),
                "room_type": booking_info.get("room_type", ""),
                "check_in": booking_info.get("check_in", ""),
                "check_out": booking_info.get("check_out", ""),
                "num_guests": booking_info.get("num_guests", ""),
                "total_price": booking_info.get("total_price", ""),
                "special_requests": booking_info.get("special_requests", "None")
            }).content

            logger.info("LLM-generated detailed follow-up message created")
            return {"message": message, "awaiting_activity_consent": True}

        except Exception as e:
            logger.error(f"Failed to generate detailed follow-up: {e}")
            # Fallback to simple message
            first_name = booking_info.get("first_name", "valued guest")
            booking_number = booking_info.get("booking_number", "your booking")

            message = (
                f"🎉 Thank you {first_name} for your booking (Ref: {booking_number})! "
                "Would you like suggestions for things to do in the area during your visit?"
            )
            return {"message": message, "awaiting_activity_consent": True}
    else:
        # Fallback if no booking info available
        message = (
            "🎉 Thank you for your booking! "
            "Would you like suggestions for things to do in the area during your stay?"
        )
        return {"message": message, "awaiting_activity_consent": True}


# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
followup_tool = Tool(
    name="followup_tool",
    func=lambda q: handle_followup_response(q, st.session_state),
    description="Handles guest replies to post-booking follow-up messages about local activity suggestions."
)