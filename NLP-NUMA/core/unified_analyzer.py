"""
Unified Analyzer - Combines Workout NLP + Daily Productivity Analysis
"""
import sys
from pathlib import Path
# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent))
from workout_nlg import generate_workout_text
import json
import torch
import spacy
import pickle
import joblib
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')


class UnifiedAnalyzer:
    """Complete analysis combining workout text NLP + daily productivity classification"""
    
    def __init__(self):
        script_dir = Path(__file__).parent.parent
        
        print("Loading unified analyzer...")
        print("\n1. Loading workout NLP models...")
        
        # Workout NLP models
        sentiment_path = script_dir / 'models' /'sentiment_model'
        ner_path = script_dir / 'models' / 'ner_model'
        classifier_path = script_dir / 'models' / 'workout_classifier' / 'performance'
        encoders_path = script_dir / 'models' / 'workout_classifier' / 'label_encoders.pkl'
        
        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(str(sentiment_path))
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(str(sentiment_path))
        self.sentiment_model.eval()
        
        self.ner_model = spacy.load(str(ner_path))
        
        self.classifier_tokenizer = AutoTokenizer.from_pretrained(str(classifier_path))
        self.classifier_model = AutoModelForSequenceClassification.from_pretrained(str(classifier_path))
        self.classifier_model.eval()
        
        with open(encoders_path, 'rb') as f:
            self.label_encoders = pickle.load(f)
        
        print("   ✓ Sentiment model loaded")
        print("   ✓ NER model loaded")
        print("   ✓ Performance classifier loaded")
        
        # Daily productivity model
        print("\n2. Loading daily productivity model...")
        daily_model_dir = script_dir / 'models' / 'daily_productivity_model'
        
        self.daily_classifier = joblib.load(daily_model_dir / 'productivity_classifier.pkl')
        self.tfidf_vectorizer = joblib.load(daily_model_dir / 'tfidf_vectorizer.pkl')
        
        print("   ✓ TF-IDF vectorizer loaded")
        print("   ✓ Logistic regression loaded")
        
        print("\n✓ Unified analyzer ready!\n")
    
    
    # ==================== WORKOUT NLP ANALYSIS ====================
    
    def analyze_workout_text(self, text: str) -> Dict:
        """Analyze workout description using NLP models"""
        if not text or not text.strip():
            return None
        
        # Sentiment
        inputs = self.sentiment_tokenizer(
            text, return_tensors='pt', max_length=128,
            padding='max_length', truncation=True
        )
        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)[0]
            pred = torch.argmax(logits, dim=1).item()
        
        id_to_label = {0: 'positive', 1: 'neutral', 2: 'negative'}
        sentiment = {
            'sentiment': id_to_label[pred],
            'confidence': float(probs[pred]),
            'scores': {
                'positive': float(probs[0]),
                'neutral': float(probs[1]),
                'negative': float(probs[2])
            }
        }
        
        # Entities
        doc = self.ner_model(text)
        entities = [
            {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            }
            for ent in doc.ents
        ]
        
        # Performance
        inputs = self.classifier_tokenizer(
            text, return_tensors='pt', max_length=128,
            padding='max_length', truncation=True
        )
        with torch.no_grad():
            outputs = self.classifier_model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)[0]
            pred = torch.argmax(logits, dim=1).item()
        
        performance = {
            'performance': self.label_encoders['performance'].inverse_transform([pred])[0],
            'confidence': float(probs[pred])
        }
        
        return {
            'text': text,
            'sentiment': sentiment,
            'performance': performance,
            'entities': entities
        }
    
    
    # ==================== DAILY PRODUCTIVITY ANALYSIS ====================
    
    def analyze_daily_summary(self, daily_text: str) -> Dict:
        """Analyze daily summary using TF-IDF + LogReg"""
        
        # Vectorize
        text_vec = self.tfidf_vectorizer.transform([daily_text])
        
        # Predict
        prediction = self.daily_classifier.predict(text_vec)[0]
        probs = self.daily_classifier.predict_proba(text_vec)[0]
        
        # Build probability dict
        prob_dict = dict(zip(self.daily_classifier.classes_, probs))
        
        # Burnout risk
        burnout_risk = self._compute_burnout_risk(prob_dict)
        risk_level = self._interpret_risk(burnout_risk)
        
        return {
            'daily_state': prediction,
            'confidence': float(max(probs)),
            'probabilities': {k: float(v) for k, v in prob_dict.items()},
            'burnout_risk': burnout_risk,
            'risk_level': risk_level
        }
    
    
    def _compute_burnout_risk(self, prob_dict):
        """Calculate burnout risk score"""
        p_over = prob_dict.get("Overloaded", 0.0)
        p_dist = prob_dict.get("Distracted", 0.0)
        return p_over + 0.5 * p_dist
    
    
    def _interpret_risk(self, risk_score):
        """Interpret risk level"""
        if risk_score > 0.7:
            return "HIGH"
        elif risk_score > 0.4:
            return "MODERATE"
        else:
            return "LOW"
    
    
    # ==================== UNIFIED ANALYSIS ====================
    
    def analyze_complete_day(self, data: Dict) -> Dict:
        """
        Complete day analysis combining workout + daily productivity
        
        Input data format:
        {
            'workout_description': "Struggled with hills, knees hurt",
            'meetings': 6,
            'meeting_hours': 5.5,
            'messages': 120,
            'commits': 0,
            'sleep': 4.5,
            'workout_minutes': 20,
            'journal': "felt overwhelmed and exhausted"
        }
        """
        
        result = {
            'has_workout_text': False,
            'workout_analysis': None,
            'daily_analysis': None,
            'unified_insights': [],
            'recommendations': []
        }
        ## start


        ## start

                # 1. Workout text analysis
        user_text = data.get('workout_description', '').strip()
        journal_text = data.get('journal', '').strip()

        # ALWAYS generate NLG from metrics
        workout_metrics = {
            'distance_km': data.get('distance_km', 0),
            'duration_min': data.get('duration_min', 0),
            'avg_heart_rate': data.get('avg_heart_rate', 0),
            'max_heart_rate': data.get('max_heart_rate', 0),
            'elevation_gain': data.get('elevation_gain', 0),
            'pace': data.get('pace', 0),
            'sleep': data.get('sleep', 7),
            'baseline_hr': data.get('baseline_hr', 145),
            'baseline_pace': data.get('baseline_pace', 5.5)
        }

        nlg_text = generate_workout_text(workout_metrics)

        # Build complete workout text: user text + NLG + journal
        text_parts = []

        if user_text:
            text_parts.append(user_text)
            
        if nlg_text:
            text_parts.append(nlg_text)
            
        if journal_text:
            text_parts.append(f"Personal reflection: {journal_text}")

        # Combine all parts
        workout_text = ". ".join(text_parts) if text_parts else ""

        # Set source tracking
        if user_text and nlg_text and journal_text:
            result['text_source'] = 'user_nlg_journal'
        elif user_text and nlg_text:
            result['text_source'] = 'user_and_nlg'
        elif user_text and journal_text:
            result['text_source'] = 'user_and_journal'
        elif nlg_text and journal_text:
            result['text_source'] = 'nlg_and_journal'
        elif user_text:
            result['text_source'] = 'user_only'
        elif nlg_text:
            result['text_source'] = 'nlg_only'
        elif journal_text:
            result['text_source'] = 'journal_only'

        # Analyze the combined text
        if workout_text:
            result['has_workout_text'] = True
            result['workout_analysis'] = self.analyze_workout_text(workout_text)

        ##end

        ##end

        ##end
        # 2. Build daily summary text
        daily_text = (
            f"Meetings: {data.get('meetings', 0)} meetings totaling {data.get('meeting_hours', 0)} hours. "
            f"Chat: {data.get('messages', 0)} messages. "
            f"Code: {data.get('commits', 0)} commits. "
            f"Sleep: {data.get('sleep', 7)} hours. "
            f"Workout: {data.get('workout_minutes', 0)} minutes. "
            f"Journal: {data.get('journal', 'no entry')}"
        )
        
        # 3. Daily productivity analysis
        result['daily_analysis'] = self.analyze_daily_summary(daily_text)
        
        # 4. Generate unified insights
        result['unified_insights'] = self._generate_unified_insights(
            workout=result['workout_analysis'],
            daily=result['daily_analysis'],
            data=data
        )
        
        # 5. Generate recommendations
        result['recommendations'] = self._generate_recommendations(result)
        
        return result
    
    
    def _generate_unified_insights(self, workout, daily, data):
        """Generate insights combining both analyses"""
        insights = []
        
        daily_state = daily['daily_state']
        burnout_risk = daily['burnout_risk']
        
        # Insight 1: High burnout + workout struggle
        if burnout_risk > 0.6 and workout and workout['performance']['performance'] == 'struggle':
            insights.append({
                'type': 'critical_overload',
                'confidence': 'very_high',
                'message': f"Critical: {daily_state} day with workout struggle and {daily['risk_level']} burnout risk"
            })
        
        # Insight 2: Injury mention during overloaded day
        if workout and daily_state == 'Overloaded':
            body_parts = [e['text'] for e in workout['entities'] if e['label'] == 'BODY_PART']
            if body_parts:
                insights.append({
                    'type': 'injury_during_overload',
                    'confidence': 'high',
                    'message': f"Injury concerns ({', '.join(body_parts)}) during overloaded day - high risk"
                })
        
        # Insight 3: Poor sleep affecting both
        if data.get('sleep', 7) < 6:
            if workout and workout['sentiment']['sentiment'] == 'negative':
                insights.append({
                    'type': 'sleep_impact_both',
                    'confidence': 'high',
                    'message': f"Poor sleep ({data['sleep']}h) affecting both workout and productivity"
                })
        
        # Insight 4: High performance alignment
        if daily_state == 'High_Performance' and workout and workout['performance']['performance'] == 'improvement':
            insights.append({
                'type': 'peak_performance',
                'confidence': 'very_high',
                'message': "Peak performance day across both fitness and work domains"
            })
        
        # Insight 5: Recovery day working
        if daily_state == 'Recovery' and (not workout or workout['sentiment']['sentiment'] != 'negative'):
            insights.append({
                'type': 'successful_recovery',
                'confidence': 'high',
                'message': "Recovery strategy working - recharge in progress"
            })
        
        return insights
    
    
    def _generate_recommendations(self, analysis):
        """Generate actionable recommendations"""
        recommendations = []
        
        daily = analysis['daily_analysis']
        workout = analysis['workout_analysis']
        
        # Rec 1: Burnout risk
        if daily['burnout_risk'] > 0.7:
            recommendations.append({
                'priority': 'critical',
                'action': 'MANDATORY rest day tomorrow - cancel non-essential meetings',
                'reason': f"{daily['risk_level']} burnout risk detected ({daily['burnout_risk']:.2f})"
            })
        elif daily['burnout_risk'] > 0.4:
            recommendations.append({
                'priority': 'high',
                'action': 'Reduce workload and prioritize sleep tonight',
                'reason': f"Moderate burnout risk ({daily['burnout_risk']:.2f})"
            })
        
        # Rec 2: Injury concerns
        if workout:
            body_parts = [e['text'] for e in workout['entities'] if e['label'] == 'BODY_PART']
            if body_parts:
                recommendations.append({
                    'priority': 'high',
                    'action': f"Monitor {', '.join(body_parts)} and consider physio consultation",
                    'reason': "Physical concerns mentioned in workout"
                })
        
        # Rec 3: Overloaded state
        if daily['daily_state'] == 'Overloaded':
            recommendations.append({
                'priority': 'high',
                'action': 'Delegate tasks, block focus time, limit meetings',
                'reason': "Overloaded state detected"
            })
        
        # Rec 4: Positive reinforcement
        if daily['daily_state'] == 'High_Performance':
            recommendations.append({
                'priority': 'low',
                'action': 'Great work! Maintain this rhythm but watch for burnout',
                'reason': "High performance day"
            })
        
        return recommendations


