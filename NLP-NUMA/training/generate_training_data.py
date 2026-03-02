"""
Synthetic Training Data Generator for Strava Workout Descriptions
Generates realistic workout descriptions with labels for NLP tasks
BALANCED VERSION - 4,000 samples evenly distributed
"""

import json
import random
from pathlib import Path
from typing import Dict, List


class WorkoutDataGenerator:
    def __init__(self):
        # Expanded templates for more variety
        self.templates = {
            'struggle': [
                "Struggled with the {terrain} today, {body_part} felt {symptom}",
                "Tough {distance} run, {body_part} were {symptom} throughout",
                "Hard workout today, didn't have much energy. {body_part} {symptom}",
                "Couldn't maintain my usual pace, {body_part} feeling {symptom}",
                "Cut the run short, {body_part} started {symptom} around mile {mile}",
                "Really challenging {workout_type} - {body_part} giving me trouble",
                "Pushed through but {body_part} were {symptom} the whole time",
                "{distance} felt way harder than it should, {body_part} not cooperating",
                "Barely made it through, {body_part} {symptom} and energy was low",
                "Not my day - {body_part} acting up and couldn't find my rhythm"
            ],
            'success': [
                "PR on {distance}! Felt {positive_feeling}, {weather} weather",
                "Amazing {workout_type} this morning! {body_part} felt strong",
                "New personal best! {distance} in great time, feeling {positive_feeling}",
                "Perfect conditions for a {workout_type}, everything clicked today",
                "Crushed my {workout_type} today, {positive_feeling} and energized",
                "Hit a new {distance} PR! Training is really paying off",
                "Best {workout_type} in months - felt powerful and {positive_feeling}",
                "Absolutely nailed it today! {distance} felt effortless",
                "Everything came together perfectly - {positive_feeling} from start to finish",
                "Strong finish on my {workout_type}, feeling {positive_feeling} about progress"
            ],
            'recovery': [
                "Easy recovery {workout_type}, taking it slow after {previous_workout}",
                "Light {workout_type} today, {body_part} still {symptom} from yesterday",
                "Recovery day - gentle {workout_type} and stretching",
                "Taking it easy, {body_part} needs time to heal",
                "Short and slow, focusing on recovery and mobility work",
                "Nice easy pace, letting my body recover from {previous_workout}",
                "Restorative {workout_type} - kept heart rate low and easy",
                "Active recovery session, just moving blood through the legs",
                "Gentle {distance} to stay loose, no pressure today",
                "Recovery mode: easy spin/jog, felt good to move without pushing"
            ],
            'neutral': [
                "Standard {distance} {workout_type} today",
                "Regular training session, nothing special",
                "Maintenance run on the {terrain}",
                "{workout_type} in {weather} conditions",
                "Routine {distance} to keep the streak going",
                "Solid {workout_type}, hit my target pace",
                "Normal training day - {distance} at steady effort",
                "Standard weekday {workout_type}, checking the box",
                "Another {distance} in the books, felt fine",
                "Regular {workout_type}, no highs or lows"
            ],
            'fatigue': [
                "Feeling exhausted, barely finished {distance}",
                "No energy today, struggled through {workout_type}",
                "Didn't sleep well, workout felt really hard",
                "Too tired from work, cut the {workout_type} short",
                "Running on empty, need more rest",
                "Dead legs today - {distance} was a grind",
                "Completely wiped out, every step felt heavy",
                "Mentally and physically drained, pushed through {distance} somehow",
                "Zero energy, considered skipping but forced myself out",
                "Exhausted from the week, {workout_type} felt like a chore"
            ],
            'pain': [
                "Sharp pain in {body_part} around mile {mile}, had to stop",
                "{body_part} hurting more than usual during {workout_type}",
                "Persistent {symptom} in {body_part}, might need to see a doctor",
                "Pain in {body_part} getting worse, took it very easy",
                "{body_part} still bothering me from last week",
                "Had to walk/stop multiple times - {body_part} pain",
                "Tried to push through but {body_part} pain got too intense",
                "Concerning pain in {body_part}, cutting back training",
                "{body_part} flared up badly during {workout_type}",
                "Not good - {body_part} pain forced me to stop early"
            ]
        }
        
        # Expanded vocabulary
        self.terrain = ['hills', 'trails', 'track', 'road', 'treadmill', 'beach', 'mountain paths', 
                       'park loops', 'riverside path', 'bike path', 'forest trails', 'urban streets']
        
        self.body_parts = ['knees', 'ankles', 'calves', 'hamstrings', 'quads', 'feet', 'hips', 
                          'lower back', 'shoulders', 'achilles', 'IT band', 'shin', 'glutes']
        
        self.symptoms = ['sore', 'tight', 'painful', 'stiff', 'weak', 'hurting', 'aching', 
                        'throbbing', 'burning', 'sharp', 'nagging']
        
        self.distances = ['5K', '10K', '5 miles', '10 miles', 'half marathon', 'marathon', 
                         '3K', '15K', '8K', '12 miles', '20K', '13.1 miles']
        
        self.workout_types = ['run', 'jog', 'bike ride', 'swim', 'workout', 'training session', 
                             'interval session', 'tempo run', 'long run', 'easy run', 'speed work']
        
        self.positive_feelings = ['amazing', 'great', 'energized', 'strong', 'confident', 
                                 'motivated', 'powerful', 'fired up', 'pumped', 'unstoppable']
        
        self.weather = ['perfect', 'beautiful', 'ideal', 'challenging', 'hot', 'cold', 'rainy', 
                       'windy', 'humid', 'crisp', 'sunny']
        
        self.previous_workouts = ['yesterday\'s long run', 'Monday\'s speed work', 'last week\'s race', 
                                 'tough interval session', 'weekend\'s hard effort', 'Thursday\'s tempo']
        
        self.miles = ['2', '3', '4', '5', '6', '8']
    
    def generate_description(self, category: str) -> Dict:
        """Generate a single workout description with labels"""
        template = random.choice(self.templates[category])
        
        # Fill in the template
        text = template.format(
            terrain=random.choice(self.terrain),
            body_part=random.choice(self.body_parts),
            symptom=random.choice(self.symptoms),
            distance=random.choice(self.distances),
            workout_type=random.choice(self.workout_types),
            positive_feeling=random.choice(self.positive_feelings),
            weather=random.choice(self.weather),
            previous_workout=random.choice(self.previous_workouts),
            mile=random.choice(self.miles)
        )
        
        # Assign labels
        labels = self._get_labels(category, text)
        
        # Extract entities (NON-OVERLAPPING)
        entities = self._extract_entities(text)
        
        return {
            'text': text,
            'category': category,
            'labels': labels,
            'entities': entities
        }
    
    def _get_labels(self, category: str, text: str) -> Dict:
        """Assign multi-label classifications"""
        label_mapping = {
            'struggle': {
                'performance': 'struggle',
                'physical_state': 'fatigued',
                'mental_state': 'frustrated',
                'pain_present': True
            },
            'success': {
                'performance': 'improvement',
                'physical_state': 'energized',
                'mental_state': 'motivated',
                'pain_present': False
            },
            'recovery': {
                'performance': 'neutral',
                'physical_state': 'recovering',
                'mental_state': 'neutral',
                'pain_present': 'sore' in text.lower() or 'tight' in text.lower()
            },
            'neutral': {
                'performance': 'neutral',
                'physical_state': 'normal',
                'mental_state': 'neutral',
                'pain_present': False
            },
            'fatigue': {
                'performance': 'struggle',
                'physical_state': 'fatigued',
                'mental_state': 'unmotivated',
                'pain_present': False
            },
            'pain': {
                'performance': 'struggle',
                'physical_state': 'pain',
                'mental_state': 'concerned',
                'pain_present': True
            }
        }
        return label_mapping[category]
    
    def _extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities from text (NON-OVERLAPPING)"""
        entities = []
        used_positions = set()
        
        def is_overlapping(start, end):
            return any(pos in used_positions for pos in range(start, end))
        
        # Distances (longest first)
        for dist in sorted(self.distances, key=len, reverse=True):
            if dist in text:
                start = text.index(dist)
                end = start + len(dist)
                if not is_overlapping(start, end):
                    entities.append({
                        'text': dist,
                        'label': 'DISTANCE',
                        'start': start,
                        'end': end
                    })
                    for pos in range(start, end):
                        used_positions.add(pos)
        
        # Body parts
        for bp in self.body_parts:
            if bp in text.lower():
                start = text.lower().index(bp)
                end = start + len(bp)
                if not is_overlapping(start, end):
                    entities.append({
                        'text': bp,
                        'label': 'BODY_PART',
                        'start': start,
                        'end': end
                    })
                    for pos in range(start, end):
                        used_positions.add(pos)
        
        # Terrain/locations
        for terrain in self.terrain:
            if terrain in text.lower():
                start = text.lower().index(terrain)
                end = start + len(terrain)
                if not is_overlapping(start, end):
                    entities.append({
                        'text': terrain,
                        'label': 'LOCATION',
                        'start': start,
                        'end': end
                    })
                    for pos in range(start, end):
                        used_positions.add(pos)
        
        # Symptoms
        for symptom in self.symptoms:
            if symptom in text.lower():
                start = text.lower().index(symptom)
                end = start + len(symptom)
                if not is_overlapping(start, end):
                    entities.append({
                        'text': symptom,
                        'label': 'SYMPTOM',
                        'start': start,
                        'end': end
                    })
                    for pos in range(start, end):
                        used_positions.add(pos)
        
        return entities
    
    def generate_balanced_dataset(self) -> List[Dict]:
        """Generate perfectly balanced 4,000 sample dataset"""
        
        # Target distribution for balanced daily labels
        category_counts = {
            'success': 800,      # → High_Performance
            'struggle': 800,     # → Overloaded
            'neutral': 800,      # → Focused
            'recovery': 400,     # → Recovery (split with pain)
            'fatigue': 800,      # → Distracted
            'pain': 400          # → Recovery (split with recovery)
        }
        
        dataset = []
        for category, count in category_counts.items():
            print(f"  Generating {count} '{category}' samples...")
            for _ in range(count):
                dataset.append(self.generate_description(category))
        
        # Shuffle
        random.shuffle(dataset)
        return dataset


def main():
    """Generate and save balanced 4,000 sample dataset"""
    generator = WorkoutDataGenerator()
    
    print("="*80)
    print("GENERATING BALANCED 4,000 SAMPLE DATASET")
    print("="*80)
    print("\nTarget distribution:")
    print("  success: 800 → High_Performance")
    print("  struggle: 800 → Overloaded")
    print("  neutral: 800 → Focused")
    print("  recovery: 400 → Recovery")
    print("  fatigue: 800 → Distracted")
    print("  pain: 400 → Recovery")
    print("  TOTAL: 4,000 samples")
    print()
    
    dataset = generator.generate_balanced_dataset()
    
    # Split: 70/15/15
    train_size = int(0.7 * len(dataset))
    val_size = int(0.15 * len(dataset))
    
    train_data = dataset[:train_size]
    val_data = dataset[train_size:train_size + val_size]
    test_data = dataset[train_size + val_size:]
    
    # Get current directory
    current_dir = Path(__file__).parent.parent
    data_dir = current_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # Save
    with open(data_dir / 'train_data.json', 'w') as f:
        json.dump(train_data, f, indent=2)
    
    with open(data_dir / 'val_data.json', 'w') as f:
        json.dump(val_data, f, indent=2)
    
    with open(data_dir / 'test_data.json', 'w') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"\n✓ Dataset generated in: {data_dir}")
    print(f"   Training: {len(train_data)} samples (70%)")
    print(f"   Validation: {len(val_data)} samples (15%)")
    print(f"   Test: {len(test_data)} samples (15%)")
    
    # Show distribution
    from collections import Counter
    print("\n✓ Actual category distribution in full dataset:")
    for cat, count in Counter([s['category'] for s in dataset]).items():
        print(f"   {cat}: {count}")
    
    # Show samples
    print("\n" + "="*80)
    print("SAMPLE WORKOUT DESCRIPTIONS")
    print("="*80)
    for i, sample in enumerate(random.sample(dataset, 5), 1):
        print(f"\n{i}. Text: {sample['text']}")
        print(f"   Category: {sample['category']}")
        print(f"   Performance: {sample['labels']['performance']}")
        print(f"   Entities: {[e['text'] + ' (' + e['label'] + ')' for e in sample['entities']]}")


if __name__ == "__main__":
    main()