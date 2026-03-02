"""
Test with your own custom data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.unified_analyzer import UnifiedAnalyzer

analyzer = UnifiedAnalyzer()

# YOUR CUSTOM TEST DATA
my_day = {
    'workout_description': 'Had an amazing 5K run today!',
    'distance_km': 5.0,
    'pace': 5.0,
    'avg_heart_rate': 155,
    'sleep': 8.0,
    'meetings': 3,
    'meeting_hours': 2.0,
    'messages': 40,
    'commits': 6,
    'journal': 'Productive day with great energy'
}

result = analyzer.analyze_complete_day(my_day)

print("\n" + "="*80)
print("MY CUSTOM TEST")
print("="*80)

if result['workout_analysis']:
    w = result['workout_analysis']
    print(f"\nWorkout Sentiment: {w['sentiment']['sentiment']}")
    print(f"Performance: {w['performance']['performance']}")

d = result['daily_analysis']
print(f"\nDaily State: {d['daily_state']}")
print(f"Burnout Risk: {d['burnout_risk']:.2f} ({d['risk_level']})")

if result['recommendations']:
    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  - {rec['action']}")