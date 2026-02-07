"""
API Package - Strava and Google Fit Integration

This package provides clean, object-oriented interfaces for:
- Strava API: Activity tracking and fitness data
- Google Fit API: Comprehensive health and fitness metrics

Usage:
    from api.strava_api import StravaAPI
    from api.google_fit_api import GoogleFitAPI
"""

from .strava_api import StravaAPI
from .google_fit_api import GoogleFitAPI

__all__ = ['StravaAPI', 'GoogleFitAPI']
