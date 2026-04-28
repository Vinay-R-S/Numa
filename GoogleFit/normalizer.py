"""
Data Normalizer Module
Combines data from all health sources into unified structure.

Provides:
- Individual source normalization
- Combined data aggregation
- Graceful handling of missing data
"""

from datetime import datetime
from typing import Dict, Any, Optional

from auth import get_google_fit_service, is_strava_configured
from time_utils import TimePreset, get_time_range_millis, format_time_range
from google_fit_api import fetch_all_fitness_data
from strava_fetcher import fetch_all_strava_data


# ============================================================================
# NORMALIZATION HELPERS
# ============================================================================

def _safe_value(value: Any, default: Any = None) -> Any:
    """Return value if not None, otherwise return default."""
    return value if value is not None else default


def normalize_google_fit(raw_data: Dict) -> Dict[str, Any]:
    """
    Ensure Google Fit data has consistent structure.
    
    Handles missing values gracefully.
    """
    return {
        "steps": _safe_value(raw_data.get("steps")),
        "active_minutes": _safe_value(raw_data.get("active_minutes")),
        "calories": _safe_value(raw_data.get("calories")),
        "distance_km": _safe_value(raw_data.get("distance_km")),
        "sleep_hours": _safe_value(raw_data.get("sleep_hours")),
        "activities": _safe_value(raw_data.get("activities"), {}),
        "activity_segments": _safe_value(raw_data.get("activity_segments"), []),
    }


def normalize_strava(raw_data: Dict) -> Dict[str, Any]:
    """
    Ensure Strava data has consistent structure.
    
    Handles missing values and unconfigured state.
    """
    return {
        "configured": raw_data.get("configured", False),
        "activities": raw_data.get("activities", []),
        "summary": raw_data.get("summary", {
            "total_activities": 0,
            "total_distance_km": 0,
            "total_duration_min": 0,
            "total_calories": 0,
            "by_type": {}
        }),
        "error": raw_data.get("error")
    }


# ============================================================================
# MAIN AGGREGATION FUNCTION
# ============================================================================

def fetch_all_health_data(
    preset: TimePreset = TimePreset.TODAY,
    custom_start: Optional[datetime] = None,
    custom_end: Optional[datetime] = None,
    include_strava: bool = True
) -> Dict[str, Any]:
    """
    Fetch and combine all health data from all sources.
    
    Args:
        preset: Time range preset (today, 7d, 30d, custom)
        custom_start: Start datetime for custom range
        custom_end: End datetime for custom range
        include_strava: Whether to fetch Strava data
    
    Returns:
        Unified health data dictionary:
        {
            "time_range": {...},
            "google_fit": {...},
            "strava": {...},
            "last_updated": str
        }
    """
    # Calculate time range
    start_millis, end_millis = get_time_range_millis(
        preset, custom_start, custom_end
    )
    
    # Initialize result
    result = {
        "time_range": {
            "preset": preset.value,
            **format_time_range(start_millis, end_millis)
        },
        "google_fit": None,
        "strava": None,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "errors": []
    }
    
    # Fetch Google Fit data
    try:
        service = get_google_fit_service()
        hours = max(1, (end_millis - start_millis) // (1000 * 60 * 60))
        raw_gfit = fetch_all_fitness_data(service, hours=hours)
        result["google_fit"] = normalize_google_fit(raw_gfit)
    except FileNotFoundError as e:
        result["errors"].append(f"Google Fit: {str(e)}")
        result["google_fit"] = normalize_google_fit({})
    except Exception as e:
        result["errors"].append(f"Google Fit error: {str(e)}")
        result["google_fit"] = normalize_google_fit({})
    
    # Fetch Strava data (if requested)
    if include_strava:
        try:
            raw_strava = fetch_all_strava_data(start_millis, end_millis)
            result["strava"] = normalize_strava(raw_strava)
        except Exception as e:
            result["errors"].append(f"Strava error: {str(e)}")
            result["strava"] = normalize_strava({"configured": False})
    else:
        result["strava"] = normalize_strava({"configured": False})
    
    return result


def get_summary_stats(data: Dict) -> Dict[str, Any]:
    """
    Calculate combined summary statistics.
    
    Useful for overview displays.
    """
    gfit = data.get("google_fit", {})
    strava = data.get("strava", {})
    strava_summary = strava.get("summary", {})
    
    return {
        "total_steps": _safe_value(gfit.get("steps"), 0),
        "total_active_minutes": _safe_value(gfit.get("active_minutes"), 0),
        "total_calories": _safe_value(gfit.get("calories"), 0),
        "total_sleep_hours": _safe_value(gfit.get("sleep_hours"), 0),
        "total_distance_km": (
            _safe_value(gfit.get("distance_km"), 0) +
            _safe_value(strava_summary.get("total_distance_km"), 0)
        ),
        "strava_activities": strava_summary.get("total_activities", 0),
        "google_fit_activities": len(gfit.get("activities", {}))
    }


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import json
    
    print("📊 Health Data Normalizer - Test Run")
    print("=" * 50)
    
    print("\n📡 Fetching all health data (last 7 days)...")
    data = fetch_all_health_data(TimePreset.LAST_7_DAYS)
    
    print("\n📊 Combined Results:")
    print(json.dumps(data, indent=2, default=str))
    
    print("\n📈 Summary Stats:")
    summary = get_summary_stats(data)
    print(json.dumps(summary, indent=2))
