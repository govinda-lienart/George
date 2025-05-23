# calendar.py - Fully synchronized booking system

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


def get_all_rooms_availability():
    """Get availability for all rooms efficiently"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT room_id FROM rooms ORDER BY room_id")
        room_ids = [row[0] for row in cursor.fetchall()]

        availability_data = {}
        for room_id in room_ids:
            availability_data[str(room_id)] = get_room_availability(room_id)

        return availability_data

    except Exception as e:
        st.error(f"Error getting all rooms availability: {e}")
        return {}
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

        # Check manual availability blocks
        availability_conflict_query = """
            SELECT date FROM room_availability
            WHERE room_id = %s AND is_available = 0 
            AND date >= %s AND date < %s
        """
        cursor.execute(availability_conflict_query, (room_id, check_in, check_out))
        availability_conflicts = cursor.fetchall()

        conflicts = []

        if booking_conflicts:
            for booking in booking_conflicts:
                conflicts.append(f"Booking conflict: {booking[0]} ({booking[1]} to {booking[2]})")

        if availability_conflicts:
            blocked_dates = [str(date[0]) for date in availability_conflicts]
            conflicts.append(f"Manually blocked dates: {', '.join(blocked_dates)}")

        return len(conflicts) > 0, conflicts

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


def render_synchronized_visual_calendar(rooms, all_availability, selected_room_key):
    """
    Renders synchronized visual calendar that updates based on form selections
    """

    # Create room data for JavaScript
    room_js_data = {}
    for room in rooms:
        room_id = str(room['room_id'])
        room_js_data[room_id] = {
            'name': room['room_type'],
            'price': room['price'],
            'capacity': room['guest_capacity'],
            'description': room.get('description', ''),
            'unavailable_dates': all_availability.get(room_id, [])
        }

    # Get currently selected room from session state
    if selected_room_key in st.session_state:
        current_room_id = st.session_state[selected_room_key]
    else:
        current_room_id = rooms[0]['room_id']

    # Enhanced visual calendar HTML with synchronization
    calendar_html = f"""
    <div id="booking-calendar" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <style>
            .calendar-widget {{ 
                max-width: 100%; 
                background: white; 
                border-radius: 12px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.08); 
                overflow: hidden; 
                margin: 20px 0;
                border: 1px solid #e1e5e9;
            }}
            .calendar-header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 25px; 
                text-align: center; 
            }}
            .calendar-header h3 {{ 
                margin: 0; 
                font-size: 1.5em; 
                font-weight: 600; 
            }}
            .sync-notice {{
                padding: 15px 20px;
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                margin: 0;
                color: #1565c0;
                font-weight: 500;
            }}
            .calendar-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                gap: 25px; 
                padding: 25px; 
            }}
            .month-calendar {{ 
                border: 1px solid #e9ecef; 
                border-radius: 10px; 
                overflow: hidden; 
                background: white;
            }}
            .month-header {{ 
                background: #667eea; 
                color: white; 
                padding: 16px; 
                text-align: center; 
                font-weight: 600; 
                font-size: 1.1em;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .nav-btn {{ 
                background: rgba(255,255,255,0.2); 
                border: none; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 6px; 
                cursor: pointer; 
                font-size: 16px;
                transition: background 0.3s;
            }}
            .nav-btn:hover {{ 
                background: rgba(255,255,255,0.3); 
            }}
            .weekdays {{ 
                display: grid; 
                grid-template-columns: repeat(7, 1fr); 
                background: #f8f9fa; 
            }}
            .weekday {{ 
                padding: 12px 8px; 
                text-align: center; 
                font-weight: 600; 
                color: #6c757d; 
                font-size: 0.85em;
                text-transform: uppercase;
            }}
            .days-grid {{ 
                display: grid; 
                grid-template-columns: repeat(7, 1fr); 
                gap: 1px; 
                background: #e9ecef; 
            }}
            .day {{ 
                aspect-ratio: 1; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                background: white; 
                cursor: pointer; 
                transition: all 0.2s ease; 
                font-weight: 500;
                position: relative;
                font-size: 14px;
            }}
            .day:hover {{ 
                background: #e3f2fd; 
                transform: scale(1.05);
                z-index: 2;
            }}
            .day.other-month {{ 
                color: #adb5bd; 
                background: #f8f9fa; 
            }}
            .day.unavailable {{ 
                background: #dc3545 !important; 
                color: white !important; 
                cursor: not-allowed; 
                font-weight: 600;
            }}
            .day.unavailable:hover {{ 
                transform: none; 
                background: #c82333 !important;
            }}
            .day.unavailable::after {{ 
                content: '✕'; 
                position: absolute; 
                top: 2px; 
                right: 4px; 
                font-size: 10px; 
                opacity: 0.9;
            }}
            .day.selected-checkin {{ 
                background: #28a745 !important; 
                color: white !important; 
                font-weight: 700;
                border-radius: 50% 0 0 50%;
            }}
            .day.selected-checkout {{ 
                background: #007bff !important; 
                color: white !important; 
                font-weight: 700;
                border-radius: 0 50% 50% 0;
            }}
            .day.in-range {{ 
                background: #cce5ff !important; 
                color: #0056b3;
                font-weight: 600;
            }}
            .legend {{ 
                padding: 20px; 
                background: #f8f9fa; 
                border-top: 1px solid #e9ecef;
                display: flex; 
                gap: 25px; 
                flex-wrap: wrap; 
                justify-content: center;
            }}
            .legend-item {{ 
                display: flex; 
                align-items: center; 
                gap: 8px; 
                font-size: 14px;
                font-weight: 500;
            }}
            .legend-color {{ 
                width: 18px; 
                height: 18px; 
                border-radius: 50%; 
                border: 2px solid rgba(0,0,0,0.1);
            }}
            .status-message {{ 
                padding: 16px 20px; 
                margin: 0 20px 20px 20px; 
                border-radius: 8px; 
                text-align: center; 
                font-weight: 500;
                transition: all 0.3s;
            }}
            .status-default {{ 
                background: #e7f3ff; 
                color: #0056b3; 
                border: 1px solid #bee5eb;
            }}
            .status-selecting {{ 
                background: #fff3cd; 
                color: #856404; 
                border: 1px solid #ffeaa7;
            }}
            .status-selected {{ 
                background: #d4edda; 
                color: #155724; 
                border: 1px solid #c3e6cb;
            }}
            .room-info {{ 
                padding: 15px 20px; 
                background: white; 
                border-top: 1px solid #e9ecef;
                font-size: 14px;
                color: #6c757d;
            }}
        </style>

        <div class="calendar-widget">
            <div class="calendar-header">
                <h3>🏨 Visual Calendar</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Synchronized with booking form below</p>
            </div>

            <div class="sync-notice">
                🔄 This calendar automatically updates when you change the room selection in the booking form below.
                Click dates here to help select your booking period.
            </div>

            <div id="roomInfo" class="room-info"></div>

            <div id="statusMessage" class="status-message status-default">
                Click on available dates to help select your booking period
            </div>

            <div class="calendar-grid">
                <div class="month-calendar">
                    <div class="month-header">
                        <button class="nav-btn" onclick="changeMonth(-1)">‹</button>
                        <span id="month1Header">May 2025</span>
                        <button class="nav-btn" onclick="changeMonth(1)">›</button>
                    </div>
                    <div class="weekdays">
                        <div class="weekday">Sun</div><div class="weekday">Mon</div><div class="weekday">Tue</div>
                        <div class="weekday">Wed</div><div class="weekday">Thu</div><div class="weekday">Fri</div><div class="weekday">Sat</div>
                    </div>
                    <div class="days-grid" id="month1Days"></div>
                </div>

                <div class="month-calendar">
                    <div class="month-header">
                        <button class="nav-btn" onclick="changeMonth(-1)">‹</button>
                        <span id="month2Header">June 2025</span>
                        <button class="nav-btn" onclick="changeMonth(1)">›</button>
                    </div>
                    <div class="weekdays">
                        <div class="weekday">Sun</div><div class="weekday">Mon</div><div class="weekday">Tue</div>
                        <div class="weekday">Wed</div><div class="weekday">Thu</div><div class="weekday">Fri</div><div class="weekday">Sat</div>
                    </div>
                    <div class="days-grid" id="month2Days"></div>
                </div>
            </div>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #dc3545;"></div>
                    <span>Unavailable</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #28a745;"></div>
                    <span>Check-in</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #007bff;"></div>
                    <span>Check-out</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #cce5ff; border-color: #007bff;"></div>
                    <span>Selected Range</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const roomData = {json.dumps(room_js_data)};
        let selectedRoom = '{current_room_id}';
        let checkinDate = null;
        let checkoutDate = null;
        let currentMonth = new Date(2025, 4, 1); // May 2025

        // Function to update calendar when room changes (called from Streamlit)
        function updateCalendarForRoom(newRoomId) {{
            selectedRoom = newRoomId.toString();
            checkinDate = null;
            checkoutDate = null;
            updateRoomInfo();
            renderCalendars();
            updateStatusMessage();
        }}

        function updateRoomInfo() {{
            const room = roomData[selectedRoom];
            if (!room) return;

            const unavailableCount = room.unavailable_dates.length;
            document.getElementById('roomInfo').innerHTML = `
                <strong>${{room.name}}</strong> - €${{room.price}}/night - Max ${{room.capacity}} guests<br>
                ${{room.description || 'No description available'}}<br>
                <span style="color: ${{unavailableCount > 0 ? '#dc3545' : '#28a745'}};">
                    ${{unavailableCount}} unavailable dates shown in red
                </span>
            `;
        }}

        function changeMonth(direction) {{
            currentMonth.setMonth(currentMonth.getMonth() + direction);
            renderCalendars();
        }}

        function renderCalendars() {{
            const month1 = new Date(currentMonth);
            const month2 = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);

            document.getElementById('month1Header').textContent = month1.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});
            document.getElementById('month2Header').textContent = month2.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});

            renderMonth(month1, 'month1Days');
            renderMonth(month2, 'month2Days');
        }}

        function renderMonth(monthDate, containerId) {{
            const container = document.getElementById(containerId);
            container.innerHTML = '';

            const year = monthDate.getFullYear();
            const month = monthDate.getMonth();
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const startDate = new Date(firstDay);
            startDate.setDate(startDate.getDate() - firstDay.getDay());

            for (let i = 0; i < 42; i++) {{
                const date = new Date(startDate);
                date.setDate(startDate.getDate() + i);

                const dayEl = document.createElement('div');
                dayEl.className = 'day';
                dayEl.textContent = date.getDate();

                const dateString = date.toISOString().split('T')[0];
                const isCurrentMonth = date.getMonth() === month;
                const isPast = date < new Date().setHours(0, 0, 0, 0);
                const room = roomData[selectedRoom];
                const isUnavailable = room && room.unavailable_dates.includes(dateString);

                if (!isCurrentMonth) {{
                    dayEl.classList.add('other-month');
                }} else if (isPast || isUnavailable) {{
                    dayEl.classList.add('unavailable');
                }} else {{
                    dayEl.addEventListener('click', () => selectDate(date));
                }}

                // Highlight selected dates
                if (checkinDate && date.toDateString() === checkinDate.toDateString()) {{
                    dayEl.classList.add('selected-checkin');
                }}
                if (checkoutDate && date.toDateString() === checkoutDate.toDateString()) {{
                    dayEl.classList.add('selected-checkout');
                }}
                if (checkinDate && checkoutDate && date > checkinDate && date < checkoutDate) {{
                    dayEl.classList.add('in-range');
                }}

                container.appendChild(dayEl);
            }}
        }}

        function selectDate(date) {{
            if (!checkinDate || (checkinDate && checkoutDate)) {{
                // Start new selection
                checkinDate = new Date(date);
                checkoutDate = null;
            }} else if (date > checkinDate) {{
                // Valid checkout date
                checkoutDate = new Date(date);
            }} else {{
                // Date is before checkin, restart
                checkinDate = new Date(date);
                checkoutDate = null;
            }}

            renderCalendars();
            updateStatusMessage();
        }}

        function updateStatusMessage() {{
            const msgEl = document.getElementById('statusMessage');
            const room = roomData[selectedRoom];

            if (!room) {{
                msgEl.innerHTML = 'Room data loading...';
                return;
            }}

            if (checkinDate && checkoutDate) {{
                const nights = Math.ceil((checkoutDate - checkinDate) / (1000 * 60 * 60 * 24));
                const totalPrice = nights * room.price;
                msgEl.className = 'status-message status-selected';
                msgEl.innerHTML = `
                    <strong>✅ Suggested Dates:</strong> ${{checkinDate.toLocaleDateString()}} to ${{checkoutDate.toLocaleDateString()}} 
                    (${{nights}} nights) - <strong>Estimated: €${{totalPrice}}</strong><br>
                    <small>Use the form below to complete your booking with these dates</small>
                `;
            }} else if (checkinDate) {{
                msgEl.className = 'status-message status-selecting';
                msgEl.innerHTML = `<strong>Check-in:</strong> ${{checkinDate.toLocaleDateString()}} - Click your check-out date`;
            }} else {{
                msgEl.className = 'status-message status-default';
                msgEl.innerHTML = 'Click on available dates to help select your booking period';
            }}
        }}

        // Initialize
        updateRoomInfo();
        renderCalendars();

        // Make function available globally for Streamlit to call
        window.updateCalendarForRoom = updateCalendarForRoom;
    </script>
    """

    return st.components.v1.html(calendar_html, height=700)


def render_booking_form():
    """Main booking form with synchronized visual calendar"""
    rooms = get_rooms()
    if not rooms:
        st.warning("No rooms available or failed to load room list.")
        return

    # Initialize session state for selected room
    if 'selected_room_index' not in st.session_state:
        st.session_state.selected_room_index = 0

    # Create room mapping
    room_names = [
        f"{room['room_type']} (id: {room['room_id']}) - €{room['price']}/night - Max {room['guest_capacity']} guests"
        for room in rooms]
    room_mapping = {
        f"{room['room_type']} (id: {room['room_id']}) - €{room['price']}/night - Max {room['guest_capacity']} guests": {
            "id": room["room_id"],
            "type": room["room_type"],
            "price": room["price"],
            "capacity": room["guest_capacity"],
            "description": room.get("description", "")
        } for room in rooms
    }

    # Country codes
    country_codes = [
        "+32 Belgium", "+1 USA/Canada", "+44 UK", "+33 France", "+49 Germany", "+84 Vietnam",
        "+91 India", "+81 Japan", "+61 Australia", "+34 Spain", "+39 Italy", "+86 China", "+7 Russia"
    ]

    # Visual calendar option
    use_visual_calendar = st.checkbox("🗓️ Use Interactive Visual Calendar", value=True)

    if use_visual_calendar:
        with st.spinner("Loading room availability..."):
            all_availability = get_all_rooms_availability()

        # Render the synchronized visual calendar
        render_synchronized_visual_calendar(rooms, all_availability, 'selected_room_index')

    # Main booking form
    with st.form("booking_form"):
        st.markdown("### 📝 Complete Your Booking")

        # Personal Information
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name *", help="Required field")
            last_name = st.text_input("Last Name *", help="Required field")
        with col2:
            email = st.text_input("Email Address *", help="Required field")
            country_code = st.selectbox("Country Code", country_codes, index=0)

        phone_number = st.text_input("Phone Number (without country code)", help="Optional but recommended")
        phone = f"{country_code.split()[0]} {phone_number}" if phone_number else ""

        # Booking Details with synchronized room selection
        col3, col4 = st.columns(2)
        with col3:
            num_guests = st.number_input("Number of Guests", min_value=1, max_value=10, value=1)
        with col4:
            # Room selector that triggers calendar update
            selected_room = st.selectbox(
                "Room Selection",
                room_names,
                key="room_selectbox",
                help="Calendar above will update automatically"
            )

            # Update selected room in session state and trigger calendar update
            current_room_info = room_mapping[selected_room]
            current_room_id = current_room_info["id"]

            # JavaScript to update calendar when room changes
            if use_visual_calendar:
                st.markdown(f"""
                <script>
                if (window.updateCalendarForRoom) {{
                    window.updateCalendarForRoom({current_room_id});
                }}
                </script>
                """, unsafe_allow_html=True)

        # Date inputs
        col5, col6 = st.columns(2)
        with col5:
            check_in = st.date_input(
                "Check-in Date",
                min_value=datetime.today(),
                help="Select here or use visual calendar above"
            )
        with col6:
            check_out = st.date_input(
                "Check-out Date",
                min_value=datetime.today() + timedelta(days=1),
                help="Select here or use visual calendar above"
            )

        # Validation
        room_info = current_room_info

        # Guest capacity validation
        capacity_error = None
        if num_guests > room_info["capacity"]:
            capacity_error = f"This room accommodates maximum {room_info['capacity']} guests. You selected {num_guests} guests."

        # Date validation
        date_validation_error = None
        conflict_details = []

        if check_in and check_out:
            if check_in >= check_out:
                date_validation_error = "Check-out date must be after check-in date."
            else:
                has_conflicts, conflicts = check_date_conflicts(room_info["id"], check_in, check_out)
                if has_conflicts:
                    date_validation_error = "Date conflicts detected"
                    conflict_details = conflicts

        # Display validation messages
        if capacity_error:
            st.error(f"❌ {capacity_error}")

        if date_validation_error:
            st.error(f"❌ {date_validation_error}")
            if conflict_details:
                for conflict in conflict_details:
                    st.warning(f"⚠️ {conflict}")

        # Show room availability info
        if not date_validation_error and not capacity_error:
            unavailable_dates = get_room_availability(room_info["id"])
            if unavailable_dates:
                with st.expander(f"📅 Room {room_info['id']} Availability Details"):
                    st.write(f"**Unavailable dates:** {len(unavailable_dates)} days")
                    if len(unavailable_dates) <= 10:
                        st.write(", ".join(unavailable_dates))
                    else:
                        st.write(", ".join(unavailable_dates[:10]) + f"... and {len(unavailable_dates) - 10} more")
            else:
                st.success("✅ This room is fully available for your selected dates!")

        special_requests = st.text_area("Special Requests",
                                        placeholder="Any special requirements, dietary restrictions, early check-in requests, etc.")

        # Calculate pricing
        if check_in and check_out and not date_validation_error:
            nights = (check_out - check_in).days
            total_price = room_info["price"] * nights

            st.info(f"""
            **Booking Summary:**
            - **Room:** {room_info['type']} (€{room_info['price']}/night)
            - **Dates:** {check_in.strftime('%B %d, %Y')} to {check_out.strftime('%B %d, %Y')}
            - **Duration:** {nights} nights
            - **Guests:** {num_guests}
            - **Total Price:** €{total_price}
            """)

        # Submit button
        all_errors = [e for e in [capacity_error, date_validation_error] if e]
        submitted = st.form_submit_button(
            "🏨 Confirm Booking",
            disabled=bool(all_errors),
            help="Complete your booking" if not all_errors else "Please fix the errors above"
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
                "room_id": room_info["id"],
                "room_type": room_info["type"],
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
                **Guest Name:** {first_name} {last_name}  
                **Email:** {email}  
                **Phone:** {phone}  
                **Room:** {room_type} (ID: {room_info['id']})  
                **Check-in:** {check_in.strftime('%A, %B %d, %Y')}  
                **Check-out:** {check_out.strftime('%A, %B %d, %Y')}  
                **Duration:** {nights} nights  
                **Guests:** {num_guests}  
                **Total Price:** €{final_price}  
                **Special Requests:** {special_requests or 'None'}  

                {email_status}

                ---
                *Thank you for choosing Chez Govinda! We look forward to hosting you.*
                """)

                # Clear booking mode
                if 'booking_mode' in st.session_state:
                    st.session_state.booking_mode = False

            else:
                st.error(f"❌ Booking Failed: {result}")
                st.markdown("Please try different dates or contact us for assistance.")


# Export functions
__all__ = ["render_booking_form"]