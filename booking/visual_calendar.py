# visual_calendar.py - Updated with better synchronization and error handling

import streamlit as st
import json


def render_visual_calendar(rooms, all_availability, selected_room_id=None):
    """
    Renders the interactive visual calendar component.

    Args:
        rooms: List of room dictionaries from database
        all_availability: Dict of {room_id: [unavailable_dates]}
        selected_room_id: Currently selected room ID (optional)
    """

    if not rooms:
        st.error("No rooms available to display calendar.")
        return

    st.markdown("### 🗓️ Interactive Booking Calendar")
    st.markdown("**Red dates** = Unavailable (bookings + manual blocks) | **Green dates** = Your selection")

    # Create room data for JavaScript with error handling
    room_js_data = {}
    for room in rooms:
        room_id = str(room['room_id'])
        unavailable_dates = all_availability.get(room_id, [])

        # Ensure unavailable_dates is always a list
        if not isinstance(unavailable_dates, list):
            unavailable_dates = []

        room_js_data[room_id] = {
            'name': room.get('room_type', 'Unknown Room'),
            'price': room.get('price', 0),
            'capacity': room.get('guest_capacity', 1),
            'description': room.get('description', ''),
            'unavailable_dates': unavailable_dates
        }

    # Set default selected room
    if selected_room_id is None:
        selected_room_id = rooms[0]['room_id']

    # Create unique key for this calendar instance
    calendar_key = f"calendar_{selected_room_id}_{len(all_availability)}"

    # Enhanced visual calendar HTML with better error handling
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
            .error-message {{
                padding: 15px 20px;
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
                border-radius: 5px;
                margin: 20px;
            }}
        </style>

        <div class="calendar-widget">
            <div class="calendar-header">
                <h3>🏨 Visual Calendar</h3>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Synchronized with room selection</p>
            </div>

            <div class="sync-notice">
                🔄 This calendar shows availability for the currently selected room. 
                Change the room selection in the booking form to update this calendar.
            </div>

            <div id="roomInfo" class="room-info">Loading room information...</div>

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
        // Initialize with error handling
        let roomData;
        let selectedRoom = '{selected_room_id}';
        let checkinDate = null;
        let checkoutDate = null;
        let currentMonth = new Date(2025, 4, 1); // May 2025

        try {{
            roomData = {json.dumps(room_js_data)};

            // Verify data loaded correctly
            if (!roomData || Object.keys(roomData).length === 0) {{
                throw new Error('No room data available');
            }}

            // Verify selected room exists
            if (!roomData[selectedRoom]) {{
                selectedRoom = Object.keys(roomData)[0];
                console.warn('Selected room not found, using first available room:', selectedRoom);
            }}

        }} catch (error) {{
            console.error('Error loading room data:', error);
            document.getElementById('roomInfo').innerHTML = '<div class="error-message">Error loading room data. Please refresh the page.</div>';
        }}

        // Function to update calendar for specific room (called externally)
        function updateCalendarForRoom(newRoomId) {{
            try {{
                if (roomData && roomData[newRoomId.toString()]) {{
                    selectedRoom = newRoomId.toString();
                    checkinDate = null;
                    checkoutDate = null;
                    updateRoomInfo();
                    renderCalendars();
                    updateStatusMessage();
                }} else {{
                    console.error('Room not found:', newRoomId);
                }}
            }} catch (error) {{
                console.error('Error updating calendar:', error);
            }}
        }}

        function updateRoomInfo() {{
            try {{
                const room = roomData[selectedRoom];
                if (!room) {{
                    document.getElementById('roomInfo').innerHTML = '<div class="error-message">Room information not available</div>';
                    return;
                }}

                const unavailableCount = room.unavailable_dates ? room.unavailable_dates.length : 0;
                document.getElementById('roomInfo').innerHTML = `
                    <strong>${{room.name || 'Unknown Room'}}</strong> - €${{room.price || 0}}/night - Max ${{room.capacity || 1}} guests<br>
                    ${{room.description || 'No description available'}}<br>
                    <span style="color: ${{unavailableCount > 0 ? '#dc3545' : '#28a745'}};">
                        ${{unavailableCount}} unavailable dates shown in red
                    </span>
                `;
            }} catch (error) {{
                console.error('Error updating room info:', error);
                document.getElementById('roomInfo').innerHTML = '<div class="error-message">Error displaying room information</div>';
            }}
        }}

        function changeMonth(direction) {{
            try {{
                currentMonth.setMonth(currentMonth.getMonth() + direction);
                renderCalendars();
            }} catch (error) {{
                console.error('Error changing month:', error);
            }}
        }}

        function renderCalendars() {{
            try {{
                const month1 = new Date(currentMonth);
                const month2 = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);

                document.getElementById('month1Header').textContent = month1.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});
                document.getElementById('month2Header').textContent = month2.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});

                renderMonth(month1, 'month1Days');
                renderMonth(month2, 'month2Days');
            }} catch (error) {{
                console.error('Error rendering calendars:', error);
            }}
        }}

        function renderMonth(monthDate, containerId) {{
            try {{
                const container = document.getElementById(containerId);
                if (!container) return;

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

                    // Safely check for unavailable dates
                    const room = roomData[selectedRoom];
                    const unavailableDates = room && room.unavailable_dates ? room.unavailable_dates : [];
                    const isUnavailable = unavailableDates.includes(dateString);

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
            }} catch (error) {{
                console.error('Error rendering month:', error);
            }}
        }}

        function selectDate(date) {{
            try {{
                if (!checkinDate || (checkinDate && checkoutDate)) {{
                    checkinDate = new Date(date);
                    checkoutDate = null;
                }} else if (date > checkinDate) {{
                    checkoutDate = new Date(date);
                }} else {{
                    checkinDate = new Date(date);
                    checkoutDate = null;
                }}

                renderCalendars();
                updateStatusMessage();
            }} catch (error) {{
                console.error('Error selecting date:', error);
            }}
        }}

        function updateStatusMessage() {{
            try {{
                const msgEl = document.getElementById('statusMessage');
                if (!msgEl) return;

                const room = roomData[selectedRoom];
                if (!room) {{
                    msgEl.innerHTML = 'Room data not available';
                    return;
                }}

                if (checkinDate && checkoutDate) {{
                    const nights = Math.ceil((checkoutDate - checkinDate) / (1000 * 60 * 60 * 24));
                    const totalPrice = nights * (room.price || 0);
                    msgEl.className = 'status-message status-selected';
                    msgEl.innerHTML = `
                        <strong>✅ Suggested Dates:</strong> ${{checkinDate.toLocaleDateString()}} to ${{checkoutDate.toLocaleDateString()}} 
                        (${{nights}} nights) - <strong>Estimated: €${{totalPrice}}</strong><br>
                        <small>Use the booking form below to complete your reservation</small>
                    `;
                }} else if (checkinDate) {{
                    msgEl.className = 'status-message status-selecting';
                    msgEl.innerHTML = `<strong>Check-in:</strong> ${{checkinDate.toLocaleDateString()}} - Click your check-out date`;
                }} else {{
                    msgEl.className = 'status-message status-default';
                    msgEl.innerHTML = 'Click on available dates to help select your booking period';
                }}
            }} catch (error) {{
                console.error('Error updating status message:', error);
            }}
        }}

        // Initialize everything
        if (roomData && Object.keys(roomData).length > 0) {{
            updateRoomInfo();
            renderCalendars();
        }}

        // Make function available globally for external calls
        window.updateCalendarForRoom = updateCalendarForRoom;

    </script>
    """

    return st.components.v1.html(calendar_html, height=700, key=calendar_key)


def get_selected_dates_from_calendar():
    """
    Helper function to get selected dates from the visual calendar.
    Note: This would need bidirectional communication in a production environment.
    """
    return None, None