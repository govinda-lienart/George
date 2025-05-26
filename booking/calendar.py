# ========================================
# 📋 ROLE OF THIS SCRIPT - calendar.py
# ========================================

"""
Calendar booking form module for the George AI Hotel Receptionist app.
- Handles room booking form rendering and user input validation
- Manages database connections for booking operations
- Processes booking confirmations and sends email notifications
- Integrates with follow-up tool for post-booking activities
- Generates unique booking numbers and handles room availability checks
"""

### Last updated: 2025-05-23

# ========================================
# 📦 IMPORTS & CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 📚 STANDARD LIBRARY IMPORTS
# ────────────────────────────────────────────────
import os  # Operating system interfaces, environment variables
from datetime import datetime, timedelta  # Date and time handling utilities
from dotenv import load_dotenv  # Load environment variables from .env file

# ────────────────────────────────────────────────
# 🔧 THIRD-PARTY LIBRARY IMPORTS
# ────────────────────────────────────────────────
import streamlit as st  # Web app framework for interactive UI
import mysql.connector  # MySQL database connectivity

# ────────────────────────────────────────────────
# 📧 CUSTOM EMAIL MODULE
# ────────────────────────────────────────────────
from booking.email import send_confirmation_email  # Email confirmation functionality

# ────────────────────────────────────────────────
# 🛠️ CUSTOM FOLLOW-UP TOOL
# ────────────────────────────────────────────────
# ✅ ADD FOLLOW-UP IMPORT
from tools.followup_tool import create_followup_message  # Post-booking follow-up messaging

# ┌─────────────────────────────────────────┐
# │  ENVIRONMENT VARIABLES LOADING          │
# └─────────────────────────────────────────┘
# Load environment variables
load_dotenv()


# ========================================
# 🔐 SECURE SECRET ACCESS
# ========================================

# ────────────────────────────────────────────────
# 🔑 SECRET MANAGEMENT UTILITY
# ────────────────────────────────────────────────
def get_secret(key, default=None):
    """
    Retrieve a secret value by key.
    First tries to get the secret from Streamlit's secrets management.
    If not found, falls back to environment variables.
    Returns a default value if the key is not found in either.
    """
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# ========================================
# 🛠️ DATABASE CONNECTION CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 📊 DB CONNECTION FOR BOOKING FORM
# ────────────────────────────────────────────────
db_config = {
    "host": get_secret("DB_HOST_FORM"),
    "port": int(get_secret("DB_PORT_FORM", 3306)),
    "user": get_secret("DB_USERNAME_FORM"),
    "password": get_secret("DB_PASSWORD_FORM") or '',
    "database": get_secret("DB_DATABASE_FORM")
}


# ========================================
# 🏨 ROOM DATA MANAGEMENT
# ========================================

# ────────────────────────────────────────────────
# 🏨 ROOM FETCH UTILITY
# ────────────────────────────────────────────────
def get_rooms():
    """
    Retrieve all available rooms from the database.
    Returns a list of room dictionaries with room details.
    Handles database connection errors gracefully.
    """
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


# ========================================
# 🆔 BOOKING REFERENCE SYSTEM
# ========================================

# ────────────────────────────────────────────────
# 🆔 BOOKING NUMBER GENERATOR
# ────────────────────────────────────────────────
def generate_booking_number(booking_id):
    """
    Generate a unique booking reference number.
    Format: BKG-YYYYMMDD-XXXX (where XXXX is zero-padded booking ID)
    """
    today_str = datetime.today().strftime("%Y%m%d")
    return f"BKG-{today_str}-{str(booking_id).zfill(4)}"


# ========================================
# 🧾 BOOKING PROCESSING ENGINE
# ========================================

# ────────────────────────────────────────────────
# 🧾 BOOKING INSERT LOGIC
# ────────────────────────────────────────────────
def insert_booking(data):
    """
    Insert a new booking into the database after checking for conflicts.
    Returns (success: bool, result: tuple/str) where result is either
    booking details on success or error message on failure.
    """
    try:
        # ┌─────────────────────────────────────────┐
        # │  DATABASE CONNECTION SETUP              │
        # └─────────────────────────────────────────┘
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # ┌─────────────────────────────────────────┐
        # │  BOOKING CONFLICT DETECTION             │
        # └─────────────────────────────────────────┘
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

        # ┌─────────────────────────────────────────┐
        # │  BOOKING INSERTION PROCESS              │
        # └─────────────────────────────────────────┘
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

        # ┌─────────────────────────────────────────┐
        # │  BOOKING NUMBER GENERATION & UPDATE     │
        # └─────────────────────────────────────────┘
        booking_number = generate_booking_number(booking_id)
        update_query = "UPDATE bookings SET booking_number = %s WHERE booking_id = %s"
        cursor.execute(update_query, (booking_number, booking_id))
        conn.commit()

        return True, (booking_number, data['total_price'], data['room_type'])

    except Exception as e:
        return False, str(e)
    finally:
        # ┌─────────────────────────────────────────┐
        # │  DATABASE CONNECTION CLEANUP            │
        # └─────────────────────────────────────────┘
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
        except:
            pass


# ========================================
# 📋 USER INTERFACE COMPONENTS
# ========================================

