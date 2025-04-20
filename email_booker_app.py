# email_booker_app.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os

# Yahoo SMTP Configuration
smtp_host = "smtp.mail.yahoo.com"
smtp_port = 587
smtp_user = "hugovindas@yahoo.com"
smtp_password = "jgrymnaehfewtybg"  # Yahoo App Password

def send_confirmation_email(to_email, first_name, last_name, booking_number, check_in, check_out, testing=False):
    if testing:
        to_email = "gdh.lienart@gmail.com"

    subject = "📅 Your Booking Confirmation"
    body = f"""
    Hello {first_name} {last_name},

    Thank you for booking your stay with us!

    Your booking has been confirmed with the following details:

    - Booking Number: {booking_number}
    - Check-in: {check_in}
    - Check-out: {check_out}

    We're looking forward to hosting you!

    If you have any questions or need to make changes, feel free to reply to this email.

    Best regards,  
    Chez Govinda Team
    """

    # Create email
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- MOCK TEST FUNCTION ---
def test_email():
    print("\n--- Running Mock Email Test ---")
    send_confirmation_email(
        to_email="ignored@domain.com",
        first_name="Test",
        last_name="User",
        booking_number=999,
        check_in=datetime.today().date(),
        check_out=(datetime.today().date()).replace(day=datetime.today().day + 1),
        testing=True
    )

if __name__ == "__main__":
    test_email()