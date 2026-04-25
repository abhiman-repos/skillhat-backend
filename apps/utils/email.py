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
        "subject": "🔐 Your Admin Login OTP - Secure Verification",
        "html": f"""
        <div style="font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    max-width: 520px; 
                    margin: 40px auto; 
                    padding: 40px 30px; 
                    border: 1px solid #e5e7eb; 
                    border-radius: 16px;
                    background-color: #ffffff;">
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1e3a8a; margin: 0; font-size: 24px; font-weight: 600;">
                    Admin Login Verification
                </h1>
            </div>

            <!-- OTP Section -->
            <div style="background-color: #f8fafc; 
                        padding: 24px; 
                        border-radius: 12px; 
                        text-align: center; 
                        border: 2px solid #e0e7ff; 
                        margin-bottom: 24px;">
                
                <p style="color: #374151; font-size: 15px; margin: 0 0 12px 0;">
                    Your One-Time Password (OTP) is:
                </p>
                
                <p style="font-size: 36px; 
                        font-weight: 700; 
                        letter-spacing: 12px; 
                        color: #1e40af; 
                        margin: 16px 0 20px 0; 
                        font-family: monospace;">
                    {otp}
                </p>
                
                <p style="color: #64748b; font-size: 14px; margin: 0;">
                    This code is valid for <strong>{expiry_minutes} minutes</strong>
                </p>
            </div>

            <!-- Instructions -->
            <p style="color: #374151; line-height: 1.6; font-size: 15px;">
                Please enter this OTP to complete your admin login. 
                For security reasons, do not share this code with anyone.
            </p>

            <!-- Warning / Security Notice -->
            <div style="background-color: #fef3c7; 
                        border-left: 4px solid #f59e0b; 
                        padding: 16px; 
                        margin: 24px 0; 
                        border-radius: 6px;">
                <p style="color: #92400e; font-size: 14px; margin: 0; line-height: 1.5;">
                    <strong>⚠️ Security Warning:</strong><br>
                    This OTP is for your use only. If you did not request this code, 
                    please ignore this email and contact your administrator immediately.
                </p>
            </div>

            <!-- Footer -->
            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 13px; text-align: center;">
                <p style="margin: 0;">
                    This is an automated security email from your Admin Portal.<br>
                    If you have any concerns, please reach out to your system administrator.
                </p>
            </div>
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