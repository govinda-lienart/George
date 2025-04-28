import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load .env locally (useful when not deployed)
load_dotenv()

print("🔵 Loading environment variables...")

# Fetch API keys safely: first try env var, then fallback to st.secrets
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or st.secrets.get("DEEPSEEK_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

print(f"🟠 DEEPSEEK_API_KEY detected: {'Yes ✅' if deepseek_api_key else 'No ❌'}")
print(f"🟠 OPENAI_API_KEY detected: {'Yes ✅' if openai_api_key else 'No ❌'}")

# Validate API keys
if not deepseek_api_key:
    raise ValueError("❌ Missing DEEPSEEK_API_KEY! Please set it in your .env or Streamlit Secrets.")

if not openai_api_key:
    raise ValueError("❌ Missing OPENAI_API_KEY! Please set it in your .env or Streamlit Secrets.")

# Initialize LLM
print("🧠 Initializing DeepSeek ChatOpenAI model...")
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com/v1"
)

# Initialize Vectorstore
print("🗂️ Initializing Pinecone VectorStore with OpenAI embeddings...")
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=openai_api_key)
)

print("✅ Initialization complete!")