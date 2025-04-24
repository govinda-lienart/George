# Last updated: 2025-04-24 22:11:38
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load .env variables
load_dotenv()

# Shared LLM (DeepSeek)
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1"
)

# Shared vectorstore
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
)