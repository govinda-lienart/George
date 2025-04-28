import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load .env variables
load_dotenv()

# Fetch API keys safely
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Validate API keys
if not deepseek_api_key:
    raise ValueError("Missing DEEPSEEK_API_KEY! Please set it in your .env or Streamlit Secrets.")

if not openai_api_key:
    raise ValueError("Missing OPENAI_API_KEY! Please set it in your .env or Streamlit Secrets.")

# Shared LLM (DeepSeek)
llm = ChatOpenAI(
    model_name="deepseek-chat",
    temperature=0,
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com/v1"
)

# Shared vectorstore (OpenAI Embeddings)
vectorstore = PineconeVectorStore.from_existing_index(
    index_name="george",
    embedding=OpenAIEmbeddings(openai_api_key=openai_api_key)
)