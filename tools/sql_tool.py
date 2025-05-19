# Last updated: 2025-05-19 — logging fixed and improved

from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
import mysql.connector
import os
import re
import streamlit as st
from logger import logger

# --- Prompt Template for SQL generation ---
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

Rules:
- Use exact column names.
- Use `check_in`, not `check_in_date`.
- Use `check_out`, not `check_out_date`.
- Use `booking_number` (not reservation ID).
- DO NOT include backticks or markdown formatting like ```sql.
- DO NOT include explanations or commentary.
- ONLY return the raw SQL query.

Example:
User: “Can you get me the details for BKG-20250401-0003?”
SELECT * FROM bookings WHERE booking_number = 'BKG-20250401-0003';

User: "{input}"

Respond ONLY with the SQL query, and NOTHING else.
"""
)

# --- Clean the SQL string safely ---
def clean_sql(raw_sql: str) -> str:
    cleaned = (
        raw_sql.strip()
        .replace("```sql", "")
        .replace("```", "")
        .replace("Query:", "")
    )
    match = re.search(r"(SELECT\s+.*?;)", cleaned, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return cleaned.strip()

# --- Execute the SQL query safely ---
def run_sql(query: str):
    cleaned = clean_sql(query)
    logger.info(f"🧠 Generated SQL query:\n{cleaned}")
    st.write(f"🔍 SQL query received:\n```sql\n{cleaned}\n```")

    try:
        db_user = os.getenv("DB_USERNAME")
        logger.info(f"👤 Using DB user: {db_user}")
        st.write(f"👤 Using DB user: {db_user}")

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=db_user,
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )
        st.write("✅ Connected to DB")
        cursor = conn.cursor()
        cursor.execute(cleaned)
        result = cursor.fetchall()

        logger.info(f"✅ Query executed. Rows returned: {len(result)}")
        return result

    except Exception as e:
        logger.error(f"❌ SQL ERROR: {str(e)}", exc_info=True)
        st.write(f"❌ SQL ERROR: {e}")
        return f"SQL ERROR: {e}"

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# --- Generate explanation of SQL results ---
def explain_sql(user_question, result):
    logger.info(f"📣 Explaining result for user question: {user_question}")
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
    logger.info(f"✅ Generated explanation: {response}")
    return response

# --- LangChain Tool definition ---
sql_tool = Tool(
    name="sql",
    func=lambda q: explain_sql(q, run_sql((sql_prompt | llm).invoke({
        "summary": st.session_state.chat_summary,
        "input": q
    }).content)),
    description="Access bookings, availability, prices, and reservations from the SQL database."
)
