"""
Quick test to verify all models load correctly after path changes
"""

from pathlib import Path
import sys

# Add parent directory to path so we can import from core
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_model_loading():
    """Test if all models load without errors"""
    
    print("="*80)
    print("TESTING MODEL LOADING AFTER PATH CHANGES")
    print("="*80)
    
    # Test 1: Workout Analyzer (loads 3 models)
    print("\n1. Testing Workout Analyzer...")
    try:
        from core.workout_analyzer import WorkoutAnalyzer
        analyzer = WorkoutAnalyzer()
        print("   ✅ SUCCESS - All 3 models loaded (sentiment, NER, classifier)")
    except Exception as e:
        print(f"   ❌ FAILED - {str(e)}")
        return False
    
    # Test 2: Test a sample analysis
    print("\n2. Testing sample workout analysis...")
    try:
        result = analyzer.analyze("Great 10K run today! Felt strong.")
        print(f"   ✅ SUCCESS - Sentiment: {result['sentiment']['sentiment']}")
        print(f"                Performance: {result['performance']['performance']}")
    except Exception as e:
        print(f"   ❌ FAILED - {str(e)}")
        return False
    
    # Test 3: Unified Analyzer (loads all models + daily productivity)
    print("\n3. Testing Unified Analyzer...")
    try:
        from core.unified_analyzer import UnifiedAnalyzer
        unified = UnifiedAnalyzer()
        print("   ✅ SUCCESS - All models loaded (workout NLP + daily productivity)")
    except Exception as e:
        print(f"   ❌ FAILED - {str(e)}")
        return False
    
    # Test 4: Test complete day analysis
    print("\n4. Testing complete day analysis...")
    try:
        test_data = {
            'workout_description': 'Struggled with hills',
            'meetings': 5,
            'messages': 80,
            'commits': 2,
            'sleep': 6.0,
            'workout_minutes': 30,
            'journal': 'tired day'
        }
        result = unified.analyze_complete_day(test_data)
        print(f"   ✅ SUCCESS - Daily State: {result['daily_analysis']['daily_state']}")
    except Exception as e:
        print(f"   ❌ FAILED - {str(e)}")
        return False
    
    # Test 5: NLG
    print("\n5. Testing NLG (workout text generation)...")
    try:
        from core.workout_nlg import generate_workout_text
        nlg_text = generate_workout_text({
            'distance_km': 5.0,
            'pace': 6.0,
            'avg_heart_rate': 160,
            'sleep': 7.0
        })
        print(f"   ✅ SUCCESS - Generated: {nlg_text[:50]}...")
    except Exception as e:
        print(f"   ❌ FAILED - {str(e)}")
        return False
    
    # Test 6: Hybrid Analyzer
    print("\n6. Testing Hybrid Analyzer...")
    try:
        from core.hybrid_analyzer import HybridWorkoutAnalyzer
        hybrid = HybridWorkoutAnalyzer()
        print("   ✅ SUCCESS - Hybrid analyzer loaded")
    except Exception as e:
        print(f"   ❌ FAILED - {str(e)}")
        return False
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - Models are working correctly!")
    print("="*80)
    return True


if __name__ == "__main__":
    success = test_model_loading()
    if not success:
        print("\n❌ SOME TESTS FAILED - Check the errors above")
        sys.exit(1)