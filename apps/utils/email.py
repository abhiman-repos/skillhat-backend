import resend
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Set API key once at module level
resend.api_key = settings.RESEND_API_KEY

def send_otp_email(to_email: str, otp: str, expiry_minutes: int = 5):
    if not resend.api_key:
        logger.error("RESEND_API_KEY is not set in settings")
        raise ValueError("Resend API key is missing. Check your .env file.")

    params = {
        "from": "onboarding@resend.dev",   # Change to your verified domain
        "to": [to_email],
        "subject": "🔐 Your Admin Login OTP",
        "html": f"""
        <div style="font-family: system-ui, sans-serif; max-width: 500px; margin: 40px auto; padding: 30px; border: 1px solid #e5e7eb; border-radius: 12px;">
            <h2 style="color: #1e40af;">Your One-Time Password</h2>
            <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #111827; margin: 20px 0;">
                {otp}
            </p>
            <p>This code is valid for <strong>{expiry_minutes} minutes</strong>.</p>
            <p style="color: #6b7280; font-size: 14px;">If you did not request this OTP, please ignore this email.</p>
        </div>
        """
    }

    try:
        response = resend.Emails.send(params)
        logger.info(f"OTP email sent successfully to {to_email}. Response: {response}")
        return True
    except Exception as e:
        logger.error(f"Resend error while sending to {to_email}: {str(e)}")
        raise