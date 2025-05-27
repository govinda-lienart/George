# ========================================
# 📋 ROLE OF THIS SCRIPT - sql_tool.py
# ========================================

"""
SQL tool module for the George AI Hotel Receptionist app.
- Handles database queries for booking information, room availability, and reservations
- Translates natural language questions into MySQL queries using LLM
- Executes SQL queries against the hotel's booking database
- Converts raw SQL results into natural language responses for guests
- Accesses booking details, room information, and availability data
- Manages conversation memory integration for contextual database queries
- Essential component for George's data-driven guest service capabilities
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
import streamlit as st  # Session state for conversation memory
import mysql.connector  # MySQL database connection library
import os  # Environment variables access
import re  # Regular expressions for SQL cleaning
from logger import logger

# ========================================
# 🧾 PROMPT TEMPLATE FOR SQL GENERATION
# ========================================
sql_prompt = PromptTemplate(
    input_variables=["summary", "input"],  # Conversation history + user question
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
- Use exact column names.
- Use `check_in`, not `check_in_date`.
- Use `check_out`, not `check_out_date`.
- Use `booking_number` (not reservation ID).
- DO NOT include backticks or markdown formatting like ```sql.
- DO NOT include explanations or commentary.
- ONLY return the raw SQL query.

Example:
User: "Can you get me the details for BKG-20250401-0003?"
SELECT * FROM bookings WHERE booking_number = 'BKG-20250401-0003';

User: "{input}"

Respond ONLY with the SQL query, and NOTHING else.
"""
)


# ========================================
# 🧼 SQL STRING CLEANING FUNCTION
# ========================================
# ┌─────────────────────────────────────────┐
# │  CLEAN SQL FROM RAW LLM OUTPUT          │
# └─────────────────────────────────────────┘
def clean_sql(raw_sql: str) -> str:
    """
    Cleans LLM-generated SQL by removing markdown formatting and extracting pure SQL.

    Args:
        raw_sql: Raw SQL string from LLM (may contain ```sql blocks, explanations)

    Returns:
        str: Clean SQL query ready for execution
    """
    # Remove common LLM formatting artifacts
    cleaned = raw_sql.strip().replace("```sql", "").replace("```", "").replace("Query:", "")

    # Extract SELECT statement using regex (most common query type)
    match = re.search(r"(SELECT\s+.*?;)", cleaned, re.IGNORECASE | re.DOTALL)

    # Return matched SQL or fallback to cleaned string
    return match.group(1).strip() if match else cleaned.strip()


# ========================================
# 🗄️ SQL EXECUTION FUNCTION
# ========================================
# ┌─────────────────────────────────────────┐
# │  EXECUTE SQL ON MYSQL DATABASE          │
# └─────────────────────────────────────────┘
def run_sql(query: str):
    """
    Executes SQL query against the hotel database.

    Args:
        query: SQL query string to execute

    Returns:
        list: Query results as list of tuples, or error message string
    """
    # Clean the SQL query first
    cleaned = clean_sql(query)
    logger.info(f"🧠 Generated SQL query: {cleaned}")

    try:
        # Get database credentials from environment variables
        db_user = os.getenv("DB_USERNAME")
        logger.info(f"👤 Using DB user: {db_user}")

        # Establish database connection
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=db_user,
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )

        # Execute query and fetch results
        with conn.cursor() as cursor:
            cursor.execute(cleaned)  # Execute the cleaned SQL
            result = cursor.fetchall()  # Get all rows as list of tuples
            logger.info(f"✅ Query executed. Rows returned: {len(result)}")
            return result

    except Exception as e:
        # Log any database errors and return error message
        logger.error(f"❌ SQL ERROR: {str(e)}", exc_info=True)
        return f"SQL ERROR: {e}"

    finally:
        # Always close database connection
        try:
            conn.close()
        except:
            pass


# ========================================
# 🧠 LLM RESPONSE GENERATION FROM SQL RESULT
# ========================================
# ┌─────────────────────────────────────────┐
# │  SUMMARIZE SQL RESULTS FOR THE GUEST    │
# └─────────────────────────────────────────┘
def explain_sql(user_question: str, result) -> str:
    """
    Converts raw SQL results into a natural language response for the guest.

    Args:
        user_question: Original question from the guest
        result: Raw SQL query results (list of tuples or error message)

    Returns:
        str: Natural language explanation of the results
    """
    logger.info(f"💬 User question: {user_question}")

    # Create prompt to translate SQL results to natural language
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

    # Generate natural language response using LLM
    response = (prompt | llm).invoke({
        "question": user_question,
        "result": str(result)  # Convert result to string for LLM processing
    }).content.strip()

    logger.info(f"🤖 Assistant response: {response}")
    return response


# ========================================
# 🧩 LANGCHAIN TOOL OBJECT (Exported)
# ========================================
# ┌─────────────────────────────────────────┐
# │  WRAP LLM + SQL INTO LangChain Tool     │
# └─────────────────────────────────────────┘
sql_tool = Tool(
    name="sql",
    func=lambda q: explain_sql(  # Lambda function chains the SQL pipeline:
        q,  # 1. Pass user question to explain_sql
        run_sql(  # 2. Execute SQL query generated by LLM
            (sql_prompt | llm).invoke({  # 3. Generate SQL from user question
                "summary": st.session_state.george_memory.load_memory_variables({}).get("summary", ""),
                # Conversation history
                "input": q  # Current user question
            }).content  # Extract LLM response content
        )
    ),
    description="Access bookings, availability, prices, and reservations from the SQL database."
)