import os
import time
from dotenv import load_dotenv
load_dotenv()

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import FireCrawlLoader
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS

# === DEBUG MODE ===
DEBUG_MODE = True  # Set to False to ingest all pages
MAX_URLS = 1 if DEBUG_MODE else None

# Initialize OpenAI Embeddings
print("🔍 Initializing OpenAI Embeddings...")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# List of URLs to scrape
urls_to_scrape = [
    "https://sites.google.com/view/chez-govinda/home?authuser=0",
    "https://sites.google.com/view/chez-govinda/rooms?authuser=0",
    "https://sites.google.com/view/chez-govinda/policy?authuser=0",
    "https://sites.google.com/view/chez-govinda/enviroment?authuser=0",
    "https://sites.google.com/view/chez-govinda/contactlocation?authuser=0",
    "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities?authuser=0"
]

# Directory to save the FAISS index
faiss_index_dir = "/Users/govinda-dashugolienart/Library/CloudStorage/GoogleDrive-govinda.lienart@three-monkeys.org/My Drive/TMWC - Govinda /TMWC - Govinda /Data Science/GitHub/George"

# Function to clean text (remove empty lines and cookie boilerplate)
def clean_text(text):
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    cleaned = [line for line in cleaned if "cookie" not in line.lower()]
    return "\n".join(cleaned)

# Function to ingest URLs and create vector store
def ingest_specific_urls():
    print("\n⚙️  Running ingestion script...\n📥 Starting ingestion process...\n")

    all_docs = []

    for i, url in enumerate(urls_to_scrape[:MAX_URLS] if MAX_URLS else urls_to_scrape, start=1):
        print(f"🔗 [{i}/{len(urls_to_scrape)}] Scraping URL: {url}")
        try:
            loader = FireCrawlLoader(
                url=url,
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

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
    chunks = splitter.split_documents(all_docs)
    print(f"🧩 Total chunks created: {len(chunks)}")

    # Add metadata
    for doc in chunks:
        if "source" not in doc.metadata:
            doc.metadata["source"] = "https://sites.google.com/view/chez-govinda"

    # Save FAISS vector store
    print("🚀 Saving to FAISS vector store...")
    os.makedirs(faiss_index_dir, exist_ok=True)
    faiss_store = FAISS.from_documents(chunks, embeddings)
    faiss_store.save_local(faiss_index_dir)
    print(f"✅ Done! Saved at: {faiss_index_dir}")

if __name__ == "__main__":
    ingest_specific_urls()