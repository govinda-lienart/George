# ========================================
# 📆 Imports and Initialization ###
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
from chat_ui import get_user_input, render_chat_bubbles # Removed render_header from import
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

Choose the correct tool for the user's question, following these guidelines:

Available tools:
- sql_tool: For checking room availability, prices, booking status, or existing reservation details
- vector_tool: For room descriptions, hotel policies, breakfast, amenities, dining information
- booking_tool: When the user confirms they want to book a room or asks for help booking
- chat_tool: For basic pleasantries AND any questions unrelated to the hotel, OR SPECIFICALLY ABOUT: website, smoking, quiet hours, parties, events, languages spoken.

ROUTING RULES:
1. Basic pleasantries (e.g., "How are you?", "Good morning") → chat_tool
2. Personal questions/advice → chat_tool (e.g., relationship advice, personal problems)
3. Questions about external topics → chat_tool (politics, sports, tech, weather)
4. **ANY question containing keywords: smoke, smoking, where can I smoke → chat_tool**
5. **ANY question containing keywords: website, link, url → chat_tool**
6. **ANY question containing keywords: quiet hours, noise after, sleep time → chat_tool**
7. **ANY question containing keywords: parties, events, gatherings → chat_tool**
8. **ANY question containing keywords: languages, speak, parler, spreken → chat_tool**
9. Hotel services, amenities, policies (EXCEPT smoking, quiet hours, parties) → vector_tool
10. Room availability and prices → sql_tool
11. Booking confirmation → booking_tool
12. ANY questions about breakfast, dining, food options → vector_tool

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

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
    route_result = router_chain.invoke(
        {"question": input_text},
        config={"callbacks": [LangChainTracer()]}
    )
    tool_choice = route_result["tool_choice"].strip()
    logger.info(f"Tool selected: {tool_choice}")

    tool_response = execute_tool(tool_choice, input_text)

    st.session_state.george_memory.save_context(
        {"input": input_text},
        {"output": tool_response}
    )

    return str(tool_response)


# 🌐 Streamlit Config
st.set_page_config(
    page_title="Chez Govinda – AI Hotel Assistant",
    page_icon="🏨",
    layout="wide",  # Full width layout
    initial_sidebar_state="expanded"
)
# render_header() # This line remains commented out

# 🧠 Sidebar Panels
with st.sidebar:
    logo = Image.open("assets/george_foto.png")
    st.image(logo, use_container_width=True)

    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )
    st.session_state.show_log_panel = st.checkbox(
        "📋 Show General Log Panel",
        value=st.session_state.get("show_log_panel", False)
    )
    st.session_state.show_pipeline = st.checkbox(
        "🔄 Show Pipeline",
        value=st.session_state.get("show_pipeline", False)
    )

    st.markdown("### 🔗 Useful Links")
    link1_text = "Technical Documentation"  # You can customize the text here
    link1_url = "https://govindalienart.notion.site/George-Online-AI-Hotel-Receptionist-1f95d3b67d38809889e1fa689107b5ea?pvs=4"  # Replace with your desired URL
    st.markdown(
        f'<a href="{link1_url}" target="_blank"><button style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; color: #333; text-align: center;">{link1_text}</button></a>',
        unsafe_allow_html=True)

    link2_text = "Chez Govinda Website"  # You can customize the text here
    link2_url = "https://sites.google.com/view/chez-govinda/home"  # Replace with your desired URL
    st.markdown(
        f'<a href="{link2_url}" target="_blank"><button style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; color: #333; text-align: center;">{link2_text}</button></a>',
        unsafe_allow_html=True)

# Display the appropriate title and interface
if st.session_state.get("show_pipeline"):
    st.markdown("### 🔄 George's Assistant Pipeline Overview")
    pipeline_svg_url = "https://www.mermaidchart.com/raw/89841b63-50c1-4817-b115-f31ae565470f?theme=light&version=v0.1&format=svg"
    st.components.v1.html(f"""
        <div style='display: flex; justify-content: center;'>
            <img src="{pipeline_svg_url}" style="width: 95%; max-width: 1600px;">
        </div>
    """, height=700)
elif not st.session_state.show_sql_panel:
    # --- UPDATED HEADER HERE ---
    st.header("CHAT WITH OUR AI HOTEL RECEPTIONIST", divider='gray')
    # --- END UPDATED HEADER ---

    # Only render chat interface when SQL panel is disabled
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