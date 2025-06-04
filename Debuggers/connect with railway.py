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

    cursor.execute("CREATE USER IF NOT EXISTS 'george'@'%' IDENTIFIED BY 'GeorgeSecure123!';")
    cursor.execute("GRANT ALL PRIVILEGES ON railway.* TO 'george'@'%';")
    cursor.execute("FLUSH PRIVILEGES;")

    conn.commit()
    print("✅ External user 'george' created successfully.")
except mysql.connector.Error as err:
    print(f"❌ Error: {err}")
finally:
    if conn.is_connected():
        cursor.close()
        conn.close()
