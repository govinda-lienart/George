import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("❌ OPENAI_API_KEY is missing in your .env file")

# File path to your hotel description .txt file
hotel_info_path = "/Users/govinda-dashugolienart/.../Pycharm/udemy/hotel/chez_govinda/hotel_description/hotel_descriptions.txt"

# Where to save the FAISS index
faiss_index_dir = "/Users/govinda-dashugolienart/Pycharm/udemy/hotel/chez_govinda/hotel_description_vectordb5"

# Initialize embeddings
embeddings = OpenAIEmbeddings(openai_api_key=openai_key)

def embed_hotel_info():
    print("📄 Loading hotel description...")
    loader = TextLoader(hotel_info_path)
    documents = loader.load()

    print("🔪 Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = splitter.split_documents(documents)
    print(f"✅ Split into {len(texts)} chunks.")

    print("🧠 Creating FAISS vector DB...")
    vectorstore = FAISS.from_documents(texts, embedding=embeddings)

    print("💾 Saving FAISS DB to disk...")
    os.makedirs(faiss_index_dir, exist_ok=True)
    vectorstore.save_local(faiss_index_dir)

    print(f"✅ Done! FAISS DB saved at: {faiss_index_dir}")

if __name__ == "__main__":
    embed_hotel_info()