# Last updated: 2025-05-19 18:26:37
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import os

# --- Load hotel facts from static file ---
HOTEL_FACTS_PATH = os.path.join("static", "hotel_facts.txt")

try:
    with open(HOTEL_FACTS_PATH, "r", encoding="utf-8") as f:
        hotel_facts_text = f.read()
        logger.info("✅ hotel_facts.txt loaded successfully.")
except Exception as e:
    hotel_facts_text = ""
    logger.error(f"❌ Failed to load hotel facts: {e}")

# --- Prompt Template ---
chat_prompt = PromptTemplate.from_template("""
You are George, the friendly hotel assistant at Chez Govinda.

Use only the information provided below to answer the user's question:

{facts}

If you cannot find the answer in the provided facts, respond:
🙁 I'm sorry, I don't have the answer to that question.  
For further assistance, feel free to contact us by phone or email — our staff will be happy to help with your inquiry. Thank you!

User: {input}
Response:
""")

# --- Tool Function ---
def chat_tool_func(user_input: str) -> str:
    try:
        response = (chat_prompt | llm).invoke({
            "input": user_input,
            "facts": hotel_facts_text
        }).content.strip()
        logger.info(f"🤖 Assistant response: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ chat_tool_func error: {e}", exc_info=True)
        return "I'm sorry, something went wrong while processing your question."

# --- LangChain Tool Definition ---
chat_tool = Tool(
    name="chat_tool",
    func=chat_tool_func,
    description="General assistant for hospitality questions not related to bookings, prices, or specific hotel rooms."
)
