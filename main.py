# ========================================
# 📦 Imports and Initialization
# ========================================

import os
import streamlit as st
import pandas as pd
import mysql.connector
from PIL import Image
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.agents import initialize_agent, AgentType
from langsmith import traceable
from langchain_core.tracers.langchain import wait_for_all_tracers
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Custom tool modules and UI components
from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool
from chat_ui import render_header, get_user_input, render_chat_bubbles
from booking.calendar import render_booking_form
from utils.config import llm

# ========================================
# 🔐 Load environment variables
# ========================================

load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# ========================================
# 🧠 Load LLM & Router
# ========================================

router_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# ========================================
# 🧠 Routing Prompt Template
# ========================================

router_prompt = PromptTemplate.from_template("""
You are a routing assistant for an AI hotel receptionist named George at Chez Govinda.

Choose the correct tool for the user's question, following these guidelines:

Available tools:
- sql_tool: For checking room availability, prices, booking status, or existing reservation details
- vector_tool: For room descriptions, hotel policies, breakfast, amenities, dining information
- booking_tool: When the user confirms they want to book a room, asks for help booking, OR wants to see a visual calendar of room availability
- chat_tool: For basic pleasantries AND any questions unrelated to the hotel

ROUTING RULES:
1. Basic pleasantries (e.g., "How are you?", "Good morning") → chat_tool
2. Personal questions/advice → chat_tool (e.g., relationship advice, personal problems)
3. Questions about external topics → chat_tool (politics, sports, tech, weather)
4. Hotel services, amenities, policies → vector_tool
5. Room availability and prices → sql_tool
6. Booking confirmation → booking_tool
7. ANY questions about breakfast, dining, food options → vector_tool
8. Requests to see a visual calendar or availability chart → booking_tool
9. Requests to cancel, exit, or reset booking flow → booking_tool (e.g., "cancel booking", "exit booking", "reset")

Examples of specific routing:
- "Do you have breakfast?" → vector_tool
- "What time is breakfast served?" → vector_tool
- "Is breakfast included?" → vector_tool
- "Are there vegan options at breakfast?" → vector_tool
- "How much is breakfast?" → vector_tool
- "Show me a calendar of available rooms" → booking_tool 
- "I want to see which dates are available" → booking_tool
- "When are rooms free?" → booking_tool
- "Can I see the room availability calendar?" → booking_tool
- "Cancel my booking" → booking_tool
- "Exit the booking form" → booking_tool
- "Go back to chat" → booking_tool

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

Question: "{question}"
Tool:
""")

# ========================================
# 🎭 LangChain Agent Setup
# ========================================

agent_executor = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    agent_kwargs={
        "system_message": """You are George, the friendly AI receptionist at Chez Govinda.

Always follow these rules:

- ✅ Use `vector_tool` for room types, room descriptions, hotel policies, breakfast, and amenities.
- ❌ Never use `sql_tool` for room descriptions or general hotel info.
- ✅ Use `sql_tool` only for checking availability, bookings, or price queries.
- ✅ Use `booking_tool` when users want to book a room OR see a visual calendar of room availability.
- ✅ Use `booking_tool` when users want to cancel, exit, or reset the booking process.

If someone asks about rooms, **always return the full list of the seven room types** from hotel documentation in the database.

If a user asks a question unrelated to the hotel, kindly respond with something like:
"I'm here to assist with hotel-related questions only. Could you ask something about your stay?"

Speak warmly, like a real hotel receptionist. Use phrases like "our hotel," "we offer," etc.
"""
    }
)


# ========================================
# 🧪 Traced Query Handler
# ========================================

@traceable(name="GeorgeChatbotTrace", run_type="chain", tags=["chat", "routed"])
def process_user_query(input_text: str) -> str:
    # Check if this is a new query while booking form is active
    # Only reset booking mode if the query is not related to the booking process
    cancel_keywords = ["cancel", "exit", "quit", "remove", "stop", "back", "reset"]

    if (st.session_state.get("booking_mode", False) and input_text and
            not any(keyword in input_text.lower() for keyword in cancel_keywords)):
        tool_choice = router_llm.predict(router_prompt.format(question=input_text)).strip()

        # Only exit booking mode if the query is not related to booking
        if tool_choice != "booking_tool":
            st.session_state.booking_mode = False
            st.session_state.show_calendar = False

    tool_choice = router_llm.predict(router_prompt.format(question=input_text)).strip()

    def execute_tool(tool_name: str, query: str):
        if tool_name == "sql_tool":
            return sql_tool.func(query)
        elif tool_name == "vector_tool":
            return vector_tool.func(query)
        elif tool_name == "booking_tool":
            return booking_tool.func(query)
        elif tool_name == "chat_tool":
            return chat_tool.func(query)
        else:
            return f"Error: Tool '{tool_name}' not found."

    tool_response = execute_tool(tool_choice, input_text)

    if not tool_response or str(tool_response).strip() == "[]" or "SQL ERROR" in str(tool_response):
        return agent_executor.run(input_text)
    else:
        return str(tool_response)


# ========================================
# 🌐 Streamlit Configuration
# ========================================

st.set_page_config(
    page_title="Chez Govinda – AI Hotel Assistant",
    page_icon="🏨",
    layout="centered",
    initial_sidebar_state="auto"
)
render_header()

# ========================================
# 🛠️ Sidebar: Tools & Dev Panel
# ========================================

with st.sidebar:
    logo = Image.open("assets/logo.png")
    st.image(logo, use_container_width=True)

    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

    st.markdown("### 📄 Documentation")
    st.session_state.show_docs_panel = st.checkbox(
        "