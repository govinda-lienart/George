# calendar.py - Fixed version without problematic key parameter

import streamlit as st
import mysql.connector
from datetime import datetime, timedelta
from booking.email import send_confirmation_email
from dotenv import load_dotenv
import os

load_dotenv()


def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


db_config = {
    "host": get_secret("DB_HOST_FORM"),
    "port": int(get_secret("DB_PORT_FORM", 3306)),
    "user": get_secret("DB_USERNAME_FORM"),
    "password": get_secret("DB_PASSWORD_FORM") or '',
    "database": get_secret("DB_DATABASE_FORM")
}


def get_room_availability(room_id):
    """Get unavailable dates for a specific room"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        blocked_dates = set()

        # Get booking conflicts
        booking_query = """
            SELECT check_in, check_out FROM bookings 
            WHERE room_id = %s 
            AND check_out > CURDATE()
            AND check_in IS NOT NULL 
            AND check_out IS NOT NULL
        """
        cursor.execute(booking_query, (room_id,))
        bookings = cursor.fetchall()

        # Add booking periods
        for check_in, check_out in bookings:
            if check_in and check_out:
                current_date = check_in
                while current_date < check_out:
                    blocked_dates.add(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=1)

        # Get manual availability blocks
        try:
            availability_query = """
                SELECT date FROM room_availability 
                WHERE room_id = %s 
                AND is_available = 0 
                AND date >= CURDATE()
                AND date IS NOT NULL
            """
            cursor.execute(availability_query, (room_id,))
            manual_blocks = cursor.fetchall()

            # Add manually blocked dates
            for (date_obj,) in manual_blocks:
                if date_obj:
                    if hasattr(date_obj, 'strftime'):
                        blocked_dates.add(date_obj.strftime('%Y-%m-%d'))
                    else:
                        blocked_dates.add(str(date_obj))
        except:
            pass  # room_availability table might not exist

        return sorted(list(blocked_dates))

    except Exception as e:
        st.error(f"Error checking room {room_id} availability: {e}")
        return []
    finally:
        try:
            if conn.is_connected():
                cursor.close()
                conn.close()
        except:
            pass


def get_rooms():
    """Get all rooms from database"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM rooms ORDER BY room_id")
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


