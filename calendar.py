import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD") or '',
    "database": os.getenv("DB_NAME")
}

st.set_page_config(page_title="🛎️ Book Your Room", layout="centered")
st.title("🏨 Book Your Stay")

# --- DB Helpers ---
def get_rooms():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rooms")
        return cursor.fetchall()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def insert_booking(data):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Check for date conflict
        conflict_query = """
        SELECT COUNT(*) FROM bookings
        WHERE room_id = %s AND NOT (
            %s >= check_out OR %s <= check_in
        )
        """
        cursor.execute(conflict_query, (
            data['room_id'],
            data['check_in'],
            data['check_out']
        ))
        conflict_count = cursor.fetchone()[0]

        if conflict_count > 0:
            return "conflict"

        # Safe insert
        insert_query = """
        INSERT INTO bookings 
        (first_name, last_name, email, phone, room_id, check_in, check_out, num_guests, total_price, special_requests)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            data['first_name'], data['last_name'], data['email'], data['phone'],
            data['room_id'], data['check_in'], data['check_out'],
            data['num_guests'], data['total_price'], data['special_requests']
        ))
        conn.commit()
        return "success"
    except Exception as e:
        st.error(f"❌ Booking error: {e}")
        return "error"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# --- Room Selection ---
rooms = get_rooms()
room_options = {
    f"{r['room_type']} – €{r['price']} (max {r['guest_capacity']} guests)": r
    for r in rooms
}
selected_label = st.selectbox("🛏️ Choose your room", list(room_options.keys()))
room = room_options[selected_label]

# --- Guest Info ---
st.subheader("📝 Guest Info")
first_name = st.text_input("First name")
last_name = st.text_input("Last name")
email = st.text_input("Email")
phone = st.text_input("Phone")

# --- Stay Info ---
st.subheader("📅 Stay Details")
today = datetime.today().date()
check_in = st.date_input("Check-in", min_value=today)
check_out = st.date_input("Check-out", min_value=check_in + timedelta(days=1))
num_guests = st.number_input("👥 Number of guests", min_value=1, max_value=room['guest_capacity'])
special_requests = st.text_area("💬 Special requests (optional)")

# --- Price ---
nights = (check_out - check_in).days
price = nights * room['price']
st.info(f"💸 Total price for {nights} night(s): €{price}")

# --- Confirm Booking ---
if st.button("✅ Confirm Booking"):
    if not first_name or not last_name or not email or not phone:
        st.warning("Please complete all fields.")
    elif check_out <= check_in:
        st.error("❌ Check-out must be after check-in.")
    else:
        booking = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "room_id": room['room_id'],
            "check_in": check_in,
            "check_out": check_out,
            "num_guests": num_guests,
            "total_price": price,
            "special_requests": special_requests
        }

        status = insert_booking(booking)

        if status == "conflict":
            st.error("🚫 This room is already booked for part of your selected dates.")
        elif status == "success":
            st.success(f"🎉 Booking confirmed for {room['room_type']} from {check_in} to {check_out}")
            st.balloons()