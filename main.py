import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import mysql.connector
from PIL import Image

# ✅ NEW: Faster agent libraries
from langchain.agents import AgentExecutor
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import AgentTokenBufferMemory
from langchain.agents.openai_functions_agent.base import create_openai_functions_agent
from langchain.schema.messages import SystemMessage
from langchain.agents.openai_functions_agent.base import create_openai_functions_agent

# ✅ Your tools
from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

# ✅ Your UI and LLM config
from utils.config import llm
from chat_ui import render_header, render_chat_bubbles, get_user_input
from booking.calendar import render_booking_form

# ========================================
# 🔁 Load .env for local fallback
# ========================================
load_dotenv()

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ========================================
# ⚙️ Streamlit page config
# ========================================
st.set_page_config(
    page_title="Chez Govinda – AI Hotel Assistant",
    page_icon="🏨",
    layout="centered",
    initial_sidebar_state="auto"
)
render_header()

# ========================================
# 🧠 Sidebar Developer Tools
# ========================================
with st.sidebar:
    logo = Image.open("assets/logo.png")
    st.image(logo, use_container_width=True)

    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

# ========================================
# 🔍 SQL Query Panel
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
            st.subheader("🔍 Debug: Database Connection Settings")
            st.code(f"""
port    = {get_secret('DB_PORT_READ_ONLY')}
user    = {get_secret('DB_USERNAME_READ_ONLY')}
            """)

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
                st.caption(f"Columns: {col_names}")

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
# 🤖 LangChain OpenAI Function Agent Setup
# ========================================
if "history" not in st.session_state:
    st.session_state.history = []

if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""

if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

# ✅ Create faster function-calling agent
agent = create_openai_functions_agent(
    llm=llm,
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    system_message=SystemMessage(
        content="""
You are George, the friendly AI receptionist at Chez Govinda.

Use tools to answer user questions about hotel rooms, availability, bookings, policies, and breakfast.

Always use `vector_tool` for hotel descriptions, and `sql_tool` for availability and pricing.

Reply warmly and clearly like a hotel receptionist. Do not simulate thought steps. Just call the right tool and respond directly.
"""
    )
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    verbose=True,
    handle_parsing_errors=True
)

# ========================================
# 💬 George the Assistant (chatbot)
# ========================================
if not st.session_state.show_sql_panel:

    if not st.session_state.history:
        st.session_state.history.append((
            "bot",
            "👋 Hello, I’m George. How can I help you today?"
        ))

    render_chat_bubbles(st.session_state.history)

    user_input = get_user_input()
    if user_input:
        st.session_state.history.append(("user", user_input))
        render_chat_bubbles(st.session_state.history)

        with st.chat_message("assistant"):
            with st.spinner("🤖 George is typing..."):
                response = agent_executor.run(user_input)

        st.session_state.history.append(("bot", response))
        st.rerun()

# ========================================
# 📅 Show Booking Form if Triggered
# ========================================
if st.session_state.booking_mode:
    render_booking_form()
