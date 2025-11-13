# backend/utils/email.py
import os
import logging
import hashlib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Content, HtmlContent, PlainTextContent, Email

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")  # e.g. medguardian1@gmail.com (verified)
SENDGRID_SANDBOX = os.getenv("SENDGRID_SANDBOX", "false").lower() in ("1", "true", "yes")

def send_verification_email(to_email: str, code: str, expires_minutes: int = 10) -> bool:
    """
    Send a simple verification email via SendGrid.
    Returns True if send was accepted (202 or 200 depending) - logs and returns False on failure.
    """
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        logger.error("SendGrid not configured (missing API key or sender email).")
        return False

    subject = "Verify your Med Guardian email"
    plain_text = f"Your Med Guardian verification code is: {code}\nThis code expires in {expires_minutes} minutes."
    html = f"""
    <p>Your Med Guardian verification code is: <strong>{code}</strong></p>
    <p>This code expires in {expires_minutes} minutes.</p>
    <p>If you did not request this, ignore this email.</p>
    """

    message = Mail(
        from_email=Email(SENDGRID_FROM_EMAIL),
        to_emails=To(to_email),
        subject=subject,
        plain_text_content=PlainTextContent(plain_text),
        html_content=HtmlContent(html)
    )

    # Sandbox mode available for dev (does not deliver)
    if SENDGRID_SANDBOX:
        try:
            # set mail settings for sandbox (SendGrid uses MailSettings to set sandbox)
            message.mail_settings = {
                "sandbox_mode": {"enable": True}
            }
        except Exception:
            # older helper doesn't support mail_settings dict assignment easily; log and continue
            logger.info("SendGrid sandbox mode requested.")

    try:
        client = SendGridAPIClient(SENDGRID_API_KEY)
        resp = client.send(message)
        code_resp = resp.status_code if resp is not None else None
        logger.info("SendGrid send result: %s", code_resp)
        # SendGrid returns 202 on success, treat 200/202 as ok
        if code_resp in (200, 202):
            return True
        else:
            logger.warning("SendGrid returned non-2xx: %s %s", resp.status_code, getattr(resp, "body", ""))
            return False
    except Exception as e:
        logger.exception("Failed to send email via SendGrid: %s", e)
        return False
