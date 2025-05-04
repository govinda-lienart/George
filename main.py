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
            st.subheader("🔍 Debug: Database Connection Settings")
            st.code(f"""
port    = {get_secret('DB_PORT_READ_ONLY')}
channel = {get_secret('DB_USERNAME_READ_ONLY')}
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
if not st.session_state.show_sql_panel:
    st.markdown("### 💬 George the Assistant")

    user_input = st.chat_input("Ask about availability, bookings, or anything else...")
    if user_input:
        st.session_state.history.append(("user", user_input))
        with st.spinner("George is replying..."):
            response = agent.run(user_input)
        st.session_state.history.append(("bot", response))

    # ✅ Render conversation so far
    render_chat_bubbles(st.session_state.history)

    # ✅ Inline: show booking form right after relevant reply
    if st.session_state.booking_mode:
        render_booking_form()

    # ✅ Inline: add booking confirmation as chat reply
    if st.session_state.get("booking_success") and st.session_state.get("booking_result"):
        result = st.session_state.booking_result
        confirmation_text = (
            f"✅ **Booking confirmed!**\n\n"
            f"**Booking Number:** {result['booking_number']}\n"
            f"**Room Type:** {result['room_type']}\n"
            f"**Guests:** {result['num_guests']}\n"
            f"**Total Price:** €{result['total_price']}\n\n"
            f"A confirmation email has been sent to {result['email']}."
        )
        st.session_state.history.append(("bot", confirmation_text))
        # Reset to avoid duplicate confirmation
        st.session_state.booking_success = False
        st.session_state.booking_result = None

    # ✅ Re-render with new history including confirmation
    render_chat_bubbles(st.session_state.history)
