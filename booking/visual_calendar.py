# visual_calendar.py - Separate visual calendar component

import streamlit as st
import json


def render_visual_calendar(rooms, all_availability):
    """
    Renders the interactive visual calendar component.

    Args:
        rooms: List of room dictionaries from database
        all_availability: Dict of {room_id: [unavailable_dates]}
    """

    st.markdown("### 🗓️ Interactive Booking Calendar")
    st.markdown("**Red dates** = Unavailable (bookings + manual blocks) | **Green dates** = Your selection")

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

    # Enhanced visual calendar HTML
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
            .room-selector {{ 
                padding: 20px; 
                background: #f8f9fa; 
                border-bottom: 1px solid #e9ecef;
            }}
            .room-selector select {{ 
                width: 100%; 
                padding: 12px 16px; 
                border: 2px solid #ced4da; 
                border-radius: 8px; 
                font-size: 16px; 
                background: white;
                transition: border-color 0.3s;
            }}
            .room-selector select:focus {{ 
                border-color: #667eea; 
                outline: none; 
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
                <h3>🏨 Select Your Booking Dates</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Choose your room and dates</p>
            </div>

            <div class="room-selector">
                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #495057;">
                    🏠 Select Room:
                </label>
                <select id="roomSelector" onchange="updateCalendar()">
                    {' '.join([f'<option value="{room["room_id"]}">{room["room_type"]} - €{room["price"]}/night (Max {room["guest_capacity"]} guests)</option>' for room in rooms])}
                </select>
            </div>

            <div id="roomInfo" class="room-info"></div>

            <div id="statusMessage" class="status-message status-default">
                Click on available dates to select your check-in and check-out dates
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
        let selectedRoom = '{rooms[0]["room_id"]}';
        let checkinDate = null;
        let checkoutDate = null;
        let currentMonth = new Date(2025, 4, 1); // May 2025

        function updateCalendar() {{
            selectedRoom = document.getElementById('roomSelector').value;
            checkinDate = null;
            checkoutDate = null;
            updateRoomInfo();
            renderCalendars();
            updateStatusMessage();
        }}

        function updateRoomInfo() {{
            const room = roomData[selectedRoom];
            const unavailableCount = room.unavailable_dates.length;
            document.getElementById('roomInfo').innerHTML = `
                <strong>${{room.name}}</strong> - €${{room.price}}/night - Max ${{room.capacity}} guests<br>
                ${{room.description || 'No description available'}}<br>
                <span style="color: ${{unavailableCount > 0 ? '#dc3545' : '#28a745'}};">
                    ${{unavailableCount}} unavailable dates in the next 6 months
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
                const isUnavailable = roomData[selectedRoom].unavailable_dates.includes(dateString);

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

            if (checkinDate && checkoutDate) {{
                const nights = Math.ceil((checkoutDate - checkinDate) / (1000 * 60 * 60 * 24));
                const totalPrice = nights * roomData[selectedRoom].price;
                msgEl.className = 'status-message status-selected';
                msgEl.innerHTML = `
                    <strong>✅ Dates Selected:</strong> ${{checkinDate.toLocaleDateString()}} to ${{checkoutDate.toLocaleDateString()}} 
                    (${{nights}} nights) - <strong>Total: €${{totalPrice}}</strong>
                `;
            }} else if (checkinDate) {{
                msgEl.className = 'status-message status-selecting';
                msgEl.innerHTML = `<strong>Check-in:</strong> ${{checkinDate.toLocaleDateString()}} - Now select your check-out date`;
            }} else {{
                msgEl.className = 'status-message status-default';
                msgEl.innerHTML = 'Click on available dates to select your check-in and check-out dates';
            }}
        }}

        // Initialize
        updateRoomInfo();
        renderCalendars();
    </script>
    """

    st.components.v1.html(calendar_html, height=700)


def get_selected_dates_from_calendar():
    """
    Helper function to get selected dates from the visual calendar.
    Note: This is a placeholder - in a real implementation, you'd need
    to use JavaScript to communicate back to Streamlit.
    """
    # In a production environment, you'd use st.components.v1.html with
    # bidirectional communication or session state to track selected dates
    return None, None