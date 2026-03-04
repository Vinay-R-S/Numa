import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)

def send_email(summary_text: str) -> bool:
    """
    Sends an email notification with the given summary text.
    
    Args:
        summary_text: The body of the email.
        
    Returns:
        True if sent successfully, False otherwise.
    """
    if not settings.EMAIL_ENABLED:
        logger.info("Email notifications are disabled.")
        return False

    sender_email = settings.EMAIL_SENDER
    sender_password = settings.EMAIL_PASSWORD
    recipient_email = settings.EMAIL_RECIPIENT
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT

    if not all([sender_email, sender_password, recipient_email]):
        logger.error("Email configuration is incomplete. Skipping email.")
        return False

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = "[NUMA Slack Monitor] Important Activity Detected"
    
    # Add body to email
    message.attach(MIMEText(summary_text, "plain"))

    try:
        # Create secure connection with server and send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls() # Secure the connection
        server.login(sender_email, sender_password)
        text = message.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        logger.info(f"Email notification sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
