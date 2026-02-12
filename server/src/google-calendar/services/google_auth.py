"""
Google OAuth2 Authentication Service
Handles OAuth flow for Google Calendar and Gmail APIs
Uses InstalledAppFlow with gCalender_credentials.json
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]

# Credentials file from Google Cloud Console (installed app)
CREDENTIALS_FILE = 'gCalender_credentials.json'

# Token file to store and reuse OAuth tokens
TOKEN_FILE = 'token.json'


def get_credentials():
    """
    Get valid Google credentials using OAuth2 installed application flow.
    
    - Loads saved token from token.json if available
    - Refreshes expired tokens automatically
    - Runs browser-based OAuth flow for first-time auth
    - Saves token to token.json for reuse
    
    Returns:
        Credentials: Valid Google OAuth2 credentials
    """
    creds = None
    
    # Load existing token from token.json if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If no valid credentials, initiate OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired credentials
            creds.refresh(Request())
        else:
            # Start new OAuth flow using installed app credentials
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token to token.json for future use
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds
