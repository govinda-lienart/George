import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import mysql.connector
from langchain.agents import initialize_agent, AgentType

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

from utils.config import llm
from chat_ui import render_header # Assuming this only renders the header
from booking.calendar import render_booking_form

# ========================================
# 🔁 Load .env for local fallback
# ========================================
load_dotenv()

# ========================================
# ✅ Smart secret getter: Cloud or local
# ========================================
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ========================================
# ⚙️ Streamlit page config
# ========================================
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# ========================================
# 🧠 Developer tools toggle in sidebar
# ========================================
with st.sidebar:
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
            # 🔎 DEBUG: Print connection info (not password)
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
# 🤖 LangChain Agent Setup
# ========================================
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_summary" not in st.session_state:
    st.session_state.chat_summary = ""
if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

agent = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# ========================================
# 💬 George the Assistant (chatbot)
# ========================================
def render_chat_bubbles(history):
    for role, message in history:
        with st.chat_message(role):
            st.markdown(message)

if not st.session_state.show_sql_panel:
    st.markdown("### 💬 George the Assistant")

    user_input = st.chat_input("Ask about availability, bookings, or anything else...", key="user_chat_input")

    if user_input:
        # Append user's message to history IMMEDIATELY
        st.session_state.history.append(("user", user_input))

        # Clear the input field in the session state
        st.session_state["user_chat_input"] = ""

        # Force a rerun to update the UI with the user's message
        st.rerun()

    # Render the entire chat history
    render_chat_bubbles(st.session_state.history)

    # If there was user input in the last interaction, process it now (after the UI has updated)
    if st.session_state.get("last_user_input") and not st.session_state.get("processing"):
        st.session_state["processing"] = True
        with st.chat_message("assistant"):
            bot_message_container = st.empty()
            bot_message_container.markdown("⏳ George is replying...")
            response = agent.run(st.session_state["last_user_input"])
            bot_message_container.markdown(response)
            st.session_state.history.append(("bot", response))
        st.session_state["last_user_input"] = None
        st.session_state["processing"] = False
        st.rerun() # Rerun to show the bot's response

    # Store the current user input for the next interaction
    if user_input:
        st.session_state["last_user_input"] = user_input

# ========================================
# 📅 Show Booking Form if Triggered
# ========================================
if st.session_state.booking_mode:
    render_booking_form()