# chat_tool.py
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

# Initialize a small, fast LLM for generating the refusal
chat_model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.2)

refusal_prompt = PromptTemplate.from_template("""
You are a polite AI assistant for a hotel. A user has asked a question that is outside the scope of hotel information, bookings, or their stay.

Generate a concise and polite response explaining that you can only help with hotel-related inquiries.

User's question: "{query}"

Polite refusal:""")

def chat_tool_func(query: str) -> str:
    """Responds politely to questions unrelated to the hotel using an LLM."""
    prompt_value = refusal_prompt.format_prompt(query=query)
    refusal_message = chat_model.predict(prompt_value.to_string()).strip()
    return refusal_message

chat_tool = Tool(
    name="chat_tool",
    func=chat_tool_func,
    description="Use this tool for questions unrelated to the hotel or the user's stay."
)