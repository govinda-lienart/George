import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Load environment variables from a .env file
load_dotenv()

# Retrieve the API key from environment variables
api_key = os.getenv("FIRECRAWL_API_KEY")

# Initialize the Firecrawl application with the API key
app = FirecrawlApp(api_key=api_key)

# Define the URL you want to scrape
url_to_scrape = "https://sites.google.com/view/chez-govinda/home"

# Perform the scraping operation
try:
    response = app.scrape_url(url_to_scrape, formats=["markdown", "html"])
    print("✅ Firecrawl returned content.")
    print("📝 First 300 characters of markdown:\n")
    print(response.markdown[:300])
except Exception as e:
    print(f"❌ Error: {e}")