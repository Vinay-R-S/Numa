"""
Test NLG Integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from unified_analyzer import UnifiedAnalyzer


def main():
    print("="*80)
    print("NLG INTEGRATION TEST")
    print("="*80)
    
    analyzer = UnifiedAnalyzer()
    
    # Test 1: User provides text (original behavior)
    print("\n" + "="*80)
    print("TEST 1: User-Written Text (No NLG)")
    print("="*80)
    
    test1 = {
        'workout_description': 'Struggled with hills, knees hurt badly',
        'meetings': 5,
        'meeting_hours': 4.0,
        'messages': 80,
        'commits': 2,
        'sleep': 5.5,
        'workout_minutes': 30,
        'journal': 'felt exhausted'
    }
    
    result1 = analyzer.analyze_complete_day(test1)
    
    print(f"\nText Source: {result1.get('text_source', 'N/A')}")
    if result1['workout_analysis']:
        w = result1['workout_analysis']
        print(f"Text Used: \"{w['text']}\"")
        print(f"Sentiment: {w['sentiment']['sentiment']} ({w['sentiment']['confidence']:.1%})")
        print(f"Performance: {w['performance']['performance']}")
    print(f"\nDaily State: {result1['daily_analysis']['daily_state']}")
    print(f"Burnout Risk: {result1['daily_analysis']['burnout_risk']:.2f}")
    # Test 2: No user text - NLG generates from metrics
    print("\n" + "="*80)
    print("TEST 2: No User Text → NLG Generation")
    print("="*80)
    
    test2 = {
        'workout_description': 'knees hurt very bad, everything because of trekking for 10kms',  # EMPTY - triggers NLG!
        'distance_km': 10.0,
        'duration_min': 180.0,
        'avg_heart_rate': 175,
        'max_heart_rate': 185,
        'pace': 8.0,
        'sleep': 5.0,
        'baseline_hr': 145,
        'baseline_pace': 5.5,
        'meetings': 0,
        'meeting_hours': 0,
        'messages': 10,
        'commits': 0,
        'journal': 'Although I did struggle all the bones in my body, still the satisfaction of being on top of the mountain was something else, Felt so good watching the sunrise, One of the best days of my entire life'
    }
    
    result2 = analyzer.analyze_complete_day(test2)
    
    print(f"\nText Source: {result2.get('text_source', 'N/A')}")
    if result2['workout_analysis']:
        w = result2['workout_analysis']
        print(f"NLG Generated Text: \"{w['text']}\"")
        print(f"Sentiment: {w['sentiment']['sentiment']} ({w['sentiment']['confidence']:.1%})")
        print(f"Performance: {w['performance']['performance']}")
    
    print(f"\nDaily State: {result2['daily_analysis']['daily_state']}")
    print(f"Burnout Risk: {result2['daily_analysis']['burnout_risk']:.2f}")
    
    # Test 3: Good performance with NLG
    print("\n" + "="*80)
    print("TEST 3: Strong Performance → NLG Generation")
    print("="*80)
    
    test3 = {
        'workout_description': '',  # EMPTY
        'distance_km': 10.0,
        'duration_min': 45.0,
        'avg_heart_rate': 155,
        'pace': 4.5,
        'sleep': 8.0,
        'baseline_hr': 145,
        'baseline_pace': 5.5,
        'meetings': 2,
        'meeting_hours': 1.5,
        'messages': 30,
        'commits': 7,
        'journal': 'I love my day, I won a lottery today and I won Tammanah Battia as gift, now I can have her all for myself'
    }
    
    result3 = analyzer.analyze_complete_day(test3)
    
    print(f"\nText Source: {result3.get('text_source', 'N/A')}")
    if result3['workout_analysis']:
        w = result3['workout_analysis']
        print(f"NLG Generated Text: \"{w['text']}\"")
        print(f"Sentiment: {w['sentiment']['sentiment']} ({w['sentiment']['confidence']:.1%})")
        print(f"Performance: {w['performance']['performance']}")
    # ADD THIS:
    print(f"\nDaily State: {result3['daily_analysis']['daily_state']}")
    print(f"Burnout Risk: {result3['daily_analysis']['burnout_risk']:.2f}")

    print("\n" + "="*80)
    print("✓ NLG Integration Complete!")
    print("="*80)


if __name__ == "__main__":
    main()