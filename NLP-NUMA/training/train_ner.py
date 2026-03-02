"""
Named Entity Recognition for Fitness/Health Entities
Extracts: BODY_PART, SYMPTOM, DISTANCE, LOCATION, WORKOUT_TYPE
"""

import json
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
import random
from pathlib import Path


def convert_to_spacy_format(data):
    """Convert our JSON format to spaCy training format"""
    training_data = []
    
    for item in data:
        text = item['text']
        entities = item['entities']
        
        # Convert to spaCy format: (start, end, label)
        ents = [(e['start'], e['end'], e['label']) for e in entities]
        
        training_data.append((text, {"entities": ents}))
    
    return training_data


def train_ner_model(train_data, val_data, output_dir="ner_model", n_iter=30):
    """Train a spaCy NER model"""
    
    # Convert to Path
    script_dir = Path(__file__).parent.parent
    output_path = script_dir / 'models' / output_dir
    
    print("Preparing training data...")
    train_examples = convert_to_spacy_format(train_data)
    val_examples = convert_to_spacy_format(val_data)
    
    print(f"Training samples: {len(train_examples)}")
    print(f"Validation samples: {len(val_examples)}")
    
    # Create blank English model
    nlp = spacy.blank("en")
    
    # Add NER pipeline
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")
    
    # Add labels
    labels = set()
    for _, annotations in train_examples:
        for ent in annotations.get("entities"):
            labels.add(ent[2])
    
    for label in labels:
        ner.add_label(label)
    
    print(f"\nEntity labels: {labels}")
    
    # Training
    print(f"\nTraining for {n_iter} iterations...")
    
    # Get names of other pipes to disable during training
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    
    # Only train NER
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        
        for iteration in range(n_iter):
            random.shuffle(train_examples)
            losses = {}
            
            # Batch the examples
            batches = minibatch(train_examples, size=compounding(4.0, 32.0, 1.001))
            
            for batch in batches:
                examples = []
                for text, annotations in batch:
                    doc = nlp.make_doc(text)
                    example = Example.from_dict(doc, annotations)
                    examples.append(example)
                
                nlp.update(examples, drop=0.5, losses=losses)
            
            # Print progress
            if (iteration + 1) % 5 == 0:
                print(f"Iteration {iteration + 1}/{n_iter}, Loss: {losses['ner']:.4f}")
    
    # Save model
    output_path.mkdir(exist_ok=True)
    nlp.to_disk(output_path)
    
    print(f"\n Model saved to {output_path}")
    
    return nlp


def evaluate_ner(model, test_data):
    """Evaluate NER model"""
    print("\n" + "="*50)
    print("Evaluating NER Model")
    print("="*50)
    
    test_examples = convert_to_spacy_format(test_data)
    
    tp = 0  # True positives
    fp = 0  # False positives
    fn = 0  # False negatives
    
    for text, annotations in test_examples:
        doc = model(text)
        pred_entities = set((ent.start_char, ent.end_char, ent.label_) for ent in doc.ents)
        true_entities = set(annotations['entities'])
        
        tp += len(pred_entities & true_entities)
        fp += len(pred_entities - true_entities)
        fn += len(true_entities - pred_entities)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\nNER Results:")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    
    # Show some examples
    print("\n Example Predictions:\n")
    for i, (text, _) in enumerate(test_examples[:5]):
        doc = model(text)
        print(f"{i+1}. Text: {text}")
        print(f"   Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")
        print()
    
    return precision, recall, f1


if __name__ == "__main__":
    # Load data
    script_dir = Path(__file__).parent.parent
    
    print("Loading data...")
    with open(script_dir / 'data' / 'train_data.json') as f:
        train_data = json.load(f)
    with open(script_dir / 'data' / 'val_data.json') as f:
        val_data = json.load(f)
    with open(script_dir / 'data' / 'test_data.json') as f:
        test_data = json.load(f)
    
    # Train NER model
    nlp = train_ner_model(
        train_data, 
        val_data, 
        output_dir='ner_model',
        n_iter=30
    )
    
    # Evaluate
    evaluate_ner(nlp, test_data)
