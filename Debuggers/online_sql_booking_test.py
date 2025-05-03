import os

import mysql.connector
from dotenv import load_dotenv

print("🔄 Loading environment variables...")
load_dotenv()

# Print env variables to confirm they're loaded (hide password)
print("✅ Environment variables loaded:")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")
print(f"DB_USERNAME: {os.getenv('DB_USERNAME')}")
print(f"DB_DATABASE: {os.getenv('DB_DATABASE')}")

# Try connecting
print("\n🔌 Attempting to connect to the database...")
try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )
    print("✅ Connected to Google Cloud SQL")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit()

# Example data
data = (
    "Jane",             # first_name
    "Doe",              # last_name
    "jane.doe@example.com",
    "+1234567890",
    2,                  # room_id
    "2025-05-05",       # check_in
    "2025-05-07",       # check_out
    2,                  # num_guests
    300.00,             # total_price
    "No peanuts",       # special_requests
    "BK20250501-JD01"   # booking_number
)

print("\n📝 Prepared booking data:")
for i, value in enumerate(data):
    print(f"  Field {i+1}: {value}")

# Insert SQL
query = """
INSERT INTO bookings (
    first_name, last_name, email, phone, room_id, check_in, check_out,
    num_guests, total_price, special_requests, booking_number
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# Execute query
print("\n🚀 Inserting booking into database...")
try:
    cursor = conn.cursor()
    cursor.execute(query, data)
    conn.commit()
    print("✅ Booking inserted successfully!")
except Exception as e:
    print(f"❌ Failed to insert booking: {e}")
finally:
    print("🔒 Closing connection...")
    try:
        cursor.close()
        conn.close()
        print("✅ Connection closed.")
    except Exception as close_err:
        print(f"⚠️ Error closing connection: {close_err}")
