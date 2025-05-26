# ========================================
# 📋 ROLE OF THIS SCRIPT - config.py
# ========================================

"""
Configuration module for the George AI Hotel Receptionist app.
- Manages environment variables and API key configuration
- Initializes LLM models with fallback priority (DeepSeek → OpenAI)
- Sets up Pinecone vector store connection for semantic search
- Handles both .env file and Streamlit secrets management
- Provides centralized configuration for all AI services
- Ensures secure credential handling and validation
- Essential foundation component for all AI-powered features
"""

#config.py

#Last updated: 2025-05-19 18:26:37
# ========================================
# 📦 Load Dependencies
# ========================================

import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# ========================================
# 🔐 Load Environment Variables
# ========================================

load_dotenv()

# ========================================
# 🔍 Check Access to Secrets
# ========================================

try:
    secrets_available = True if st.secrets else False
except Exception:
    secrets_available = False

# ========================================
# 🔑 Fetch API Keys from env or secrets
# ========================================

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or (st.secrets.get("DEEPSEEK_API_KEY") if secrets_available else None)
openai_api_key = os.getenv("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY") if secrets_available else None)

# ========================================
# 🧠 Initialize LLM
# ========================================

if deepseek_api_key:
    llm = ChatOpenAI(
        model_name="deepseek-chat",
        temperature=0,
        openai_api_key=deepseek_api_key,
        openai_api_base="https://api.deepseek.com/v1"
    )
elif openai_api_key:
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        temperature=0,
        openai_api_key=openai_api_key
    )
else:
    raise ValueError("Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY found! Please set them in your .env or Streamlit Secrets.")

# ========================================
# 🗂️ Initialize Pinecone VectorStore
# ========================================

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY missing! Cannot initialize Pinecone vectorstore embeddings.")

vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=openai_api_key)
)