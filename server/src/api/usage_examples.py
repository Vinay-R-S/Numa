"""
Usage Examples for Strava and Google Fit API Classes

This file demonstrates how to use the API classes with environment variables
from the .env file in the server directory.
"""

from api import StravaAPI, GoogleFitAPI
from datetime import datetime, timedelta


def example_strava_usage():
    """
    Example: Using Strava API
    
    The StravaAPI class automatically loads credentials from environment variables:
    - STRAVA_CLIENT_ID
    - STRAVA_CLIENT_SECRET
    - STRAVA_REFRESH_TOKEN
    
    These are defined in server/.env file.
    """
    # Initialize - credentials loaded automatically from .env
    strava = StravaAPI()
    
    # Calculate time range (last 7 days)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    
    # Fetch all data
    data = strava.fetch_all_data(start_time, end_time)
    
    # Access results
    if data.get('configured'):
        print(f"Total activities: {data['summary']['total_activities']}")
        print(f"Total distance: {data['summary']['total_distance_km']} km")
        print(f"Total duration: {data['summary']['total_duration_min']} min")
        print(f"Activities by type: {data['summary']['by_type']}")
    else:
        print(f"Error: {data.get('error')}")


def example_google_fit_usage():
    """
    Example: Using Google Fit API
    
    The GoogleFitAPI class automatically loads the credentials file path from:
    - GOOGLE_FIT_CREDENTIALS_FILE environment variable (defaults to 'credentials.json')
    
    The credentials file is located in server/src/config/credentials.json
    Token file is automatically saved to server/src/config/token.json
    """
    # Initialize - credentials path loaded automatically from .env
    google_fit = GoogleFitAPI()
    
    # Calculate time range (last 24 hours)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
    
    # Fetch all data
    data = google_fit.fetch_all_data(start_time, end_time)
    
    # Access results
    print(f"Steps: {data['steps']}")
    print(f"Calories: {data['calories']}")
    print(f"Active minutes: {data['active_minutes']}")
    print(f"Distance: {data['distance_km']} km")
    print(f"Sleep: {data['sleep_hours']} hours")
    print(f"Activities: {data['activities']}")


def example_manual_credentials():
    """
    Example: Manually providing credentials (overrides .env)
    
    You can still provide credentials manually if needed.
    """
    # Strava with manual credentials
    strava = StravaAPI(
        client_id="your_client_id",
        client_secret="your_client_secret",
        refresh_token="your_refresh_token"
    )
    
    # Google Fit with custom file paths
    google_fit = GoogleFitAPI(
        credentials_file="/path/to/custom/credentials.json",
        token_file="/path/to/custom/token.json"
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Strava API Example")
    print("=" * 60)
    example_strava_usage()
    
    print("\n" + "=" * 60)
    print("Google Fit API Example")
    print("=" * 60)
    example_google_fit_usage()
