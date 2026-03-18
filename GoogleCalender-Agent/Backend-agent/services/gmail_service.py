"""
Gmail Service
Sends emails via Gmail API
"""

from googleapiclient.discovery import build
from services.google_auth import get_credentials
import base64
from email.mime.text import MIMEText


def get_gmail_service():
    """
    Build and return Gmail API service
    
    Returns:
        Resource: Gmail API service instance
    """
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    return service


def send_email(to: str, subject: str, body: str, sender: str = 'me'):
    """
    Send an email via Gmail
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        sender: Sender identifier (default: 'me' for authenticated user)
    
    Returns:
        dict: Sent message details including message ID
    """
    service = get_gmail_service()
    
    # Create MIME message
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    
    # Encode message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    # Send message
    sent_message = service.users().messages().send(
        userId=sender,
        body={'raw': raw_message}
    ).execute()
    
    return {
        'message_id': sent_message.get('id'),
        'thread_id': sent_message.get('threadId'),
        'to': to,
        'subject': subject
    }
