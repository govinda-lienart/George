# Last updated: 2025-05-05 19:29:09
import os
import time
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore

# Load environment variables
load_dotenv()

# Validate required keys
if not os.getenv("FIRECRAWL_API_KEY") or not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_ENVIRONMENT"):
    raise EnvironmentError("Missing API keys in .env")

# Initialize Firecrawl and OpenAI
app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Pinecone index name
INDEX_NAME = "george"

# List of URLs to scrape
urls_to_scrape = [
    "https://sites.google.com/view/chez-govinda/home",
    "https://sites.google.com/view/chez-govinda/rooms",
    "https://sites.google.com/view/chez-govinda/policy",
    "https://sites.google.com/view/chez-govinda/enviroment",
    "https://sites.google.com/view/chez-govinda/contactlocation",
    "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities",
    "https://sites.google.com/view/chez-govinda/environmental-commitment"
]

def clean_text(text):
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    cleaned = [line for line in cleaned if "cookie" not in line.lower()]
    return "\n".join(cleaned)

def ingest_full_pages():
    print("\n⚙️ Starting ingestion with chunking...\n")
    all_docs = []

    for i, url in enumerate(urls_to_scrape, start=1):
        print(f"🔗 [{i}/{len(urls_to_scrape)}] Scraping: {url}")
        try:
            response = app.scrape_url(url, formats=["markdown", "html"])
            cleaned = clean_text(response.markdown)
            all_docs.append(Document(page_content=cleaned, metadata={"source": url}))
            print("📦 Stored cleaned content.")
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")

        time.sleep(2)

    # Chunk documents
    print("\n🔍 Splitting documents into smaller chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    documents = splitter.split_documents(all_docs)
    print(f"🧩 Total chunks created: {len(documents)}")

    # Upload to Pinecone
    print(f"\n🚀 Uploading to Pinecone index: {INDEX_NAME}")
    PineconeVectorStore.from_documents(
        documents,
        embedding=embeddings,
        index_name=INDEX_NAME
    )
    print("✅ Upload complete!")

if __name__ == "__main__":
    ingest_full_pages()