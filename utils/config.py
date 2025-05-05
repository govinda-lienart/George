# Last updated: 2025-05-05 – Fast & Streaming-Ready
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load environment variables for local development
load_dotenv()

print("🔵 Checking environment and Streamlit secrets...")

# Check if Streamlit secrets are accessible
try:
    secrets_available = True if st.secrets else False
except Exception:
    secrets_available = False

# Print detected environment variables
print("ENV VARS:")
print(" - DEEPSEEK_API_KEY in os.environ?", "✅" if "DEEPSEEK_API_KEY" in os.environ else "❌")
print(" - OPENAI_API_KEY in os.environ?", "✅" if "OPENAI_API_KEY" in os.environ else "❌")

print("STREAMLIT SECRETS:")
if secrets_available:
    print(" - DEEPSEEK_API_KEY in st.secrets?", "✅" if "DEEPSEEK_API_KEY" in st.secrets else "❌")
    print(" - OPENAI_API_KEY in st.secrets?", "✅" if "OPENAI_API_KEY" in st.secrets else "❌")
else:
    print(" - No Streamlit secrets found (expected for local run).")

# Securely fetch API keys
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or (st.secrets.get("DEEPSEEK_API_KEY") if secrets_available else None)
openai_api_key = os.getenv("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY") if secrets_available else None)

print(f"🟠 DEEPSEEK_API_KEY detected: {'✅ Yes' if deepseek_api_key else '❌ No'}")
print(f"🟠 OPENAI_API_KEY detected: {'✅ Yes' if openai_api_key else '❌ No'}")

# ✅ Initialize Chat LLM with streaming enabled
if deepseek_api_key:
    print("🧠 Using DeepSeek ChatOpenAI model...")
    llm = ChatOpenAI(
        model_name="deepseek-chat",
        temperature=0.3,
        streaming=True,
        openai_api_key=deepseek_api_key,
        openai_api_base="https://api.deepseek.com/v1"
    )
    print("✅ DeepSeek model initialized.")
elif openai_api_key:
    print("🧠 Using OpenAI GPT-3.5-Turbo model...")
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo-1106",  # Function-calling ready
        temperature=0.3,
        streaming=True,
        openai_api_key=openai_api_key
    )
    print("✅ OpenAI GPT model initialized.")
else:
    raise ValueError("❌ No valid API key found! Set DEEPSEEK_API_KEY or OPENAI_API_KEY.")

# ✅ Initialize Pinecone VectorStore (OpenAI embeddings only)
if not openai_api_key:
    raise ValueError("❌ OPENAI_API_KEY required for initializing Pinecone embeddings!")

print("🗂️ Initializing Pinecone VectorStore...")
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=openai_api_key)
)

print("✅ Pinecone vectorstore ready.")
print("🚀 Config loaded successfully.")
