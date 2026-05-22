import resend
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
resend.api_key = settings.resend_api_key


def _send(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success, False on failure."""
    try:
        result = resend.Emails.send({
            "from": settings.resend_from_email,
            "to": to,
            "subject": subject,
            "html": html,
        })
        logger.info("Email sent to %s | id=%s", to, result.get("id") if isinstance(result, dict) else result)
        return True
    except Exception as e:
        err = str(e)
        if "verify a domain" in err or "testing emails" in err:
            logger.warning(
                "Resend domain not verified — email to %s skipped. "
                "Add and verify your domain at https://resend.com/domains "
                "then update RESEND_FROM_EMAIL in .env. Error: %s",
                to, err,
            )
        else:
            logger.error("Failed to send email to %s: %s", to, err)
        return False


def send_verification_email(email: str, token: str) -> bool:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#fff;border:1px solid #e5e5e5;border-radius:8px">
      <h2 style="color:#111;margin-bottom:8px">Welcome to {settings.app_name}!</h2>
      <p style="color:#555;margin-bottom:24px">Please verify your email address to activate your account.</p>
      <a href="{link}"
         style="display:inline-block;background:#111;color:#fff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600">
        Verify Email
      </a>
      <p style="color:#999;font-size:12px;margin-top:24px">This link expires in 24 hours. If you didn't create an account, ignore this email.</p>
    </div>
    """
    return _send(email, f"Verify your email — {settings.app_name}", html)


def send_password_reset_email(email: str, otp: str) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#fff;border:1px solid #e5e5e5;border-radius:8px">
      <h2 style="color:#111;margin-bottom:8px">Password Reset</h2>
      <p style="color:#555;margin-bottom:16px">Use the code below to reset your password. It expires in 1 hour.</p>
      <div style="background:#f5f5f5;border-radius:6px;padding:20px;text-align:center;font-size:32px;font-weight:700;letter-spacing:8px;color:#111">
        {otp}
      </div>
      <p style="color:#999;font-size:12px;margin-top:24px">If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    return _send(email, f"Password reset code — {settings.app_name}", html)
