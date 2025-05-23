# calendar.py - Unified calendar booking system

import streamlit as st
import mysql.connector
from datetime import datetime, timedelta
from booking.email import send_confirmation_email
from dotenv import load_dotenv
import os
import json

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
            pass

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


def check_date_conflicts(room_id, check_in_str, check_out_str):
    """Check for booking conflicts using date strings"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

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
        has_conflict, conflict_details = check_date_conflicts(
            data['room_id'], data['check_in'], data['check_out']
        )

        if has_conflict:
            return False, f"Booking conflicts: {'; '.join(conflict_details)}"

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        check_in_date = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(data['check_out'], '%Y-%m-%d').date()

        insert_query = """
            INSERT INTO bookings 
            (first_name, last_name, email, phone, room_id, check_in, check_out, num_guests, total_price, special_requests)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data['first_name'], data['last_name'], data['email'], data['phone'],
            data['room_id'], check_in_date, check_out_date,
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


def render_unified_calendar_booking(selected_room_id, selected_room, unavailable_dates):
    """
    Unified calendar that shows selection and allows booking in one interface
    """

    calendar_html = f"""
    <div style="border: 1px solid #ddd; border-radius: 15px; overflow: hidden; margin: 20px 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 25px; text-align: center;">
            <h3 style="margin: 0; font-size: 1.6em;">🗓️ Select Your Dates & Book</h3>
            <p style="margin: 8px 0 0; opacity: 0.9; font-size: 1.1em;">Click available dates, then complete booking below</p>
        </div>

        <div style="padding: 18px; background: #f8f9fa; border-bottom: 1px solid #e9ecef;">
            <strong style="font-size: 1.1em;">Room {selected_room_id}: {selected_room['room_type']}</strong> - 
            <span style="color: #667eea; font-weight: 600;">€{selected_room['price']}/night</span> - 
            <span style="color: {'#dc3545' if unavailable_dates else '#28a745'}; font-weight: 600;">
                {len(unavailable_dates) if unavailable_dates else 0} unavailable dates
            </span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px; background: #e9ecef;">
            <div style="background: white;">
                <div style="background: #495057; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.1em;">
                    May 2025
                </div>
                <div style="display: grid; grid-template-columns: repeat(7, 1fr); background: #f8f9fa;">
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Sun</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Mon</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Tue</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Wed</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Thu</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Fri</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Sat</div>
                </div>
                <div id="may-days" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; background: #e9ecef;"></div>
            </div>

            <div style="background: white;">
                <div style="background: #495057; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.1em;">
                    June 2025
                </div>
                <div style="display: grid; grid-template-columns: repeat(7, 1fr); background: #f8f9fa;">
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Sun</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Mon</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Tue</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Wed</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Thu</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Fri</div>
                    <div style="padding: 10px; text-align: center; font-size: 13px; font-weight: bold; color: #6c757d;">Sat</div>
                </div>
                <div id="june-days" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; background: #e9ecef;"></div>
            </div>
        </div>

        <div style="padding: 20px; background: #f8f9fa; display: flex; gap: 25px; justify-content: center; flex-wrap: wrap; border-top: 1px solid #e9ecef;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 18px; height: 18px; background: #dc3545; border-radius: 50%;"></div>
                <span style="font-size: 14px; font-weight: 500;">Unavailable</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 18px; height: 18px; background: #28a745; border-radius: 50%;"></div>
                <span style="font-size: 14px; font-weight: 500;">Available</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 18px; height: 18px; background: #ff8c00; border-radius: 50%;"></div>
                <span style="font-size: 14px; font-weight: 500;">Selected</span>
            </div>
        </div>

        <div id="selection-display" style="padding: 20px; background: #e3f2fd; text-align: center; font-weight: 500; color: #1565c0; border-top: 1px solid #e9ecef;">
            Click on available (green) dates to select your check-in and check-out
        </div>
    </div>

    <script>
        const unavailableDates = {json.dumps(unavailable_dates)};
        const roomPrice = {selected_room['price']};
        let checkinDate = null;
        let checkoutDate = null;

        function createCalendar(year, month, containerId) {{
            const container = document.getElementById(containerId);
            if (!container) return;

            container.innerHTML = '';

            const firstDay = new Date(year, month, 1);
            const startDate = new Date(firstDay);
            startDate.setDate(startDate.getDate() - firstDay.getDay());

            for (let i = 0; i < 42; i++) {{
                const date = new Date(startDate);
                date.setDate(startDate.getDate() + i);

                const dayElement = document.createElement('div');
                dayElement.style.cssText = `
                    padding: 12px; text-align: center; cursor: pointer; background: white;
                    transition: all 0.3s ease; border: 1px solid #e9ecef; min-height: 40px;
                    display: flex; align-items: center; justify-content: center; font-weight: 500; font-size: 14px;
                `;

                dayElement.textContent = date.getDate();

                const dateString = date.toISOString().split('T')[0];
                const isCurrentMonth = date.getMonth() === month;
                const isPast = date < new Date().setHours(0, 0, 0, 0);
                const isUnavailable = unavailableDates.includes(dateString);

                if (!isCurrentMonth) {{
                    dayElement.style.color = '#ccc';
                    dayElement.style.background = '#f8f8f8';
                    dayElement.style.cursor = 'default';
                }} else if (isPast || isUnavailable) {{
                    dayElement.style.background = '#dc3545';
                    dayElement.style.color = 'white';
                    dayElement.style.cursor = 'not-allowed';
                    dayElement.style.fontWeight = '600';
                }} else {{
                    dayElement.style.background = '#28a745';
                    dayElement.style.color = 'white';
                    dayElement.style.fontWeight = '600';
                    dayElement.addEventListener('click', () => selectDate(date));
                    dayElement.addEventListener('mouseenter', () => {{
                        if (!dayElement.classList.contains('selected')) {{
                            dayElement.style.background = '#218838';
                            dayElement.style.transform = 'scale(1.05)';
                        }}
                    }});
                    dayElement.addEventListener('mouseleave', () => {{
                        if (!dayElement.classList.contains('selected')) {{
                            dayElement.style.background = '#28a745';
                            dayElement.style.transform = 'scale(1)';
                        }}
                    }});
                }}

                if (checkinDate && date.toDateString() === checkinDate.toDateString()) {{
                    dayElement.style.background = '#ff8c00';
                    dayElement.style.color = 'white';
                    dayElement.style.fontWeight = '700';
                    dayElement.style.transform = 'scale(1.1)';
                    dayElement.classList.add('selected');
                }}
                if (checkoutDate && date.toDateString() === checkoutDate.toDateString()) {{
                    dayElement.style.background = '#ff8c00';
                    dayElement.style.color = 'white';
                    dayElement.style.fontWeight = '700';
                    dayElement.style.transform = 'scale(1.1)';
                    dayElement.classList.add('selected');
                }}

                if (checkinDate && checkoutDate && 
                    date > checkinDate && date < checkoutDate &&
                    isCurrentMonth && !isPast && !isUnavailable) {{
                    dayElement.style.background = '#ffd700';
                    dayElement.style.color = '#333';
                    dayElement.style.fontWeight = '600';
                }}

                container.appendChild(dayElement);
            }}
        }}

        function selectDate(date) {{
            if (!checkinDate || (checkinDate && checkoutDate)) {{
                checkinDate = new Date(date);
                checkoutDate = null;
            }} else if (date > checkinDate) {{
                checkoutDate = new Date(date);
            }} else {{
                checkinDate = new Date(date);
                checkoutDate = null;
            }}

            updateCalendars();
            updateSelectionDisplay();
        }}

        function updateCalendars() {{
            createCalendar(2025, 4, 'may-days');
            createCalendar(2025, 5, 'june-days');
        }}

        function updateSelectionDisplay() {{
            const display = document.getElementById('selection-display');
            if (!display) return;

            if (checkinDate && checkoutDate) {{
                const nights = Math.ceil((checkoutDate - checkinDate) / (1000 * 60 * 60 * 24));
                const totalPrice = nights * roomPrice;
                display.innerHTML = `
                    <strong>✅ SELECTED:</strong> ${{checkinDate.toLocaleDateString()}} to ${{checkoutDate.toLocaleDateString()}} 
                    (${{nights}} night${{nights !== 1 ? 's' : ''}}) - <strong>Total: €${{totalPrice}}</strong><br>
                    <small style="margin-top: 8px; display: block; color: #155724;">Ready to book! Complete the form below.</small>
                `;
                display.style.background = '#d4edda';
                display.style.color = '#155724';

                // Store selected dates globally for the form
                window.selectedBookingDates = {{
                    checkin: checkinDate.toISOString().split('T')[0],
                    checkout: checkoutDate.toISOString().split('T')[0],
                    nights: nights,
                    total: totalPrice
                }};

            }} else if (checkinDate) {{
                display.innerHTML = `<strong>Check-in:</strong> ${{checkinDate.toLocaleDateString()}} - Now select check-out date (orange)`;
                display.style.background = '#fff3cd';
                display.style.color = '#856404';
                window.selectedBookingDates = null;
            }} else {{
                display.innerHTML = 'Click on available (green) dates to select your check-in and check-out';
                display.style.background = '#e3f2fd';
                display.style.color = '#1565c0';
                window.selectedBookingDates = null;
            }}
        }}

        updateCalendars();
    </script>
    """

    return st.components.v1.html(calendar_html, height=650)


