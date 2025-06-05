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

IMPORTANT: Look at the conversation context above. If the user's current question refers to something from previous messages (like "it", "for 2 nights", "how much", etc.), use the context to understand what they mean.

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

Facts:
- The hotel has exactly 7 rooms.
- Each `room_type` corresponds to a unique `room_id`. For example:
    "Single" → room_id = 1
    "Double" → room_id = 2
    "Twin" → room_id = 3
    "Family" → room_id = 4
    "Romantic" → room_id = 5
    "Business" → room_id = 6
    "Studio" → room_id = 7

Rules:
- To check **room availability**, query the `bookings` table.
- A room is considered **booked** if there exists a booking for the same `room_id` where:
    check_in < desired_check_out AND check_out > desired_check_in
- If no such row exists, the room is **available**.
- Always use this pattern:
    SELECT COUNT(*) = 0 AS is_available FROM bookings WHERE room_id = X AND check_in < 'YYYY-MM-DD' AND check_out > 'YYYY-MM-DD';
- Only use the `room_availability` table if the user explicitly mentions it.
- Assume all dates are in the year 2025 unless the user specifies another year.
- Use only exact column names from the schema.
- Do not include SQL comments, markdown, or explanation.
- Return only the SQL query, nothing else.

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
