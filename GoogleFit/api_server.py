"""
Flask API Server for Health Dashboard
Provides REST API endpoints for the React frontend to fetch Google Fit and Strava data.

Run with: python api_server.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import traceback

# Import existing fetchers
from google_fit_api import get_fitness_service, fetch_all_fitness_data
from strava_fetcher import fetch_all_strava_data
from time_utils import get_time_range_millis
from auth import is_strava_configured

app = Flask(__name__)
CORS(app)  # Enable CORS for React dev server


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_time_range_from_request():
    """
    Extract time range from request parameters.
    
    Expected params:
    - range_type: 'today', 'yesterday', 'last_7_days', 'last_30_days', 'this_week', 'this_month'
    - OR custom_start and custom_end (ISO format)
    
    Returns:
        tuple: (start_millis, end_millis)
    """
    range_type = request.args.get('range_type', 'today')
    
    # Handle custom range
    if range_type == 'custom':
        try:
            custom_start = request.args.get('start')
            custom_end = request.args.get('end')
            
            start_dt = datetime.fromisoformat(custom_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(custom_end.replace('Z', '+00:00'))
            
            start_millis = int(start_dt.timestamp() * 1000)
            end_millis = int(end_dt.timestamp() * 1000)
            
            return start_millis, end_millis
        except:
            range_type = 'today'  # Fallback
    
    # Handle presets
    now = datetime.now()
    
    if range_type == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    elif range_type == 'yesterday':
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    elif range_type == 'last_7_days':
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    elif range_type == 'last_30_days':
        start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    elif range_type == 'this_week':
        # Monday to Sunday
        day_of_week = now.weekday()
        start = (now - timedelta(days=day_of_week)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
    
    elif range_type == 'this_month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Last day of month
        next_month = start.replace(day=28) + timedelta(days=4)
        end = (next_month - timedelta(days=next_month.day)).replace(hour=23, minute=59, second=59, microsecond=999999)
    
    else:
        # Default to today
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    start_millis = int(start.timestamp() * 1000)
    end_millis = int(end.timestamp() * 1000)
    
    return start_millis, end_millis


def calculate_distance_km(steps, avg_stride_meters=0.762):
    """Estimate distance from steps (if not directly available)."""
    if not steps:
        return None
    return round((steps * avg_stride_meters) / 1000, 2)


def format_activity_segments(activities_dict):
    """Convert activities dict to activity segments format."""
    if not activities_dict:
        return []
    
    # Map activity types to more readable names
    activity_mapping = {
        'walking': 'Walking',
        'running': 'Running',
        'biking': 'Cycling',
        'hiking': 'Hiking',
        'yoga': 'Yoga',
        'swimming': 'Swimming',
        'strength_training': 'Strength Training',
        'gym_workout': 'Gym Workout',
        'meditation': 'Meditation'
    }
    
    segments = []
    for activity_name, count in activities_dict.items():
        display_name = activity_mapping.get(activity_name, activity_name.replace('_', ' ').title())
        segments.append({
            'type': display_name,
            'duration': f'{count}x',
            'calories': '—',
            'time': 'Today'
        })
    
    return segments


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/google-fit', methods=['GET'])
def get_google_fit_data():
    """
    Fetch Google Fit data for specified time range.
    
    Query params:
    - range_type: today|yesterday|last_7_days|last_30_days|this_week|this_month
    """
    try:
        start_millis, end_millis = get_time_range_from_request()
        
        # Get Google Fit service and fetch data
        service = get_fitness_service()
        
        # Fetch all data — pass millis directly so custom ranges work correctly
        raw_data = fetch_all_fitness_data(service, start_millis=start_millis, end_millis=end_millis)
        
        # Normalize to dashboard format
        steps = raw_data.get('steps')
        active_minutes = raw_data.get('active_minutes')
        calories = raw_data.get('calories')
        sleep_hours = raw_data.get('sleep_hours')
        activities = raw_data.get('activities', [])
        
        # Calculate distance (if not available, estimate from steps)
        distance = calculate_distance_km(steps) if steps else None
        
        # Convert activities list to dict for compatibility
        activities_dict = {}
        if isinstance(activities, list):
            for activity in activities:
                activities_dict[activity] = activities_dict.get(activity, 0) + 1
        
        response_data = {
            'steps': {
                'value': steps or 0,
                'unit': 'steps',
                'label': 'Steps Today',
                'goal': 10000,
                'percentage': min(100, int((steps or 0) / 100)) if steps else 0
            },
            'activeMinutes': {
                'value': active_minutes or 0,
                'unit': 'min',
                'label': 'Active Minutes',
                'goal': 60,
                'percentage': min(100, int((active_minutes or 0) / 60 * 100)) if active_minutes else 0
            },
            'calories': {
                'value': calories or 0,
                'unit': 'kcal',
                'label': 'Calories Burned',
                'goal': 2500,
                'percentage': min(100, int((calories or 0) / 2500 * 100)) if calories else 0
            },
            'distance': {
                'value': distance or 0,
                'unit': 'km',
                'label': 'Distance Covered',
                'goal': 8,
                'percentage': min(100, int((distance or 0) / 8 * 100)) if distance else 0
            },
            'sleep': {
                'value': sleep_hours or 0,
                'unit': 'hrs',
                'label': 'Sleep Duration',
                'goal': 8,
                'percentage': min(100, int((sleep_hours or 0) / 8 * 100)) if sleep_hours else 0,
                'stages': raw_data.get('sleep_stages')  # deep / light / rem / generic hours
            },
            'activitySegments': format_activity_segments(activities_dict),
            'timestamp': datetime.now().isoformat(),
            'timeRange': raw_data.get('time_range', {})
        }
        
        return jsonify(response_data)
    
    except FileNotFoundError as e:
        return jsonify({
            'error': 'Google Fit not configured',
            'message': str(e),
            'configured': False
        }), 401
    
    except Exception as e:
        print(f"Error fetching Google Fit data: {e}")
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to fetch Google Fit data',
            'message': str(e)
        }), 500


@app.route('/api/strava', methods=['GET'])
def get_strava_data():
    """
    Fetch Strava data for specified time range.
    
    Query params:
    - range_type: today|yesterday|last_7_days|last_30_days|this_week|this_month
    """
    try:
        # Check if Strava is configured
        if not is_strava_configured():
            return jsonify({
                'error': 'Strava not configured',
                'message': 'Add Strava credentials to .env file',
                'configured': False
            }), 401
        
        start_millis, end_millis = get_time_range_from_request()
        
        # Fetch Strava data
        raw_data = fetch_all_strava_data(start_millis, end_millis)
        
        if not raw_data.get('configured'):
            return jsonify({
                'error': 'Strava not configured',
                'configured': False
            }), 401
        
        summary = raw_data.get('summary', {})
        activities = raw_data.get('activities', [])
        
        # Normalize to dashboard format
        response_data = {
            'activities': {
                'value': summary.get('total_activities', 0),
                'unit': 'activities',
                'label': 'This Period',
                'change': f"+{summary.get('total_activities', 0)}"
            },
            'distance': {
                'value': summary.get('total_distance_km', 0),
                'unit': 'km',
                'label': 'Total Distance',
                'change': f"+{summary.get('total_distance_km', 0)} km"
            },
            'duration': {
                'value': round(summary.get('total_duration_min', 0) / 60, 1),
                'unit': 'hrs',
                'label': 'Total Duration',
                'change': f"+{round(summary.get('total_duration_min', 0) / 60, 1)} hrs"
            },
            'calories': {
                'value': summary.get('total_calories', 0),
                'unit': 'kcal',
                'label': 'Calories Burned',
                'change': f"+{summary.get('total_calories', 0)} kcal"
            },
            'recentActivities': [
                {
                    'id': i + 1,
                    'name': activity.get('name', 'Untitled'),
                    'type': activity.get('type', 'Unknown'),
                    'distance': f"{activity.get('distance_km', 0)} km",
                    'duration': f"{int(activity.get('duration_min', 0))} min",
                    'pace': f"{activity.get('distance_km', 0) / (activity.get('duration_min', 1) / 60):.1f} km/h" if activity.get('duration_min', 0) > 0 else '—',
                    'calories': activity.get('calories') or 0,
                    'time': activity.get('date', '—')
                }
                for i, activity in enumerate(activities[:10])
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Error fetching Strava data: {e}")
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to fetch Strava data',
            'message': str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Check which APIs are configured."""
    return jsonify({
        'google_fit': {
            'configured': True,  # Google Fit is always available if token exists
            'status': 'ready'
        },
        'strava': {
            'configured': is_strava_configured(),
            'status': 'ready' if is_strava_configured() else 'not_configured'
        }
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🏥 Health Dashboard API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET /api/health         - Health check")
    print("  GET /api/status         - Check API configuration")
    print("  GET /api/google-fit     - Fetch Google Fit data")
    print("  GET /api/strava         - Fetch Strava data")
    print("\nQuery Parameters:")
    print("  range_type: today | yesterday | last_7_days | last_30_days | this_week | this_month")
    print("\nStarting server on http://localhost:5000")
    print("=" * 60)
    print()
    
    app.run(debug=True, port=5000, host='0.0.0.0')
