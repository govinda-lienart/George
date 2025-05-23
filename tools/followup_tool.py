# Updated followup_tool.py - LLM USES STATIC FILE FOR ACTIVITIES

import os
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import streamlit as st

# --- Path to your static hotel info file ---
HOTEL_FACTS_FILE = "static/hotel_facts.txt"


# ========================================
# 📄 Content Loading from Static File
# ========================================
def load_activities() -> str:
    """Load activities and local attractions from static file"""
    try:
        with open(HOTEL_FACTS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"✅ Successfully loaded {len(content)} characters from {HOTEL_FACTS_FILE}")
            return content
    except FileNotFoundError:
        logger.error(f"❌ Static file not found: {HOTEL_FACTS_FILE}")
        return "I'm sorry, I couldn't find the activity information file. Please contact reception for local recommendations."
    except Exception as e:
        logger.error(f"❌ Failed to load hotel facts: {e}", exc_info=True)
        return "I'm sorry, I couldn't load the activity suggestions at this time. Please contact reception for assistance."


# ========================================
# 🧠 LLM Intent Detection (Only for user response)
# ========================================
intent_prompt = PromptTemplate.from_template("""
You are analyzing a guest's response to this question:
"Would you like suggestions for things to do in the area during your stay?"

Their reply was: "{user_reply}"

Classify their intent as:
- POSITIVE: They want activity suggestions (yes, sure, sounds good, please, I'd like that, tell me more, etc.)
- NEGATIVE: They don't want suggestions (no, not interested, no thanks, I'm fine, etc.)
- UNCLEAR: Ambiguous response (maybe, not sure, what kind of things, etc.)

Respond with only: POSITIVE, NEGATIVE, or UNCLEAR
""")

# ========================================
# 🧠 LLM Activity Response Generator (Uses Static File Content)
# ========================================
activity_response_prompt = PromptTemplate.from_template("""
You are George, a friendly hotel receptionist at Chez Govinda. A guest has asked for activity suggestions during their stay.

Here is the complete information about local activities and attractions from our hotel guide:

{activities_info}

Please create a warm, helpful response that:
- Thanks them for their interest
- Presents the activities in a well-organized, easy-to-read format
- Uses a friendly, conversational tone as a hotel receptionist
- Highlights the most popular or recommended options
- Includes practical details like distances, opening hours, or booking info if mentioned in the guide
- ONLY mentions what's provided in the static file - do not add information not contained in the guide
- Keeps the response comprehensive but not overwhelming

Format the response with clear sections or bullet points to make it easy to scan.

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
# 💬 Follow-up Response Handler (Enhanced with Static File)
# ========================================
def handle_followup_response(user_input: str, session_state) -> str:
    """Handle user's response to activity suggestions follow-up"""
    try:
        # Use LLM to detect user intent
        intent = (intent_prompt | llm).invoke({"user_reply": user_input}).content.strip().upper()
        logger.info(f"🎯 Follow-up intent detected: {intent}")
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}", exc_info=True)
        return "I'm sorry, I had trouble understanding that. Could you please clarify if you'd like activity recommendations?"

    if intent == "POSITIVE":
        # Load activities from static file
        activities_info = load_activities()

        # Check if static file loaded successfully
        if "couldn't" in activities_info.lower() or "sorry" in activities_info.lower():
            return activities_info  # Return error message from load_activities()

        try:
            # Use LLM to generate a comprehensive response with the static file content
            response = (activity_response_prompt | llm).invoke({
                "activities_info": activities_info,
                "user_input": user_input
            }).content

            logger.info("✅ Successfully generated activity recommendations from static file")
            return response

        except Exception as e:
            logger.error(f"❌ Failed to generate LLM activity response: {e}")
            # Fallback: return raw static file content with simple formatting
            return (
                f"🌟 Great! Here are some wonderful things to do in our area:\n\n"
                f"{activities_info}\n\n"
                "Have a fantastic time exploring! If you need any additional information, feel free to ask."
            )

    elif intent == "NEGATIVE":
        return (
            "No problem at all! If you change your mind during your stay, just let me know. "
            "Have a wonderful and relaxing time with us! 😊"
        )
    else:  # UNCLEAR
        return (
            "I'd be happy to help! Would you like some suggestions for local attractions and activities? "
            "We have information about restaurants, sightseeing, outdoor activities, and cultural attractions in the area. "
            "Just say 'yes' if you'd like me to share some recommendations!"
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

            logger.info("✅ LLM-generated detailed follow-up message created")
            return {"message": message, "awaiting_activity_consent": True}

        except Exception as e:
            logger.error(f"❌ Failed to generate detailed follow-up: {e}")
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
    description="Handles guest replies to post-booking follow-up messages about local activity suggestions using static file content."
)