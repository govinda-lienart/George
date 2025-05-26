# ========================================
# 📋 ROLE OF THIS SCRIPT - ingestion_firecrawl.py
# ========================================

"""
Data ingestion module for the George AI Hotel Receptionist app.
- Web scrapes hotel website content using Firecrawl API
- Processes and cleans scraped content for optimal AI understanding
- Creates document embeddings using OpenAI's text-embedding models
- Chunks documents for efficient vector storage and retrieval
- Uploads processed content to Pinecone vector database for semantic search
- Provides the knowledge base that powers George's hotel information responses
"""

# ========================================
# 📦 IMPORTS & CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 📚 STANDARD LIBRARY IMPORTS
# ────────────────────────────────────────────────
import os  # Operating system interfaces, environment variables
import time  # Time utilities for rate limiting and delays

# ────────────────────────────────────────────────
# 🔧 THIRD-PARTY LIBRARY IMPORTS
# ────────────────────────────────────────────────
from dotenv import load_dotenv  # Load environment variables from .env file
from firecrawl import FirecrawlApp  # Web scraping service integration

# ────────────────────────────────────────────────
# 🤖 LANGCHAIN LIBRARY IMPORTS
# ────────────────────────────────────────────────
from langchain_core.documents import Document  # Document structure for LangChain
from langchain_openai import OpenAIEmbeddings  # OpenAI embedding models
from langchain.text_splitter import RecursiveCharacterTextSplitter  # Text chunking utilities
from langchain_pinecone import PineconeVectorStore  # Pinecone vector database integration

# ┌─────────────────────────────────────────┐
# │  ENVIRONMENT VARIABLES LOADING          │
# └─────────────────────────────────────────┘
# Load environment variables
load_dotenv()

# ========================================
# 🔐 API CREDENTIALS VALIDATION
# ========================================

# ────────────────────────────────────────────────
# 🔑 REQUIRED API KEYS VERIFICATION
# ────────────────────────────────────────────────
# Validate required keys
if not os.getenv("FIRECRAWL_API_KEY") or not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_ENVIRONMENT"):
    raise EnvironmentError("Missing API keys in .env")

# ========================================
# ⚙️ SERVICE INITIALIZATION
# ========================================

# ────────────────────────────────────────────────
# 🔥 FIRECRAWL SERVICE SETUP
# ────────────────────────────────────────────────
# Initialize Firecrawl and OpenAI
app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

# ────────────────────────────────────────────────
# 🤖 OPENAI EMBEDDINGS CONFIGURATION
# ────────────────────────────────────────────────
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# ────────────────────────────────────────────────
# 📊 PINECONE DATABASE CONFIGURATION
# ────────────────────────────────────────────────
# Pinecone index name
INDEX_NAME = "george"

# ========================================
# 🌐 WEBSITE CONTENT SOURCES
# ========================================

# ────────────────────────────────────────────────
# 📋 URL SCRAPING TARGET LIST
# ────────────────────────────────────────────────
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


# ========================================
# 🧹 TEXT PROCESSING UTILITIES
# ========================================

# ────────────────────────────────────────────────
# 🧼 CONTENT CLEANING FUNCTION
# ────────────────────────────────────────────────
def clean_text(text):
    """
    Clean and preprocess scraped text content.
    - Removes empty lines and excessive whitespace
    - Filters out cookie-related content that's not relevant to hotel info
    - Normalizes text formatting for consistent processing

    Parameters:
    - text: Raw scraped text content

    Returns:
    - Cleaned and formatted text string
    """
    # ┌─────────────────────────────────────────┐
    # │  LINE-BY-LINE PROCESSING               │
    # └─────────────────────────────────────────┘
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]

    # ┌─────────────────────────────────────────┐
    # │  IRRELEVANT CONTENT FILTERING           │
    # └─────────────────────────────────────────┘
    cleaned = [line for line in cleaned if "cookie" not in line.lower()]

    return "\n".join(cleaned)


# ========================================
# 🚀 MAIN INGESTION PIPELINE
# ========================================

# ────────────────────────────────────────────────
# 📥 FULL PAGE INGESTION ORCHESTRATOR
# ────────────────────────────────────────────────
def ingest_full_pages():
    """
    Main ingestion pipeline that orchestrates the complete data processing workflow:
    1. Scrapes content from all hotel website pages
    2. Cleans and preprocesses the scraped content
    3. Chunks documents for optimal vector storage
    4. Creates embeddings and uploads to Pinecone vector database

    This function provides the knowledge base that enables George to answer
    questions about hotel amenities, policies, rooms, and services.
    """
    # ┌─────────────────────────────────────────┐
    # │  PIPELINE INITIALIZATION                │
    # └─────────────────────────────────────────┘
    print("\n⚙️ Starting ingestion with chunking...\n")
    all_docs = []

    # ┌─────────────────────────────────────────┐
    # │  ITERATIVE WEB SCRAPING PROCESS         │
    # └─────────────────────────────────────────┘
    for i, url in enumerate(urls_to_scrape, start=1):
        print(f"🔗 [{i}/{len(urls_to_scrape)}] Scraping: {url}")
        try:
            # ┌─────────────────────────────────────────┐
            # │  FIRECRAWL CONTENT EXTRACTION           │
            # └─────────────────────────────────────────┘
            response = app.scrape_url(url, formats=["markdown", "html"])
            cleaned = clean_text(response.markdown)
            all_docs.append(Document(page_content=cleaned, metadata={"source": url}))
            print("📦 Stored cleaned content.")
        except Exception as e:
            # ┌─────────────────────────────────────────┐
            # │  ERROR HANDLING FOR FAILED SCRAPES      │
            # └─────────────────────────────────────────┘
            print(f"❌ Error scraping {url}: {e}")

        # ┌─────────────────────────────────────────┐
        # │  RATE LIMITING DELAY                    │
        # └─────────────────────────────────────────┘
        time.sleep(2)

    # ┌─────────────────────────────────────────┐
    # │  DOCUMENT CHUNKING PROCESS              │
    # └─────────────────────────────────────────┘
    # Chunk documents
    print("\n🔍 Splitting documents into smaller chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    documents = splitter.split_documents(all_docs)
    print(f"🧩 Total chunks created: {len(documents)}")

    # ┌─────────────────────────────────────────┐
    # │  VECTOR DATABASE UPLOAD                 │
    # └─────────────────────────────────────────┘
    # Upload to Pinecone
    print(f"\n🚀 Uploading to Pinecone index: {INDEX_NAME}")
    PineconeVectorStore.from_documents(
        documents,
        embedding=embeddings,
        index_name=INDEX_NAME
    )
    print("✅ Upload complete!")


# ========================================
# 🎯 SCRIPT EXECUTION ENTRY POINT
# ========================================

# ────────────────────────────────────────────────
# 🏃 MAIN EXECUTION BLOCK
# ────────────────────────────────────────────────
if __name__ == "__main__":
    ingest_full_pages()