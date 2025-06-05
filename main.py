# ========================================
# 📋 ROLE OF THIS SCRIPT - main.py
# ========================================

"""
Main script for the George AI Hotel Receptionist app.
- Routes user questions to booking, info, chat tools.
- Manages conversation memory for context.
- Handles bookings and follow-up messages.
- Provides developer tools like SQL panel and logs.
- Displays the main user interface with chat and booking forms.
"""

# ========================================
# 📦 IMPORTS SECTION
# ========================================

# ────────────────────────────────────────────────
# 📚 STANDARD LIBRARY IMPORTS
# ────────────────────────────────────────────────
import os  # Operating system interfaces, environment variables
import re  # Regular expressions for pattern matching

# ────────────────────────────────────────────────
# 🔧 THIRD-PARTY LIBRARY IMPORTS
# ────────────────────────────────────────────────
import streamlit as st  # Web app framework for interactive UI
import pandas as pd  # To display SQL results in a table
import mysql.connector  # MySQL database connectivity
from PIL import Image  # George photo import
from dotenv import load_dotenv  # Load environment variables from .env file

# ────────────────────────────────────────────────
# 🤖 LANGCHAIN LIBRARY IMPORTS
# ────────────────────────────────────────────────
from langchain.prompts import PromptTemplate  # Prompt template management for LLMs
from langchain.chat_models import ChatOpenAI  # OpenAI Chat model wrapper
from langchain.chains import LLMChain  # Chain together prompts and LLM calls
from langchain.callbacks import LangChainTracer  # Trace LangChain for LangSmith
from langchain.memory import ConversationSummaryMemory  # Memory with conversation summaries

# ────────────────────────────────────────────────
# 🪵 CUSTOM LOGGING UTILITIES
# ────────────────────────────────────────────────
from logger import logger, log_stream  # Custom logging setup and stream

# ────────────────────────────────────────────────
# 🛠️ CUSTOM TOOL MODULES
# ────────────────────────────────────────────────
from tools.sql_tool import sql_tool  # SQL query processing tool
from tools.vector_tool import vector_tool  # Vector search tool
from tools.chat_tool import chat_tool  # Chat processing tool
from tools.booking_tool import booking_tool  # Booking related tool
from tools.followup_tool import create_followup_message, handle_followup_response  # Follow-up message helpers

# ────────────────────────────────────────────────
# 🎨 UI HELPER MODULES
# ────────────────────────────────────────────────
from chat_ui import get_user_input, render_chat_bubbles  # Functions to handle user input and chat UI rendering

# ────────────────────────────────────────────────
# 📅 BOOKING CALENDAR UI
# ────────────────────────────────────────────────
from booking.calendar import render_booking_form  # Render the booking form in the UI

# ========================================
# ⚙️ APPLICATION INITIALIZATION
# ========================================

# ┌─────────────────────────────────────────┐
# │  STARTUP LOGGING & ENVIRONMENT SETUP   │
# └─────────────────────────────────────────┘
logger.info("App launched")
load_dotenv()

# ┌─────────────────────────────────────────┐
# │  CONVERSATION MEMORY INITIALIZATION     │
# └─────────────────────────────────────────┘
# Initialize lightweight conversation memory
if "george_memory" not in st.session_state:
    st.session_state.george_memory = ConversationSummaryMemory(
        llm=ChatOpenAI(model_name="gpt-3.5-turbo"),
        memory_key="summary",
        return_messages=False
    )

# ┌─────────────────────────────────────────┐
# │  FOLLOW-UP STATE TRACKING SETUP        │
# └─────────────────────────────────────────┘
# Setup follow-up state tracking for post-booking activities
if "awaiting_activity_consent" not in st.session_state:
    st.session_state.awaiting_activity_consent = False

if "latest_booking_number" not in st.session_state:
    st.session_state.latest_booking_number = None


# ========================================
# 🔧 UTILITY FUNCTIONS
# ========================================

