# ========================================
# 📋 ROLE OF THIS SCRIPT - reset_firecrawl_ingestion.py
# ========================================

"""
Reset Firecrawl ingestion module for the George AI Hotel Receptionist app.
- Provides database cleanup and reset functionality for the vector store
- Connects to Pinecone vector database to clear existing embeddings
- Validates index existence before attempting reset operations
- Enables fresh data ingestion cycles by clearing old content
- Essential maintenance tool for updating hotel information knowledge base
- Supports development and production environment resets
"""

# Last updated: 2025-05-19 18:26:37
# reset_firecrawl_index.py

# ========================================
# 📦 IMPORTS & CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 📚 STANDARD LIBRARY IMPORTS
# ────────────────────────────────────────────────
import os  # Operating system interfaces, environment variables

# ────────────────────────────────────────────────
# 🔧 THIRD-PARTY LIBRARY IMPORTS
# ────────────────────────────────────────────────
from dotenv import load_dotenv  # Load environment variables from .env file
from pinecone import Pinecone  # Pinecone vector database client

# ┌─────────────────────────────────────────┐
# │  ENVIRONMENT VARIABLES LOADING          │
# └─────────────────────────────────────────┘
load_dotenv()

# ========================================
# 🔐 DATABASE CREDENTIALS & CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 🔑 PINECONE CREDENTIALS RETRIEVAL
# ────────────────────────────────────────────────
# 🔐 Get Pinecone credentials
api_key = os.getenv("PINECONE_API_KEY")
index_name = "george"

# ────────────────────────────────────────────────
# 🔌 DATABASE CONNECTION ESTABLISHMENT
# ────────────────────────────────────────────────
# 🔌 Connect using new Pinecone class
pc = Pinecone(api_key=api_key)

# ========================================
# 🧹 INDEX RESET OPERATIONS
# ========================================

# ────────────────────────────────────────────────
# ✅ INDEX EXISTENCE VALIDATION & RESET EXECUTION
# ────────────────────────────────────────────────
# ✅ Check if index exists
existing_indexes = pc.list_indexes().names()
if index_name not in existing_indexes:
    # ┌─────────────────────────────────────────┐
    # │  INDEX NOT FOUND ERROR HANDLING         │
    # └─────────────────────────────────────────┘
    print(f"❌ Pinecone index '{index_name}' does not exist.")
else:
    # ┌─────────────────────────────────────────┐
    # │  INDEX RESET PROCESS EXECUTION          │
    # └─────────────────────────────────────────┘
    print(f"🧹 Resetting Pinecone index: '{index_name}'...")
    index = pc.Index(index_name)
    index.delete(delete_all=True)
    print("✅ All vectors deleted. The index is now empty.")