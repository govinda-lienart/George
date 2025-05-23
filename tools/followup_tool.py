# followup_tool.py

import os
import mysql.connector
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import streamlit as st

# --- Path to your static hotel info file ---
HOTEL_FACTS_FILE = "static/hotel_facts.txt"


# ========================================
# 🗃️ Database Helper Functions
# ========================================
def get_secret(key: str, default: str = "") -> str:
    """Get secret from Streamlit secrets or environment variables"""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


def get_booking_details(booking_number: str) -> tuple:
    """
    Fetch client name and booking dates from database.
    Returns: (client_name, check_in_date, check_out_date)
    """
    try:
        conn = mysql.connector.connect(
            host=get_secret("DB_HOST_READ_ONLY"),
            port=int(get_secret("DB_PORT_READ_ONLY", 3306)),
            user=get_secret("DB_USERNAME_READ_ONLY"),
            password=get_secret("DB_PASSWORD_READ_ONLY"),
            database=get_secret("DB_DATABASE_READ_ONLY")
        )
        cursor = conn.cursor()

        # Adjust column names to match your actual database schema
        query = """
        SELECT client_name, check_in_date, check_out_date 
        FROM bookings 
        WHERE booking_number = %s
        """
        cursor.execute(query, (booking_number,))
        result = cursor.fetchone()

        if result:
            client_name, check_in, check_out = result
            # Format dates nicely
            check_in_str = check_in.strftime("%B %d, %Y") if check_in else "your check-in date"
            check_out_str = check_out.strftime("%B %d, %Y") if check_out else "your check-out date"
            return client_name, check_in_str, check_out_str
        else:
            logger.warning(f"No booking found for number: {booking_number}")
            return "valued guest", "your upcoming stay", ""

    except Exception as e:
        logger.error(f"Failed to fetch booking details: {e}", exc_info=True)
        return "valued guest", "your upcoming stay", ""
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


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
# 🧠 LLM Intent Detection
# ========================================
intent_prompt = PromptTemplate.from_template("""
You are an intelligent hotel assistant analyzing guest responses.

The guest was asked: "Would you like suggestions for things to do in the area during your stay?"

Their reply was: "{user_reply}"

Analyze their intent and classify as:
- POSITIVE: They want activity suggestions (yes, sure, sounds good, I'd love that, please, etc.)
- NEGATIVE: They don't want suggestions (no, not interested, no thanks, I'm good, etc.)
- UNCLEAR: Ambiguous or unrelated response

Consider variations like:
- "Yes please" / "That would be great" / "Sure!" → POSITIVE
- "No thanks" / "Not interested" / "I'm good" / "Maybe later" → NEGATIVE  
- "What do you mean?" / "Tell me about rooms instead" → UNCLEAR

Respond with only: POSITIVE, NEGATIVE, or UNCLEAR
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
        activities = load_activities()
        return (
            "🌟 Wonderful! Here are some great things to do in the area during your stay:\n\n"
            f"{activities}\n\n"
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
# 📝 Post Booking Follow-up Message
# ========================================
def post_booking_followup(latest_booking_number: str) -> dict:
    """
    Prepare personalized follow-up message after booking to ask user about interest in local activities.
    Args:
        latest_booking_number (str): The booking reference number.
    Returns:
        dict: Contains follow-up message and flag if awaiting user consent.
    """
    if not latest_booking_number:
        logger.warning("No latest booking number found for follow-up.")
        return {"message": "", "awaiting_activity_consent": False}

    # Fetch client details from database
    client_name, check_in_date, check_out_date = get_booking_details(latest_booking_number)

    # Create personalized message
    if check_out_date:  # If we have both dates
        date_info = f"from {check_in_date} to {check_out_date}"
    else:  # If we only have check-in or fallback
        date_info = check_in_date

    message = (
        f"Thank you {client_name} for your booking (Ref: {latest_booking_number})! "
        f"I see you have booked your stay {date_info}. "
        "Would you like suggestions for things to do in the area during your visit? "
        "I'd be happy to share some local attractions and activities!"
    )

    logger.info(f"Post booking follow-up message prepared for {client_name}")
    return {"message": message, "awaiting_activity_consent": True}


# ========================================
# 🧰 LangChain Tool Wrapper
# ========================================
followup_tool = Tool(
    name="followup_tool",
    func=lambda q: handle_followup_response(q, st.session_state),
    description="Handles guest replies to post-booking follow-up messages about local activity suggestions.