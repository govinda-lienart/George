# Last updated: 2025-05-19 18:26:37
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

load_dotenv()

# ========================================
# 🔐 logger
# ========================================
from logger import logger


def send_confirmation_email(to_email, first_name, last_name, booking_number, check_in, check_out, total_price, num_guests, phone, room_type):
    msg = EmailMessage()
    msg["Subject"] = f"Booking Confirmation – {booking_number}"
    msg["From"] = os.getenv("smtp_user")
    msg["To"] = to_email

    body = f"""
Dear {first_name} {last_name},

Thank you for booking with Chez Govinda!

📅 Booking Number: {booking_number}
🛏️ Room Type: {room_type}
👥 Guests: {num_guests}
📆 Check-in: {check_in}
📆 Check-out: {check_out}
💶 Total Price: €{total_price}
📞 Phone: {phone}

We look forward to hosting you!

Sincerely,  
Chez Govinda
"""
    msg.set_content(body)

    try:
        smtp_server = os.getenv("smtp_host")
        smtp_port = int(os.getenv("smtp_port", 587))
        smtp_user = os.getenv("smtp_user")
        smtp_password = os.getenv("smtp_password")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

            logger.info(f"✅ Email sent to {to_email} for booking #{booking_number}")
            print("Email sent successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}", exc_info=True)
        print(f"Failed to send email: {e}")
