import mysql.connector

config = {
    'host': 'switchback.proxy.rlwy.net',  # ✅ Use Railway's public host
    'port': 47246,                         # ✅ Use the correct external port
    'user': 'root',
    'password': 'mGGqppWgZFMoJXtwWrfaJfAFevQSkBnW',
    'database': 'railway'
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    cursor.execute("GRANT SELECT, INSERT ON railway.* TO 'form_client'@'%';")
    cursor.execute("FLUSH PRIVILEGES;")

    conn.commit()
    print("✅ Permissions updated for 'form_client' (SELECT, INSERT).")

except mysql.connector.Error as err:
    print(f"❌ Error: {err}")

finally:
    try:
        if conn.is_connected():
            cursor.close()
            conn.close()
    except NameError:
        pass  # conn was never defined due to earlier failure
