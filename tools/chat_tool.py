from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
from logger import logger
import streamlit as st
import os

HOTEL_FACTS_PATH = "static/hotel_facts.txt"

try:
    with open(HOTEL_FACTS_PATH, "r", encoding="utf-8") as f:
        hotel_facts_text = f.read()
        logger.info("✅ hotel_facts.txt loaded successfully.")
except Exception as e:
    hotel_facts_text = ""
    logger.error(f"❌ Failed to load hotel facts: {e}")

chat_prompt = PromptTemplate(
    input_variables=["summary", "facts", "input"],
    template="""
You are George, the friendly hotel assistant at Chez Govinda.

Conversation so far:
{summary}

Hotel Facts:
{facts}

User: {input}
Response:
"""
)

def chat_tool_func(user_input: str) -> str:
    try:
        summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        response = (chat_prompt | llm).invoke({
            "input": user_input,
            "facts": hotel_facts_text,
            "summary": summary
        }).content.strip()

        st.session_state.george_memory.save_context(
            {"input": user_input},
            {"output": response}
        )

        logger.info(f"🤖 Assistant response: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ chat_tool_func error: {e}", exc_info=True)
        return "I'm sorry, something went wrong while processing your question."

chat_tool = Tool(
    name="chat_tool",
    func=chat_tool_func,
    description="General assistant for hospitality questions not related to bookings, prices, or specific hotel rooms."
)
