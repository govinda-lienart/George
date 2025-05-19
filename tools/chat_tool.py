# Last updated: 2025-05-19 — per-input logging added

from langchain.agents import Tool
from utils.config import llm
from logger import logger

def handle_non_hotel_questions(question: str) -> str:
    """
    Handles non-hotel related questions, allowing basic pleasantries
    but redirecting more complex off-topic questions.
    """
    logger.info(f"💬 Chat tool received user input: {question}")

    # List of basic pleasantries to respond to naturally
    pleasantries = [
        "how are you", "how's your day", "how is your day",
        "good morning", "good afternoon", "good evening", "hello", "hi",
        "nice to meet you", "how are things", "how's it going"
    ]

    if any(phrase in question.lower() for phrase in pleasantries):
        response = llm.invoke(
            f"Respond as George the hotel receptionist to this greeting: '{question}'. "
            "Keep it brief, friendly and professional. Mention you're happy to help with hotel questions."
        ).content.strip()
        logger.info(f"🤖 Chat response: {response}")
        return response

    # If not a pleasantry
    logger.info("❗ Off-topic input — redirecting to hotel-only response.")
    return "😊 I can only help with questions about our hotel and your stay. Could you ask something about your visit to Chez Govinda?"

chat_tool = Tool(
    name="chat",
    func=handle_non_hotel_questions,
    description="For handling basic pleasantries naturally but redirecting other off-topic questions."
)