# ────────────────────────────────────────────────
# 🔐 SECRET MANAGEMENT UTILITY
# ────────────────────────────────────────────────
def get_secret(key: str, default: str = "") -> str:
    """
    Retrieve a secret value by key.
    First tries to get the secret from Streamlit's secrets management.
    If not found, falls back to environment variables.
    Returns a default value if the key is not found in either.
    """
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# ────────────────────────────────────────────────
# 📋 BOOKING NUMBER EXTRACTION UTILITY
# ────────────────────────────────────────────────
def extract_booking_number_from_result(booking_result: str) -> str:
    """
    Extract booking reference number from a booking confirmation string.
    The extracted booking number is stored in st.session_state.latest_booking_number to remember it throughout the user's session.
    """
    try:
        # Common patterns for booking references
        patterns = [
            r"[Bb]ooking\s+(?:confirmed|reference|ref|number)[\s:]+([A-Z0-9]+)",
            r"[Rr]eference[\s:]+([A-Z0-9]+)",
            r"[Bb]ooking[\s#:]+([A-Z0-9]+)",
            r"[Cc]onfirmation[\s#:]+([A-Z0-9]+)",
            r"REF[\s:]*([A-Z0-9]+)",
            r"#([A-Z0-9]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, booking_result)
            if match:
                booking_number = match.group(1)
                logger.info(f"📋 Extracted booking number: {booking_number}")
                return booking_number

        logger.warning("No booking number found in booking result")
        return None

    except Exception as e:
        logger.error(f"Error extracting booking number: {e}")
        return None


# ========================================
# 🧠 AI ROUTING SYSTEM CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 🤖 ROUTER LLM SETUP
# ────────────────────────────────────────────────
# Lightweight Tool Router LLM - the decision-making brain
router_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# ────────────────────────────────────────────────
# 📝 ROUTER PROMPT TEMPLATE WITH CONVERSATION CONTEXT
# ────────────────────────────────────────────────

router_prompt = PromptTemplate.from_template("""
You are a routing assistant for an AI hotel receptionist named George at Chez Govinda.

Choose the correct tool for the user's question, following these guidelines:

Available tools:
- sql_tool: For checking room availability, prices, booking status, or existing reservation details
- vector_tool: For room descriptions, hotel policies, breakfast, amenities, dining information, location, address, street, AND ROOM RECOMMENDATIONS
- booking_tool: When the user confirms they want to book a room or asks for help booking
- chat_tool: For basic pleasantries AND any questions unrelated to the hotel, OR SPECIFICALLY ABOUT: website, smoking, quiet hours, parties, events, languages spoken.

ROUTING RULES:
1. Basic pleasantries (e.g., "How are you?", "Good morning") → chat_tool
2. Personal questions/advice → chat_tool (e.g., relationship advice, personal problems)
3. Questions about external topics → chat_tool (politics, sports, tech, weather)
4. **ANY question containing keywords: smoke, smoking, where can I smoke → chat_tool**
5. **ANY question containing keywords: website, link, url → chat_tool**
6. **ANY question containing keywords: quiet hours, noise after, sleep time → chat_tool**
7. **ANY question containing keywords: nearby attractions, parties, events, gatherings → chat_tool**
8. **ANY question containing keywords: languages, speak, parler, spreken → chat_tool**
9. **ROOM RECOMMENDATIONS: which room, recommend room, best room, romantic room, budget room, cheap room, poor, affordable → vector_tool**
10. Hotel services, amenities, policies (EXCEPT smoking, quiet hours, parties) → vector_tool
11. Room availability and prices → sql_tool
12. Booking confirmation → booking_tool
13. ANY questions about breakfast, dining, food options → vector_tool
14. Pets → vector_tool
15. **IF conversation mentions room prices and user asks "what about [room]?" → sql_tool**
16. **IF conversation mentions room features and user asks "what about [room]?" → vector_tool**17. **Direct price questions: "price", "cost", "how much" → sql_tool**
17. Room recommendations: "which room", "recommend", "best room" → vector_tool
18. Room descriptions and amenities → vector_tool

EXAMPLES:
- Previous: "price for economy room" Current: "what about family room?" → sql_tool (price follow-up)
- Previous: "features of economy room" Current: "what about family room?" → vector_tool (features follow-up)

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

Question: "{question}"
Tool:
""")

# ────────────────────────────────────────────────
# 🔗 ROUTER CHAIN CREATION
# ────────────────────────────────────────────────
router_chain = LLMChain(llm=router_llm, prompt=router_prompt, output_key="tool_choice")


# ========================================
# ⚡ CORE INTELLIGENCE ENGINE
# ========================================

# ────────────────────────────────────────────────
# 🧠 MAIN USER QUERY PROCESSING FUNCTION
# ────────────────────────────────────────────────
def process_user_query(input_text: str) -> str:
    """George AI's core intelligence engine that routes user messages to appropriate tools and manages conversation flow."""

    # ┌─────────────────────────────────────────┐
    # │  PRIORITY: POST-BOOKING FOLLOW-UP       │
    # └─────────────────────────────────────────┘
    # If awaiting user consent for activity after booking, handle that first
    if st.session_state.awaiting_activity_consent:
        try:
            response = handle_followup_response(input_text, st.session_state)
            # Reset the consent flag after handling
            st.session_state.awaiting_activity_consent = False
            logger.info("Follow-up conversation completed")
            return response
        except Exception as e:
            logger.error(f"Follow-up response failed: {e}")
            st.session_state.awaiting_activity_consent = False
            return "I'm sorry, I had trouble processing your response. How else can I help you today?"

    # ┌─────────────────────────────────────────┐
    # │  NORMAL ROUTING & PROCESSING PIPELINE   │
    # └─────────────────────────────────────────┘
    # Otherwise, route question to appropriate tool as usual
    try:
        # ⚡ STEP 1: AI ROUTING DECISION WITH CONTEXT
        conversation_summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")

        # Add debugging to see what context the router gets
        logger.info(f"🧠 Conversation summary being sent to router: {conversation_summary[:200]}...")

        route_result = router_chain.invoke(
            {
                "question": input_text,
                "conversation_summary": conversation_summary
            },
            config={"callbacks": [LangChainTracer()]}
        )
        tool_choice = route_result["tool_choice"].strip()
        logger.info(f"Tool selected: {tool_choice} (with context: {len(conversation_summary)} chars)")

        # ⚡ STEP 2: TOOL EXECUTION
        tool_response = execute_tool(tool_choice, input_text)

        # ⚡ STEP 3: CONVERSATION MEMORY STORAGE
        # Save conversation to memory for context
        st.session_state.george_memory.save_context(
            {"input": input_text},
            {"output": tool_response}
        )

        return str(tool_response)

    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
        return "I'm sorry, I encountered an error processing your request. Please try again or rephrase your question."


# ────────────────────────────────────────────────
# 🛠️ TOOL EXECUTION DISPATCHER
# ────────────────────────────────────────────────
def execute_tool(tool_name: str, query: str):
    """
    Executes the appropriate tool based on the tool name and handles post-booking follow-up if needed.
    """
    # ┌─────────────────────────────────────────┐
    # │  TOOL ROUTING LOGIC                     │
    # └─────────────────────────────────────────┘
    if tool_name == "sql_tool":
        return sql_tool.func(query)
    elif tool_name == "vector_tool":
        return vector_tool.func(query)
    elif tool_name == "booking_tool":
        result = booking_tool.func(query)

        # ┌─────────────────────────────────────────┐
        # │  POST-BOOKING FOLLOW-UP TRIGGER         │
        # └─────────────────────────────────────────┘
        # Check if booking was just completed (set by calendar.py)
        if st.session_state.get("booking_just_completed", False):
            try:
                followup = create_followup_message()  # Uses booking data from session state
                st.session_state.awaiting_activity_consent = followup["awaiting_activity_consent"]
                st.session_state.booking_just_completed = False  # Reset flag

                # Add follow-up message to chat
                return result + "\n\n" + followup["message"]
            except Exception as e:
                logger.error(f"Follow-up failed: {e}")
                return result
        else:
            return result
    elif tool_name == "chat_tool":
        return chat_tool.func(query)


# ========================================
# 🖥️ STREAMLIT APPLICATION SETUP
# ========================================

# ────────────────────────────────────────────────
# ⚙️ PAGE CONFIGURATION (MUST BE FIRST)
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Chez Govinda – AI Hotel Assistant",
    page_icon="🏨",
    layout="wide",  # Full width layout
    initial_sidebar_state="expanded"
)
# render_header() # This line remains commented out

