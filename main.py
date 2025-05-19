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
from langchain.chains import LLMChain
from langchain.callbacks import LangChainTracer
from langchain.memory import ConversationSummaryMemory
from langchain_core.runnables import RunnablePassthrough

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

Choose the most appropriate tool for the user's question, considering both the keywords and the conversation history.

Available tools:
- sql_tool: For checking room availability, prices, booking status, or existing reservation details.
- vector_tool: For general hotel information, room descriptions, amenities, policies, and frequently asked questions.
- booking_tool: When the user wants to make, confirm, or modify a booking.
- chat_tool: For casual conversation, greetings, and questions that don't fit the other tools, OR SPECIFICALLY ABOUT: website, smoking, quiet hours, parties, events, languages spoken, OR when continuing a conversation about a specific topic where chat_tool has already been used.

ROUTING RULES:
1.  If the user is continuing a conversation about a specific topic (e.g., a previous booking, a special occasion, room preferences, or a service request), prioritize the tool that was most relevant to that topic.
2.  Avoid switching tools unnecessarily. If a tool has been helpful in the recent past, consider using it again unless the current question clearly requires a different tool.
3.  If the user asks a question that requires specific data retrieval or manipulation (e.g., booking details, prices, availability, modifications), use sql_tool.
4.  If the user asks for general information or assistance, and the conversation history doesn't suggest a more specific tool, use chat_tool or vector_tool. Choose the most appropriate.
5.  **ANY question containing keywords:** smoke, smoking, where can I smoke → chat_tool
6.  **ANY question containing keywords:** website, link, url → chat_tool
7.  **ANY question containing keywords:** quiet hours, noise after, sleep time → chat_tool
8.  **ANY question containing keywords:** parties, events, gatherings → chat_tool
9.  **ANY question containing keywords:** languages, speak, parler, spreken → chat_tool
10. **If the user asks about room types, room features, or amenities in the context of a special occasion (e.g., "romantic," "honeymoon," "celebration"), use chat_tool to provide tailored suggestions.**
11. **If the user is asking multiple clarifying questions within a short time frame (e.g., "What's the price?" followed by "Is breakfast included?"), stick with the tool that handled the initial question if possible.**
12. **If the user expresses a desire to perform an action (e.g., "I want to book a room," "Can I change my reservation?"), use booking_tool.**

Conversation History:
{history}

Question: "{question}"
Tool:
""")

router_chain = LLMChain(llm=router_llm, prompt=router_prompt, output_key="tool_choice")


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


def process_user_query(input_text: str) -> str:
    # Get the conversation history from memory
    conversation_history = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

    # Invoke the router chain, passing in the history
    route_result = router_chain.invoke(
        {"question": input_text, "history": conversation_history},
        config={"callbacks": [LangChainTracer()]}
    )
    tool_choice = route_result["tool_choice"].strip()

    logger.info(f"Tool selected: {tool_choice}")

    tool_response = execute_tool(tool_choice, input_text)

    # Save this interaction to memory
    st.session_state.george_memory.save_context(
        {"input": input_text},
        {"output": tool_response}
    )

    return str(tool_response)


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