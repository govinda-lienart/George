import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load .env for local development
load_dotenv()

print("🔵 Checking environment and Streamlit secrets...")

# Print env and secret detection
print("ENV VARS:")
print(" - DEEPSEEK_API_KEY found in os.environ?", "✅" if "DEEPSEEK_API_KEY" in os.environ else "❌")
print(" - OPENAI_API_KEY found in os.environ?", "✅" if "OPENAI_API_KEY" in os.environ else "❌")

print("STREAMLIT SECRETS:")
print(" - DEEPSEEK_API_KEY found in st.secrets?", "✅" if "DEEPSEEK_API_KEY" in st.secrets else "❌")
print(" - OPENAI_API_KEY found in st.secrets?", "✅" if "OPENAI_API_KEY" in st.secrets else "❌")

# Fetch API keys safely: env first, fallback to st.secrets
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or st.secrets.get("DEEPSEEK_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

# Confirm keys fetched
print(f"🟠 DEEPSEEK_API_KEY detected: {'✅ Yes' if deepseek_api_key else '❌ No'}")
print(f"🟠 OPENAI_API_KEY detected: {'✅ Yes' if openai_api_key else '❌ No'}")

# Initialize LLM
if deepseek_api_key:
    print("🧠 Initializing DeepSeek ChatOpenAI model...")
    llm = ChatOpenAI(
        model_name="deepseek-chat",
        temperature=0,
        openai_api_key=deepseek_api_key,
        openai_api_base="https://api.deepseek.com/v1"
    )
    print("✅ DeepSeek model ready.")
elif openai_api_key:
    print("🧠 DeepSeek not found. Falling back to OpenAI ChatGPT model...")
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0,
        openai_api_key=openai_api_key
    )
    print("✅ OpenAI GPT model ready.")
else:
    raise ValueError("❌ Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY found! Please set them in your .env or Streamlit Secrets.")

# Initialize VectorStore (always needs OpenAI key for embeddings)
if not openai_api_key:
    raise ValueError("❌ OPENAI_API_KEY missing! Cannot initialize Pinecone vectorstore embeddings.")

print("🗂️ Initializing Pinecone VectorStore with OpenAI embeddings...")
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=openai_api_key)
)

print("✅ Vectorstore initialized successfully.")
print("🚀 App setup complete.")