# ========================================
# 🧭 SIDEBAR INTERFACE
# ========================================

# ────────────────────────────────────────────────
# 🎨 SIDEBAR LAYOUT & BRANDING
# ────────────────────────────────────────────────
with st.sidebar:
    # ┌─────────────────────────────────────────┐
    # │  GEORGE'S PHOTO DISPLAY                 │
    # └─────────────────────────────────────────┘
    logo = Image.open("assets/george_foto.png")
    st.image(logo, use_container_width=True)

    # ┌─────────────────────────────────────────┐
    # │  DEVELOPER TOOLS SECTION                │
    # └─────────────────────────────────────────┘
    st.markdown("### 🛠️ Developer Tools")
    st.session_state.show_sql_panel = st.checkbox(
        "🧠 Enable SQL Query Panel",
        value=st.session_state.get("show_sql_panel", False)
    )
    st.session_state.show_log_panel = st.checkbox(
        "📋 Show General Log Panel",
        value=st.session_state.get("show_log_panel", False)
    )

    # ┌─────────────────────────────────────────┐
    # │  EXTERNAL LINKS SECTION                 │
    # └─────────────────────────────────────────┘
    st.markdown("### 🔗 Useful Links")
    link1_text = "Technical Documentation"
    link1_url = "https://govindalienart.notion.site/George-Online-AI-Hotel-Receptionist-1f95d3b67d38809889e1fa689107b5ea?pvs=4"
    st.markdown(
        f'<a href="{link1_url}" target="_blank"><button style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; color: #333; text-align: center;">{link1_text}</button></a>',
        unsafe_allow_html=True)
    link3_text = "System Architecture Diagram"
    link3_url = "https://bejewelled-nougat-9ce61a.netlify.app"
    st.markdown(
        f'<a href="{link3_url}" target="_blank"><button style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; color: #333; text-align: center;">{link3_text}</button></a>',
        unsafe_allow_html=True)
    link2_text = "Chez Govinda Website"
    link2_url = "https://sites.google.com/view/chez-govinda/home"
    st.markdown(
        f'<a href="{link2_url}" target="_blank"><button style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; color: #333; text-align: center;">{link2_text}</button></a>',
        unsafe_allow_html=True)

