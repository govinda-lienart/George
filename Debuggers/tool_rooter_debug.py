import os
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI

# Load .env for API keys
load_dotenv()

# Use OpenAI (GPT-3.5) for routing
router_llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0
)

# Define the routing prompt
router_prompt = PromptTemplate.from_template("""
You are a routing assistant for an AI hotel receptionist.

Choose the correct tool for the user's question.

Available tools:
- sql_tool: check room availability, prices, booking status, or existing reservation details
- vector_tool: room descriptions, hotel policies, breakfast, amenities
- booking_tool: when the user confirms they want to book
- chat_tool: if the question is unrelated to the hotel (e.g. weather, personal questions, general small talk)

Important:
- If the question is not related to the hotel, choose `chat_tool`. The assistant will then respond kindly: 
  “😊 I can only help with questions about our hotel and your stay. Could you ask something about your visit to Chez Govinda?”

Return only one word: sql_tool, vector_tool, booking_tool, or chat_tool

Question: "{question}"
Tool:
""")


# List of sample queries to test
test_queries = [
    "what is the location of the hotel?",
]

# Run test
print("🔍 Tool routing test:")
for q in test_queries:
    tool = router_llm.predict(router_prompt.format(question=q)).strip()
    print(f"🔹 Query: {q}\n   → Tool: {tool}\n")
