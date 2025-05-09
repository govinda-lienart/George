# Last updated: 2025-05-09 15:45:00
from langchain.agents import Tool
from utils.config import llm


def handle_non_hotel_questions(question: str) -> str:
    """
    Handles non-hotel related questions, allowing basic pleasantries
    but redirecting more complex off-topic questions.
    """
    # List of basic pleasantries to respond to naturally
    pleasantries = [
        "how are you", "how's your day", "how is your day",
        "good morning", "good afternoon", "good evening", "hello", "hi",
        "nice to meet you", "how are things", "how's it going"
    ]

    # Check if the question is a basic pleasantry
    if any(phrase in question.lower() for phrase in pleasantries):
        return llm.invoke(
            f"Respond as George the hotel receptionist to this greeting: '{question}'. " +
            "Keep it brief, friendly and professional. Mention you're happy to help with hotel questions."
        ).content.strip()
    else:
        # For all other off-topic questions, redirect
        return "😊 I can only help with questions about our hotel and your stay. Could you ask something about your visit to Chez Govinda?"


chat_tool = Tool(
    name="chat",
    func=handle_non_hotel_questions,
    description="For handling basic pleasantries naturally but redirecting other off-topic questions."
)