# ========================================
# 🖥️ MAIN CONTENT DISPLAY SYSTEM
# ========================================

# ────────────────────────────────────────────────
# 🔄 MODE 1: PIPELINE VISUALIZATION (Developer Tool)
# ────────────────────────────────────────────────
if st.session_state.get("show_pipeline"):
    st.markdown("### 🔄 George's Assistant Pipeline Overview")
    pipeline_svg_url = "https://www.mermaidchart.com/raw/89841b63-50c1-4817-b115-f31ae565470f?theme=light&version=v0.1&format=svg"
    st.components.v1.html(f"""
        <div style='display: flex; justify-content: center;'>
            <img src="{pipeline_svg_url}" style="width: 95%; max-width: 1600px;">
        </div>
    """, height=700)

# ────────────────────────────────────────────────
# 💬 MODE 2: NORMAL CHAT INTERFACE (Main User Experience)
# ────────────────────────────────────────────────
elif not st.session_state.show_sql_panel:

    # ┌─────────────────────────────────────────┐
    # │  CHAT INTERFACE HEADER                  │
    # └─────────────────────────────────────────┘
    st.header("CHAT WITH OUR AI HOTEL RECEPTIONIST", divider='gray')

    # ┌─────────────────────────────────────────┐
    # │  CHAT HISTORY INITIALIZATION            │
    # └─────────────────────────────────────────┘
    # Initialize empty chat history if first visit
    if "history" not in st.session_state:
        st.session_state.history = []
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    # Add George's welcome message if no conversation yet
    if not st.session_state.history:
        st.session_state.history.append(("bot", "👋 Hello, I'm George. How can I help you today?"))

    # ┌─────────────────────────────────────────┐
    # │  RENDER EXISTING CONVERSATION           │
    # └─────────────────────────────────────────┘
    # Display all previous messages (chat bubbles)
    render_chat_bubbles(st.session_state.history)

    # ┌─────────────────────────────────────────┐
    # │  BOOKING FORM CONDITIONAL DISPLAY       │
    # └─────────────────────────────────────────┘
    # Show booking form if user requested it
    if st.session_state.get("booking_mode"):
        render_booking_form()
        # Allow user to remove booking form
        if st.button("❌ Remove Booking Form"):
            st.session_state.booking_mode = False
            st.session_state.history.append(("bot", "Booking form removed. How else can I help you today?"))
            st.rerun()

    # ┌─────────────────────────────────────────┐
    # │  USER INPUT CAPTURE                     │
    # └─────────────────────────────────────────┘
    # Get new message from user (if any)
    user_input = get_user_input()

    # ┌─────────────────────────────────────────┐
    # │  PROCESS NEW USER MESSAGE               │
    # └─────────────────────────────────────────┘
    # If user just typed something, add it to history
    if user_input:
        logger.info(f"User asked: {user_input}")
        st.session_state.history.append(("user", user_input))
        st.session_state.user_input = user_input
        st.rerun()  # Refresh page to show new user message

    # ┌─────────────────────────────────────────┐
    # │  GENERATE GEORGE'S RESPONSE             │
    # └─────────────────────────────────────────┘
    # If there's a pending user message, process it
    if st.session_state.user_input:
        with st.chat_message("assistant"):
            with st.spinner("🧠 George is typing..."):
                try:
                    # Call the main brain function to generate response
                    response = process_user_query(st.session_state.user_input)

                    # Display George's response
                    st.write(response)

                    # Add George's response to conversation history
                    st.session_state.history.append(("bot", response))

                except Exception as e:
                    # ┌─────────────────────────────────────┐
                    # │  ERROR HANDLING                     │
                    # └─────────────────────────────────────┘
                    error_msg = f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    st.error(error_msg)
                    st.session_state.history.append(("bot", error_msg))

        # ┌─────────────────────────────────────────┐
        # │  CLEAN UP AND PREPARE FOR NEXT INPUT   │
        # └─────────────────────────────────────────┘
        # Clear the processed input and refresh page
        st.session_state.user_input = ""
        st.rerun()

