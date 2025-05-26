# ========================================
# 📋 ROLE OF THIS SCRIPT - chat_tool.py
# ========================================

"""
Chat tool module for the George AI Hotel Receptionist app.
- Handles general hospitality conversations and guest support queries
- Provides empathetic responses for emotional support situations
- Processes questions about hotel policies, amenities, and general information
- Loads static hotel facts from text files for consistent responses
- Manages fallback responses when information is not available
- Integrates with LangChain for conversational AI capabilities
- Essential component for George's friendly and professional communication
"""

# ========================================
# 💬 CHAT TOOL MODULE (GENERAL ASSISTANT)
# ========================================

# ────────────────────────────────────────────────
# 🧠 LANGCHAIN, CONFIG & LOGGER IMPORTS
# ────────────────────────────────────────────────
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import os

# ────────────────────────────────────────────────
# 📁 STATIC FACT SOURCE
# ────────────────────────────────────────────────
HOTEL_FACTS_PATH = "static/hotel_facts.txt"

try:
    with open(HOTEL_FACTS_PATH, "r", encoding="utf-8") as f:
        hotel_facts_text = f.read().strip()
        if hotel_facts_text:
            logger.info("✅ hotel_facts.txt loaded successfully.")
        else:
            logger.warning("⚠️ hotel_facts.txt is empty.")
except Exception as e:
    hotel_facts_text = ""
    logger.error(f"❌ Failed to load hotel facts: {e}")

# ========================================
# 🧾 PROMPT TEMPLATE FOR GENERAL CHAT
# ========================================
chat_prompt = PromptTemplate.from_template("""
You are George, the friendly and professional AI hotel assistant at Chez Govinda in Belgium.

You must answer using the facts provided below when possible.

{facts}

If a guest expresses emotions like loneliness, sadness, or stress:
- Do not offer medical or psychological advice.
- Gently acknowledge the feeling and offer light, comforting suggestions like relaxing in the lounge, visiting a nearby café, or enjoying the calm of our garden or surrounding area.
- Stay warm, respectful, and never overstep your role.

If the answer is not found in the facts:
- Say: "I'm afraid I don't have that information at the moment. You're always welcome to contact us directly by phone or email — our team will be happy to assist you."
- **IMPORTANT: Do not include meta-comments like "Note: the facts do not mention..." or explanations about missing data. Simply give a polite fallback response.**

User: {input}
Response:
""")

# ========================================
# ⚙️ CHAT TOOL FUNCTION
# ========================================
# ┌──────────────────────────────────────────┐
# │  PROCESS GENERAL HOSPITALITY QUERIES        │
# └──────────────────────────────────────────┘
def chat_tool_func(user_input: str) -> str:
    """Answer general user questions based on hotel facts."""
    logger.info(f"💬 User asked: {user_input}")

    try:
        if hotel_facts_text:
            logger.info("📄 Responding using hotel_facts.txt")
        else:
            logger.warning("📄 hotel_facts.txt missing or empty — fallback prompt will be used.")

        response = (chat_prompt | llm).invoke({
            "input": user_input,
            "facts": hotel_facts_text or "[NO FACTS AVAILABLE]"
        }).content.strip()

        logger.info(f"🤖 Assistant response: {response}")
        return response

    except Exception as e:
        logger.error(f"❌ chat_tool_func error: {e}", exc_info=True)
        return "I'm sorry, something went wrong while processing your question."

# ========================================
# 🧩 LANGCHAIN TOOL OBJECT (EXPORTED)
# ========================================
# ┌──────────────────────────────────────────┐
# │  WRAP CHAT TOOL INTO LangChain TOOL OBJECT  │
# └──────────────────────────────────────────┘
chat_tool = Tool(
    name="chat_tool",
    func=chat_tool_func,
    description="General assistant for hospitality questions not related to bookings, prices, or specific hotel rooms."
)