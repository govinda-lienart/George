# main.py

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
from chat_ui import render_header, render_chat_bubbles
from booking.calendar import render_booking_form

# ===============================
# 🔁 Load .env for local fallback
# ===============================
load_dotenv()

# ✅ Smart getter: streamlit secrets or fallback
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ===============================
# ⚙️ Streamlit page setup
# ===============================
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# ===============================
# 🧠 Developer Tools in sidebar
# ===============================
with st.sidebar:
    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

# ===============================
# 🔍 SQL Panel
# ===============================
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
            st.subheader("🔍 Debug: Connection Info")
            st.code(f"host = {get_secret('DB_HOST_READ_ONLY')}\nuser = {get_secret('DB_USERNAME_READ_ONLY')}")

            with status_container:
                st.write("🔐 Connecting...")

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
                st.error("❌ Query failed:")
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
                    st.warning(f"⚠️ Close failed:\n\n{close_err}")

# ===============================
# 💬 Chatbot section
# ===============================
if "history" not in st.session_state:
    st.session_state.history = [("bot", "How may I assist you today?")]
if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False
if "booking_success" not in st.session_state:
    st.session_state.booking_success = False
if "booking_result" not in st.session_state:
    st.session_state.booking_result = None

# ✅ Init LangChain Agent
agent = initialize_agent(
    tools=[sql_tool, vector_tool, chat_tool, booking_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# ✅ Render chat + form
if not st.session_state.show_sql_panel:

    # 🗨️ Chat history
    render_chat_bubbles(st.session_state.history)

    # 📅 If booking triggered
    if st.session_state.booking_mode:
        render_booking_form()

        # 📨 Add confirmation to chat
        if st.session_state.booking_success and st.session_state.booking_result:
            result = st.session_state.booking_result
            confirmation = (
                f"✅ **Booking confirmed!**\n\n"
                f"**Booking Number:** {result['booking_number']}\n"
                f"**Room Type:** {result['room_type']}\n"
                f"**Guests:** {result['num_guests']}\n"
                f"**Total Price:** €{result['total_price']}\n\n"
                f"A confirmation email has been sent to {result['email']}."
            )
            st.session_state.history.append(("bot", confirmation))
            st.session_state.booking_success = False
            st.session_state.booking_result = None
            st.rerun()

    # 💬 Input
    user_input = st.chat_input("Ask about availability, bookings, or anything else...")
    if user_input:
        st.session_state.history.append(("user", user_input))
        render_chat_bubbles(st.session_state.history)

        # ⏳ Show temporary placeholder
        with st.chat_message("assistant"):
            st.markdown("⏳ Thinking...")

        # 🤖 Run agent
        response = agent.run(user_input)

        # 💬 Add reply to history
        st.session_state.history.append(("bot", response))
        st.rerun()
