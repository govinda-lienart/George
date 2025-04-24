import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PDFMinerLoader
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Retrieve OpenAI API key
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("❌ Missing OPENAI_API_KEY")

# Define file paths
file_path = "/hotel_descriptions.txt"
faiss_index_dir = "/hotel_description_vectordb5"

# Initialize embeddings and LLM
embedding = OpenAIEmbeddings(openai_api_key=openai_key)
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=openai_key)

def auto_chunk_with_llm(text):
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
You are a smart document assistant.

Split the hotel description below into meaningful sections such as "Room Descriptions", "Policies", "Amenities", etc.
Each section should start with a title (on a separate line), followed by its full content.
Do not modify or summarize any content. Just label and organize clearly.

Text:
{text}

Output:
"""
    )
    response = (prompt | llm).invoke({"text": text}).content.strip()

    # Now parse the result into Document objects
    raw_chunks = response.split("\n\n")
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

    print("🧠 LLM chunking by semantic meaning...")
    docs = auto_chunk_with_llm(raw_text)
    print(f"✅ Created {len(docs)} smart chunks:")
    for d in docs:
        print(f"   - 📘 {d.metadata['section']}")

    print("💾 Saving to FAISS vector store...")
    os.makedirs(faiss_index_dir, exist_ok=True)
    vectorstore = FAISS.from_documents(docs, embedding=embedding)
    vectorstore.save_local(faiss_index_dir)
    print(f"✅ Done! Saved at: {faiss_index_dir}")

if __name__ == "__main__":
    ingest_file()