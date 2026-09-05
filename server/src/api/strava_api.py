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

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
import logging
import os
import time

import requests

# `print` wrote straight to stdout, so nothing this module said passed the
# redaction filter, and the bodies below come from the OAuth token endpoint
# (NUMA-134 P6, PLAN 8).
log = logging.getLogger(__name__)


def _clean_secret(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip().strip("\"'")
    return cleaned or None


def _server_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _default_strava_dir() -> str:
    return os.path.join(_server_dir(), "apiConfig", "strava")


def _resolve_file_path(path: Optional[str], default_name: str) -> str:
    candidate = _clean_secret(path)
    if not candidate:
        candidate = os.path.join(_default_strava_dir(), default_name)
    elif not os.path.isabs(candidate):
        candidate = os.path.join(_default_strava_dir(), candidate)
    if os.path.isdir(candidate) or candidate.endswith((os.sep, "/", "\\")):
        candidate = os.path.join(candidate, default_name)
    return candidate


def _parse_expires_at(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        pass
    try:
        return int(datetime.fromisoformat(str(value).strip().strip("\"'").replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


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
        self.token_file = _resolve_file_path(os.getenv("STRAVA_TOKEN_FILE"), "token.json")
        self.credentials_file = _resolve_file_path(
            os.getenv("STRAVA_CREDENTIALS_FILE"),
            "credentials.json",
        )

        saved_token = self._load_json(self.token_file)
        saved_credentials = self._load_json(self.credentials_file)

        # Try to load from explicit params, environment variables, token file, then credentials file.
        self.client_id = (
            _clean_secret(client_id)
            or _clean_secret(os.getenv('STRAVA_CLIENT_ID'))
            or _clean_secret(saved_token.get('client_id'))
            or _clean_secret(saved_credentials.get('client_id'))
        )
        self.client_secret = (
            _clean_secret(client_secret)
            or _clean_secret(os.getenv('STRAVA_CLIENT_SECRET'))
            or _clean_secret(saved_credentials.get('client_secret'))
        )
        self.refresh_token = (
            _clean_secret(refresh_token)
            or _clean_secret(os.getenv('STRAVA_REFRESH_TOKEN'))
            or _clean_secret(saved_token.get('refresh_token'))
            or _clean_secret(saved_credentials.get('refresh_token'))
        )
        self._access_token = (
            _clean_secret(os.getenv('STRAVA_ACCESS_TOKEN'))
            or _clean_secret(saved_token.get('access_token'))
        )
        self._expires_at = (
            _parse_expires_at(os.getenv('STRAVA_TOKEN_EXPIRES_AT'))
            or _parse_expires_at(saved_token.get('expires_at'))
            or _parse_expires_at(saved_token.get('expires_at_iso'))
        )

        # Backward compatibility for older local config paths.
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
            config_file = os.path.join(config_dir, 'strava_credentials.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.client_id = self.client_id or _clean_secret(config.get('client_id'))
                    self.client_secret = self.client_secret or _clean_secret(config.get('client_secret'))
                    self.refresh_token = self.refresh_token or _clean_secret(config.get('refresh_token'))

    @staticmethod
    def _load_json(path: str) -> Dict[str, Any]:
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_token(self, data: Dict[str, Any]) -> None:
        expires_at = _parse_expires_at(data.get("expires_at"))
        payload = {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token") or self.refresh_token,
            "expires_at": expires_at,
            "expires_at_iso": (
                datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
                if expires_at
                else None
            ),
            "token_type": data.get("token_type"),
            "scope": data.get("scope"),
            "athlete": data.get("athlete"),
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _has_valid_access_token(self) -> bool:
        return bool(self._access_token and self._expires_at and self._expires_at > int(time.time()) + 60)
    
    def _get_access_token(self) -> Optional[str]:
        """
        Obtain a fresh access token using the refresh token.
        
        Strava access tokens expire after 6 hours. This method exchanges
        the refresh token for a new access token.
        
        Returns:
            Access token string if successful, None otherwise
        """
        if self._has_valid_access_token():
            return self._access_token

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return None
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = _clean_secret(data.get("access_token"))
                self.refresh_token = _clean_secret(data.get("refresh_token")) or self.refresh_token
                self._expires_at = _parse_expires_at(data.get("expires_at"))
                self._save_token(data)
                return self._access_token
            else:
                log.error("Strava token refresh failed: HTTP %s", response.status_code)
                return None
                
        except requests.RequestException as e:
            log.error("Strava token refresh request failed: %s", e)
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
                params=params or {},
                timeout=20,
            )
            
            if response.status_code == 200:
                return response.json()
            if response.status_code == 401:
                self._access_token = None
                headers = {"Authorization": f"Bearer {self._get_access_token()}"}
                response = requests.get(
                    f"{self.API_BASE}{endpoint}",
                    headers=headers,
                    params=params or {},
                    timeout=20,
                )
                if response.status_code == 200:
                    return response.json()
                log.warning(
                    "Strava request to %s failed after retry: HTTP %s",
                    endpoint, response.status_code,
                )
                return None
            else:
                log.warning("Strava request to %s failed: HTTP %s", endpoint, response.status_code)
                return None
                
        except requests.RequestException as e:
            log.warning("Strava request to %s failed: %s", endpoint, e)
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
        
        raw_activities: List[Dict] = []
        page = 1
        per_page = 100

        while True:
            page_items = self._make_request(
                "/athlete/activities",
                params={
                    "after": start_epoch,
                    "before": end_epoch,
                    "per_page": per_page,
                    "page": page,
                },
            )
            if not page_items:
                break
            raw_activities.extend(page_items)
            if len(page_items) < per_page:
                break
            page += 1

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
