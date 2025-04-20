import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Yahoo SMTP Configuration
smtp_host = "smtp.mail.yahoo.com"
smtp_port = 587
smtp_user = "hugovindas@yahoo.com"
smtp_password = "jgrymnaehfewtybg"  # Yahoo App Password

def send_confirmation_email(to_email, first_name, last_name, booking_number):
    subject = "📅 Your Booking Confirmation"
    body = f"""
    Hello {first_name} {last_name},

    Thank you for booking your stay with us!

    Your booking has been confirmed with the following details:

    - Booking Number: {booking_number}
    - Check-in: {datetime.today().date()}
    - Check-out: (your selected check-out date)

    We're looking forward to hosting you!

    If you have any questions or need to make changes, feel free to reply to this email.

    Best regards,  
    Your Hotel Team
    """

    # Create email
    msg = MIMEMultipart()
    from_name = "Chez Govinda"
    msg['From'] = f"{from_name} <{smtp_user}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Send it
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email. Error: {e}")

# ------------------------
# Run the test
# ------------------------

send_confirmation_email(
    to_email="gdh.lienart@gmail.com",
    first_name="Govinda",
    last_name="Lienart",
    booking_number="BKG-YAHOO-TEST"
)