# ========================================
# 🔧 DEVELOPER DEBUGGING PANELS
# ========================================

# ────────────────────────────────────────────────
# 🧪 SQL DEBUG PANEL (Developer Tool)
# ────────────────────────────────────────────────
if st.session_state.show_sql_panel:
    st.markdown("### 🔍 SQL Query Panel")
    sql_input = st.text_area("🔍 Enter SQL query to run:", "SELECT * FROM bookings LIMIT 50;")
    if st.button("Run Query"):
        try:
            # ┌─────────────────────────────────────────┐
            # │  DATABASE CONNECTION SETUP              │
            # └─────────────────────────────────────────┘
            conn = mysql.connector.connect(
                host=get_secret("DB_HOST_READ_ONLY"),
                port=int(get_secret("DB_PORT_READ_ONLY", 3306)),
                user=get_secret("DB_USERNAME_READ_ONLY"),
                password=get_secret("DB_PASSWORD_READ_ONLY"),
                database=get_secret("DB_DATABASE_READ_ONLY")
            )

            # ┌─────────────────────────────────────────┐
            # │  SQL QUERY EXECUTION                    │
            # └─────────────────────────────────────────┘
            cursor = conn.cursor()
            cursor.execute(sql_input)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]

            # ┌─────────────────────────────────────────┐
            # │  RESULTS DISPLAY                        │
            # └─────────────────────────────────────────┘
            df = pd.DataFrame(rows, columns=cols)
            st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"❌ SQL Error: {e}")
        finally:
            # ┌─────────────────────────────────────────┐
            # │  DATABASE CONNECTION CLEANUP            │
            # └─────────────────────────────────────────┘
            try:
                cursor.close()
                conn.close()
            except:
                pass

# ────────────────────────────────────────────────
# 📋 APPLICATION LOG PANEL (Developer Tool)
# ────────────────────────────────────────────────
if st.session_state.get("show_log_panel"):
    st.markdown("### 📋 Log Output")

    # ┌─────────────────────────────────────────┐
    # │  LOG PROCESSING & FORMATTING            │
    # └─────────────────────────────────────────┘
    raw_logs = log_stream.getvalue()
    filtered_lines = [line for line in raw_logs.splitlines() if "App launched" not in line]
    formatted_logs = ""

    for line in filtered_lines:
        if "—" in line:
            ts, msg = line.split("—", 1)

            # Make user queries bold
            if "User asked:" in msg:
                # Extract the user query part and make it bold
                parts = msg.split("User asked:", 1)
                if len(parts) == 2:
                    msg = f"{parts[0]}User asked: **{parts[1].strip()}**"

            formatted_logs += f"\n\n**{ts.strip()}** — {msg.strip()}"
        else:
            formatted_logs += f"\n{line}"

    # ┌─────────────────────────────────────────┐
    # │  LOG DISPLAY & DOWNLOAD                 │
    # └─────────────────────────────────────────┘
    if formatted_logs.strip():
        st.markdown(f"<div class='log-box'>{formatted_logs}</div>", unsafe_allow_html=True)
    else:
        st.info("No logs yet.")

    st.download_button("⬇️ Download Log File", "\n".join(filtered_lines), "general_log.log")
    # ========================================
    # 🧭 Auto-Scroll to Latest Message
    # ========================================
    import streamlit as st

    st.markdown("""
        <script>
        window.scrollTo(0, document.body.scrollHeight);
        </script>
    """, unsafe_allow_html=True)