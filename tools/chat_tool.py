from langchain.agents import Tool
from utils.config import llm

chat_tool = Tool(
    name="chat",
    func=lambda q: llm.invoke(q).content.strip(),
    description="General chat."
)