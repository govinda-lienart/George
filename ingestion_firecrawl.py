import os
import time
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore

# Load environment variables
load_dotenv()

# Retrieve API keys and environment variables
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")

# Validate API keys
if not FIRECRAWL_API_KEY:
    raise ValueError("Missing FIRECRAWL_API_KEY in environment variables.")
if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_ENVIRONMENT in environment variables.")

# Initialize Firecrawl application
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

# Initialize OpenAI Embeddings
print("🔍 Initializing OpenAI Embeddings...")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Define the list of URLs to scrape
urls_to_scrape = [
    "https://sites.google.com/view/chez-govinda/home",
    "https://sites.google.com/view/chez-govinda/rooms",
    "https://sites.google.com/view/chez-govinda/policy",
    "https://sites.google.com/view/chez-govinda/enviroment",
    "https://sites.google.com/view/chez-govinda/contactlocation",
    "https://sites.google.com/view/chez-govinda/breakfast-guest-amenities"
]

# Function to clean text
def clean_text(text):
    """
    Basic cleaning: remove empty lines and cookie boilerplate.
    """
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    cleaned = [line for line in cleaned if "cookie" not in line.lower()]
    return "\n".join(cleaned)

# Initialize list to hold all documents
all_docs = []

# Iterate over each URL and scrape content
for idx, url in enumerate(urls_to_scrape, start=1):
    print(f"🔗 [{idx}/{len(urls_to_scrape)}] Scraping URL: {url}")
    try:
        response = app.scrape_url(url, formats=["markdown", "html"])
        markdown_content = response.markdown
        cleaned_content = clean_text(markdown_content)
        if cleaned_content:
            all_docs.append(Document(page_content=cleaned_content, metadata={"source": url}))
            print(f"✅ Successfully scraped and cleaned content from: {url}")
        else:
            print(f"⚠️ No content extracted from: {url}")
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
    time.sleep(2)  # Delay to avoid hitting rate limits

# Check if any documents were collected
if not all_docs:
    print("⚠️ No documents collected. Exiting.")
    exit()

# Split documents into chunks
print("🧩 Splitting documents into chunks...")
splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
docs = splitter.split_documents(all_docs)
print(f"🧩 Total chunks created: {len(docs)}")

# Upload to Pinecone
print("🚀 Uploading to Pinecone index: george")
PineconeVectorStore.from_documents(
    docs,
    embedding=embeddings,
    index_name="george"
)
print("✅ Upload complete!")