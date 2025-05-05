# Last updated: calendar
import streamlit as st
import mysql.connector
from datetime import datetime, timedelta
from booking.email import send_confirmation_email

# ✅ Load secrets from Streamlit or fallback to local .env
from dotenv import load_dotenv
import os
load_dotenv()

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# ✅ DB connection config for FORM user
db_config = {
    "host": get_secret("DB_HOST_FORM"),
    "port": int(get_secret("DB_PORT_FORM", 3306)),
    "user": get_secret("DB_USERNAME_FORM"),
    "password": get_secret("DB_PASSWORD_FORM") or '',
    "database": get_secret("DB_DATABASE_FORM")
}

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
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
        except:
            pass

def generate_booking_number(booking_id):
    today_str = datetime.today().strftime("%Y%m%d")
    return f"BKG-{today_str}-{str(booking_id).zfill(4)}"

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
            INSERT INTO bookings 
            (first_name, last_name, email, phone, room_id, check_in, check_out, num_guests, total_price, special_requests)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data['first_name'], data['last_name'], data['email'], data['phone'],
            data['room_id'], data['check_in'], data['check_out'],
            data['num_guests'], data['total_price'], data['special_requests']
        )
        cursor.execute(insert_query, values)
        conn.commit()
        booking_id = cursor.lastrowid

        booking_number = generate_booking_number(booking_id)
        update_query = "UPDATE bookings SET booking_number = %s WHERE booking_id = %s"
        cursor.execute(update_query, (booking_number, booking_id))
        conn.commit()

        return True, (booking_number, data['total_price'], data['room_type'])

    except Exception as e:
        return False, str(e)
    finally:
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
        except:
            pass

def render_booking_form():
    rooms = get_rooms()
    if not rooms:
        st.warning("No rooms available or failed to load room list.")
        return

    ROOM_NAME_KEY = "room_type"
    ROOM_PRICE_KEY = "price"

    room_names = [f"{room[ROOM_NAME_KEY]} (id: {room['room_id']})" for room in rooms]
    room_mapping = {
        f"{room[ROOM_NAME_KEY]} (id: {room['room_id']})": {
            "id": room["room_id"],
            "type": room[ROOM_NAME_KEY],
            "price": room[ROOM_PRICE_KEY]
        } for room in rooms
    }

    with st.form("booking_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        num_guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=1)
        selected_room = st.selectbox("Select a Room", room_names)
        check_in = st.date_input("Check-in Date", min_value=datetime.today())
        check_out = st.date_input("Check-out Date", min_value=datetime.today() + timedelta(days=1))
        special_requests = st.text_area("Special Requests", placeholder="Optional")
        submitted = st.form_submit_button("Book Now")

    if submitted:
        room_info = room_mapping[selected_room]
        nights = (check_out - check_in).days
        total_price = room_info["price"] * nights * num_guests

        booking_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "room_id": room_info["id"],
            "room_type": room_info["type"],
            "check_in": check_in,
            "check_out": check_out,
            "num_guests": num_guests,
            "total_price": total_price,
            "special_requests": special_requests
        }

        success, result = insert_booking(booking_data)
        if success:
            booking_number, total_price, room_type = result
            send_confirmation_email(
                email, first_name, last_name, booking_number,
                check_in, check_out, total_price, num_guests, phone, room_type
            )
            st.success("✅ Booking confirmed!")
            st.info(
                f"**Booking Number:** {booking_number}\n"
                f"**Room Type:** {room_type}\n"
                f"**Guests:** {num_guests}\n"
                f"**Total Price:** €{total_price}\n\n"
                f"A confirmation email has been sent to {email}."
            )
            st.session_state.booking_mode = False
            st.experimental_rerun()
        else:
            st.error(f"❌ Booking failed: {result}")

# ✅ Export explicitly for import in booking_tool
__all__ = ["render_booking_form"]
