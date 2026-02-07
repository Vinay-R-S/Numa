# Fitness API Integration - Setup Guide

Professional Python API clients for Strava and Google Fit.

## Prerequisites

- Python 3.7 or higher
- pip package manager

## Installation

Install required dependencies:

```bash
pip install requests google-api-python-client google-auth-oauthlib google-auth-httplib2
```

## Project Structure

```
server/
├── .env                      # Environment variables (you'll create this)
└── src/
    ├── config/
    │   ├── credentials.json  # Google Fit OAuth credentials (you'll add this)
    │   └── token.json        # Auto-generated on first run
    └── api/
        ├── strava_api.py
        ├── google_fit_api.py
        └── usage_examples.py
```

## Configuration

### 1. Strava API Setup

#### Step 1: Create a Strava Application

1. Go to [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
2. Click "Create App" or use an existing application
3. Fill in the required details:
   - **Application Name**: Choose any name
   - **Category**: Select appropriate category
   - **Website**: Use `http://localhost` if you don't have one
   - **Authorization Callback Domain**: Enter `localhost`
4. After creation, note down:
   - **Client ID**
   - **Client Secret**

#### Step 2: Get Authorization Code

1. Replace `YOUR_CLIENT_ID` in the URL below and visit it in your browser:

   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
   ```

2. Click "Authorize" to grant permissions

3. You'll be redirected to a URL like:

   ```
   http://localhost/?code=XXXXXXXXXXXXXXXXXXXXXXXX
   ```

4. Copy the code after `?code=` (this is your **Authorization Code**)

#### Step 3: Exchange Authorization Code for Refresh Token

Run this curl command in your terminal (replace the placeholders):

```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=YOUR_AUTHORIZATION_CODE \
  -d grant_type=authorization_code
```

The response will look like:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": ...
}
```

5. Copy the **refresh_token** value (you'll need this for the .env file)

#### Step 4: Add Strava Credentials to .env

Open or create `server/.env` and add these lines:

```env
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_REFRESH_TOKEN=your_refresh_token_here
```

### 2. Google Fit API Setup

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top, then "New Project"
3. Enter a project name (e.g., "Numa Fitness Tracker")
4. Click "Create"
5. Wait for the project to be created and select it

#### Step 2: Enable Google Fit API

1. In the left sidebar, go to **APIs & Services** > **Library**
2. Search for "Fitness API"
3. Click on "Fitness API"
4. Click the **Enable** button

#### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** user type (unless you have a Google Workspace)
3. Click **Create**
4. Fill in the required fields:
   - **App name**: Your app name (e.g., "Numa Fitness")
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click **Save and Continue**
6. On the "Scopes" page, click **Save and Continue** (no changes needed)
7. On the "Test users" page, click **Add Users** and add your Google account email
8. Click **Save and Continue**

#### Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. For "Application type", select **Desktop app**
4. Enter a name (e.g., "Desktop Client")
5. Click **Create**
6. A dialog will appear with your credentials
7. Click **Download JSON**
8. Save the downloaded file

#### Step 5: Add Google Fit Credentials to Config

1. Rename the downloaded JSON file to `credentials.json`
2. Move it to `server/src/config/credentials.json`
3. Open or create `server/.env` and add:

```env
GOOGLE_FIT_CREDENTIALS_FILE=credentials.json
```

#### Step 6: First-Time Authorization

The first time you run the Google Fit API:

1. A browser window will automatically open
2. Sign in with your Google account
3. Click "Allow" to grant permissions
4. The browser will show "The authentication flow has completed"
5. A `token.json` file will be automatically created in `server/src/config/`

Future runs will use the saved token automatically.

## Environment Variables Summary

Your `server/.env` file should contain:

```env
# Strava Configuration
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_REFRESH_TOKEN=your_strava_refresh_token

# Google Fit Configuration
GOOGLE_FIT_CREDENTIALS_FILE=credentials.json
```

## File Checklist

Before running the application, ensure you have:

- [ ] `server/.env` file with Strava credentials
- [ ] `server/.env` file with Google Fit configuration
- [ ] `server/src/config/credentials.json` (Google Fit OAuth credentials)
- [ ] All required Python packages installed

## Security Notes

**Important**: Never commit sensitive files to version control!

Add these to your `.gitignore`:

```
.env
server/src/config/credentials.json
server/src/config/token.json
```

## Troubleshooting

### Strava Issues

**"Token refresh failed"**

- Verify your `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, and `STRAVA_REFRESH_TOKEN` in `.env`
- Ensure there are no extra spaces or quotes around the values
- Check that you haven't revoked access in your Strava account settings

**"No activities returned"**

- Make sure you have activities recorded in Strava
- Verify the authorization scope includes `activity:read_all`

### Google Fit Issues

**"credentials.json not found"**

- Ensure the file is located at `server/src/config/credentials.json`
- Check that the filename is exactly `credentials.json` (case-sensitive)

**"Browser doesn't open for authorization"**

- Look for an authorization URL in the console output
- Copy and paste it into your browser manually
- Complete the authorization flow

**"No data returned"**

- Ensure Google Fit app is installed on your phone
- Check that fitness tracking is enabled
- Verify you granted all permissions during OAuth flow
- Make sure you have activity data in the requested time range

## Support Resources

- [Strava API Documentation](https://developers.strava.com/docs/reference/)
- [Google Fit API Documentation](https://developers.google.com/fit/rest)
- Usage examples: See `server/src/api/usage_examples.py`
