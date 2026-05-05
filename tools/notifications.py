import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from config import (
    EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM,
)


def _build_appointment_message(appointment: dict) -> str:
    return (
        f"Hi {appointment['customer_name']},\n\n"
        f"Your appointment has been confirmed!\n\n"
        f"  Car Model : {appointment['car_model']}\n"
        f"  Date      : {appointment['preferred_date']}\n"
        f"  Time      : {appointment['preferred_time']}\n"
        f"  Ref ID    : {appointment['id']}\n\n"
        f"Our team will be in touch shortly. We look forward to seeing you!\n\n"
        f"Kia Sales Team"
    )


def send_email(appointment: dict) -> bool:
    """Send appointment confirmation email."""
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = appointment["email"]
        msg["Subject"] = f"Appointment Confirmed - {appointment['car_model']} | {appointment['id']}"

        body = _build_appointment_message(appointment)
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, appointment["email"], msg.as_string())

        print(f"[Email] Sent to {appointment['email']}")
        return True
    except Exception as e:
        print(f"[Email] Failed: {e}")
        return False


def send_whatsapp(appointment: dict) -> bool:
    """Send appointment confirmation via WhatsApp using Twilio."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        body = _build_appointment_message(appointment)
        to_number = f"whatsapp:{appointment['phone']}"

        client.messages.create(
            body=body,
            from_=TWILIO_WHATSAPP_FROM,
            to=to_number,
        )
        print(f"[WhatsApp] Sent to {appointment['phone']}")
        return True
    except Exception as e:
        print(f"[WhatsApp] Failed: {e}")
        return False


def send_notifications(appointment: dict) -> dict:
    """
    Tool: Send confirmation via both email and WhatsApp.
    Returns status of each channel.
    """
    email_ok = send_email(appointment)
    whatsapp_ok = send_whatsapp(appointment)
    return {
        "email_sent": email_ok,
        "whatsapp_sent": whatsapp_ok,
    }
