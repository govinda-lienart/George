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

# Initialize Pinecone and OpenAI
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def find_source_link(docs, keyword):
    policy_keywords = ["policy", "policies", "rules", "terms", "conditions", "pet-policy", "pets"]
    if keyword == "policy":
        for doc in docs:
            source = doc["metadata"].get("source", "")  # Access metadata with ["metadata"]
            if source and any(pk.lower() in source.lower() for pk in policy_keywords):
                return source
    else:
        for doc in docs:
            source = doc["metadata"].get("source", "")  # Access metadata with ["metadata"]
            if source and keyword.lower() in source.lower():
                return source
    return None

def retrieve_and_test(query):
    print(f"Query: {query}")

    try:
        # Connect to Pinecone and fetch relevant documents
        index = pc.Index(INDEX_NAME)  # Get the index
        vectorstore = PineconeVectorStore(
            index=index,  # Pass the index object
            embedding=embeddings
        )
        docs_and_scores = vectorstore.similarity_search_with_score(query, k=10)  # Get top 10 results
        docs = [doc.page_content for doc, _ in docs_and_scores]  # Extract the content
        metadatas = [doc.metadata for doc, _ in docs_and_scores]  # Extract the metadatas

        # Combine content and metadata for find_source_link compatibility
        combined_docs = [{"page_content": docs[i], "metadata": metadatas[i]} for i in range(len(docs))]

        policy_link = find_source_link(combined_docs, "policy")

        if policy_link:
            print(f"Found policy link: {policy_link}")
        else:
            print("No policy link found.")

    except Exception as e:
        print(f"Error retrieving data from Pinecone: {e}")

# Test cases
retrieve_and_test("what is the dog policy?")
retrieve_and_test("hotel policy")
retrieve_and_test("dog allowed in room")
retrieve_and_test("check-in policy")

# No need to deinit, the pc instance will be garbage collected.
# pinecone.deinit()