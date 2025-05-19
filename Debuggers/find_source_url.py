# Last updated: 2025-05-19 18:26:37
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone  # Import the Pinecone class

# Load environment variables
load_dotenv()

# Validate required keys
if not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_ENVIRONMENT"):
    raise EnvironmentError("Missing Pinecone API keys in .env")

# Pinecone index name
INDEX_NAME = "george"

# Initialize embeddings and Pinecone client
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def retrieve_and_show_chunks(query):
    print(f"\n=== Query: {query} ===")

    try:
        index = pc.Index(INDEX_NAME)
        vectorstore = PineconeVectorStore(index=index, embedding=embeddings)

        # Retrieve top 5 documents
        docs_and_scores = vectorstore.similarity_search_with_score(query, k=5)

        for i, (doc, score) in enumerate(docs_and_scores, start=1):
            print(f"\n--- Result {i} (score: {score:.4f}) ---")
            print("Chunk content:\n", doc.page_content.strip())
            print("Source:", doc.metadata.get("source", "No source found"))

    except Exception as e:
        print(f"Error: {e}")

# Test queries
queries = [
    "what time is breakfast served?",
    "can I take my pet into my room?",
    "what amenities exist to do yoga?",
    "what is the address of the hotel?"
]

for q in queries:
    retrieve_and_show_chunks(q)
