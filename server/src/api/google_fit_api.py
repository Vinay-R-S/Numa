"""
Google Fit API Client - Object-Oriented Implementation

This module provides a clean, optimized interface for interacting with the Google Fit API.
It handles OAuth 2.0 authentication and fetches various fitness data types.

Main Features:
- OAuth 2.0 authentication with token persistence
- Fetch steps, calories, active minutes, distance, and sleep data
- Fetch activity segments (walking, running, cycling, etc.)
- Normalize and aggregate fitness data

Data Types Supported:
- Steps: com.google.step_count.delta
- Calories: com.google.calories.expended
- Active Minutes: com.google.active_minutes
- Distance: com.google.distance.delta
- Sleep: com.google.sleep.segment
- Activity Segments: com.google.activity.segment

Usage:
    from google_fit_api import GoogleFitAPI
    
    google_fit = GoogleFitAPI(credentials_file='credentials.json')
    data = google_fit.fetch_all_data(start_millis, end_millis)
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleFitAPI:
    """
    Main class for interacting with the Google Fit API.
    
    Handles OAuth 2.0 authentication, data fetching, and normalization
    of various fitness data types.
    """
    
    # OAuth 2.0 scopes required for comprehensive fitness data access
    SCOPES = [
        'https://www.googleapis.com/auth/fitness.activity.read',  # Steps, calories, active minutes
        'https://www.googleapis.com/auth/fitness.sleep.read',     # Sleep data
        'https://www.googleapis.com/auth/fitness.location.read',  # Activity segments
    ]
    
    # Activity type mapping (Google Fit activity codes to readable names)
    ACTIVITY_MAP = {
        0: "in_vehicle", 1: "biking", 2: "on_foot", 3: "still", 4: "unknown",
        5: "tilting", 6: "walking", 7: "walking", 8: "running", 9: "aerobics",
        10: "badminton", 11: "baseball", 12: "basketball", 13: "biathlon",
        14: "handbiking", 15: "mountain_biking", 16: "road_biking", 17: "spinning",
        18: "stationary_biking", 19: "utility_biking", 20: "boxing", 21: "calisthenics",
        22: "circuit_training", 23: "cricket", 24: "dancing", 25: "elliptical",
        26: "fencing", 27: "football_american", 28: "football_australian",
        29: "football_soccer", 30: "frisbee", 31: "gardening", 32: "golf",
        33: "gymnastics", 34: "handball", 35: "hiking", 36: "hockey",
        37: "horseback_riding", 38: "housework", 39: "ice_skating", 40: "jumping_rope",
        41: "kayaking", 42: "kettlebell_training", 43: "kickboxing", 44: "kitesurfing",
        45: "martial_arts", 46: "meditation", 47: "mixed_martial_arts", 48: "p90x",
        49: "paragliding", 50: "pilates", 51: "polo", 52: "racquetball",
        53: "rock_climbing", 54: "rowing", 55: "rowing_machine", 56: "rugby",
        57: "running_jogging", 58: "running_sand", 59: "running_treadmill",
        72: "sleeping", 73: "snowboarding", 74: "snowmobile", 75: "snowshoeing",
        76: "squash", 77: "stair_climbing", 78: "stair_climbing_machine",
        79: "standup_paddleboarding", 80: "strength_training", 81: "surfing",
        82: "swimming", 83: "swimming_pool", 84: "swimming_open_water",
        85: "table_tennis", 86: "team_sports", 87: "tennis", 88: "treadmill",
        89: "volleyball", 90: "volleyball_beach", 91: "volleyball_indoor",
        92: "wakeboarding", 93: "walking_fitness", 94: "walking_nordic",
        95: "walking_treadmill", 96: "waterpolo", 97: "weightlifting",
        98: "wheelchair", 99: "windsurfing", 100: "yoga", 101: "zumba",
        108: "sleep", 109: "sleep_light", 110: "sleep_deep", 111: "sleep_rem",
        112: "sleep_awake"
    }
    
    # Activities to exclude from reporting (non-meaningful activities)
    EXCLUDED_ACTIVITIES = {'still', 'unknown', 'tilting', 'in_vehicle', 'sleep_awake'}
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        """
        Initialize the Google Fit API client.
        
        Credentials file path is loaded in the following priority:
        1. credentials_file parameter
        2. GOOGLE_FIT_CREDENTIALS_FILE environment variable
        3. Default: ../config/credentials.json
        
        Token file defaults to ../config/token.json
        
        Args:
            credentials_file: Path to OAuth 2.0 credentials JSON file (optional if set in .env)
            token_file: Path to store/load access tokens (optional, defaults to ../config/token.json)
        """
        import os
        
        # Default to config directory relative to this file
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        
        # Load credentials file path from env or use default
        default_creds = os.getenv('GOOGLE_FIT_CREDENTIALS_FILE', 'credentials.json')
        # If it's just a filename, prepend config directory
        if default_creds and not os.path.isabs(default_creds):
            default_creds = os.path.join(config_dir, default_creds)
        
        self.credentials_file = credentials_file or default_creds
        self.token_file = token_file or os.path.join(config_dir, 'token.json')
        self._service = None
    
    def _authenticate(self) -> Credentials:
        """
        Authenticate user via OAuth 2.0 browser flow.
        
        On first run, opens browser for user consent and saves tokens.
        On subsequent runs, uses saved tokens and refreshes if expired.
        
        Returns:
            Credentials object for API access
            
        Raises:
            FileNotFoundError: If credentials.json is missing
        """
        creds = None
        
        # Check for existing tokens
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # Authenticate if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                creds.refresh(Request())
            else:
                # Full OAuth flow required
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"'{self.credentials_file}' not found. "
                        "Download OAuth credentials from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save tokens for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def get_service(self):
        """
        Create and return authenticated Google Fitness API service.
        
        Returns:
            Google Fitness API service instance
        """
        if not self._service:
            creds = self._authenticate()
            self._service = build('fitness', 'v1', credentials=creds)
        return self._service
    
    def _extract_int_value(self, response: dict) -> Optional[int]:
        """
        Extract integer value from aggregate API response.
        
        Google Fit API returns data in a nested structure. This method
        traverses the structure to extract and sum integer values.
        
        Args:
            response: Raw API response dictionary
            
        Returns:
            Extracted integer value or None if not found
        """
        try:
            total = 0
            found = False
            for bucket in response.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        for val in point.get('value', []):
                            if 'intVal' in val:
                                total += val['intVal']
                                found = True
                            elif 'fpVal' in val:
                                total += int(val['fpVal'])
                                found = True
            return total if found else None
        except (KeyError, TypeError):
            return None
    
    def _extract_float_value(self, response: dict) -> Optional[float]:
        """
        Extract float value from aggregate API response.
        
        Args:
            response: Raw API response dictionary
            
        Returns:
            Extracted float value or None if not found
        """
        try:
            total = 0.0
            found = False
            for bucket in response.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        for val in point.get('value', []):
                            if 'fpVal' in val:
                                total += val['fpVal']
                                found = True
                            elif 'intVal' in val:
                                total += float(val['intVal'])
                                found = True
            return total if found else None
        except (KeyError, TypeError):
            return None
    
    def _fetch_aggregate_data(self, data_type_name: str, start_millis: int, 
                             end_millis: int, data_source_id: Optional[str] = None) -> dict:
        """
        Generic function to fetch aggregated data from Google Fit.
        
        Args:
            data_type_name: Google Fit data type (e.g., 'com.google.step_count.delta')
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            data_source_id: Optional specific data source ID
            
        Returns:
            Raw API response dictionary
        """
        service = self.get_service()
        
        aggregate_by = {"dataTypeName": data_type_name}
        if data_source_id:
            aggregate_by["dataSourceId"] = data_source_id
        
        body = {
            "aggregateBy": [aggregate_by],
            "bucketByTime": {"durationMillis": end_millis - start_millis},
            "startTimeMillis": start_millis,
            "endTimeMillis": end_millis
        }
        
        try:
            return service.users().dataset().aggregate(userId="me", body=body).execute()
        except HttpError:
            return {}
    
    def fetch_steps(self, start_millis: int, end_millis: int) -> Optional[int]:
        """
        Fetch step count from Google Fit.
        
        Data Type: com.google.step_count.delta
        Counts individual steps detected by phone sensors or wearables,
        aggregated across all connected devices.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Total step count or None if unavailable
        """
        response = self._fetch_aggregate_data(
            "com.google.step_count.delta",
            start_millis, end_millis,
            "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
        )
        return self._extract_int_value(response)
    
    def fetch_active_minutes(self, start_millis: int, end_millis: int) -> Optional[int]:
        """
        Fetch active minutes from Google Fit.
        
        Data Type: com.google.active_minutes
        Minutes where user was physically active, based on movement intensity detection.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Total active minutes or None if unavailable
        """
        response = self._fetch_aggregate_data(
            "com.google.active_minutes",
            start_millis, end_millis
        )
        return self._extract_int_value(response)
    
    def fetch_calories(self, start_millis: int, end_millis: int) -> Optional[int]:
        """
        Fetch calories expended from Google Fit.
        
        Data Type: com.google.calories.expended
        Total calories burned (includes BMR + activity),
        calculated from activity data and user profile.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Total calories (rounded) or None if unavailable
        """
        response = self._fetch_aggregate_data(
            "com.google.calories.expended",
            start_millis, end_millis
        )
        result = self._extract_float_value(response)
        return int(result) if result is not None else None
    
    def fetch_distance(self, start_millis: int, end_millis: int) -> Optional[float]:
        """
        Fetch distance traveled from Google Fit.
        
        Data Type: com.google.distance.delta
        Total distance in meters from all activities, returned in kilometers.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Total distance in kilometers or None if unavailable
        """
        response = self._fetch_aggregate_data(
            "com.google.distance.delta",
            start_millis, end_millis
        )
        result = self._extract_float_value(response)
        if result is not None:
            # Convert meters to kilometers
            return round(result / 1000, 2)
        return None
    
    def fetch_sleep(self, start_millis: int, end_millis: int) -> Optional[float]:
        """
        Fetch sleep duration from Google Fit.
        
        Data Type: com.google.sleep.segment
        Sleep segments tracked by phone or wearable.
        Requires sleep tracking to be enabled.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Total sleep hours (float) or None if unavailable
        """
        service = self.get_service()
        
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.sleep.segment"}],
            "bucketByTime": {"durationMillis": end_millis - start_millis},
            "startTimeMillis": start_millis,
            "endTimeMillis": end_millis
        }
        
        try:
            response = service.users().dataset().aggregate(userId="me", body=body).execute()
            
            total_sleep_millis = 0
            for bucket in response.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        # Sleep segments have start and end times
                        start = int(point.get('startTimeNanos', 0)) // 1_000_000
                        end = int(point.get('endTimeNanos', 0)) // 1_000_000
                        if start and end:
                            total_sleep_millis += (end - start)
            
            if total_sleep_millis > 0:
                # Convert milliseconds to hours
                return round(total_sleep_millis / (1000 * 60 * 60), 1)
            return None
            
        except HttpError:
            return None
    
    def fetch_activity_segments(self, start_millis: int, end_millis: int) -> Dict[str, int]:
        """
        Fetch activity segments with counts from Google Fit.
        
        Uses Sessions API to find recorded activities like walking, running, cycling, etc.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Dictionary mapping activity names to occurrence counts
        """
        service = self.get_service()
        activities = {}
        
        try:
            # Use sessions API to get activity sessions
            response = service.users().sessions().list(
                userId="me",
                startTime=datetime.fromtimestamp(start_millis / 1000).isoformat() + "Z",
                endTime=datetime.fromtimestamp(end_millis / 1000).isoformat() + "Z"
            ).execute()
            
            for session in response.get('session', []):
                activity_type = session.get('activityType', 4)
                activity_name = self.ACTIVITY_MAP.get(activity_type, f"activity_{activity_type}")
                
                # Filter out non-meaningful activities
                if activity_name not in self.EXCLUDED_ACTIVITIES:
                    activities[activity_name] = activities.get(activity_name, 0) + 1
            
        except HttpError:
            pass
        
        return activities
    
    def fetch_all_data(self, start_millis: int, end_millis: int) -> Dict[str, Any]:
        """
        Fetch all available Google Fit data and return normalized structure.
        
        This is the main method to call for retrieving comprehensive Google Fit data.
        It collects steps, active minutes, calories, distance, sleep, and activities.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Normalized dictionary with all fitness data:
            {
                "steps": int or None,
                "active_minutes": int or None,
                "calories": int or None,
                "distance_km": float or None,
                "sleep_hours": float or None,
                "activities": dict of activity_name: count,
                "time_range": {"start": str, "end": str},
                "last_updated": str
            }
        """
        # Fetch all data types (gracefully handling missing data)
        data = {
            "steps": self.fetch_steps(start_millis, end_millis),
            "active_minutes": self.fetch_active_minutes(start_millis, end_millis),
            "calories": self.fetch_calories(start_millis, end_millis),
            "distance_km": self.fetch_distance(start_millis, end_millis),
            "sleep_hours": self.fetch_sleep(start_millis, end_millis),
            "activities": self.fetch_activity_segments(start_millis, end_millis),
            "time_range": {
                "start": datetime.fromtimestamp(start_millis / 1000).strftime('%Y-%m-%d %H:%M'),
                "end": datetime.fromtimestamp(end_millis / 1000).strftime('%Y-%m-%d %H:%M')
            },
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return data
