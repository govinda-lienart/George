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
- vector_tool: For room descriptions, hotel policies, breakfast, amenities
- booking_tool: When the user confirms they want to book a room or asks for help booking
- chat_tool: For basic pleasantries AND any questions unrelated to the hotel

ROUTING RULES:
1. Basic pleasantries (e.g., "How are you?", "Good morning") → chat_tool
2. Personal questions/advice → chat_tool (e.g., relationship advice, personal problems)
3. Questions about external topics → chat_tool (politics, sports, tech, weather)
4. Hotel services, amenities, policies → vector_tool
5. Room availability and prices → sql_tool
6. Booking confirmation → booking_tool

Examples of chat_tool questions:
- "How are you today?"
- "Should I divorce my wife?"
- "What's the weather like?"
- "How's your day going?"
- "Tell me about politics"

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
    # Reset booking mode if user is asking a new question instead of filling the form
    if st.session_state.get("booking_mode", False) and input_text:
        st.session_state.booking_mode = False

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
        "📄 Show Documentation",
        value=st.session_state.get("show_docs_panel", False)
    )

    if st.button("🧪 Run Chat Routing Test"):
        result = process_user_query("Can I book a room with breakfast?")
        st.success("✅ Test Response:")
        st.info(result)

# ========================================
# 📚 Docs Panel
# ========================================

if st.session_state.get("show_docs_panel"):
    st.markdown("### 📖 Technical Documentation")
    st.components.v1.iframe("https://www.google.com")

# ========================================
# 🗒️ SQL Debug Panel
# ========================================

if st.session_state.show_sql_panel:
    st.markdown("### 🔍 SQL Query Panel")
    sql_input = st.text_area(
        "🔍 Enter SQL query to run:",
        value="SELECT * FROM bookings LIMIT 10;",
        height=150,
        key="sql_input_box"
    )
    run_query = st.button("Run Query", key="run_query_button", type="primary")
    status_container = st.container()
    result_container = st.container()

    if run_query:
        try:
            with status_container:
                st.write("🔐 Connecting to database...")
            conn = mysql.connector.connect(
                host=get_secret("DB_HOST_READ_ONLY"),
                port=int(get_secret("DB_PORT_READ_ONLY", 3306)),
                user=get_secret("DB_USERNAME_READ_ONLY"),
                password=get_secret("DB_PASSWORD_READ_ONLY"),
                database=get_secret("DB_DATABASE_READ_ONLY")
            )
            with status_container:
                st.success("✅ Connected to MySQL!")
            cursor = conn.cursor()
            cursor.execute(sql_input)
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            with result_container:
                df = pd.DataFrame(rows, columns=col_names)
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            import traceback

            with status_container:
                st.error("❌ Connection failed:")
                st.code(traceback.format_exc())
        finally:
            try:
                if 'conn' in locals() and conn.is_connected():
                    cursor.close()
                    conn.close()
                    with status_container:
                        st.info("🔌 Connection closed.")
            except Exception as close_err:
                with status_container:
                    st.warning(f"⚠️ Error closing connection:\n\n{close_err}")

# ========================================
# 💬 Chatbot Interface
# ========================================

if not st.session_state.show_sql_panel:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "chat_summary" not in st.session_state:
        st.session_state.chat_summary = ""
    if "booking_mode" not in st.session_state:
        st.session_state.booking_mode = False
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    if not st.session_state.history:
        st.session_state.history.append(("bot", "👋 Hello, I'm George. How can I help you today?"))

    render_chat_bubbles(st.session_state.history)

    # Only show booking form if in booking mode
    if st.session_state.booking_mode:
        render_booking_form()
        # Add a cancel button for the booking form
        if st.button("❌ Cancel Booking", key="cancel_booking_button"):
            st.session_state.booking_mode = False
            st.session_state.history.append(("bot", "Booking cancelled. How else can I help you today?"))
            st.rerun()

    user_input = get_user_input()

    if user_input:
        st.session_state.history.append(("user", user_input))
        st.session_state.user_input = user_input
        st.rerun()

    if st.session_state.user_input:
        with st.chat_message("assistant"):
            with st.spinner("🧠 George is thinking..."):
                try:
                    response = process_user_query(st.session_state.user_input)
                    st.write(response)
                    st.session_state.history.append(("bot", response))
                except Exception as e:
                    response = f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}"
                    st.error(response)
                    st.session_state.history.append(("bot", response))

        st.session_state.user_input = ""
        st.rerun()

# ========================================
# 🩵 End Tracing
# ========================================

wait_for_all_tracers()