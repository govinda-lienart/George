# calendar.py - Interactive calendar restored and properly fixed

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


def render_working_interactive_calendar(selected_room_id, unavailable_dates):
    """
    Interactive calendar that actually works - no problematic key parameter
    """

    # Create calendar HTML without the problematic key parameter
    calendar_html = f"""
    <div style="border: 1px solid #ddd; border-radius: 10px; overflow: hidden; margin: 20px 0; font-family: Arial, sans-serif;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; text-align: center;">
            <h3 style="margin: 0;">🗓️ Interactive Calendar</h3>
            <p style="margin: 5px 0 0; opacity: 0.9;">Click available dates to select your stay</p>
        </div>

        <!-- Room info -->
        <div style="padding: 15px; background: #f8f9fa; border-bottom: 1px solid #e9ecef;">
            <strong>Room {selected_room_id} Availability</strong> - 
            <span style="color: {'#dc3545' if unavailable_dates else '#28a745'};">
                {len(unavailable_dates) if unavailable_dates else 0} unavailable dates
            </span>
        </div>

        <!-- Calendar Grid -->
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1px; background: #e9ecef;">
            <!-- May 2025 -->
            <div style="background: white;">
                <div style="background: #6c757d; color: white; padding: 10px; text-align: center; font-weight: bold;">
                    May 2025
                </div>
                <div style="display: grid; grid-template-columns: repeat(7, 1fr); background: #f8f9fa;">
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Sun</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Mon</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Tue</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Wed</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Thu</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Fri</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Sat</div>
                </div>
                <div id="may-days" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; background: #e9ecef;">
                </div>
            </div>

            <!-- June 2025 -->
            <div style="background: white;">
                <div style="background: #6c757d; color: white; padding: 10px; text-align: center; font-weight: bold;">
                    June 2025
                </div>
                <div style="display: grid; grid-template-columns: repeat(7, 1fr); background: #f8f9fa;">
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Sun</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Mon</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Tue</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Wed</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Thu</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Fri</div>
                    <div style="padding: 8px; text-align: center; font-size: 12px; font-weight: bold;">Sat</div>
                </div>
                <div id="june-days" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; background: #e9ecef;">
                </div>
            </div>
        </div>

        <!-- Legend -->
        <div style="padding: 15px; background: #f8f9fa; display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 16px; height: 16px; background: #dc3545; border-radius: 50%;"></div>
                <span style="font-size: 14px;">Unavailable</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 16px; height: 16px; background: #28a745; border-radius: 50%;"></div>
                <span style="font-size: 14px;">Available</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 16px; height: 16px; background: #ffc107; border-radius: 50%;"></div>
                <span style="font-size: 14px;">Selected</span>
            </div>
        </div>

        <!-- Selection display -->
        <div id="selection-display-{selected_room_id}" style="padding: 15px; background: #e3f2fd; text-align: center; font-weight: 500; color: #1565c0;">
            Click on available dates to select your check-in and check-out
        </div>
    </div>

    <script>
        // Calendar data and state for room {selected_room_id}
        const unavailableDates_{selected_room_id} = {json.dumps(unavailable_dates)};
        let checkinDate_{selected_room_id} = null;
        let checkoutDate_{selected_room_id} = null;

        // Create calendars for room {selected_room_id}
        function createCalendar_{selected_room_id}(year, month, containerId) {{
            const container = document.getElementById(containerId);
            if (!container) return;

            container.innerHTML = '';

            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const startDate = new Date(firstDay);
            startDate.setDate(startDate.getDate() - firstDay.getDay());

            for (let i = 0; i < 42; i++) {{
                const date = new Date(startDate);
                date.setDate(startDate.getDate() + i);

                const dayElement = document.createElement('div');
                dayElement.style.cssText = `
                    padding: 10px;
                    text-align: center;
                    cursor: pointer;
                    background: white;
                    transition: all 0.2s;
                    border: 1px solid #e9ecef;
                    min-height: 35px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 500;
                `;

                dayElement.textContent = date.getDate();

                const dateString = date.toISOString().split('T')[0];
                const isCurrentMonth = date.getMonth() === month;
                const isPast = date < new Date().setHours(0, 0, 0, 0);
                const isUnavailable = unavailableDates_{selected_room_id}.includes(dateString);

                if (!isCurrentMonth) {{
                    dayElement.style.color = '#ccc';
                    dayElement.style.background = '#f8f8f8';
                }} else if (isPast || isUnavailable) {{
                    dayElement.style.background = '#dc3545';
                    dayElement.style.color = 'white';
                    dayElement.style.cursor = 'not-allowed';
                    if (isUnavailable) {{
                        dayElement.title = 'This date is not available';
                    }}
                }} else {{
                    dayElement.addEventListener('click', () => selectDate_{selected_room_id}(date));
                    dayElement.addEventListener('mouseenter', () => {{
                        if (dayElement.style.background !== '#ffc107') {{
                            dayElement.style.background = '#e3f2fd';
                        }}
                    }});
                    dayElement.addEventListener('mouseleave', () => {{
                        if (dayElement.style.background === 'rgb(227, 242, 253)') {{
                            dayElement.style.background = 'white';
                        }}
                    }});
                }}

                // Highlight selected dates
                if (checkinDate_{selected_room_id} && date.toDateString() === checkinDate_{selected_room_id}.toDateString()) {{
                    dayElement.style.background = '#ffc107';
                    dayElement.style.color = '#212529';
                }}
                if (checkoutDate_{selected_room_id} && date.toDateString() === checkoutDate_{selected_room_id}.toDateString()) {{
                    dayElement.style.background = '#ffc107';
                    dayElement.style.color = '#212529';
                }}

                container.appendChild(dayElement);
            }}
        }}

        function selectDate_{selected_room_id}(date) {{
            if (!checkinDate_{selected_room_id} || (checkinDate_{selected_room_id} && checkoutDate_{selected_room_id})) {{
                checkinDate_{selected_room_id} = new Date(date);
                checkoutDate_{selected_room_id} = null;
            }} else if (date > checkinDate_{selected_room_id}) {{
                checkoutDate_{selected_room_id} = new Date(date);
            }} else {{
                checkinDate_{selected_room_id} = new Date(date);
                checkoutDate_{selected_room_id} = null;
            }}

            updateCalendars_{selected_room_id}();
            updateSelectionDisplay_{selected_room_id}();
        }}

        function updateCalendars_{selected_room_id}() {{
            createCalendar_{selected_room_id}(2025, 4, 'may-days');    // May 2025
            createCalendar_{selected_room_id}(2025, 5, 'june-days');   // June 2025
        }}

        function updateSelectionDisplay_{selected_room_id}() {{
            const display = document.getElementById('selection-display-{selected_room_id}');
            if (!display) return;

            if (checkinDate_{selected_room_id} && checkoutDate_{selected_room_id}) {{
                const nights = Math.ceil((checkoutDate_{selected_room_id} - checkinDate_{selected_room_id}) / (1000 * 60 * 60 * 24));
                display.innerHTML = `
                    <strong>✅ Selected:</strong> ${{checkinDate_{selected_room_id}.toLocaleDateString()}} to ${{checkoutDate_{selected_room_id}.toLocaleDateString()}} 
                    (${{nights}} night${{nights !== 1 ? 's' : ''}})
                `;
                display.style.background = '#d4edda';
                display.style.color = '#155724';
            }} else if (checkinDate_{selected_room_id}) {{
                display.innerHTML = `<strong>Check-in:</strong> ${{checkinDate_{selected_room_id}.toLocaleDateString()}} - Now select check-out date`;
                display.style.background = '#fff3cd';
                display.style.color = '#856404';
            }} else {{
                display.innerHTML = 'Click on available dates to select your check-in and check-out';
                display.style.background = '#e3f2fd';
                display.style.color = '#1565c0';
            }}
        }}

        // Initialize calendars for room {selected_room_id}
        updateCalendars_{selected_room_id}();
    </script>
    """

    # Use basic st.components.v1.html without the key parameter
    return st.components.v1.html(calendar_html, height=600)


def render_booking_form():
    """Main booking form with restored interactive calendar"""
    rooms = get_rooms()
    if not rooms:
        st.warning("No rooms available or failed to load room list.")
        return

    st.markdown("## 🏨 Hotel Booking")

    # Room selection with session state
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

    # Render the working interactive calendar
    st.markdown("### 🗓️ Interactive Room Calendar")
    render_working_interactive_calendar(selected_room['room_id'], unavailable_dates)

    # Show text summary too
    if unavailable_dates:
        with st.expander("📋 View unavailable dates list"):
            # Group consecutive dates
            date_ranges = []
            if unavailable_dates:
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

            for date_range in date_ranges:
                if len(date_range) == 1:
                    st.write(f"• {date_range[0]}")
                else:
                    st.write(f"• {date_range[0]} to {date_range[-1]} ({len(date_range)} days)")
    else:
        st.success("✅ This room is fully available!")

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