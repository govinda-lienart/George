# Last updated: 2025-04-29 14:23:14
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database config
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

try:
    print("Connecting to database...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Your test query
    booking_number = "BKG-20250424-0035"
    query = f"SELECT * FROM bookings WHERE booking_number = '{booking_number}'"

    cursor.execute(query)
    results = cursor.fetchall()

    print(f"✅ Query executed. Number of results: {len(results)}")
    for row in results:
        print(row)

except Exception as e:
    print("❌ ERROR:", e)

finally:
    try:
        cursor.close()
        conn.close()
    except:
        pass