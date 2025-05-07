# Last updated: 2025-05-07 14:45:57
from langchain.agents import Tool
from langchain.prompts import PromptTemplate
from utils.config import llm
import mysql.connector
import os
import streamlit as st

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
- If the user provides a reference like BKG-YYYYMMDD-NNNN, it refers to booking_number.
- If unsure, always try matching BKG codes to booking_number.

Example:
User: “Can you get me the details for BKG-20250401-0003?”
Query: SELECT * FROM bookings WHERE booking_number = 'BKG-20250401-0003';
User: "{input}"
"""
)

# --- Clean the SQL string ---
def clean_sql(raw_sql: str) -> str:
    return (
        raw_sql.strip()
        .removeprefix("```sql")
        .removesuffix("```")
        .replace("```", "")
        .strip()
    )

# --- Execute the SQL query safely ---
def run_sql(query: str):
    cleaned = clean_sql(query)
    st.write(f"🔍 SQL query received:\n```sql\n{cleaned}\n```")

    try:
        db_user = os.getenv("DB_USERNAME")
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
        return cursor.fetchall()
    except Exception as e:
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
    return (prompt | llm).invoke({
        "question": user_question,
        "result": str(result)
    }).content.strip()

# --- LangChain Tool definition ---
sql_tool = Tool(
    name="sql",
    func=lambda q: explain_sql(q, run_sql((sql_prompt | llm).invoke({
        "summary": st.session_state.chat_summary,
        "input": q
    }).content)),
    description="Access bookings, availability, prices, and reservations from the SQL database."
)