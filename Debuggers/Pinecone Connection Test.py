# Last updated: 2025-05-07 14:45:57
import os
from dotenv import load_dotenv
from pinecone import Pinecone

# Load .env file
load_dotenv()

# Get credentials
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    print("❌ Pinecone API key not found in .env.")
    exit()

# Initialize new Pinecone client
print("🔌 Connecting to Pinecone...")
pc = Pinecone(api_key=PINECONE_API_KEY)

# List all available indexes
try:
    indexes = pc.list_indexes().names()
    print(f"📦 Available indexes: {indexes}")

    if "george" in indexes:
        index = pc.Index("george")
        stats = index.describe_index_stats()
        print("📊 'george' index stats:")
        print(stats)
    else:
        print("⚠️ Index 'george' not found.")
except Exception as e:
    print(f"❌ Error while connecting to Pinecone: {e}")