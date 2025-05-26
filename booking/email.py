# ========================================
# 📋 ROLE OF THIS SCRIPT - email.py
# ========================================

"""
Email confirmation module for the George AI Hotel Receptionist app.
- Sends automated booking confirmation emails to guests
- Handles SMTP server configuration and authentication
- Formats professional email templates with booking details
- Provides comprehensive error logging for email delivery issues
- Integrates with the booking system for seamless notifications
"""

# Last updated: 2025-05-19 18:26:37

# ========================================
# 📦 IMPORTS & CONFIGURATION
# ========================================

# ────────────────────────────────────────────────
# 📚 STANDARD LIBRARY IMPORTS
# ────────────────────────────────────────────────
import os  # Operating system interfaces, environment variables
import smtplib  # SMTP protocol client for sending emails
from email.message import EmailMessage  # Email message composition and formatting

# ────────────────────────────────────────────────
# 🔧 THIRD-PARTY LIBRARY IMPORTS
# ────────────────────────────────────────────────
from dotenv import load_dotenv  # Load environment variables from .env file

# ┌─────────────────────────────────────────┐
# │  ENVIRONMENT VARIABLES LOADING          │
# └─────────────────────────────────────────┘
load_dotenv()

# ========================================
# 🔐 LOGGING SYSTEM INTEGRATION
# ========================================

# ────────────────────────────────────────────────
# 🪵 LOGGER INITIALIZATION
# ────────────────────────────────────────────────
from logger import logger  # Custom logging system for email operations


# ========================================
# 📧 EMAIL DELIVERY SYSTEM
# ========================================

# ────────────────────────────────────────────────
# 📨 BOOKING CONFIRMATION EMAIL SENDER
# ────────────────────────────────────────────────
def send_confirmation_email(to_email, first_name, last_name, booking_number, check_in, check_out, total_price,
                            num_guests, phone, room_type):
    """
    Send a professionally formatted booking confirmation email to the guest.

    Parameters:
    - to_email: Recipient's email address
    - first_name, last_name: Guest's name information
    - booking_number: Unique booking reference number
    - check_in, check_out: Stay dates
    - total_price: Total booking cost
    - num_guests: Number of guests in the booking
    - phone: Guest's contact phone number
    - room_type: Type/category of booked room

    Handles SMTP authentication, email formatting, and comprehensive error logging.
    """
    # ┌─────────────────────────────────────────┐
    # │  EMAIL MESSAGE COMPOSITION              │
    # └─────────────────────────────────────────┘
    msg = EmailMessage()
    msg["Subject"] = f"Booking Confirmation – {booking_number}"
    msg["From"] = os.getenv("smtp_user")
    msg["To"] = to_email

    # ┌─────────────────────────────────────────┐
    # │  EMAIL BODY TEMPLATE FORMATTING         │
    # └─────────────────────────────────────────┘
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

    # ┌─────────────────────────────────────────┐
    # │  SMTP SERVER CONFIGURATION & DELIVERY   │
    # └─────────────────────────────────────────┘
    try:
        # ┌─────────────────────────────────────────┐
        # │  SMTP CREDENTIALS RETRIEVAL             │
        # └─────────────────────────────────────────┘
        smtp_server = os.getenv("smtp_host")
        smtp_port = int(os.getenv("smtp_port", 587))
        smtp_user = os.getenv("smtp_user")
        smtp_password = os.getenv("smtp_password")

        # ┌─────────────────────────────────────────┐
        # │  SECURE SMTP CONNECTION & DELIVERY      │
        # └─────────────────────────────────────────┘
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Enable TLS encryption
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

            # ┌─────────────────────────────────────────┐
            # │  SUCCESS LOGGING & CONFIRMATION         │
            # └─────────────────────────────────────────┘
            logger.info(f"✅ Email sent to {to_email} for booking #{booking_number}")
            print("Email sent successfully.")

    except Exception as e:
        # ┌─────────────────────────────────────────┐
        # │  ERROR HANDLING & LOGGING               │
        # └─────────────────────────────────────────┘
        logger.error(f"❌ Failed to send email to {to_email}: {e}", exc_info=True)
        print(f"Failed to send email: {e}")