def check_date_conflicts(room_id, check_in, check_out):
    """Check for booking conflicts"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Check booking conflicts
        booking_conflict_query = """
            SELECT booking_number, check_in, check_out FROM bookings
            WHERE room_id = %s AND (
                (check_in <= %s AND check_out > %s) OR
                (check_in < %s AND check_out >= %s) OR
                (check_in >= %s AND check_in < %s)
            )
        """
        cursor.execute(booking_conflict_query, (
            room_id, check_in, check_in, check_out, check_out, check_in, check_out
        ))
        booking_conflicts = cursor.fetchall()

        if booking_conflicts:
            conflict_details = []
            for booking in booking_conflicts:
                conflict_details.append(f"Conflicts with booking {booking[0]} ({booking[1]} to {booking[2]})")
            return True, conflict_details

        return False, []

    except Exception as e:
        return True, [f"Error checking conflicts: {e}"]
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
    """Insert booking with conflict checking"""
    try:
        # Check for conflicts
        has_conflict, conflict_details = check_date_conflicts(
            data['room_id'], data['check_in'], data['check_out']
        )

        if has_conflict:
            return False, f"Booking conflicts: {'; '.join(conflict_details)}"

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert booking
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

        # Generate booking number
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


def render_simple_calendar_display(room_id, room_name, unavailable_dates):
    """Simple calendar display that definitely works"""

    st.markdown("### 🗓️ Room Availability Calendar")

    if not unavailable_dates:
        st.success(f"✅ **{room_name}** is fully available!")
        return

    # Show unavailable dates in a user-friendly way
    st.warning(f"🚫 **{room_name}** - Unavailable dates:")

    # Group consecutive dates for better display
    if len(unavailable_dates) > 0:
        date_ranges = []
        current_range = [unavailable_dates[0]]

        for i in range(1, len(unavailable_dates)):
            prev_date = datetime.strptime(unavailable_dates[i - 1], '%Y-%m-%d')
            curr_date = datetime.strptime(unavailable_dates[i], '%Y-%m-%d')

            if (curr_date - prev_date).days == 1:
                current_range.append(unavailable_dates[i])
            else:
                date_ranges.append(current_range)
                current_range = [unavailable_dates[i]]

        date_ranges.append(current_range)

        # Display date ranges
        for date_range in date_ranges[:8]:  # Show max 8 ranges
            if len(date_range) == 1:
                st.write(f"• {date_range[0]}")
            else:
                st.write(f"• {date_range[0]} to {date_range[-1]} ({len(date_range)} days)")

        if len(date_ranges) > 8:
            st.write(f"... and {len(date_ranges) - 8} more periods")

        total_blocked = len(unavailable_dates)
        st.info(f"📊 Total unavailable days: **{total_blocked}**")


def render_booking_form():
    """Simplified booking form that works reliably"""
    rooms = get_rooms()
    if not rooms:
        st.warning("No rooms available or failed to load room list.")
        return

    st.markdown("## 🏨 Hotel Booking")

    # Room selection with session state for persistence
    if 'selected_room_idx' not in st.session_state:
        st.session_state.selected_room_idx = 0

    # Create room options
    room_options = []
    for room in rooms:
        room_options.append(f"{room['room_type']} - €{room['price']}/night (Max {room['guest_capacity']} guests)")

    # Room selector
    selected_room_idx = st.selectbox(
        "🏠 **Select Your Room:**",
        range(len(room_options)),
        format_func=lambda x: room_options[x],
        index=st.session_state.selected_room_idx
    )

    # Update session state
    st.session_state.selected_room_idx = selected_room_idx
    selected_room = rooms[selected_room_idx]

    # Get availability for selected room
    with st.spinner("Loading availability..."):
        unavailable_dates = get_room_availability(selected_room['room_id'])

    # Show simple calendar display
    render_simple_calendar_display(
        selected_room['room_id'],
        selected_room['room_type'],
        unavailable_dates
    )

    # Show detailed availability in expander
    if unavailable_dates:
        with st.expander("📋 View all unavailable dates"):
            # Create columns for better display
            num_cols = 3
            cols = st.columns(num_cols)

            for i, date in enumerate(unavailable_dates[:30]):  # Show max 30 dates
                col_idx = i % num_cols
                cols[col_idx].write(f"• {date}")

            if len(unavailable_dates) > 30:
                st.write(f"... and {len(unavailable_dates) - 30} more dates")

    # Country codes
    country_codes = [
        "+32 Belgium", "+1 USA/Canada", "+44 UK", "+33 France", "+49 Germany", "+84 Vietnam",
        "+91 India", "+81 Japan", "+61 Australia", "+34 Spain", "+39 Italy", "+86 China", "+7 Russia"
    ]

    # Main booking form
    with st.form("booking_form"):
        st.markdown("### 📝 Booking Details")

        # Personal Information
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name *")
            last_name = st.text_input("Last Name *")
        with col2:
            email = st.text_input("Email Address *")
            country_code = st.selectbox("Country Code", country_codes, index=0)

        phone_number = st.text_input("Phone Number (without country code)")
        phone = f"{country_code.split()[0]} {phone_number}" if phone_number else ""

        # Booking Details
        col3, col4 = st.columns(2)
        with col3:
            num_guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=1)
        with col4:
            # Display selected room info
            st.write("**Selected Room:**")
            st.info(f"{selected_room['room_type']} - €{selected_room['price']}/night")

        # Date inputs
        col5, col6 = st.columns(2)
        with col5:
            check_in = st.date_input("Check-in Date", min_value=datetime.today())
        with col6:
            check_out = st.date_input("Check-out Date", min_value=datetime.today() + timedelta(days=1))

        # Validation
        room_info = selected_room

        # Guest capacity validation
        capacity_error = None
        if num_guests > room_info["guest_capacity"]:
            capacity_error = f"This room accommodates maximum {room_info['guest_capacity']} guests. You selected {num_guests} guests."

        # Date validation
        date_validation_error = None
        conflict_details = []

        if check_in and check_out:
            if check_in >= check_out:
                date_validation_error = "Check-out date must be after check-in date."
            else:
                has_conflicts, conflicts = check_date_conflicts(room_info["room_id"], check_in, check_out)
                if has_conflicts:
                    date_validation_error = "Selected dates conflict with existing bookings"
                    conflict_details = conflicts

        # Display validation messages
        if capacity_error:
            st.error(f"❌ {capacity_error}")

        if date_validation_error:
            st.error(f"❌ {date_validation_error}")
            if conflict_details:
                for conflict in conflict_details:
                    st.warning(f"⚠️ {conflict}")

        special_requests = st.text_area("Special Requests", placeholder="Any special requirements...")

        # Calculate pricing
        if check_in and check_out and not date_validation_error:
            nights = (check_out - check_in).days
            total_price = room_info["price"] * nights

            st.success(f"""
            **Booking Summary:**
            - **Room:** {room_info['room_type']}
            - **Dates:** {check_in.strftime('%B %d, %Y')} to {check_out.strftime('%B %d, %Y')}
            - **Duration:** {nights} nights
            - **Guests:** {num_guests}
            - **Total Price:** €{total_price}
            """)

        # Submit button
        all_errors = [e for e in [capacity_error, date_validation_error] if e]
        submitted = st.form_submit_button(
            "🏨 Confirm Booking",
            disabled=bool(all_errors)
        )

        if submitted and not all_errors:
            if not first_name or not last_name or not email:
                st.warning("⚠️ Please fill in all required fields marked with *")
                return

            nights = (check_out - check_in).days
            total_price = room_info["price"] * nights

            booking_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "room_id": room_info["room_id"],
                "room_type": room_info["room_type"],
                "check_in": check_in,
                "check_out": check_out,
                "num_guests": num_guests,
                "total_price": total_price,
                "special_requests": special_requests
            }

            with st.spinner("Processing your booking..."):
                success, result = insert_booking(booking_data)

            if success:
                booking_number, final_price, room_type = result

                # Send confirmation email
                try:
                    send_confirmation_email(
                        email, first_name, last_name, booking_number,
                        check_in, check_out, final_price, num_guests, phone, room_type
                    )
                    email_status = "✅ Confirmation email sent"
                except Exception as e:
                    email_status = f"⚠️ Booking confirmed but email failed: {e}"

                st.success("🎉 Booking Successfully Confirmed!")
                st.balloons()

                # Display booking confirmation
                st.markdown(f"""
                ### 📋 Booking Confirmation

                **Booking Number:** `{booking_number}`  
                **Guest:** {first_name} {last_name}  
                **Email:** {email}  
                **Phone:** {phone}  
                **Room:** {room_type} (ID: {room_info['room_id']})  
                **Check-in:** {check_in.strftime('%A, %B %d, %Y')}  
                **Check-out:** {check_out.strftime('%A, %B %d, %Y')}  
                **Duration:** {nights} nights  
                **Guests:** {num_guests}  
                **Total Price:** €{final_price}  

                {email_status}

                ---
                *Thank you for choosing Chez Govinda!*
                """)

                # Clear booking mode
                if 'booking_mode' in st.session_state:
                    st.session_state.booking_mode = False

            else:
                st.error(f"❌ Booking Failed: {result}")


# Export functions
__all__ = ["render_booking_form"]