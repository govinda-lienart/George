# Last updated: 2025-05-05 19:29:09
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load environment variables
load_dotenv()

# Load the vectorstore from Pinecone
print("🔍 Connecting to Pinecone vectorstore...")
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
)

# Run similarity search
query = "What room types are available?"
results = vectorstore.similarity_search(query, k=10)

# Print retrieved chunks
print(f"\n🔎 Results for query: '{query}'")
for i, doc in enumerate(results):
    print(f"\n--- Chunk {i+1} ---\n{doc.page_content}")