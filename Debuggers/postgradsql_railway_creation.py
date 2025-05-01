import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch credentials from environment
host = os.getenv("PG_HOST")
port = os.getenv("PG_PORT")
user = os.getenv("PG_USER")
password = os.getenv("PG_PASSWORD")
dbname = os.getenv("PG_DB")

print(f"🔌 Attempting connection to {host}:{port} as {user}...")

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")