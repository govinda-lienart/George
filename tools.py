import os
from dotenv import load_dotenv
from langchain.agents import Tool, initialize_agent, AgentType
from langchain_community.chat_models import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAIEmbeddings
import mysql.connector

# Load environment variables
load_dotenv()

# LLM setup (DeepSeek)
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1"
)

# Vector store
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
)

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

# SQL runner
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

# SQL summarizer
def explain_sql(user_question, result):
    prompt = PromptTemplate(
        input_variables=["question", "result"],
        template="""
You are a hotel assistant.

Summarize this SQL result for the guest:
User Question: {question}
SQL Result: {result}
Response:
"""
    )
    return (prompt | llm).invoke({"question": user_question, "result": str(result)}).content.strip()

# Helper to find matching doc source
def find_source_link(docs, keyword):
    for doc in docs:
        source = doc.metadata.get("source", "")
        if keyword.lower() in source.lower():
            return source
    return None

# Vector Search
def vector_search(query):
    docs = vectorstore.similarity_search(query, k=30)

    if not docs:
        return "❌ I couldn’t find anything relevant in our documents."

    if all(len(doc.page_content.strip()) < 50 for doc in docs):
        return "Hmm, I found some documents but they seem too short to be helpful. Could you rephrase your question?"

    # Deduplicate similar docs
    seen = set()
    unique_docs = []
    for doc in docs:
        if doc.page_content[:100] not in seen:
            unique_docs.append(doc)
            seen.add(doc.page_content[:100])
    docs = unique_docs

    # Boost sustainability-related results only if the query is about that
    relevant_terms = ["eco", "green", "environment", "sustainab", "organic"]
    boost_needed = any(term in query.lower() for term in relevant_terms)

    if boost_needed:
        docs = sorted(
            docs,
            key=lambda d: any(term in d.page_content.lower() for term in relevant_terms),
            reverse=True
        )

    docs = docs[:10]  # Always trim to top 10

    # Prompt setup
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are George, the friendly receptionist at Chez Govinda.

Answer the user's question in a warm and concise paragraph, using only the information below. Prioritize anything about sustainability or green practices when applicable.

{context}

User: {question}
"""
    )

    context = "\n\n".join(doc.page_content for doc in docs)
    final_answer = (prompt | llm).invoke({"context": context, "question": query}).content.strip()

    # Smart link addition
    env_link = find_source_link(docs, "environment")
    rooms_link = find_source_link(docs, "rooms")

    if env_link:
        final_answer += f"\n\n🌱 You can read more about this on our [Environmental Commitment page]({env_link})."
    elif rooms_link:
        final_answer += f"\n\n🛏️ You can check out more details on our [Rooms page]({rooms_link})."

    return final_answer

# Tools setup
tools = [
    Tool(
        name="sql",
        func=lambda q: explain_sql(q, run_sql((sql_prompt | llm).invoke({"summary": "", "input": q}).content.strip())),
        description="Bookings, prices, availability."
    ),
    Tool(name="vector", func=vector_search, description="Hotel details and policies."),
    Tool(name="chat", func=lambda q: llm.invoke(q).content.strip(), description="General chat.")
]

# Agent setup with verbose logging
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=1,
    early_stopping_method="generate"
)