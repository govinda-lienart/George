# chat_tool.py
from langchain.tools import Tool

def chat_tool_func(query: str) -> str:
    """Responds politely to questions unrelated to the hotel."""
    return "😊 I can only help with questions about our hotel and your stay at Chez Govinda. Could you ask something related to your visit?"

chat_tool = Tool(
    name="chat_tool",
    func=chat_tool_func,
    description="Use this tool for questions unrelated to the hotel or the user's stay."
)