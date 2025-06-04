# ========================================
# 📋 ROLE OF THIS SCRIPT - sql_tool.py
# ========================================

"""
SQL tool module for the George AI Hotel Receptionist app.
- Translates natural language into SQL using LLM
- Executes the SQL against the hotel's database
- Summarizes results in human language for guests
- Uses LangChain memory for contextual SQL generation
"""

# ========================================
# 📦 SQL TOOL DEFINITION
# ========================================

# ────────────────────────────────────────────────
# 🧠 LANGCHAIN & CONFIG IMPORTS
# ────────────────────────────────────────────────
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm

# ────────────────────────────────────────────────
# 🔧 STANDARD & THIRD-PARTY IMPORTS
# ────────────────────────────────────────────────
import streamlit as st
import mysql.connector
import os
import re
from logger import logger

sql_prompt = PromptTemplate(
    input_variables=["summary", "input"],
    template="""
You are an SQL assistant for a hotel booking system.

Conversation summary so far:
{summary}

Translate the user's question into a MySQL query using this schema:

bookings(
  booking_id,
  first_name,
  last_name,
  email,
  phone,
  room_id,
  check_in,
  check_out,
  num_guests,
  total_price,
  special_requests,
  booking_number
)

rooms(
  room_id,
  room_type,
  price,
  guest_capacity,
  description
)

room_availability(
  id,
  room_id,
  date,
  is_available
)

Important facts:
- This hotel has exactly 7 rooms.
- Each `room_type` corresponds to a unique `room_id`. For example, there is only one Single room (room_id = 1), one Double room (room_id = 2), etc.
- So when the user asks about a room by type (e.g., "Single"), you must translate it to the correct `room_id`.

Rules:
- To check **availability** of a room for a date range, search the `bookings` table for any overlapping booking where the same `room_id` exists and:
    check_in < desired_check_out AND check_out > desired_check_in
    → If such a row exists, the room is **already booked** for that period.
    → If no such rows exist, the room is **available**.
- Assume dates are in the current year (2025) if no year is specified by the user.
- The hotel has exactly 7 rooms, and each `room_type` corresponds to a unique `room_id`.
  For example: "Single" → room_id = 1, "Double" → room_id = 2, etc.
- Only use the `room_availability` table if the user **explicitly** mentions it.
- Use exact column names from the schema.
- Use `check_in`, not `check_in_date`.
- Use `check_out`, not `check_out_date`.
- Use `booking_number` (not reservation ID).
- NEVER include backticks, markdown formatting, or explanations.
- ONLY return the raw SQL query, and NOTHING else.


User: "{input}"
"""
)


# ========================================
# 🧼 CLEANING FUNCTION
# ========================================
def clean_sql(raw_sql: str) -> str:
    cleaned = raw_sql.strip().replace("```sql", "").replace("```", "").replace("Query:", "")
    match = re.search(r"(SELECT\s+.*?;)", cleaned, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else cleaned.strip()

# ========================================
# 🗄️ SQL EXECUTION FUNCTION
# ========================================
def run_sql(query: str):
    cleaned = clean_sql(query)
    logger.info(f"🧠 Generated SQL query: {cleaned}")

    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )

        with conn.cursor() as cursor:
            cursor.execute(cleaned)
            result = cursor.fetchall()
            logger.info(f"✅ Query executed. Rows returned: {len(result)}")
            return result

    except Exception as e:
        logger.error(f"❌ SQL ERROR: {e}", exc_info=True)
        return f"SQL ERROR: {e}"

    finally:
        try:
            conn.close()
        except:
            pass

# ========================================
# 🧠 NATURAL LANGUAGE RESPONSE FUNCTION
# ========================================
def explain_sql(user_question: str, result) -> str:
    prompt = PromptTemplate(
        input_variables=["question", "result"],
        template="""
    You are a helpful and concise hotel assistant.

    Summarize the result of this SQL query for the guest based only on the information provided.
    User Question: {question}
    SQL Result: {result}

    Do **not** ask the guest any follow-up questions or offer additional help.
    Only respond with a clear, complete answer based on the data above.

    Response:
    """
    )

    response = (prompt | llm).invoke({
        "question": user_question,
        "result": str(result)
    }).content.strip()

    logger.info(f"🤖 Assistant response: {response}")
    return response

# ========================================
# 🧠 SQL TOOL FUNCTION (FOR ROUTER)
# ========================================
def sql_tool_func(q):
    summary = st.session_state.george_memory.load_memory_variables({}).get("summary", "")
    query = (sql_prompt | llm).invoke({"summary": summary, "input": q}).content
    result = run_sql(query)
    return explain_sql(q, result)

# ========================================
# 🧩 LANGCHAIN TOOL OBJECT (Exported)
# ========================================
sql_tool = Tool(
    name="sql_tool",
    func=sql_tool_func,
    description="Access bookings, availability, prices, and reservations from the SQL database."
)
