import time
from dotenv import load_dotenv
import pinecone
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import FireCrawlLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from langchain.prompts import PromptTemplate
from pinecone import ServerlessSpec

# === DEBUG MODE ===
DEBUG_MODE = False  # Set to False to ingest all pages
MAX_URLS = 1 if DEBUG_MODE else None

# Load environment variables
print("🔑 Loading environment variables...")
load_dotenv()

# Fetch OpenAI API key and Pinecone API key from environment variables
openai_key = os.getenv("OPENAI_API_KEY")
pinecone_key = os.getenv("PINECONE_API_KEY")
if not openai_key:
    raise ValueError("❌ Missing OPENAI_API_KEY")
if not pinecone_key:
    raise ValueError("❌ Missing PINECONE_API_KEY")

# Step 2: Initialize OpenAI Embeddings
print("🔍 Initializing OpenAI Embeddings...")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=openai_key)

# Step 3: Initialize LLM for semantic chunking
print("💡 Initializing LLM for semantic chunking...")
llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_key)

# Step 4: Define the URLs to scrape
urls_to_scrape = [
    "https://sites.google.com/view/chez-govinda/home?authuser=0",
    "https://sites.google.com/view/chez-govinda/rooms?authuser=0",
    "https://sites.google.com/view/chez-govinda/policy?authuser=0",
    "https://sites.google.com/view/chez-govinda/enviroment?authuser=0",
    "https://sites.google.com/view/chez-govinda/contactlocation?authuser=0",
    "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities?authuser=0"
]

# Step 5: Initialize Pinecone
print("🌲 Initializing Pinecone...")

try:
    pinecone_client = pinecone.Pinecone(api_key=pinecone_key, environment="us-west1-gcp")
    index_name = os.getenv("PINECONE_INDEX_NAME", "george")

    # Check if the index exists, if not, create it
    if index_name not in pinecone_client.list_indexes():
        print(f"Index '{index_name}' does not exist. Creating...")
        # Define the ServerlessSpec for your index configuration
        spec = ServerlessSpec(
            cloud='aws',
            region='us-east-1',  # Change to your region if needed
            dimension=1536,  # Make sure this matches the embedding dimensions (1536 for OpenAI's embedding model)
            metric='cosine'  # Adjust the metric (e.g., 'cosine' or 'euclidean')
        )
        pinecone_client.create_index(index_name, spec=spec)
    else:
        print(f"Index '{index_name}' found. Using the existing index.")
except Exception as e:
    print(f"❌ Error initializing Pinecone: {e}")
    exit(1)

# Connect to the index
index = pinecone_client.Index(index_name)


# Step 6: Clean up the text (remove unwanted lines)
def clean_text(text):
    """
    Basic cleaning: remove empty lines and cookie boilerplate.
    """
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    cleaned = [line for line in cleaned if "cookie" not in line.lower()]
    return "\n".join(cleaned)


# Step 7: Semantic Chunking Function Using LLM
def semantic_chunking(text):
    """
    Use LLM (ChatGPT) to chunk text into meaningful sections based on its content.
    """
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
You are a smart document assistant.

Please divide the text below into logical sections based on the content. Each section should be labeled with a title, followed by the corresponding content.
The sections should be based on themes and context, such as "Room Descriptions", "Policies", "Amenities", etc.

Text:
{text}

Output:
"""
    )

    response = (prompt | llm).invoke({"text": text}).content.strip()
    print("🧠 LLM chunking complete.")

    # Split the response into chunks and return as document objects
    chunks = response.split("\n\n")
    documents = []

    for chunk in chunks:
        lines = chunk.strip().split("\n")
        if len(lines) < 2:
            continue
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        documents.append({
            "page_content": content,
            "metadata": {"section": title}
        })

    return documents


# Step 8: Ingest specific URLs (Scraping first)
def ingest_specific_urls():
    print("\n⚙️  Running ingestion script...\n📥 Starting ingestion process...\n")

    all_docs = []
    urls_to_scrape = urls_to_scrape[:MAX_URLS] if MAX_URLS else urls_to_scrape

    for i, url in enumerate(urls_to_scrape, start=1):
        print(f"🔗 [{i}/{len(urls_to_scrape)}] Scraping URL: {url}")
        try:
            loader = FireCrawlLoader(
                url=url,
                api_key="your-firecrawl-api-key",  # You may replace with your FireCrawl API key
                mode="scrape",
                params={"formats": ["markdown"]}
            )
            docs = loader.load()

            for doc in docs:
                doc.page_content = clean_text(doc.page_content)

            all_docs.extend(docs)
        except Exception as e:
            print(f"   ❌ Failed to load {url}: {e}")

        if not DEBUG_MODE:
            time.sleep(6)  # Delay to avoid hitting FireCrawl's free tier limit

    print(f"\n📄 Total cleaned documents collected: {len(all_docs)}")

    if not all_docs:
        print("⚠️ No documents collected. Exiting early.")
        return

    # Step 9: Apply semantic chunking to the documents (Now chunking comes after scraping)
    print("🧠 Chunking text using LLM...")
    all_chunks = []
    for doc in all_docs:
        chunks = semantic_chunking(doc.page_content)
        all_chunks.extend(chunks)

    print(f"🧩 Total semantic chunks created: {len(all_chunks)}")

    # Add metadata to the chunks
    for doc in all_chunks:
        if "source" not in doc["metadata"]:
            doc["metadata"]["source"] = "https://sites.google.com/view/chez-govinda/home?authuser=0"

    # Step 10: Upload to Pinecone
    print("🚀 Uploading to Pinecone index: chez-govinda-index")
    try:
        PineconeVectorStore.from_documents(
            all_chunks, embeddings, index_name=index_name
        )
        print("✅ Upload complete!")
    except Exception as e:
        print(f"❌ Error uploading data to Pinecone: {e}")


# Step 11: Run the ingestion script
if __name__ == "__main__":
    ingest_specific_urls()