# ────────────────────────────────────────────────
# 📋 BOOKING FORM RENDERER
# ────────────────────────────────────────────────
def render_booking_form():
    """
    Render the interactive booking form in the Streamlit interface.
    Handles room selection, date validation, guest information collection,
    and booking confirmation with email notifications.
    """
    # ┌─────────────────────────────────────────┐
    # │  ROOM DATA LOADING & VALIDATION         │
    # └─────────────────────────────────────────┘
    rooms = get_rooms()
    if not rooms:
        st.warning("No rooms available or failed to load room list.")
        return

    # ┌─────────────────────────────────────────┐
    # │  ROOM MAPPING CONFIGURATION             │
    # └─────────────────────────────────────────┘
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

    # ┌─────────────────────────────────────────┐
    # │  COUNTRY CODE DROPDOWN SETUP            │
    # └─────────────────────────────────────────┘
    # Country code dropdown
    country_codes = [
        "+32 Belgium", "+1 USA/Canada", "+44 UK", "+33 France", "+49 Germany", "+84 Vietnam",
        "+91 India", "+81 Japan", "+61 Australia", "+34 Spain", "+39 Italy", "+86 China", "+7 Russia"
    ]

    # ┌─────────────────────────────────────────┐
    # │  BOOKING FORM INTERFACE                 │
    # └─────────────────────────────────────────┘
    with st.form("booking_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        country_code = st.selectbox("Country Code", country_codes, index=0)
        phone_number = st.text_input("Phone Number (without country code)")
        phone = f"{country_code.split()[0]} {phone_number}" if phone_number else ""
        num_guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=1)
        selected_room = st.selectbox("Select a Room", room_names)
        check_in = st.date_input("Check-in Date", min_value=datetime.today())
        check_out = st.date_input("Check-out Date", min_value=datetime.today() + timedelta(days=1))
        special_requests = st.text_area("Special Requests", placeholder="Optional")
        submitted = st.form_submit_button("Book Now")

    # ┌─────────────────────────────────────────┐
    # │  FORM SUBMISSION PROCESSING             │
    # └─────────────────────────────────────────┘
    if submitted:
        # ┌─────────────────────────────────────────┐
        # │  FORM VALIDATION                        │
        # └─────────────────────────────────────────┘
        if not first_name or not last_name or not email:
            st.warning("Please fill in all required fields: First Name, Last Name, Email.")
            return

        # ┌─────────────────────────────────────────┐
        # │  PRICING CALCULATION                    │
        # └─────────────────────────────────────────┘
        room_info = room_mapping[selected_room]
        nights = (check_out - check_in).days
        total_price = room_info["price"] * nights * num_guests

        # ┌─────────────────────────────────────────┐
        # │  BOOKING DATA PREPARATION               │
        # └─────────────────────────────────────────┘
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

        # ┌─────────────────────────────────────────┐
        # │  BOOKING PROCESSING & CONFIRMATION     │
        # └─────────────────────────────────────────┘
        success, result = insert_booking(booking_data)
        if success:
            booking_number, total_price, room_type = result

            # ┌─────────────────────────────────────────┐
            # │  SESSION STATE BOOKING INFO STORAGE    │
            # └─────────────────────────────────────────┘
            # ✅ STORE DETAILED BOOKING INFO FOR FOLLOW-UP
            st.session_state.latest_booking_info = {
                "booking_number": booking_number,
                "client_name": f"{first_name} {last_name}",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "check_in": check_in.strftime("%B %d, %Y"),
                "check_out": check_out.strftime("%B %d, %Y"),
                "room_type": room_type,
                "total_price": total_price,
                "num_guests": num_guests,
                "special_requests": special_requests or "None"
            }

            # ┌─────────────────────────────────────────┐
            # │  EMAIL CONFIRMATION SENDING             │
            # └─────────────────────────────────────────┘
            send_confirmation_email(
                email, first_name, last_name, booking_number,
                check_in, check_out, total_price, num_guests, phone, room_type
            )

            # ┌─────────────────────────────────────────┐
            # │  SUCCESS UI FEEDBACK                    │
            # └─────────────────────────────────────────┘
            # ✅ SHOW BOOKING CONFIRMATION BRIEFLY
            st.success("✅ Booking confirmed!")
            st.balloons()
            st.info(
                f"**Booking Number:** {booking_number}\n"
                f"**Room Type:** {room_type}\n"
                f"**Guests:** {num_guests}\n"
                f"**Total Price:** €{total_price}\n\n"
                f"A confirmation email has been sent to {email}."
            )

            # ┌─────────────────────────────────────────┐
            # │  FORM CLOSURE & STATE RESET             │
            # └─────────────────────────────────────────┘
            # ✅ CLOSE FORM AFTER CONFIRMATION
            st.session_state.booking_mode = False

            # ┌─────────────────────────────────────────┐
            # │  POST-BOOKING FOLLOW-UP ACTIVATION      │
            # └─────────────────────────────────────────┘
            # ✅ SIMPLIFIED HARDCODED FOLLOW-UP MESSAGE (FAST)
            followup = create_followup_message()  # Now hardcoded and instant
            st.session_state.awaiting_activity_consent = followup["awaiting_activity_consent"]

            # ┌─────────────────────────────────────────┐
            # │  CHAT HISTORY INTEGRATION               │
            # └─────────────────────────────────────────┘
            # ✅ ADD FOLLOW-UP MESSAGE TO CHAT HISTORY
            if "history" not in st.session_state:
                st.session_state.history = []
            st.session_state.history.append(("bot", followup["message"]))

            # ┌─────────────────────────────────────────┐
            # │  UI REFRESH TRIGGER                     │
            # └─────────────────────────────────────────┘
            # ✅ FORCE RERUN TO SHOW FOLLOW-UP IN CHAT
            st.rerun()

        else:
            # ┌─────────────────────────────────────────┐
            # │  ERROR HANDLING & USER FEEDBACK         │
            # └─────────────────────────────────────────┘
            st.error(f"❌ Booking failed: {result}")


# ========================================
# 📤 MODULE EXPORTS
# ========================================

# ────────────────────────────────────────────────
# 📦 EXPLICIT EXPORT CONFIGURATION
# ────────────────────────────────────────────────
# ✅ Export explicitly for import in booking_tool
__all__ = ["render_booking_form"]