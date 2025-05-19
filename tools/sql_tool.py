# Last updated: 2025-05-19 — follow-up aware SQL prompt, memory support, cleaner structure

from langchain.agents import Tool
from utils.config import llm
import mysql.connector
import os
import re
import streamlit as st
from langchain.prompts import PromptTemplate
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

Use prior information (like booking numbers) mentioned in the summary if the current question doesn’t repeat them.

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

# --- SQL string cleaner ---
def clean_sql(raw_sql: str) -> str:
    cleaned = raw_sql.strip().replace("```sql", "").replace("```", "").replace("Query:", "")
    match = re.search(r"(SELECT\s+.*?;)", cleaned, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else cleaned.strip()

# --- SQL query executor ---
def run_sql(query: str):
    cleaned = clean_sql(query)
    logger.info(f"🧠 Generated SQL query: {cleaned}")

    try:
        db_user = os.getenv("DB_USERNAME")
        logger.info(f"👤 Using DB user: {db_user}")

        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=db_user,
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )

        with conn.cursor() as cursor:
            cursor.execute(cleaned)
            result = cursor.fetchall()
            logger.info(f"✅ Query executed. Rows returned: {len(result)}")
            return result

    except Exception as e:
        logger.error(f"❌ SQL ERROR: {str(e)}", exc_info=True)
        return f"SQL ERROR: {e}"

    finally:
        try:
            conn.close()
        except:
            pass

# --- LLM Explanation of SQL result ---
def explain_sql(user_question: str, result) -> str:
    logger.info(f"💬 User question: {user_question}")
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

# --- LangChain Tool definition ---
sql_tool = Tool(
    name="sql",
    func=lambda q: explain_sql(
        q,
        run_sql(
            (sql_prompt | llm).invoke({
                "summary": st.session_state.george_memory.load_memory_variables({}).get("summary", ""),
                "input": q
            }).content
        )
    ),
    description="Access bookings, availability, prices, and reservations from the SQL database."
)
