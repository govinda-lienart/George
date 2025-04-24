# Last updated: 2025-04-24 22:11:38
# test_vector_debug.py
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load environment variables
load_dotenv()

# Setup embedding and vector store
embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
index_name = "george"
vectorstore = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding)

# Retrieve all docs
print("\n📦 Listing all documents in the Pinecone index (preview)...")
docs = vectorstore.similarity_search(".", k=100)

if not docs:
    print("❌ No documents retrieved.")
else:
    print(f"✅ Retrieved {len(docs)} documents. Previewing each:\n")
    for i, doc in enumerate(docs, 1):
        print(f"--- Document {i} ---")
        print(doc.page_content[:500])
        print(f"Source: {doc.metadata.get('source', 'No source')}\n")
