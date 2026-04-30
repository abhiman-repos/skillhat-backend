import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_otp_email(to_email: str, otp: str, expiry_minutes: int = 5):
    try:
        url = "https://api.brevo.com/v3/smtp/email"

        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json"
        }

        html_content = f"""
        <h2>Your OTP is {otp}</h2>
        <p>This OTP is valid for {expiry_minutes} minutes</p>
        """

        data = {
            "sender": {
                "name": "SkillHat",
                "email": "no-reply@skillhat.in"
            },
            "to": [{"email": to_email}],
            "subject": "🔐 Your Admin Login OTP",
            "htmlContent": html_content
        }

        response = requests.post(url, json=data, headers=headers, timeout=10)

        if response.status_code not in [200, 201]:
            logger.error(f"Brevo API failed: {response.text}")
            raise Exception("Email sending failed")

        logger.info(f"OTP email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        raise