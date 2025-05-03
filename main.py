import streamlit as st
from dotenv import load_dotenv
import os
from langchain.agents import initialize_agent, AgentType

from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool

from utils.config import llm
from chat_ui import render_header, render_chat_bubbles
from booking.calendar import render_booking_form

# Load .env
load_dotenv()

# Streamlit page setup
st.set_page_config(page_title="Chez Govinda – AI Hotel Assistant", page_icon="🏨")
render_header()

# ================================
# 🛠️ Sidebar Toggle for SQL Panel
# ================================
with st.sidebar:
    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

# ================================
# 🔍 SQL Query Panel (if toggled on)
# ================================
if st.session_state.show_sql_panel:
    # Add custom styling for the SQL panel
    st.markdown("""
    <style>
        .status-message {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .success {
            background-color: #ecf9ec;
            color: #1e7e34;
        }
        .info {
            background-color: #e6f2ff;
            color: #0c5460;
        }
    </style>
    """, unsafe_allow_html=True)

    # SQL Panel Header
    st.markdown("### 🔍 SQL Query Panel")

    # SQL query input
    st.markdown("🔎 Enter SQL query to run:")
    sql_input = st.text_area(
        label="",
        value="SELECT * FROM bookings LIMIT 10;",
        height=150,
        key="sql_input_box"
    )

    # Simple button outside columns (cleaner design)
    run_query = st.button("Run Query", key="run_query_button", type="primary")

    import pandas as pd
    import sqlalchemy

    # Status container to show connection status and query progress
    status_container = st.container()

    # Results container
    result_container = st.container()


    def execute_manual_sql(sql_query):
        """
        Connects to the SQL database, executes the given query, and returns the results.

        Args:
            sql_query (str): The SQL query to execute.

        Returns:
            dict: A dictionary containing the query, an optional error message,
                  and an optional Pandas DataFrame of the results.
        """
        try:
            # Show connection attempt status
            with status_container:
                st.markdown(f"""
                <div class="status-message info">
                    <span>🔄 Attempting to connect to the database...</span>
                </div>
                """, unsafe_allow_html=True)

            # Get connection details from environment variables
            db_host = os.getenv("DB_HOST")
            db_port = os.getenv("DB_PORT")
            db_username = os.getenv("DB_USERNAME")
            db_password = os.getenv("DB_PASSWORD")
            db_database = os.getenv("DB_DATABASE")

            # Create connection string
            connection_string = f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_database}"

            # Create engine and connect
            engine = sqlalchemy.create_engine(connection_string)
            connection = engine.connect()

            # Show successful connection status
            with status_container:
                st.markdown(f"""
                <div class="status-message success">
                    <span>✅ Successfully connected to MySQL.</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="status-message info">
                    <span>▶️ Running query:</span>
                </div>
                """, unsafe_allow_html=True)

                # Display the query with syntax highlighting
                st.code(f"""
{sql_query}
                """, language="sql")

            # Execute query
            result = connection.execute(sqlalchemy.text(sql_query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())

            return {"query": sql_query, "dataframe": df, "success": True}

        except Exception as e:
            with status_container:
                st.markdown(f"""
                <div class="status-message error" style="background-color: #f8d7da; color: #721c24;">
                    <span>❌ Error: {str(e)}</span>
                </div>
                """, unsafe_allow_html=True)
            return {"query": sql_query, "error": str(e), "success": False}

        finally:
            if 'connection' in locals() and connection:
                connection.close()


    if run_query:
        # Clear previous results
        status_container.empty()
        result_container.empty()

        # Execute query and show results
        result = execute_manual_sql(sql_input)

        # Display results if query was successful
        if result.get("success", False):
            with result_container:
                st.dataframe(result["dataframe"], use_container_width=True)

# ================================
# 🤖 LangChain Agent Setup
# ================================
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

# ================================
# 💬 Chatbot (only if SQL panel is off)
# ================================
if not st.session_state.show_sql_panel:
    st.markdown("### 💬 George the Assistant")
    user_input = st.chat_input("Ask about availability, bookings, or anything else...")
    if user_input:
        st.session_state.history.append(("user", user_input))
        with st.spinner("George is replying..."):
            response = agent.run(user_input)
        st.session_state.history.append(("bot", response))

# ================================
# 💬 Chat History UI
# ================================
if not st.session_state.show_sql_panel:
    render_chat_bubbles(st.session_state.history)

# ================================
# 📅 Booking Form if Triggered
# ================================
if st.session_state.booking_mode:
    render_booking_form()