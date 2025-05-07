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
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# ========================================
# 📦 Imports for LangChain tools and UI
# ========================================
from tools.sql_tool import sql_tool
from tools.vector_tool import vector_tool
from tools.chat_tool import chat_tool
from tools.booking_tool import booking_tool
from chat_ui import render_header, render_chat_bubbles, get_user_input
from booking.calendar import render_booking_form

# ========================================
# 🔁 Load environment variables
# ========================================
load_dotenv()

# ========================================
# ✅ Safe secret getter
# ========================================
def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ========================================
# 🧠 Set environment variables
# ========================================
os.environ["LANGSMITH_TRACING"] = get_secret("LANGSMITH_TRACING", "false")
os.environ["LANGSMITH_API_KEY"] = get_secret("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_PROJECT"] = get_secret("LANGSMITH_PROJECT", "George")
os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY", "")

# ========================================
# ⚙️ LangChain LLMs and Prompts
# ========================================
from utils.config import llm

router_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

router_prompt = PromptTemplate.from_template("""
You are a routing assistant for an AI hotel receptionist.

Choose the correct tool for the user's question.

Available tools:
- sql_tool: check room availability, prices, booking status, or existing reservation details
- vector_tool: room descriptions, hotel policies, breakfast, amenities
- booking_tool: when the user confirms they want to book
- chat_tool: if the question is unrelated to the hotel (e.g. weather, personal questions, general small talk)

Important:
- If the question is not related to the hotel, choose `chat_tool`. The assistant will then respond kindly:
  “😊 I can only help with questions about our hotel and your stay. Could you ask something about your visit to Chez Govinda?”

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

Question: "{question}"
Tool:
""")

# ========================================
# 🤖 LangChain Agent Setup
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

Speak warmly, like a real hotel receptionist. Use phrases like “our hotel,” “we offer,” etc.
"""
    }
)

# ========================================
# ✅ LangSmith Trace Functions
# ========================================
@traceable(name="streamlit_trace_test", run_type="chain", tags=["manual", "test"])
def trace_test_info():
    return {"status": "✅ Streamlit is tracing properly", "user": "Govinda", "test": True}

@traceable(name="pure_streamlit_trace", run_type="chain")
def streamlit_hello_world():
    return "✅ Hello from Streamlit with LangSmith!"

@traceable(name="langsmith_test_trace", run_type="chain")
def test_langsmith_trace():
    return llm.invoke("Just say hi to LangSmith.", config={"metadata": {"project_name": "George"}})

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
# 🧠 Developer Tools Sidebar
# ========================================
with st.sidebar:
    logo = Image.open("assets/logo.png")
    st.image(logo, use_container_width=True)
    st.markdown("### 🛠️ Developer Tools")

    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )

    if st.button("🧪 Test LangSmith (LLM)"):
        result = test_langsmith_trace()
        st.success(f"LangSmith test: {result}")

    if st.button("🧪 Send Trace Test Info"):
        result = trace_test_info()
        st.success(f"Traced: {result['status']}")

    if st.button("🔍 Ping LangSmith (String Only)"):
        msg = streamlit_hello_world()
        st.success(msg)

    st.markdown("### 🔍 LangSmith Debug")
    st.text(f"Project: {os.environ.get('LANGSMITH_PROJECT')}")
    st.text(f"Tracing: {os.environ.get('LANGSMITH_TRACING')}")
    st.text(f"API Key Set: {'✅' if os.environ.get('LANGSMITH_API_KEY') else '❌'}")

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
# 💬 George the Assistant
# ========================================
if not st.session_state.show_sql_panel:

    # Chat session state
    if "history" not in st.session_state:
        st.session_state.history = []
    if "chat_summary" not in st.session_state:
        st.session_state.chat_summary = ""
    if "booking_mode" not in st.session_state:
        st.session_state.booking_mode = False

    if not st.session_state.history:
        st.session_state.history.append(("bot", "👋 Hello, I’m George. How can I help you today?"))

    render_chat_bubbles(st.session_state.history)
    user_input = get_user_input()

    # ✅ Wrap tools for tracing
    wrapped_sql_tool = RunnableLambda(sql_tool.func).with_config(run_name="SQL Tool")
    wrapped_vector_tool = RunnableLambda(vector_tool.func).with_config(run_name="Vector Tool")
    wrapped_chat_tool = RunnableLambda(chat_tool.func).with_config(run_name="Chat Tool")
    wrapped_booking_tool = RunnableLambda(booking_tool.func).with_config(run_name="Booking Tool")

    # ✅ Tool execution with wrappers
    def execute_tool(tool_name: str, query: str):
        if tool_name == "sql_tool":
            return wrapped_sql_tool.invoke(query)
        elif tool_name == "vector_tool":
            return wrapped_vector_tool.invoke(query)
        elif tool_name == "booking_tool":
            return wrapped_booking_tool.invoke(query)
        elif tool_name == "chat_tool":
            return wrapped_chat_tool.invoke(query)
        else:
            return f"Error: Tool '{tool_name}' not found."

    if user_input:
        st.session_state.history.append(("user", user_input))
        render_chat_bubbles(st.session_state.history)

        with st.chat_message("assistant"):
            with st.spinner("🤖 George is thinking..."):
                tool_choice = router_llm.predict(router_prompt.format(question=user_input)).strip()
                print(f"Tool chosen by router: {tool_choice}")

                tool_response = execute_tool(tool_choice, user_input)

                if not tool_response or str(tool_response).strip() == "[]" or "SQL ERROR" in str(tool_response):
                    print("Tool response was insufficient or an error occurred. Falling back to main agent.")
                    response = agent_executor.run(user_input)
                else:
                    response = str(tool_response)

        st.session_state.history.append(("bot", response))
        st.rerun()

# ========================================
# 📅 Booking Form
# ========================================
if st.session_state.booking_mode:
    render_booking_form()

# ========================================
# 🧹 Flush LangSmith traces
# ========================================
wait_for_all_tracers()
