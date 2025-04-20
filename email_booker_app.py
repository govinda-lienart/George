# email_booker_app.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os
import traceback

# Yahoo SMTP Configuration
smtp_host = "smtp.mail.yahoo.com"
smtp_port = 587
smtp_user = "hugovindas@yahoo.com"
smtp_password = "jgrymnaehfewtybg"  # Yahoo App Password

def send_confirmation_email(to_email, first_name, last_name, booking_number, check_in, check_out, total_price, num_guests, phone, room_type, testing=False):
    if testing:
        to_email = "gdh.lienart@gmail.com"

    subject = "Your Booking Confirmation"
    body = f"""
    <html>
      <body>
        <p>Hello {first_name} {last_name},</p>

        <p>Thank you for booking your stay at <strong>Chez Govinda</strong>!</p>

        <p><strong>Booking Details:</strong></p>
        <p><strong>Booking Number:</strong> {booking_number}</p>
        <p><strong>Room Type:</strong> {room_type}</p>
        <p><strong>Guests:</strong> {num_guests}</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Total Price:</strong> €{total_price}</p>
        <p><strong>Check-in:</strong> {check_in}<br>
           <strong>Check-out:</strong> {check_out}</p>

        <p>If you have any questions or need to make changes, feel free to reply to this email.</p>

        <p>Warm wishes from all of us at Chez Govinda 🌿</p>
      </body>
    </html>
    """

    # Compose email
    msg = MIMEMultipart()
    msg['From'] = f"Chez Govinda <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.set_debuglevel(1)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        traceback.print_exc()

# --- MOCK TEST FUNCTION ---
def test_email():
    print("\n--- Running Mock Email Test ---")
    send_confirmation_email(
        to_email="ignored@domain.com",
        first_name="Test",
        last_name="User",
        booking_number="BKG-20250420-9999",
        check_in=datetime.today().date(),
        check_out=(datetime.today().date().replace(day=datetime.today().day + 1)),
        total_price=120,
        num_guests=2,
        phone="+32499123456",
        room_type="Single",
        testing=True
    )

if __name__ == "__main__":
    test_email()