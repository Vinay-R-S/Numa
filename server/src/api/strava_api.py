"""
Strava API Client - Object-Oriented Implementation

This module provides a clean, optimized interface for interacting with the Strava API.
It handles authentication, activity fetching, and data normalization.

Main Features:
- OAuth 2.0 authentication with token refresh
- Fetch activities within specified time ranges
- Normalize activity data to a standard format
- Calculate summary statistics across activities

Usage:
    from strava_api import StravaAPI
    
    strava = StravaAPI(client_id, client_secret, refresh_token)
    activities = strava.fetch_activities(start_millis, end_millis)
    summary = strava.get_summary(activities)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import requests


class StravaAPI:
    """
    Main class for interacting with the Strava API.
    
    Handles authentication, data fetching, and normalization of Strava activity data.
    """
    
    # Strava API base URL
    API_BASE = "https://www.strava.com/api/v3"
    TOKEN_URL = "https://www.strava.com/oauth/token"
    
    def __init__(self, client_id: str = None, client_secret: str = None, 
                 refresh_token: str = None):
        """
        Initialize the Strava API client.
        
        Credentials are loaded in the following priority:
        1. Parameters passed to __init__
        2. Environment variables (STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN)
        3. Config file at ../config/strava_credentials.json
        
        Args:
            client_id: Strava application client ID (optional if set in .env)
            client_secret: Strava application client secret (optional if set in .env)
            refresh_token: User's refresh token for obtaining access tokens (optional if set in .env)
        """
        import os
        import json
        
        # Try to load from environment variables first
        self.client_id = client_id or os.getenv('STRAVA_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('STRAVA_CLIENT_SECRET')
        self.refresh_token = refresh_token or os.getenv('STRAVA_REFRESH_TOKEN')
        
        # If still missing, try to load from config file
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
            config_file = os.path.join(config_dir, 'strava_credentials.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.client_id = self.client_id or config.get('client_id')
                    self.client_secret = self.client_secret or config.get('client_secret')
                    self.refresh_token = self.refresh_token or config.get('refresh_token')
        
        self._access_token: Optional[str] = None
    
    def _get_access_token(self) -> Optional[str]:
        """
        Obtain a fresh access token using the refresh token.
        
        Strava access tokens expire after 6 hours. This method exchanges
        the refresh token for a new access token.
        
        Returns:
            Access token string if successful, None otherwise
        """
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return None
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                return self._access_token
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"Token refresh request failed: {e}")
            return None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an authenticated request to the Strava API.
        
        Args:
            endpoint: API endpoint path (e.g., "/athlete/activities")
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary if successful, None otherwise
        """
        # Ensure we have a valid access token
        if not self._access_token:
            self._access_token = self._get_access_token()
        
        if not self._access_token:
            return None
        
        headers = {"Authorization": f"Bearer {self._access_token}"}
        
        try:
            response = requests.get(
                f"{self.API_BASE}{endpoint}",
                headers=headers,
                params=params or {}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def _normalize_activity(self, activity: Dict) -> Dict[str, Any]:
        """
        Normalize a Strava activity to a standard format.
        
        Strava returns activities with various fields. This method extracts
        the most relevant data and converts units to more readable formats.
        
        Args:
            activity: Raw activity dictionary from Strava API
            
        Returns:
            Normalized activity dictionary with standardized fields
        """
        return {
            "type": activity.get("type", "Unknown"),
            "name": activity.get("name", "Untitled"),
            "distance_km": round(activity.get("distance", 0) / 1000, 2),
            "duration_min": round(activity.get("moving_time", 0) / 60, 1),
            "elapsed_min": round(activity.get("elapsed_time", 0) / 60, 1),
            "elevation_m": activity.get("total_elevation_gain", 0),
            "calories": activity.get("calories", None),
            "date": activity.get("start_date_local", "")[:10],  # Extract YYYY-MM-DD
            "start_time": activity.get("start_date_local", "")[11:16]  # Extract HH:MM
        }
    
    def fetch_activities(self, start_millis: int, end_millis: int) -> List[Dict]:
        """
        Fetch all activities within a specified time range.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            List of normalized activity dictionaries
        """
        # Convert milliseconds to Unix timestamps (seconds)
        start_epoch = start_millis // 1000
        end_epoch = end_millis // 1000
        
        # Fetch activities from Strava API
        raw_activities = self._make_request(
            "/athlete/activities",
            params={
                "after": start_epoch,
                "before": end_epoch,
                "per_page": 100  # Maximum activities per request
            }
        )
        
        if not raw_activities:
            return []
        
        # Normalize all activities
        return [self._normalize_activity(activity) for activity in raw_activities]
    
    def get_summary(self, activities: List[Dict]) -> Dict[str, Any]:
        """
        Calculate summary statistics from a list of activities.
        
        Args:
            activities: List of normalized activity dictionaries
            
        Returns:
            Dictionary containing summary statistics:
            - total_activities: Total number of activities
            - total_distance_km: Total distance covered
            - total_duration_min: Total active time
            - total_calories: Total calories burned
            - by_type: Activity count grouped by type
        """
        if not activities:
            return {
                "total_activities": 0,
                "total_distance_km": 0,
                "total_duration_min": 0,
                "total_calories": 0,
                "by_type": {}
            }
        
        # Calculate totals
        total_distance = sum(a.get("distance_km", 0) for a in activities)
        total_duration = sum(a.get("duration_min", 0) for a in activities)
        total_calories = sum(a.get("calories", 0) or 0 for a in activities)
        
        # Count activities by type
        type_counts = {}
        for activity in activities:
            activity_type = activity.get("type", "Unknown")
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
        
        return {
            "total_activities": len(activities),
            "total_distance_km": round(total_distance, 2),
            "total_duration_min": round(total_duration, 1),
            "total_calories": total_calories,
            "by_type": type_counts
        }
    
    def fetch_all_data(self, start_millis: int, end_millis: int) -> Dict[str, Any]:
        """
        Fetch all Strava data for a time range and return a complete dataset.
        
        This is the main method to call for retrieving comprehensive Strava data.
        It fetches activities and calculates summary statistics.
        
        Args:
            start_millis: Start time in milliseconds since epoch
            end_millis: End time in milliseconds since epoch
            
        Returns:
            Dictionary containing:
            - configured: Whether Strava is properly configured
            - activities: List of normalized activities
            - summary: Summary statistics
            - time_range: Human-readable time range
            - error: Error message if any
        """
        try:
            activities = self.fetch_activities(start_millis, end_millis)
            
            # Format time range for display
            start_time = datetime.fromtimestamp(start_millis / 1000).strftime('%Y-%m-%d %H:%M')
            end_time = datetime.fromtimestamp(end_millis / 1000).strftime('%Y-%m-%d %H:%M')
            
            return {
                "configured": True,
                "activities": activities,
                "summary": self.get_summary(activities),
                "time_range": {
                    "start": start_time,
                    "end": end_time
                }
            }
            
        except Exception as e:
            return {
                "configured": True,
                "activities": [],
                "summary": self.get_summary([]),
                "error": str(e)
            }
    
    @staticmethod
    def is_configured(client_id: str, client_secret: str, refresh_token: str) -> bool:
        """
        Check if Strava credentials are properly configured.
        
        Args:
            client_id: Strava application client ID
            client_secret: Strava application client secret
            refresh_token: User's refresh token
            
        Returns:
            True if all credentials are present, False otherwise
        """
        return all([client_id, client_secret, refresh_token])
