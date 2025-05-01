import mysql.connector
import os
from dotenv import load_dotenv

def retrieve_all_bookings():
    """
    Connects to the Google Cloud SQL database and retrieves all data from the 'bookings' table.
    Prints the data to the console.
    """
    # Load environment variables
    load_dotenv()

    try:
        # Establish database connection
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )
        print("✅ Connected to Google Cloud SQL")
        cursor = conn.cursor()

        # Execute the query to retrieve all data from the bookings table
        query = "SELECT * FROM bookings;"
        cursor.execute(query)
        results = cursor.fetchall()

        # Print the column names
        cursor.execute("SHOW COLUMNS FROM bookings;")
        columns = [column[0] for column in cursor.fetchall()]
        print("\nColumns:", columns)

        # Print the data
        print("\nData from the 'bookings' table:")
        if results:
            for row in results:
                print(row)  # Print each row
        else:
            print("No bookings found in the table.")

    except Exception as e:
        print(f"❌ Error retrieving data: {e}")
    finally:
        # Close the connection
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
                print("✅ Connection closed.")
        except Exception as close_err:
            print(f"⚠️ Error closing connection: {close_err}")

if __name__ == "__main__":
    retrieve_all_bookings()
