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

# ========================================
# 🧾 UPDATED SQL PROMPT TEMPLATE
# ========================================
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

Use prior information (like booking numbers) mentioned in the summary if the current question doesn't repeat them.

Rules:
- To determine if a room is available on a given date, check whether that date is **not between `check_in` (inclusive) and `check_out` (exclusive)** in the `bookings` table.
- Avoid using the `room_availability` table for checking availability unless the user explicitly mentions it.
- Use exact column names.
- Use `check_in`, not `check_in_date`.
- Use `check_out`, not `check_out_date`.
- Use `booking_number` (not reservation ID).
- DO NOT include backticks or markdown formatting like ```sql.
- DO NOT include explanations or commentary.
- ONLY return the raw SQL query.

User: "{input}"
Respond ONLY with the SQL query, and NOTHING else.
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
You are a hotel assistant.

Summarize the result of this SQL query for the guest:
User Question: {question}
SQL Result: {result}
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
