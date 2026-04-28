"""
Time Utilities Module
Handles time range calculations for health data queries.

Supports:
- Preset ranges: today, last_7_days, last_30_days
- Custom date ranges
- Conversion between datetime and milliseconds
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
from enum import Enum


class TimePreset(Enum):
    """Available time range presets."""
    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    CUSTOM = "custom"


def get_preset_range(preset: TimePreset) -> Tuple[datetime, datetime]:
    """
    Get start and end datetime for a preset time range.
    
    Args:
        preset: TimePreset enum value
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    end = datetime.now()
    
    if preset == TimePreset.TODAY:
        # From midnight today to now
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif preset == TimePreset.LAST_7_DAYS:
        start = end - timedelta(days=7)
    elif preset == TimePreset.LAST_30_DAYS:
        start = end - timedelta(days=30)
    else:
        # Default to today
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return start, end


def get_custom_range(start_date: datetime, end_date: datetime) -> Tuple[datetime, datetime]:
    """
    Validate and return a custom date range.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        
    Returns:
        Tuple of (start_datetime, end_datetime)
        
    Raises:
        ValueError: If start_date is after end_date
    """
    if start_date > end_date:
        raise ValueError("Start date must be before end date")
    
    # Ensure end date includes full day if only date provided
    if end_date.hour == 0 and end_date.minute == 0:
        end_date = end_date.replace(hour=23, minute=59, second=59)
    
    return start_date, end_date


def datetime_to_millis(dt: datetime) -> int:
    """Convert datetime to milliseconds since epoch."""
    return int(dt.timestamp() * 1000)


def millis_to_datetime(millis: int) -> datetime:
    """Convert milliseconds since epoch to datetime."""
    return datetime.fromtimestamp(millis / 1000)


def get_time_range_millis(preset: TimePreset = TimePreset.TODAY,
                          custom_start: Optional[datetime] = None,
                          custom_end: Optional[datetime] = None) -> Tuple[int, int]:
    """
    Get time range in milliseconds for API requests.
    
    Args:
        preset: TimePreset enum value
        custom_start: Start datetime for custom range
        custom_end: End datetime for custom range
        
    Returns:
        Tuple of (start_millis, end_millis)
    """
    if preset == TimePreset.CUSTOM and custom_start and custom_end:
        start, end = get_custom_range(custom_start, custom_end)
    else:
        start, end = get_preset_range(preset)
    
    return datetime_to_millis(start), datetime_to_millis(end)


def format_time_range(start_millis: int, end_millis: int) -> dict:
    """
    Format time range for display.
    
    Returns:
        Dict with formatted start and end times
    """
    start = millis_to_datetime(start_millis)
    end = millis_to_datetime(end_millis)
    
    return {
        "start": start.strftime('%Y-%m-%d %H:%M'),
        "end": end.strftime('%Y-%m-%d %H:%M'),
        "start_date": start.strftime('%Y-%m-%d'),
        "end_date": end.strftime('%Y-%m-%d')
    }


def get_iso_range(start_millis: int, end_millis: int) -> Tuple[str, str]:
    """
    Get ISO formatted time range for APIs that require it (e.g., Strava).
    
    Returns:
        Tuple of (start_iso, end_iso)
    """
    start = millis_to_datetime(start_millis)
    end = millis_to_datetime(end_millis)
    
    return start.isoformat() + "Z", end.isoformat() + "Z"


def get_unix_timestamps(start_millis: int, end_millis: int) -> Tuple[int, int]:
    """
    Get Unix timestamps (seconds) for APIs that require it (e.g., Strava).
    
    Returns:
        Tuple of (start_epoch, end_epoch)
    """
    return start_millis // 1000, end_millis // 1000
