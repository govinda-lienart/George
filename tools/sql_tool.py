import os
import mysql.connector
from langchain.prompts import PromptTemplate
from langchain.agents import Tool
from utils.config import llm

# SQL Prompt
sql_prompt = PromptTemplate(
    input_variables=["summary", "input"],
    template="""
You are an SQL assistant for a hotel booking system.

Conversation summary so far:
{summary}

Translate the user's question into a MySQL query using this schema:

rooms(room_id, room_type, price, guest_capacity, description)
room_availability(id, room_id, date, is_available)
bookings(booking_id, first_name, last_name, email, phone, room_id, check_in, check_out, num_guests, total_price, special_requests)

Rules:
- Use raw MySQL.
- Do NOT explain anything. Only return the raw SQL query.

User: "{input}"
"""
)

def run_sql(query):
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        return f"SQL ERROR: {e}"
    finally:
        cursor.close()
        conn.close()

def explain_sql(user_question, result):
    explain_prompt = PromptTemplate(
        input_variables=["question", "result"],
        template="""
You are a hotel assistant.

Summarize this SQL result for the guest:
User Question: {question}
SQL Result: {result}
Response:
"""
    )
    return (explain_prompt | llm).invoke({"question": user_question, "result": str(result)}).content.strip()

sql_tool = Tool(
    name="sql",
    func=lambda q: explain_sql(q, run_sql((sql_prompt | llm).invoke({"summary": "", "input": q}).content.strip())),
    description="Bookings, prices, availability."
)