def render_booking_form():
    """Simplified booking form with unified calendar"""
    rooms = get_rooms()
    if not rooms:
        st.warning("No rooms available or failed to load room list.")
        return

    st.markdown("## 🏨 Hotel Booking")

    # Room selection
    if 'selected_room_idx' not in st.session_state:
        st.session_state.selected_room_idx = 0

    room_options = []
    for room in rooms:
        room_options.append(f"{room['room_type']} - €{room['price']}/night (Max {room['guest_capacity']} guests)")

    selected_room_idx = st.selectbox(
        "🏠 **Select Your Room:**",
        range(len(room_options)),
        format_func=lambda x: room_options[x],
        index=st.session_state.selected_room_idx
    )

    st.session_state.selected_room_idx = selected_room_idx
    selected_room = rooms[selected_room_idx]

    # Get availability
    with st.spinner("Loading availability..."):
        unavailable_dates = get_room_availability(selected_room['room_id'])

    # Render unified calendar
    render_unified_calendar_booking(
        selected_room['room_id'],
        selected_room,
        unavailable_dates
    )

    # Country codes
    country_codes = [
        "+32 Belgium", "+1 USA/Canada", "+44 UK", "+33 France", "+49 Germany", "+84 Vietnam",
        "+91 India", "+81 Japan", "+61 Australia", "+34 Spain", "+39 Italy", "+86 China", "+7 Russia"
    ]

    # Simplified booking form
    st.markdown("### 📝 Complete Your Booking")
    st.info(
        "💡 **Step 1:** Select dates in calendar above  •  **Step 2:** Fill details below  •  **Step 3:** Click book!")

    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name *")
            last_name = st.text_input("Last Name *")
        with col2:
            email = st.text_input("Email Address *")
            country_code = st.selectbox("Country Code", country_codes, index=0)

        phone_number = st.text_input("Phone Number (without country code)")
        phone = f"{country_code.split()[0]} {phone_number}" if phone_number else ""

        col3, col4 = st.columns(2)
        with col3:
            num_guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=1)
        with col4:
            st.write("**Selected Room:**")
            st.info(f"{selected_room['room_type']} - €{selected_room['price']}/night")

        special_requests = st.text_area("Special Requests", placeholder="Any special requirements...")

        # Validation
        capacity_error = None
        if num_guests > selected_room["guest_capacity"]:
            capacity_error = f"This room accommodates maximum {selected_room['guest_capacity']} guests."
            st.error(f"❌ {capacity_error}")

        # Submit button
        submitted = st.form_submit_button("🏨 Complete Booking")

        if submitted:
            if not first_name or not last_name or not email:
                st.warning("⚠️ Please fill in all required fields marked with *")
                return

            if capacity_error:
                st.error("❌ Please fix the guest capacity issue above.")
                return

            # Check if dates were selected (we'll use a simple date range for now)
            # In a real implementation, we'd need to get these from the JavaScript
            st.warning("🗓️ **Calendar selection detected!** Please confirm your dates:")

            # For demo purposes, let's use default dates
            # In production, you'd capture these from the calendar
            col_confirm1, col_confirm2 = st.columns(2)
            with col_confirm1:
                confirm_checkin = st.date_input("Confirm Check-in", datetime.today())
            with col_confirm2:
                confirm_checkout = st.date_input("Confirm Check-out", datetime.today() + timedelta(days=1))

            if st.button("🎯 Confirm These Dates & Book Now"):
                # Validate dates
                if confirm_checkin >= confirm_checkout:
                    st.error("Check-out must be after check-in")
                    return

                if confirm_checkin.strftime('%Y-%m-%d') in unavailable_dates:
                    st.error("Check-in date is not available")
                    return

                # Process booking
                nights = (confirm_checkout - confirm_checkin).days
                total_price = selected_room['price'] * nights

                booking_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "room_id": selected_room["room_id"],
                    "room_type": selected_room["room_type"],
                    "check_in": confirm_checkin.strftime('%Y-%m-%d'),
                    "check_out": confirm_checkout.strftime('%Y-%m-%d'),
                    "num_guests": num_guests,
                    "total_price": total_price,
                    "special_requests": special_requests
                }

                with st.spinner("Processing your booking..."):
                    success, result = insert_booking(booking_data)

                if success:
                    booking_number, final_price, room_type = result

                    try:
                        send_confirmation_email(
                            email, first_name, last_name, booking_number,
                            confirm_checkin, confirm_checkout, final_price, num_guests, phone, room_type
                        )
                        email_status = "✅ Confirmation email sent"
                    except Exception as e:
                        email_status = f"⚠️ Booking confirmed but email failed: {e}"

                    st.success("🎉 Booking Successfully Confirmed!")
                    st.balloons()

                    st.markdown(f"""
                    ### 📋 Booking Confirmation

                    **Booking Number:** `{booking_number}`  
                    **Guest:** {first_name} {last_name}  
                    **Email:** {email}  
                    **Room:** {room_type} (ID: {selected_room['room_id']})  
                    **Check-in:** {confirm_checkin.strftime('%A, %B %d, %Y')}  
                    **Check-out:** {confirm_checkout.strftime('%A, %B %d, %Y')}  
                    **Duration:** {nights} nights  
                    **Guests:** {num_guests}  
                    **Total Price:** €{final_price}  

                    {email_status}

                    ---
                    *Thank you for choosing Chez Govinda!*
                    """)

                    if 'booking_mode' in st.session_state:
                        st.session_state.booking_mode = False
                else:
                    st.error(f"❌ Booking Failed: {result}")


# Export functions
__all__ = ["render_booking_form"]