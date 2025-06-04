import mysql.connector

# Update your full-access root config (already created)
admin_config = {
    'host': 'switchback.proxy.rlwy.net',
    'port': 47246,
    'user': 'root',
    'password': 'mGGqppWgZFMoJXtwWrfaJfAFevQSkBnW',
    'database': 'railway'
}

# Define users to create with their permissions
users_to_create = [
    {
        "username": "form_client",
        "password": "FormSecure123!",
        "privileges": "INSERT",
        "description": "Form client – insert-only access"
    },
    {
        "username": "readonly_user",
        "password": "ReadOnlySecure123!",
        "privileges": "SELECT",
        "description": "Read-only user"
    }
]

try:
    conn = mysql.connector.connect(**admin_config)
    cursor = conn.cursor()

    for user in users_to_create:
        print(f"🔧 Creating user: {user['username']} ({user['description']})")
        cursor.execute(f"CREATE USER IF NOT EXISTS '{user['username']}'@'%' IDENTIFIED BY '{user['password']}';")
        cursor.execute(f"GRANT {user['privileges']} ON railway.* TO '{user['username']}'@'%';")

    cursor.execute("FLUSH PRIVILEGES;")
    conn.commit()
    print("✅ All users created and permissions applied successfully.")

except mysql.connector.Error as err:
    print(f"❌ Error: {err}")

finally:
    if conn.is_connected():
        cursor.close()
        conn.close()