# ==================== DEMO ====================

def demo():
    """Demo the unified analyzer"""
    
    analyzer = UnifiedAnalyzer()
    
    test_cases = [
        {
            'name': 'Critical Overload + Injury',
            'data': {
                'workout_description': 'Struggled with hills, knees hurt badly',
                'meetings': 7,
                'meeting_hours': 6.2,
                'messages': 140,
                'commits': 0,
                'sleep': 4.5,
                'workout_minutes': 20,
                'journal': 'completely exhausted and overwhelmed'
            }
        },
        {
            'name': 'Peak Performance Day',
            'data': {
                'workout_description': 'PR on 10K! Felt amazing',
                'meetings': 2,
                'meeting_hours': 1.5,
                'messages': 30,
                'commits': 8,
                'sleep': 7.8,
                'workout_minutes': 45,
                'journal': 'hit all my goals, great energy'
            }
        },
        {
            'name': 'No Workout Text (Daily Only)',
            'data': {
                'workout_description': '',
                'meetings': 5,
                'meeting_hours': 4.0,
                'messages': 85,
                'commits': 2,
                'sleep': 6.0,
                'workout_minutes': 15,
                'journal': 'distracted by interruptions'
            }
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print("\n" + "="*80)
        print(f"TEST CASE {i}: {test['name']}")
        print("="*80)
        
        result = analyzer.analyze_complete_day(test['data'])
        
        # Workout analysis
        if result['workout_analysis']:
            w = result['workout_analysis']
            print(f"\n📝 WORKOUT ANALYSIS:")
            print(f"   Text: {w['text']}")
            print(f"   Sentiment: {w['sentiment']['sentiment']} ({w['sentiment']['confidence']:.1%})")
            print(f"   Performance: {w['performance']['performance']}")
            if w['entities']:
                print(f"   Entities: {[(e['text'], e['label']) for e in w['entities']]}")
        else:
            print(f"\n📝 WORKOUT ANALYSIS: No text provided")
        
        # Daily analysis
        d = result['daily_analysis']
        print(f"\n📊 DAILY STATE:")
        print(f"   Classification: {d['daily_state']}")
        print(f"   Confidence: {d['confidence']:.1%}")
        print(f"   Burnout Risk: {d['burnout_risk']:.2f} ({d['risk_level']})")
        
        # Unified insights
        print(f"\n🔍 UNIFIED INSIGHTS ({len(result['unified_insights'])} found):")
        for insight in result['unified_insights']:
            print(f"   • [{insight['type'].upper()}] - {insight['confidence']}")
            print(f"     {insight['message']}")
        
        # Recommendations
        if result['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in result['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'critical' else "🟡" if rec['priority'] == 'high' else "🟢"
                print(f"   {priority_icon} [{rec['priority'].upper()}] {rec['action']}")
                print(f"      → {rec['reason']}")
    
    print("\n" + "="*80)
    print("✓ Demo complete!")
    print("="*80)


if __name__ == "__main__":
    demo()