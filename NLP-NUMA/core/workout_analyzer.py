"""
Unified Workout Description Analyzer
Combines: Sentiment Analysis + NER + Multi-label Classification
"""

import json
import torch
import spacy
import pickle
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')


class WorkoutAnalyzer:
    """Complete NLP pipeline for workout description analysis"""
    
    def __init__(self):
        # Get script directory
        script_dir = Path(__file__).parent.parent
        
        # Define all model paths
        sentiment_model_path = script_dir / 'models' / 'sentiment_model'
        ner_model_path = script_dir / 'models' / 'ner_model'
        classifier_model_path = script_dir / 'models' / 'workout_classifier' / 'performance'
        label_encoders_path = script_dir / 'models' / 'workout_classifier' / 'label_encoders.pkl'
        
        print("Loading models...")
        
        # Load sentiment model
        print("  Loading sentiment model...")
        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(str(sentiment_model_path))
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(str(sentiment_model_path))
        self.sentiment_model.eval()
        
        # Load NER model
        print("  Loading NER model...")
        self.ner_model = spacy.load(str(ner_model_path))
        
        # Load classifier
        print("  Loading performance classifier...")
        self.classifier_tokenizer = AutoTokenizer.from_pretrained(str(classifier_model_path))
        self.classifier_model = AutoModelForSequenceClassification.from_pretrained(str(classifier_model_path))
        self.classifier_model.eval()
        
        # Load label encoders
        print("  Loading label encoders...")
        with open(label_encoders_path, 'rb') as f:
            self.label_encoders = pickle.load(f)
        
        print(" All models loaded!\n")

    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        inputs = self.sentiment_tokenizer(
            text,
            return_tensors='pt',
            max_length=128,
            padding='max_length',
            truncation=True
        )
        
        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)[0]
            pred = torch.argmax(logits, dim=1).item()
        
        id_to_label = {0: 'positive', 1: 'neutral', 2: 'negative'}
        
        return {
            'sentiment': id_to_label[pred],
            'confidence': float(probs[pred]),
            'scores': {
                'positive': float(probs[0]),
                'neutral': float(probs[1]),
                'negative': float(probs[2])
            }
        }
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities"""
        doc = self.ner_model(text)
        
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        return entities
    
    def classify_performance(self, text: str) -> Dict:
        """Classify workout performance"""
        inputs = self.classifier_tokenizer(
            text,
            return_tensors='pt',
            max_length=128,
            padding='max_length',
            truncation=True
        )
        
        with torch.no_grad():
            outputs = self.classifier_model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)[0]
            pred = torch.argmax(logits, dim=1).item()
        
        # Decode prediction
        performance = self.label_encoders['performance'].inverse_transform([pred])[0]
        
        return {
            'performance': performance,
            'confidence': float(probs[pred])
        }
    
    def analyze(self, text: str) -> Dict:
        """Complete analysis of workout description"""
        
        # Run all analyses
        sentiment = self.analyze_sentiment(text)
        entities = self.extract_entities(text)
        performance = self.classify_performance(text)
        
        # Combine results
        result = {
            'text': text,
            'sentiment': sentiment,
            'performance': performance,
            'entities': entities,
            'summary': self._generate_summary(sentiment, entities, performance)
        }
        
        return result
    
    def _generate_summary(self, sentiment, entities, performance) -> str:
        """Generate human-readable summary"""
        summary_parts = []
        
        # Performance
        summary_parts.append(f"Performance: {performance['performance']}")
        
        # Sentiment
        summary_parts.append(f"Sentiment: {sentiment['sentiment']} ({sentiment['confidence']:.2f} confidence)")
        
        # Key entities
        if entities:
            body_parts = [e['text'] for e in entities if e['label'] == 'BODY_PART']
            symptoms = [e['text'] for e in entities if e['label'] == 'SYMPTOM']
            distances = [e['text'] for e in entities if e['label'] == 'DISTANCE']
            
            if body_parts:
                summary_parts.append(f"Body parts mentioned: {', '.join(body_parts)}")
            if symptoms:
                summary_parts.append(f"Symptoms: {', '.join(symptoms)}")
            if distances:
                summary_parts.append(f"Distance: {', '.join(distances)}")
        
        return " | ".join(summary_parts)
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """Analyze multiple texts"""
        return [self.analyze(text) for text in texts]


def pretty_print_analysis(result: Dict):
    """Pretty print analysis results"""
    print("="*70)
    print(f" TEXT: {result['text']}")
    print("="*70)
    
    # Sentiment
    print(f"\n SENTIMENT: {result['sentiment']['sentiment'].upper()}")
    print(f"   Confidence: {result['sentiment']['confidence']:.2%}")
    print(f"   Scores: Positive={result['sentiment']['scores']['positive']:.2f}, "
          f"Neutral={result['sentiment']['scores']['neutral']:.2f}, "
          f"Negative={result['sentiment']['scores']['negative']:.2f}")
    
    # Performance
    print(f"\n🏃 PERFORMANCE: {result['performance']['performance'].upper()}")
    print(f"   Confidence: {result['performance']['confidence']:.2%}")
    
    # Entities
    print(f"\n ENTITIES:")
    if result['entities']:
        for entity in result['entities']:
            print(f"   - {entity['text']} ({entity['label']})")
    else:
        print("   (No entities detected)")
    
    # Summary
    print(f"\n SUMMARY:")
    print(f"   {result['summary']}")
    print()


def demo():
    """Demo the complete pipeline"""
    print("\n" + "="*70)
    print("WORKOUT DESCRIPTION ANALYZER - DEMO")
    print("="*70 + "\n")
    
    script_dir = Path(__file__).parent
    
    # Initialize analyzer
    analyzer = WorkoutAnalyzer()
    
    # Test cases
    test_descriptions = [
        "PR on 10K! Felt amazing, perfect weather conditions today.",
        "Struggled with the hills, knees were painful throughout the run.",
        "Easy recovery 5 miles on the treadmill, no issues.",
        "Didn't sleep well last night, workout felt really hard and exhausting.",
        "Sharp pain in lower back around mile 3, had to stop early."
    ]
    
    # Analyze each
    for i, text in enumerate(test_descriptions, 1):
        print(f"\n{'='*70}")
        print(f"EXAMPLE {i}/{len(test_descriptions)}")
        result = analyzer.analyze(text)
        pretty_print_analysis(result)
    
    # Save results to JSON
    results = analyzer.analyze_batch(test_descriptions)
    
    output_file = script_dir.parent / 'analysis_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n Results saved to {output_file}")


if __name__ == "__main__":
    demo()
