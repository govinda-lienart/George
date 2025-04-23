# reset_firecrawl_index.py

import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

# 🔐 Get Pinecone credentials
api_key = os.getenv("PINECONE_API_KEY")
index_name = "george"

# 🔌 Connect using new Pinecone class
pc = Pinecone(api_key=api_key)

# ✅ Check if index exists
existing_indexes = pc.list_indexes().names()
if index_name not in existing_indexes:
    print(f"❌ Pinecone index '{index_name}' does not exist.")
else:
    print(f"🧹 Resetting Pinecone index: '{index_name}'...")
    index = pc.Index(index_name)
    index.delete(delete_all=True)
    print("✅ All vectors deleted. The index is now empty.")
