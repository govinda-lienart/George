# calendar_app.py

import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from email_booker_app import send_confirmation_email

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
    except Exception as e:
        st.error(f"Error retrieving rooms: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def insert_booking(data):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        conflict_query = """
            SELECT * FROM bookings
            WHERE room_id = %s AND (
                (check_in <= %s AND check_out > %s) OR
                (check_in < %s AND check_out >= %s)
            )
        """
        cursor.execute(conflict_query, (
            data['room_id'], data['check_in'], data['check_in'],
            data['check_out'], data['check_out']
        ))
        conflicts = cursor.fetchall()

        if conflicts:
            return False, "This room is already booked for the selected dates."

        insert_query = """
            INSERT INTO bookings (first_name, last_name, email, room_id, check_in, check_out, special_requests)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data['first_name'], data['last_name'], data['email'],
            data['room_id'], data['check_in'], data['check_out'], data['special_requests']
        )
        cursor.execute(insert_query, values)
        conn.commit()
        booking_id = cursor.lastrowid
        return True, booking_id

    except Exception as e:
        return False, str(e)
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# --- Main UI ---
rooms = get_rooms()
if rooms:
    ROOM_NAME_KEY = "room_type"

    room_names = [f"{room[ROOM_NAME_KEY]} (id: {room['room_id']})" for room in rooms]
    room_mapping = {f"{room[ROOM_NAME_KEY]} (id: {room['room_id']})": room['room_id'] for room in rooms}

    with st.form("booking_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        selected_room = st.selectbox("Select a Room", room_names)
        check_in = st.date_input("Check-in Date", min_value=datetime.today())
        check_out = st.date_input("Check-out Date", min_value=datetime.today() + timedelta(days=1))
        special_requests = st.text_area("Special Requests", placeholder="Optional")
        submitted = st.form_submit_button("Book Now")

    if submitted:
        booking_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "room_id": room_mapping[selected_room],
            "check_in": check_in,
            "check_out": check_out,
            "special_requests": special_requests
        }

        success, result = insert_booking(booking_data)
        if success:
            booking_id = result
            send_confirmation_email(email, first_name, last_name, booking_id, check_in, check_out)
            st.success(f"✅ Booking successful! A confirmation email has been sent. Your booking number is {booking_id}.")
        else:
            st.error(f"❌ Booking failed: {result}")
else:
    st.warning("No rooms available or failed to load room list.")