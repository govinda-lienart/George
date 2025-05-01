#streamlit run  online_sql_booking_test.py


import streamlit as st
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import date

# Load environment variables from .env
load_dotenv()

# --- DB Connection ---
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )

# --- Streamlit UI ---
st.title("📋 Manual Hotel Booking Form")

with st.form("booking_form"):
    st.subheader("Guest Information")
    guest_name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")

    st.subheader("Booking Details")
    room_id = st.number_input("Room ID", min_value=1, step=1)
    check_in = st.date_input("Check-in Date", min_value=date.today())
    check_out = st.date_input("Check-out Date", min_value=check_in)
    num_guests = st.number_input("Number of Guests", min_value=1, step=1)
    total_price = st.number_input("Total Price (€)", min_value=0.0, step=10.0)
    special_requests = st.text_area("Special Requests", height=100)

    submitted = st.form_submit_button("Submit Booking")

# --- Insert into DB ---
if submitted:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO bookings (
                guest_name, email, phone, room_id, check_in, check_out,
                num_guests, total_price, special_requests
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            guest_name, email, phone, room_id, check_in, check_out,
            num_guests, total_price, special_requests
        )
        cursor.execute(query, values)
        conn.commit()
        st.success("✅ Booking submitted successfully!")
    except Exception as e:
        st.error(f"❌ Failed to submit booking: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass