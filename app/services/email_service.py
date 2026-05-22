import resend
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
resend.api_key = settings.resend_api_key


def send_verification_email(email: str, token: str) -> None:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    html = f"""
    <h2>Welcome to {settings.app_name}!</h2>
    <p>Please verify your email by clicking the link below:</p>
    <p><a href="{link}">Verify Email</a></p>
    <p>This link expires in 24 hours.</p>
    """
    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": email,
            "subject": f"Verify your email - {settings.app_name}",
            "html": html,
        })
        logger.info("Verification email sent to %s", email)
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s", email, e)


def send_password_reset_email(email: str, otp: str) -> None:
    html = f"""
    <h2>Password Reset Request</h2>
    <p>Your password reset code is:</p>
    <h3>{otp}</h3>
    <p>This code expires in 1 hour.</p>
    <p>If you did not request this, please ignore this email.</p>
    """
    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": email,
            "subject": f"Password reset code - {settings.app_name}",
            "html": html,
        })
        logger.info("Password reset email sent to %s", email)
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", email, e)
