"""
Strava Fetcher Module
Fetches activity data from Strava API.

Collects:
- Recent activities with type, distance, duration
- Activity summaries and totals
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

import requests

from auth import get_strava_access_token, is_strava_configured
from time_utils import get_unix_timestamps, format_time_range


# ============================================================================
# CONFIGURATION
# ============================================================================

STRAVA_API_BASE = "https://www.strava.com/api/v3"


# ============================================================================
# API FUNCTIONS
# ============================================================================

def _make_strava_request(endpoint: str, access_token: str, 
                         params: Optional[Dict] = None) -> Optional[Dict]:
    """Make authenticated request to Strava API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(
            f"{STRAVA_API_BASE}{endpoint}",
            headers=headers,
            params=params or {}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Strava API error: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Strava request failed: {e}")
        return None


def _normalize_activity(activity: Dict) -> Dict[str, Any]:
    """
    Normalize a Strava activity to standard format.
    
    Strava Activity Fields:
    - type: Activity type (Run, Ride, Swim, etc.)
    - name: Activity name
    - distance: Distance in meters
    - moving_time: Moving time in seconds
    - elapsed_time: Total time in seconds
    - total_elevation_gain: Elevation in meters
    - start_date_local: Local start time
    - calories: Estimated calories (not always present)
    """
    return {
        "type": activity.get("type", "Unknown"),
        "name": activity.get("name", "Untitled"),
        "distance_km": round(activity.get("distance", 0) / 1000, 2),
        "duration_min": round(activity.get("moving_time", 0) / 60, 1),
        "elapsed_min": round(activity.get("elapsed_time", 0) / 60, 1),
        "elevation_m": activity.get("total_elevation_gain", 0),
        "calories": activity.get("calories", None),
        "date": activity.get("start_date_local", "")[:10],  # YYYY-MM-DD
        "start_time": activity.get("start_date_local", "")[11:16]  # HH:MM
    }


def _calculate_summary(activities: List[Dict]) -> Dict[str, Any]:
    """Calculate summary statistics from activities."""
    if not activities:
        return {
            "total_activities": 0,
            "total_distance_km": 0,
            "total_duration_min": 0,
            "total_calories": 0
        }
    
    total_distance = sum(a.get("distance_km", 0) for a in activities)
    total_duration = sum(a.get("duration_min", 0) for a in activities)
    total_calories = sum(a.get("calories", 0) or 0 for a in activities)
    
    # Count by type
    type_counts = {}
    for a in activities:
        atype = a.get("type", "Unknown")
        type_counts[atype] = type_counts.get(atype, 0) + 1
    
    return {
        "total_activities": len(activities),
        "total_distance_km": round(total_distance, 2),
        "total_duration_min": round(total_duration, 1),
        "total_calories": total_calories,
        "by_type": type_counts
    }


# ============================================================================
# MAIN FETCH FUNCTIONS
# ============================================================================

def fetch_strava_activities(start_millis: int, end_millis: int) -> List[Dict]:
    """
    Fetch Strava activities in time range.
    
    Args:
        start_millis: Start time in milliseconds
        end_millis: End time in milliseconds
    
    Returns:
        List of normalized activity dictionaries
    """
    access_token = get_strava_access_token()
    if not access_token:
        return []
    
    # Convert to Unix timestamps
    start_epoch, end_epoch = get_unix_timestamps(start_millis, end_millis)
    
    # Fetch activities
    raw_activities = _make_strava_request(
        "/athlete/activities",
        access_token,
        params={
            "after": start_epoch,
            "before": end_epoch,
            "per_page": 100
        }
    )
    
    if not raw_activities:
        return []
    
    # Normalize activities
    return [_normalize_activity(a) for a in raw_activities]


def fetch_all_strava_data(start_millis: int, end_millis: int) -> Dict[str, Any]:
    """
    Fetch all Strava data for time range.
    
    Args:
        start_millis: Start time in milliseconds
        end_millis: End time in milliseconds
    
    Returns:
        Normalized dictionary with activities and summary
    """
    # Check if Strava is configured
    if not is_strava_configured():
        return {
            "configured": False,
            "activities": [],
            "summary": _calculate_summary([]),
            "error": "Strava not configured"
        }
    
    try:
        activities = fetch_strava_activities(start_millis, end_millis)
        
        return {
            "configured": True,
            "activities": activities,
            "summary": _calculate_summary(activities),
            "time_range": format_time_range(start_millis, end_millis)
        }
        
    except Exception as e:
        return {
            "configured": True,
            "activities": [],
            "summary": _calculate_summary([]),
            "error": str(e)
        }


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import json
    from time_utils import get_time_range_millis, TimePreset
    
    print("🚴 Strava Fetcher - Test Run")
    print("=" * 50)
    
    if not is_strava_configured():
        print("\n❌ Strava not configured!")
        print("\nTo configure Strava:")
        print("1. Go to https://www.strava.com/settings/api")
        print("2. Create an application")
        print("3. Create strava_credentials.json with:")
        print('   {"client_id": "YOUR_ID", "client_secret": "YOUR_SECRET"}')
    else:
        print("\n📡 Fetching Strava data (last 7 days)...")
        start, end = get_time_range_millis(TimePreset.LAST_7_DAYS)
        data = fetch_all_strava_data(start, end)
        
        print("\n📊 Results:")
        print(json.dumps(data, indent=2))
