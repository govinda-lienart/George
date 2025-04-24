import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

load_dotenv()

def send_confirmation_email(to_email, first_name, last_name, booking_number, check_in, check_out, total_price, num_guests, phone, room_type):
    msg = EmailMessage()
    msg["Subject"] = f"Booking Confirmation – {booking_number}"
    msg["From"] = os.getenv("SMTP_SENDER")
    msg["To"] = to_email

    body = f"""
Dear {first_name} {last_name},

Thank you for booking with Chez Govinda!

📅 **Booking Number:** {booking_number}
🛏️ **Room Type:** {room_type}
👥 **Guests:** {num_guests}
📆 **Check-in:** {check_in}
📆 **Check-out:** {check_out}
💶 **Total Price:** €{total_price}
📞 **Phone:** {phone}

We look forward to hosting you!
Sincerely,
Chez Govinda
"""

    msg.set_content(body)

    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")