import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Keys
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("❌ OPENAI_API_KEY is missing in .env")

# ✅ Your full paths
file_path = "/Users/govinda-dashugolienart/Library/CloudStorage/GoogleDrive-govinda.lienart@three-monkeys.org/My Drive/TMWC - Govinda /TMWC - Govinda /Data Science/GitHub/George/hotel_descriptions.txt"
faiss_index_dir = "/Users/govinda-dashugolienart/Library/CloudStorage/GoogleDrive-govinda.lienart@three-monkeys.org/My Drive/TMWC - Govinda /TMWC - Govinda /Data Science/GitHub/George/hotel_description_vectordb3"

# Embedding and LLM setup
embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=openai_key)

def auto_section_chunk(text):
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
Split the following hotel description into clear, labeled sections like 'Room Descriptions', 'Pet Policy', 'Check-in Details', etc.
Each section should be separated with a clear title followed by its content.

Text:
{text}

Output:
"""
    )
    response = prompt | llm
    result = response.invoke({"text": text}).content.strip()

    raw_chunks = result.split("\n\n")
    documents = []
    for chunk in raw_chunks:
        lines = chunk.strip().split("\n")
        if len(lines) < 2:
            continue
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        documents.append(Document(page_content=content, metadata={"section": title}))
    return documents

def ingest_file():
    print("📄 Loading file...")
    loader = TextLoader(file_path)
    raw_text = loader.load()[0].page_content

    print("🧠 Using LLM to chunk the content by meaning...")
    docs = auto_section_chunk(raw_text)
    print(f"✅ Found {len(docs)} chunks:")
    for d in docs:
        print(f"   - 📘 {d.metadata['section']}")

    print("💾 Creating FAISS vectorstore...")
    vectorstore = FAISS.from_documents(docs, embedding=embeddings)
    os.makedirs(faiss_index_dir, exist_ok=True)
    vectorstore.save_local(faiss_index_dir)

    print(f"✅ Done. Vector DB saved to: {faiss_index_dir}")

if __name__ == "__main__":
    ingest_file()