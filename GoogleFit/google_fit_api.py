"""
Google Fit API Module
Core module for fetching all available Google Fit data.

Fetches multiple data types: steps, calories, active minutes, activities, sleep.
Authentication is handled by auth.py (get_google_fit_service).
Time utilities are provided by time_utils.py.

Usage:
    from google_fit_api import fetch_all_fitness_data
    from auth import get_google_fit_service

    service = get_google_fit_service()
    data = fetch_all_fitness_data(service)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from googleapiclient.errors import HttpError

# Re-export for backward compatibility
from auth import get_google_fit_service
from time_utils import get_time_range_millis

# Also expose as get_fitness_service for legacy callers in api_server.py
get_fitness_service = get_google_fit_service

# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def _extract_int_value(response: dict) -> Optional[int]:
    """
    Extract integer value from aggregate API response.
    
    Args:
        response: Raw API response dictionary
        
    Returns:
        Extracted integer value or None if not found
    """
    try:
        for bucket in response.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for val in point.get('value', []):
                        if 'intVal' in val:
                            return val['intVal']
                        if 'fpVal' in val:
                            return int(val['fpVal'])
    except (KeyError, TypeError):
        pass
    return None


def _extract_float_value(response: dict) -> Optional[float]:
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


def _fetch_aggregate_data(service, data_type_name: str, 
                          start_millis: int, end_millis: int,
                          data_source_id: Optional[str] = None) -> dict:
    """
    Generic function to fetch aggregated data from Google Fit.
    
    Args:
        service: Google Fitness API service
        data_type_name: Google Fit data type (e.g., 'com.google.step_count.delta')
        start_millis: Start time in milliseconds
        end_millis: End time in milliseconds
        data_source_id: Optional specific data source ID
        
    Returns:
        Raw API response dictionary
    """
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


def fetch_steps(service, start_millis: int, end_millis: int) -> Optional[int]:
    """
    Fetch step count from Google Fit.
    
    Data Type: com.google.step_count.delta
    - Counts individual steps detected by phone sensors or wearables
    - Aggregated across all connected devices
    
    Returns:
        Total step count or None if unavailable
    """
    response = _fetch_aggregate_data(
        service,
        "com.google.step_count.delta",
        start_millis, end_millis,
        "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
    )
    return _extract_int_value(response)


def fetch_active_minutes(service, start_millis: int, end_millis: int) -> Optional[int]:
    """
    Fetch active minutes from Google Fit.
    
    Data Type: com.google.active_minutes
    - Minutes where user was physically active
    - Based on movement intensity detection
    
    Returns:
        Total active minutes or None if unavailable
    """
    response = _fetch_aggregate_data(
        service,
        "com.google.active_minutes",
        start_millis, end_millis
    )
    return _extract_int_value(response)


def fetch_calories(service, start_millis: int, end_millis: int) -> Optional[int]:
    """
    Fetch calories expended from Google Fit.
    
    Data Type: com.google.calories.expended
    - Total calories burned (includes BMR + activity)
    - Calculated from activity data and user profile
    
    Returns:
        Total calories (rounded) or None if unavailable
    """
    response = _fetch_aggregate_data(
        service,
        "com.google.calories.expended",
        start_millis, end_millis
    )
    result = _extract_float_value(response)
    return int(result) if result is not None else None


def fetch_distance(service, start_millis: int, end_millis: int) -> Optional[float]:
    """
    Fetch distance traveled from Google Fit.
    
    Data Type: com.google.distance.delta
    - Distance traveled in meters
    - Tracked by phone GPS or wearables
    
    Returns:
        Total distance in kilometers (float) or None if unavailable
    """
    response = _fetch_aggregate_data(
        service,
        "com.google.distance.delta",
        start_millis, end_millis
    )
    result = _extract_float_value(response)
    if result is not None:
        # Convert meters to kilometers
        return round(result / 1000, 2)
    return None


def fetch_sleep(service, start_millis: int, end_millis: int) -> Optional[dict]:
    """
    Fetch sleep duration from Google Fit with accurate stage filtering.

    Google Fit sleep segment types:
      1 = Awake (in bed)    — EXCLUDED
      2 = Sleep (generic)   — INCLUDED
      3 = Out of bed        — EXCLUDED
      4 = Light sleep       — INCLUDED
      5 = Deep sleep        — INCLUDED
      6 = REM sleep         — INCLUDED

    Returns:
        Dict with 'hours' (float) and 'stages' breakdown, or None if unavailable.
    """
    SLEEP_TYPES = {2, 4, 5, 6}  # only count actual sleep, not awake/out-of-bed

    body = {
        "aggregateBy": [{"dataTypeName": "com.google.sleep.segment"}],
        "bucketByTime": {"durationMillis": end_millis - start_millis},
        "startTimeMillis": start_millis,
        "endTimeMillis": end_millis
    }

    try:
        response = service.users().dataset().aggregate(userId="me", body=body).execute()

        stages_ms = {2: 0, 4: 0, 5: 0, 6: 0}  # generic, light, deep, REM
        total_sleep_ms = 0

        for bucket in response.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    seg_start = int(point.get('startTimeNanos', 0)) // 1_000_000
                    seg_end   = int(point.get('endTimeNanos', 0))   // 1_000_000

                    if not (seg_start and seg_end and seg_end > seg_start):
                        continue

                    values = point.get('value', [])
                    sleep_type = values[0].get('intVal', 2) if values else 2

                    if sleep_type not in SLEEP_TYPES:
                        continue  # skip Awake and Out-of-bed

                    duration_ms = seg_end - seg_start
                    # Sanity: skip segments longer than 12 hours (data error)
                    if duration_ms > 12 * 60 * 60 * 1000:
                        continue

                    stages_ms[sleep_type] = stages_ms.get(sleep_type, 0) + duration_ms
                    total_sleep_ms += duration_ms

        if total_sleep_ms <= 0:
            return None

        total_hours = total_sleep_ms / (1000 * 60 * 60)
        if total_hours > 16:  # sanity cap
            return None

        def ms_to_h(ms):
            return round(ms / (1000 * 60 * 60), 1)

        return {
            'hours': round(total_hours, 1),
            'stages': {
                'deep':    ms_to_h(stages_ms.get(5, 0)),
                'light':   ms_to_h(stages_ms.get(4, 0)),
                'rem':     ms_to_h(stages_ms.get(6, 0)),
                'generic': ms_to_h(stages_ms.get(2, 0)),
            }
        }

    except HttpError:
        return None


def fetch_activities(service, start_millis: int, end_millis: int) -> List[str]:
    """
    Fetch activity types from Google Fit sessions.
    
    Uses Sessions API to find recorded activities like:
    - Walking, Running, Cycling
    - Gym workouts, Yoga, etc.
    
    Returns:
        List of unique activity names (empty list if none)
    """
    # Activity type mapping (common Google Fit activity codes)
    ACTIVITY_MAP = {
        7: "walking",
        8: "running",
        1: "biking",
        3: "still",
        4: "unknown",
        72: "sleeping",
        9: "automotive",
        82: "hiking",
        16: "gym_workout",
        6: "tilting",
        97: "yoga",
        98: "meditation",
        29: "swimming",
        75: "strength_training",
    }
    
    try:
        # Use sessions API to get activity sessions
        response = service.users().sessions().list(
            userId="me",
            startTime=datetime.fromtimestamp(start_millis / 1000).isoformat() + "Z",
            endTime=datetime.fromtimestamp(end_millis / 1000).isoformat() + "Z"
        ).execute()
        
        activities = set()
        for session in response.get('session', []):
            activity_type = session.get('activityType', 4)
            activity_name = ACTIVITY_MAP.get(activity_type, f"activity_{activity_type}")
            # Filter out non-meaningful activities
            if activity_name not in ['still', 'unknown', 'tilting', 'automotive']:
                activities.add(activity_name)
        
        return sorted(list(activities))
        
    except HttpError:
        return []


# ============================================================================
# MAIN DATA COLLECTION FUNCTION
# ============================================================================

def fetch_all_fitness_data(service, hours: int = 24,
                           start_millis: Optional[int] = None,
                           end_millis: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch all available Google Fit data and return normalized structure.

    Accepts either explicit start/end milliseconds (preferred, for custom date
    ranges) or a legacy `hours` look-back window.

    Args:
        service:       Authenticated Google Fitness API service
        hours:         Fallback hours to look back when millis not provided
        start_millis:  Explicit range start (ms since epoch)
        end_millis:    Explicit range end   (ms since epoch)

    Returns:
        Normalized dict with all fitness data.
    """
    if start_millis is None or end_millis is None:
        from time_utils import get_time_range_millis as _get_range
        start_millis, end_millis = _get_range(hours)

    sleep_result = fetch_sleep(service, start_millis, end_millis)

    data = {
        "steps":         fetch_steps(service, start_millis, end_millis),
        "active_minutes":fetch_active_minutes(service, start_millis, end_millis),
        "calories":      fetch_calories(service, start_millis, end_millis),
        "sleep_hours":   sleep_result['hours'] if sleep_result else None,
        "sleep_stages":  sleep_result['stages'] if sleep_result else None,
        "activities":    fetch_activities(service, start_millis, end_millis),
        "time_range": {
            "start": datetime.fromtimestamp(start_millis / 1000).strftime('%Y-%m-%d %H:%M'),
            "end":   datetime.fromtimestamp(end_millis   / 1000).strftime('%Y-%m-%d %H:%M')
        },
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return data


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    """Quick test to verify API module works standalone."""
    import json
    
    print("🏃 Google Fit API Module - Test Run")
    print("=" * 50)
    
    try:
        print("\n📱 Authenticating...")
        service = get_fitness_service()
        print("✅ Authentication successful!")
        
        print("\n📡 Fetching all fitness data...")
        data = fetch_all_fitness_data(service)
        
        print("\n📊 Results:")
        print(json.dumps(data, indent=2))
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
