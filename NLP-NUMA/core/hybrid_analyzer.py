"""
Hybrid Workout Analyzer
Combines NLP (text analysis) + Rule-based (numeric analysis)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from workout_analyzer import WorkoutAnalyzer
from pathlib import Path
import json


class HybridWorkoutAnalyzer:
    """Combines text NLP analysis with numeric metric analysis"""
    
    def __init__(self):
        print("Loading NLP models...")
        self.nlp_analyzer = WorkoutAnalyzer()
        print("Hybrid analyzer ready!\n")
    
    def analyze_complete_workout(self, workout_data):
        """
        Complete workout analysis using both text and numeric data
        
        Args:
            workout_data: dict with keys like:
                - description (str): User-written text
                - distance (float): meters
                - moving_time (float): seconds
                - average_heartrate (int): bpm
                - sleep_hours (float): hours of sleep
                - baseline_hr (int): user's normal resting HR
                - baseline_pace (float): user's typical pace (min/km)
        
        Returns:
            Complete analysis with NLP + numeric + combined insights
        """
        
        description = workout_data.get('description', '').strip()
        
        # Initialize result structure
        result = {
            'has_text': bool(description),
            'text_analysis': None,
            'numeric_analysis': None,
            'combined_insights': [],
            'recommendations': [],
            'alerts': []
        }
        
        # 1. NUMERIC ANALYSIS (always available)
        result['numeric_analysis'] = self._analyze_numeric_metrics(workout_data)
        
        # 2. TEXT ANALYSIS (if available)
        if description:
            result['text_analysis'] = self.nlp_analyzer.analyze(description)
        
        # 3. COMBINED INSIGHTS (validate and cross-reference)
        result['combined_insights'] = self._combine_analyses(
            text=result['text_analysis'],
            numeric=result['numeric_analysis'],
            workout_data=workout_data
        )
        
        # 4. GENERATE RECOMMENDATIONS
        result['recommendations'] = self._generate_recommendations(result)
        
        # 5. CRITICAL ALERTS
        result['alerts'] = self._generate_alerts(result)
        
        return result
    
    
    def _analyze_numeric_metrics(self, workout_data):
        """Analyze numeric workout metrics using rules"""
        
        # Extract metrics
        distance = workout_data.get('distance', 0)  # meters
        duration = workout_data.get('moving_time', 0)  # seconds
        avg_hr = workout_data.get('average_heartrate', 0)
        sleep_hours = workout_data.get('sleep_hours', 7)
        
        # User baselines (would come from historical data)
        baseline_hr = workout_data.get('baseline_hr', 145)
        baseline_pace = workout_data.get('baseline_pace', 6.0)  # min/km
        
        # Calculate derived metrics
        distance_km = distance / 1000 if distance > 0 else 0
        duration_min = duration / 60 if duration > 0 else 0
        pace_min_per_km = duration_min / distance_km if distance_km > 0 else 0
        
        # Analyze performance
        hr_elevated = avg_hr > baseline_hr * 1.1
        hr_very_high = avg_hr > baseline_hr * 1.2
        pace_slow = pace_min_per_km > baseline_pace * 1.15
        pace_very_slow = pace_min_per_km > baseline_pace * 1.3
        pace_fast = pace_min_per_km < baseline_pace * 0.9
        
        poor_sleep = sleep_hours < 6.5
        very_poor_sleep = sleep_hours < 5.5
        
        # Determine overall numeric sentiment
        if hr_very_high and pace_very_slow:
            numeric_sentiment = 'struggling'
        elif hr_elevated and pace_slow:
            numeric_sentiment = 'challenging'
        elif not hr_elevated and pace_fast:
            numeric_sentiment = 'performing_well'
        else:
            numeric_sentiment = 'normal'
        
        return {
            'metrics': {
                'distance_km': round(distance_km, 2),
                'duration_min': round(duration_min, 1),
                'pace_min_per_km': round(pace_min_per_km, 2),
                'avg_hr': avg_hr,
                'sleep_hours': sleep_hours
            },
            'flags': {
                'hr_elevated': hr_elevated,
                'hr_very_high': hr_very_high,
                'pace_slow': pace_slow,
                'pace_very_slow': pace_very_slow,
                'pace_fast': pace_fast,
                'poor_sleep': poor_sleep,
                'very_poor_sleep': very_poor_sleep
            },
            'numeric_sentiment': numeric_sentiment
        }
    
    
    def _combine_analyses(self, text, numeric, workout_data):
        """Cross-validate and combine text + numeric analyses"""
        
        insights = []
        
        # CASE 1: No text - rely on numeric only
        if not text:
            insights.append({
                'type': 'numeric_only',
                'confidence': 'medium',
                'message': f"Analysis based on metrics only: {numeric['numeric_sentiment']}"
            })
            return insights
        
        # CASE 2: Both text and numeric available - VALIDATE
        
        text_sentiment = text['sentiment']['sentiment']
        text_performance = text['performance']['performance']
        numeric_sentiment = numeric['numeric_sentiment']
        
        # VALIDATION 1: Text + Numeric agree
        if text_sentiment == 'negative' and numeric_sentiment in ['struggling', 'challenging']:
            insights.append({
                'type': 'confirmed_struggle',
                'confidence': 'very_high',
                'message': 'Negative sentiment confirmed by elevated HR and slow pace',
                'text_sentiment': text_sentiment,
                'numeric_sentiment': numeric_sentiment
            })
        
        if text_sentiment == 'positive' and numeric_sentiment == 'performing_well':
            insights.append({
                'type': 'confirmed_success',
                'confidence': 'very_high',
                'message': 'Positive sentiment confirmed by strong metrics',
                'text_sentiment': text_sentiment,
                'numeric_sentiment': numeric_sentiment
            })
        
        # VALIDATION 2: Contradiction - Flag for attention
        if text_sentiment == 'positive' and numeric_sentiment == 'struggling':
            insights.append({
                'type': 'contradiction_warning',
                'confidence': 'high',
                'message': 'Positive text but struggling metrics - possible overconfidence or delayed fatigue',
                'text_sentiment': text_sentiment,
                'numeric_sentiment': numeric_sentiment
            })
        
        if text_sentiment == 'negative' and numeric_sentiment == 'performing_well':
            insights.append({
                'type': 'mental_barrier',
                'confidence': 'high',
                'message': 'Good metrics but negative sentiment - possible mental/motivation issue',
                'text_sentiment': text_sentiment,
                'numeric_sentiment': numeric_sentiment
            })
        
        # VALIDATION 3: Injury mentions + slow pace
        if text['entities']:
            body_parts = [e['text'] for e in text['entities'] if e['label'] == 'BODY_PART']
            symptoms = [e['text'] for e in text['entities'] if e['label'] == 'SYMPTOM']
            
            if body_parts and numeric['flags']['pace_slow']:
                insights.append({
                    'type': 'injury_performance_correlation',
                    'confidence': 'very_high',
                    'message': f"Slow pace explained by {', '.join(body_parts)} issue with {', '.join(symptoms) if symptoms else 'discomfort'}",
                    'body_parts': body_parts,
                    'symptoms': symptoms
                })
            
            if body_parts and not numeric['flags']['pace_slow']:
                insights.append({
                    'type': 'injury_mention_without_impact',
                    'confidence': 'medium',
                    'message': f"Mentioned {', '.join(body_parts)} but maintained normal pace - monitor closely",
                    'body_parts': body_parts
                })
        
        # VALIDATION 4: Sleep impact
        if numeric['flags']['poor_sleep'] and text_performance == 'struggle':
            insights.append({
                'type': 'sleep_performance_link',
                'confidence': 'high',
                'message': f"Poor sleep ({numeric['metrics']['sleep_hours']}h) likely contributed to struggle",
                'sleep_hours': numeric['metrics']['sleep_hours']
            })
        
        # VALIDATION 5: Overtraining risk
        if (numeric['flags']['hr_very_high'] and 
            numeric['flags']['pace_slow'] and 
            text_sentiment == 'negative'):
            insights.append({
                'type': 'overtraining_risk',
                'confidence': 'very_high',
                'message': 'Multiple overtraining indicators: high HR, slow pace, negative sentiment',
                'avg_hr': numeric['metrics']['avg_hr'],
                'pace': numeric['metrics']['pace_min_per_km']
            })
        
        return insights
    
    
    def _generate_recommendations(self, analysis):
        """Generate actionable recommendations"""
        
        recommendations = []
        
        numeric = analysis['numeric_analysis']
        insights = analysis['combined_insights']
        
        # Check for overtraining
        overtraining = any(i['type'] == 'overtraining_risk' for i in insights)
        if overtraining:
            recommendations.append({
                'priority': 'high',
                'action': 'Take a rest day or do light recovery activity',
                'reason': 'Signs of overtraining detected'
            })
        
        # Check for injury mentions
        injury_mentions = [i for i in insights if 'injury' in i['type']]
        if injury_mentions:
            recommendations.append({
                'priority': 'high',
                'action': 'Monitor body parts mentioned and consider seeing a physio if pain persists',
                'reason': f"Injury concerns mentioned: {injury_mentions[0].get('body_parts', [])}"
            })
        
        # Check for sleep
        if numeric['flags']['very_poor_sleep']:
            recommendations.append({
                'priority': 'medium',
                'action': 'Prioritize 7-9 hours of sleep tonight',
                'reason': f"Only {numeric['metrics']['sleep_hours']} hours of sleep"
            })
        
        # Positive performance
        performing_well = any(i['type'] == 'confirmed_success' for i in insights)
        if performing_well:
            recommendations.append({
                'priority': 'low',
                'action': 'Great workout! Consider gradually increasing intensity',
                'reason': 'Strong performance indicators'
            })
        
        return recommendations
    
    
    def _generate_alerts(self, analysis):
        """Generate critical alerts that need immediate attention"""
        
        alerts = []
        insights = analysis['combined_insights']
        
        # Critical: Overtraining
        if any(i['type'] == 'overtraining_risk' for i in insights):
            alerts.append({
                'severity': 'critical',
                'message': '⚠️ OVERTRAINING RISK - Rest recommended'
            })
        
        # Warning: Injury correlation
        injury_corr = [i for i in insights if i['type'] == 'injury_performance_correlation']
        if injury_corr:
            alerts.append({
                'severity': 'warning',
                'message': f"⚠️ Injury impact detected: {injury_corr[0].get('body_parts', [])}"
            })
        
        # Info: Contradiction
        contradictions = [i for i in insights if 'contradiction' in i['type'] or 'mental_barrier' in i['type']]
        if contradictions:
            alerts.append({
                'severity': 'info',
                'message': 'ℹ️ Text and metrics show different signals - review workout context'
            })
        
        return alerts


# ============================================================================
# DEMO / TESTING
# ============================================================================

def demo():
    """Demo the hybrid analyzer"""
    
    analyzer = HybridWorkoutAnalyzer()
    
    # Test cases
    test_workouts = [
        {
            'name': 'Case 1: Struggling workout with text',
            'data': {
                'description': 'Struggled with the hills, knees felt sore and painful',
                'distance': 8000,
                'moving_time': 3600,  # 7:30/km - very slow
                'average_heartrate': 172,
                'sleep_hours': 5.5,
                'baseline_hr': 145,
                'baseline_pace': 5.5
            }
        },
        {
            'name': 'Case 2: Good workout with text',
            'data': {
                'description': 'PR on 10K! Felt amazing, perfect weather',
                'distance': 10000,
                'moving_time': 2700,  # 4:30/km - fast
                'average_heartrate': 155,
                'sleep_hours': 8.0,
                'baseline_hr': 145,
                'baseline_pace': 5.5
            }
        },
        {
            'name': 'Case 3: No text, only metrics (struggling)',
            'data': {
                'description': '',  # No text!
                'distance': 5000,
                'moving_time': 2100,  # 7:00/km - slow
                'average_heartrate': 175,
                'sleep_hours': 6.0,
                'baseline_hr': 145,
                'baseline_pace': 5.5
            }
        },
        {
            'name': 'Case 4: Contradiction - positive text but bad metrics',
            'data': {
                'description': 'Felt great today!',
                'distance': 5000,
                'moving_time': 2100,  # Slow
                'average_heartrate': 175,  # High
                'sleep_hours': 5.0,
                'baseline_hr': 145,
                'baseline_pace': 5.5
            }
        }
    ]
    
    # Analyze each
    for i, test in enumerate(test_workouts, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}: {test['name']}")
        print('='*80)
        
        result = analyzer.analyze_complete_workout(test['data'])
        
        # Print results
        print(f"\n📊 NUMERIC METRICS:")
        metrics = result['numeric_analysis']['metrics']
        print(f"   Distance: {metrics['distance_km']} km")
        print(f"   Pace: {metrics['pace_min_per_km']} min/km")
        print(f"   Avg HR: {metrics['avg_hr']} bpm")
        print(f"   Sleep: {metrics['sleep_hours']} hours")
        print(f"   Numeric Sentiment: {result['numeric_analysis']['numeric_sentiment']}")
        
        if result['text_analysis']:
            print(f"\n📝 TEXT ANALYSIS:")
            print(f"   Text: {result['text_analysis']['text']}")
            print(f"   Sentiment: {result['text_analysis']['sentiment']['sentiment']} ({result['text_analysis']['sentiment']['confidence']:.2%})")
            print(f"   Performance: {result['text_analysis']['performance']['performance']}")
            if result['text_analysis']['entities']:
                print(f"   Entities: {[(e['text'], e['label']) for e in result['text_analysis']['entities']]}")
        
        print(f"\n🔍 COMBINED INSIGHTS:")
        for insight in result['combined_insights']:
            print(f"   [{insight['type'].upper()}] ({insight['confidence']} confidence)")
            print(f"      {insight['message']}")
        
        if result['alerts']:
            print(f"\n🚨 ALERTS:")
            for alert in result['alerts']:
                print(f"   {alert['message']}")
        
        if result['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in result['recommendations']:
                print(f"   [{rec['priority'].upper()}] {rec['action']}")
                print(f"      Reason: {rec['reason']}")
    
    print(f"\n{'='*80}")
    print("Demo complete!")


if __name__ == "__main__":
    demo()