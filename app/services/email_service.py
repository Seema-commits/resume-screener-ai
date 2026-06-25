import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SENDER_EMAIL = "YOUR_GMAIL@gmail.com"
SENDER_PASSWORD = "YOUR_APP_PASSWORD"


def send_interview_email(
    candidate_email,
    candidate_name
):

    subject = "Interview Invitation"

    body = f"""
    Dear {candidate_name},

    Congratulations!

    You have been shortlisted for the next round.

    Our team will contact you shortly
    with interview details.

    Regards,
    SmartRecruit AI
    """

    msg = MIMEMultipart()

    msg["From"] = SENDER_EMAIL
    msg["To"] = candidate_email
    msg["Subject"] = subject

    msg.attach(
        MIMEText(body, "plain")
    )

    server = smtplib.SMTP(
        "smtp.gmail.com",
        587
    )

    server.starttls()

    server.login(
        SENDER_EMAIL,
        SENDER_PASSWORD
    )

    server.send_message(msg)

    server.quit()