# ========================================
# 📆 Imports and Initialization
# ========================================

import os
import streamlit as st
import pandas as pd
import mysql.connector
from PIL import Image
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv
from logger import logger, log_stream

# LangChain memory (for better follow-up understanding)
from langchain.memory import ConversationSummaryMemory

# Updated imports for LangSmith tracing
from langchain.callbacks.tracers.langchain import LangChainTracer
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.tracers import ConsoleCallbackHandler

# 🔧 Custom tool modules
from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool
from chat_ui import render_header, get_user_input, render_chat_bubbles
from booking.calendar import render_booking_form
from utils.config import llm

logger.info("App launched")
load_dotenv()

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")  # Get from environment variables
os.environ["LANGCHAIN_PROJECT"] = "chez-govinda-assistant"

# ✅ Initialize lightweight conversation memory
if "george_memory" not in st.session_state:
    st.session_state.george_memory = ConversationSummaryMemory(
        llm=ChatOpenAI(model_name="gpt-3.5-turbo"),
        memory_key="summary",
        return_messages=False
    )


def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# 🧠 Lightweight Tool Router LLM
router_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

router_prompt = PromptTemplate.from_template("""
You are a routing assistant for an AI hotel receptionist named George at Chez Govinda.

Choose the correct tool for the user's question, following these guidelines:

Available tools:
- sql_tool: For checking room availability, prices, booking status, or existing reservation details
- vector_tool: For room descriptions, hotel policies, breakfast, amenities, dining information
- booking_tool: When the user confirms they want to book a room or asks for help booking
- chat_tool: For basic pleasantries AND any questions unrelated to the hotel

ROUTING RULES:
1. Basic pleasantries (e.g., "How are you?", "Good morning") → chat_tool
2. Personal questions/advice → chat_tool (e.g., relationship advice, personal problems)
3. Questions about external topics → chat_tool (politics, sports, tech, weather)
4. Hotel services, amenities, policies → vector_tool
5. Room availability and prices → sql_tool
6. Booking confirmation → booking_tool
7. ANY questions about breakfast, dining, food options → vector_tool

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

Question: "{question}"
Tool:
""")


# ✅ Updated process_user_query with proper LangSmith tracing
def process_user_query(input_text: str) -> str:
    # Set up tracers and callback manager
    console_handler = ConsoleCallbackHandler()
    langchain_tracer = LangChainTracer(project_name="chez-govinda-assistant")
    callback_manager = CallbackManager([langchain_tracer, console_handler])

    # Log the start of query processing
    logger.info(f"Processing query: {input_text}")

    # First, use the router to determine which tool to use
    tool_choice_prompt = router_prompt.format(question=input_text)

    try:
        # Get tool choice with callbacks to trace this step
        tool_choice = router_llm.predict(
            tool_choice_prompt,
            callbacks=[callback_manager]
        ).strip()

        logger.info(f"Tool selected: {tool_choice}")

        # Execute the appropriate tool with callbacks for tracing
        def execute_tool(tool_name: str, query: str):
            try:
                # Add metadata for tracing
                run_id = f"tool_execution_{tool_name}_{hash(query) % 10000}"

                if tool_name == "sql_tool":
                    return sql_tool.func(query, callbacks=[callback_manager])
                elif tool_name == "vector_tool":
                    return vector_tool.func(query, callbacks=[callback_manager])
                elif tool_name == "booking_tool":
                    return booking_tool.func(query, callbacks=[callback_manager])
                elif tool_name == "chat_tool":
                    return chat_tool.func(query, callbacks=[callback_manager])
                else:
                    error_msg = f"Error: Tool '{tool_name}' not found."
                    logger.error(error_msg)
                    return error_msg
            except Exception as e:
                error_msg = f"Error executing {tool_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return f"I'm sorry, I encountered an error while processing your request. Please try again."

        # Execute the tool and get response
        tool_response = execute_tool(tool_choice, input_text)

        # Save interaction to memory
        st.session_state.george_memory.save_context(
            {"input": input_text},
            {"output": tool_response}
        )

        # Save trace URL for UI
        st.session_state.langsmith_project_url = "https://smith.langchain.com/projects/chez-govinda-assistant"

        return str(tool_response)

    except Exception as e:
        error_msg = f"Error in process_user_query: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}"


