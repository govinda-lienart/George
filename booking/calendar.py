# ========================================
# 📦 Imports & Configuration
# ========================================
import streamlit as st
import mysql.connector
from datetime import datetime, timedelta
import calendar
import pandas as pd
from booking.email import send_confirmation_email
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


# ========================================
# 🔐 Secure Secret Access
# ========================================
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# ========================================
# 🛠️ DB Connection for Booking Form
# ========================================
db_config = {
    "host": get_secret("DB_HOST_FORM"),
    "port": int(get_secret("DB_PORT_FORM", 3306)),
    "user": get_secret("DB_USERNAME_FORM"),
    "password": get_secret("DB_PASSWORD_FORM") or '',
    "database": get_secret("DB_DATABASE_FORM")
}


# ========================================
# 🏨 Room Fetch Utility
# ========================================
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


# ========================================
# 🆔 Booking Number Generator
# ========================================
def generate_booking_number(booking_id):
    today_str = datetime.today().strftime("%Y%m%d")
    return f"BKG-{today_str}-{str(booking_id).zfill(4)}"


# ========================================
# 📊 Room Availability Visualization
# ========================================
def visualize_availability(room_id, start_date, end_date):
    """
    Add a visual representation of room availability to the calendar
    Returns a dictionary mapping dates to availability status
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Your existing conflict_query with slight modification
        conflict_query = """
            SELECT * FROM bookings
            WHERE room_id = %s AND (
                (check_in <= %s AND check_out > %s) OR
                (check_in < %s AND check_out >= %s)
            )
        """
        cursor.execute(conflict_query, (
            room_id, end_date, start_date, end_date, start_date
        ))
        conflicts = cursor.fetchall()

        # Create a date range from start to end date
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date)
            current_date += timedelta(days=1)

        # Mark which dates are available
        availability = {}
        for date in all_dates:
            availability[date] = True  # Assume available initially

        # Mark booked dates as unavailable
        for booking in conflicts:
            booking_start = booking['check_in']
            booking_end = booking['check_out']

            # For each date in our range
            for date in all_dates:
                # If the date falls within this booking, mark as unavailable
                if booking_start <= date < booking_end:
                    availability[date] = False

        return availability

    except Exception as e:
        st.error(f"Error checking availability: {e}")
        return {}
    finally:
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
        except:
            pass


# ========================================
# 📅 Availability Calendar Display
# ========================================
def display_availability_calendar(room_id=None, selected_room_type=None):
    """Display a visual calendar for room availability"""

    # Get list of rooms if room_id not specified
    if room_id is None:
        rooms = get_rooms()
        room_options = [f"{room['room_type']} (ID: {room['room_id']})" for room in rooms]
        selected_option = st.selectbox("Select Room", room_options)
        room_id = int(selected_option.split("ID: ")[1].split(")")[0])
        selected_room_type = selected_option.split(" (ID:")[0]

    # Date range selection
    today = datetime.today().date()
    default_end = today + timedelta(days=30)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From date", today, min_value=today)
    with col2:
        end_date = st.date_input("To date", default_end, min_value=start_date)

    # Get the availability data
    availability = visualize_availability(room_id, start_date, end_date)

    if not availability:
        st.warning("Could not retrieve availability data.")
        return

    # Display availability calendar
    st.write("### Room Availability")
    if selected_room_type:
        st.write(f"**Room:** {selected_room_type}")

    # Legend
    st.write("**Legend:** 🟢 Available  |  🔴 Booked")

    # Display monthly calendars
    current_month = start_date.month
    current_year = start_date.year
    end_month = end_date.month
    end_year = end_date.year

    # Calculate the total number of months to display
    total_months = (end_year - current_year) * 12 + (end_month - current_month) + 1

    # Display each month
    for month_offset in range(total_months):
        # Calculate the month and year
        display_month = (current_month + month_offset - 1) % 12 + 1
        display_year = current_year + (current_month + month_offset - 1) // 12

        # Get the first day of the month (0 = Monday)
        first_day, days_in_month = calendar.monthrange(display_year, display_month)

        # Display month and year
        st.write(f"#### {calendar.month_name[display_month]} {display_year}")

        # Create the day headers
        cols = st.columns(7)
        for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            cols[i].write(f"**{day}**")

        # Create the calendar grid
        day = 1
        for week in range(6):  # Calendar can have up to 6 weeks
            if day > days_in_month:
                break

            cols = st.columns(7)

            for weekday in range(7):
                if (week == 0 and weekday < first_day) or day > days_in_month:
                    # Empty cell
                    cols[weekday].write("")
                else:
                    # Create date object for this day
                    this_date = datetime(display_year, display_month, day).date()

                    # Check if this date is within our range
                    if start_date <= this_date <= end_date:
                        is_available = availability.get(this_date, False)
                        if is_available:
                            cols[weekday].markdown(f"🟢 **{day}**")
                        else:
                            cols[weekday].markdown(f"🔴 **{day}**")
                    else:
                        # Date out of range, show in gray
                        cols[weekday].markdown(f"<span style='color:gray'>{day}</span>", unsafe_allow_html=True)

                    day += 1

    # Add a button to proceed to booking
    if st.button("📝 Book This Room"):
        # Store info for pre-filling the booking form
        st.session_state.pre_selected_room_id = room_id
        st.session_state.pre_selected_check_in = start_date
        st.session_state.pre_selected_check_out = end_date
        st.session_state.show_calendar = False
        st.session_state.booking_mode = True
        st.rerun()


# ========================================
# 🧾 Booking Insert Logic
# ========================================
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


# ========================================
# 📋 Booking Form Renderer
# ========================================
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

    # Add option to view availability calendar
    show_calendar = st.checkbox("📅 Check Room Availability", value=st.session_state.get("show_calendar", False))

    if show_calendar:
        # Show the availability calendar
        display_availability_calendar()
        return  # Return early - user will click 'Book This Room' to continue

    # Get pre-selected values if available
    pre_selected_room_id = st.session_state.get("pre_selected_room_id")
    pre_selected_check_in = st.session_state.get("pre_selected_check_in")
    pre_selected_check_out = st.session_state.get("pre_selected_check_out")

    # Find pre-selected room in options
    pre_selected_room_option = None
    if pre_selected_room_id:
        for room_option in room_names:
            if f"id: {pre_selected_room_id}" in room_option:
                pre_selected_room_option = room_option
                break

    # Clear pre-selection after use
    if pre_selected_room_id:
        del st.session_state.pre_selected_room_id
    if pre_selected_check_in:
        del st.session_state.pre_selected_check_in
    if pre_selected_check_out:
        del st.session_state.pre_selected_check_out

    # Country code dropdown
    country_codes = [
        "+32 Belgium", "+1 USA/Canada", "+44 UK", "+33 France", "+49 Germany", "+84 Vietnam",
        "+91 India", "+81 Japan", "+61 Australia", "+34 Spain", "+39 Italy", "+86 China", "+7 Russia"
    ]

    with st.form("booking_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        country_code = st.selectbox("Country Phone Code", country_codes, index=0)
        phone_number = st.text_input("Phone Number (without country code)")
        phone = f"{country_code.split()[0]} {phone_number}" if phone_number else ""
        num_guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=1)

        # Use pre-selected room if available
        if pre_selected_room_option:
            selected_room = st.selectbox("Select a Room", room_names,
                                         index=room_names.index(pre_selected_room_option))
        else:
            selected_room = st.selectbox("Select a Room", room_names)

        # Use pre-selected dates if available
        if pre_selected_check_in:
            check_in = st.date_input("Check-in Date", pre_selected_check_in, min_value=datetime.today())
        else:
            check_in = st.date_input("Check-in Date", min_value=datetime.today())

        if pre_selected_check_out:
            check_out = st.date_input("Check-out Date", pre_selected_check_out,
                                      min_value=check_in + timedelta(days=1))
        else:
            check_out = st.date_input("Check-out Date",
                                      min_value=check_in + timedelta(days=1))

        special_requests = st.text_area("Special Requests", placeholder="Optional")
        submitted = st.form_submit_button("Book Now")

    if submitted:
        if not first_name or not last_name or not email:
            st.warning("Please fill in all required fields: First Name, Last Name, Email.")
            return

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
            st.balloons()
            st.info(
                f"**Booking Number:** {booking_number}\n"
                f"**Room Type:** {room_type}\n"
                f"**Guests:** {num_guests}\n"
                f"**Total Price:** €{total_price}\n\n"
                f"A confirmation email has been sent to {email}."
            )
            st.session_state.booking_mode = False
        else:
            st.error(f"❌ Booking failed: {result}")


# ✅ Export explicitly for import in booking_tool
__all__ = ["render_booking_form"]