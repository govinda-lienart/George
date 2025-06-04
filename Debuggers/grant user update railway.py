import mysql.connector

config = {
    'host': 'switchback.proxy.rlwy.net',
    'port': 47246,
    'user': 'root',
    'password': 'mGGqppWgZFMoJXtwWrfaJfAFevQSkBnW',
    'database': 'railway'
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    cursor.execute("GRANT UPDATE ON railway.bookings TO 'form_client'@'%';")
    cursor.execute("FLUSH PRIVILEGES;")

    conn.commit()
    print("✅ UPDATE access granted to 'form_client' on 'bookings' table.")

except mysql.connector.Error as err:
    print(f"❌ Error: {err}")

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
