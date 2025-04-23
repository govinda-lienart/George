import os
import time
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

# Validate required keys
if not os.getenv("FIRECRAWL_API_KEY") or not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_ENVIRONMENT"):
    raise EnvironmentError("Missing API keys in .env")

# Initialize Firecrawl and embeddings
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
    "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities"
]

# Clean up scraped text
def clean_text(text):
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    cleaned = [line for line in cleaned if "cookie" not in line.lower()]
    return "\n".join(cleaned)

def ingest_full_pages():
    print("\n⚙️ Starting full-page ingestion...\n")
    raw_docs = []

    for i, url in enumerate(urls_to_scrape, start=1):
        print(f"🔗 [{i}/{len(urls_to_scrape)}] Scraping: {url}")
        try:
            response = app.scrape_url(url, formats=["markdown", "html"])
            cleaned = clean_text(response.markdown)
            raw_docs.append(Document(page_content=cleaned, metadata={"source": url}))
            print("📥 Scraped and cleaned content. Will be chunked next.")
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
        time.sleep(2)

    if not raw_docs:
        print("⚠️ No documents scraped. Exiting.")
        return

    # Chunk documents
    print("\n🔍 Splitting documents into smaller chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
    chunked_docs = splitter.split_documents(raw_docs)

    # Ensure metadata for all chunks
    for doc in chunked_docs:
        source_url = doc.metadata.get("source", "")
        doc.metadata.update({"source": source_url})

    print(f"🧩 Total chunks created: {len(chunked_docs)}")

    # Preview some chunks
    print("\n📑 Previewing a few chunks before upload:")
    for i, doc in enumerate(chunked_docs[:3], start=1):
        print(f"\n--- Chunk {i} ---\n{doc.page_content[:300]}...\nSource: {doc.metadata.get('source')}")

    # Upload to Pinecone
    print(f"\n🚀 Uploading to Pinecone index: {INDEX_NAME}")
    PineconeVectorStore.from_documents(
        chunked_docs,
        embedding=embeddings,
        index_name=INDEX_NAME
    )
    print("✅ Upload complete!")

if __name__ == "__main__":
    ingest_full_pages()