# 🌐 Streamlit Config
st.set_page_config(
    page_title="Chez Govinda – AI Hotel Assistant",
    page_icon="🏨",
    layout="centered",
    initial_sidebar_state="auto"
)
render_header()

# 🧠 Sidebar Panels
with st.sidebar:
    logo = Image.open("assets/logo.png")
    st.image(logo, use_container_width=True)

    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )
    st.session_state.show_docs_panel = st.checkbox(
        "📄 Show Documentation",
        value=st.session_state.get("show_docs_panel", False)
    )
    st.session_state.show_log_panel = st.checkbox(
        "📋 Show General Log Panel",
        value=st.session_state.get("show_log_panel", False)
    )
    st.session_state.show_langsmith = st.checkbox(
        "🔍 Show LangSmith Traces",
        value=st.session_state.get("show_langsmith", False)
    )

    if st.button("🧪 Run Chat Routing Test"):
        result = process_user_query("Can I book a room with breakfast?")
        st.success("✅ Test Response:")
        st.info(result)

# 📚 Docs Panel
if st.session_state.get("show_docs_panel"):
    st.markdown("### 📖 Technical Documentation")
    st.components.v1.iframe("https://www.google.com")

# 🧪 SQL Debug Panel
if st.session_state.show_sql_panel:
    st.markdown("### 🔍 SQL Query Panel")
    sql_input = st.text_area("🔍 Enter SQL query to run:", "SELECT * FROM bookings LIMIT 10;")
    if st.button("Run Query"):
        try:
            conn = mysql.connector.connect(
                host=get_secret("DB_HOST_READ_ONLY"),
                port=int(get_secret("DB_PORT_READ_ONLY", 3306)),
                user=get_secret("DB_USERNAME_READ_ONLY"),
                password=get_secret("DB_PASSWORD_READ_ONLY"),
                database=get_secret("DB_DATABASE_READ_ONLY")
            )
            cursor = conn.cursor()
            cursor.execute(sql_input)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=cols)
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ SQL Error: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

# 💬 Chat Interface
if not st.session_state.show_sql_panel:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    if not st.session_state.history:
        st.session_state.history.append(("bot", "👋 Hello, I'm George. How can I help you today?"))

    render_chat_bubbles(st.session_state.history)

    if st.session_state.get("booking_mode"):
        render_booking_form()
        if st.button("❌ Remove Booking Form"):
            st.session_state.booking_mode = False
            st.session_state.history.append(("bot", "Booking form removed. How else can I help you today?"))
            st.rerun()

    user_input = get_user_input()

    if user_input:
        logger.info(f"User asked: {user_input}")
        st.session_state.history.append(("user", user_input))
        st.session_state.user_input = user_input
        st.rerun()

    if st.session_state.user_input:
        with st.chat_message("assistant"):
            with st.spinner("🧠 George is typing..."):
                try:
                    response = process_user_query(st.session_state.user_input)
                    st.write(response)
                    st.session_state.history.append(("bot", response))

                    # Display LangSmith trace link if enabled
                    if st.session_state.get("show_langsmith") and "langsmith_project_url" in st.session_state:
                        st.markdown(
                            f"""<div style="padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin-top: 10px;">
                            <p><b>🔍 Query Traces:</b> <a href="{st.session_state.langsmith_project_url}" target="_blank">
                            View execution traces in LangSmith</a></p>
                            </div>""",
                            unsafe_allow_html=True
                        )

                except Exception as e:
                    error_msg = f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    st.error(error_msg)
                    st.session_state.history.append(("bot", error_msg))

        st.session_state.user_input = ""
        st.rerun()

# 📋 Log Panel
if st.session_state.get("show_log_panel"):
    st.markdown("### 📋 Log Output")
    raw_logs = log_stream.getvalue()
    filtered_lines = [line for line in raw_logs.splitlines() if "App launched" not in line]
    formatted_logs = ""
    for line in filtered_lines:
        if "—" in line:
            ts, msg = line.split("—", 1)
            formatted_logs += f"\n\n**{ts.strip()}** — {msg.strip()}"
        else:
            formatted_logs += f"\n{line}"
    if formatted_logs.strip():
        st.markdown(f"<div class='log-box'>{formatted_logs}</div>", unsafe_allow_html=True)
    else:
        st.info("No logs yet.")
    st.download_button("⬇️ Download Log File", "\n".join(filtered_lines), "general_log.log")