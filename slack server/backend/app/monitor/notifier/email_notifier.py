"""
Email notifier — sends summary emails via SMTP.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(summary_text: str) -> bool:
    """Send a summary email. Returns True on success."""
    if not settings.EMAIL_ENABLED:
        return False

    if not all([settings.EMAIL_SENDER, settings.EMAIL_PASSWORD, settings.EMAIL_RECIPIENT]):
        logger.error("Incomplete email configuration — skipping.")
        return False

    msg = MIMEMultipart()
    msg["From"]    = settings.EMAIL_SENDER
    msg["To"]      = settings.EMAIL_RECIPIENT
    msg["Subject"] = "[NUMA] Slack Activity Summary"
    msg.attach(MIMEText(summary_text, "plain"))

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_SENDER, settings.EMAIL_RECIPIENT, msg.as_string())
        logger.info("Email summary sent to %s", settings.EMAIL_RECIPIENT)
        return True
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return False
