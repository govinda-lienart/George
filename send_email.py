import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load environment variables (for email credentials)
load_dotenv()

# Your SMTP email server configuration
smtp_host = os.getenv("SMTP_HOST")  # Example: 'smtp.gmail.com'
smtp_port = os.getenv("SMTP_PORT")  # Example: '587'
smtp_user = os.getenv("SMTP_USER")  # Your email address
smtp_password = os.getenv("SMTP_PASSWORD")  # Your email password or app password

def send_confirmation_email(to_email, first_name, last_name, booking_number):
    # Create the email content
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

    # Set up the MIME
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_password)

        # Send the email
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()

        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email. Error: {e}")

# Example usage:
send_confirmation_email("clientemail@example.com", "Catherine", "Morel", "BKG-20250418-0011")