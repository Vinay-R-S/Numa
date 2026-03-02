"""
Multi-Label Classification for Workout Descriptions
Classifies: performance, physical_state, mental_state, pain_present
"""

import json
import torch
import pickle
from pathlib import Path
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    TrainingArguments, 
    Trainer
)
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')


def prepare_label_encoders(train_data):
    """Create label encoders for each classification task"""
    encoders = {}
    
    # Get all unique values for each label type
    label_types = ['performance', 'physical_state', 'mental_state']
    
    for label_type in label_types:
        values = [item['labels'][label_type] for item in train_data]
        encoder = LabelEncoder()
        encoder.fit(values)
        encoders[label_type] = encoder
    
    # pain_present is boolean, no encoder needed
    encoders['pain_present'] = None
    
    return encoders


def create_simple_dataset(data, tokenizer, label_encoders, label_type):
    """Create a simple dataset for single-label classification"""
    
    class SimpleDataset(Dataset):
        def __init__(self, data, tokenizer, encoder, label_type):
            self.data = data
            self.tokenizer = tokenizer
            self.encoder = encoder
            self.label_type = label_type
        
        def __len__(self):
            return len(self.data)
        
        def __getitem__(self, idx):
            item = self.data[idx]
            text = item['text']
            
            encoding = self.tokenizer(
                text,
                max_length=128,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            label_value = item['labels'][self.label_type]
            if isinstance(label_value, bool):
                label = float(label_value)
            else:
                label = self.encoder.transform([label_value])[0]
            
            return {
                'input_ids': encoding['input_ids'].squeeze(),
                'attention_mask': encoding['attention_mask'].squeeze(),
                'labels': torch.tensor(label, dtype=torch.long)
            }
    
    return SimpleDataset(data, tokenizer, label_encoders[label_type], label_type)


def train_classifier(train_file, val_file, output_dir="workout_classifier"):
    """Train the multi-label classification model"""
    
    # Convert to Path
    script_dir = Path(__file__).parent.parent
    train_file = script_dir / 'data' / train_file
    val_file = script_dir / 'data' / val_file
    output_dir = script_dir / 'models' / output_dir
    
    print("Loading data...")
    with open(train_file) as f:
        train_data = json.load(f)
    with open(val_file) as f:
        val_data = json.load(f)
    
    print(f"Training samples: {len(train_data)}")
    print(f"Validation samples: {len(val_data)}")
    
    # Prepare label encoders
    print("\nPreparing label encoders...")
    label_encoders = prepare_label_encoders(train_data)
    
    for label_type, encoder in label_encoders.items():
        if encoder is not None:
            print(f"  {label_type}: {encoder.classes_}")
    
    # Load tokenizer and model
    print("\nLoading model...")
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Train performance classifier
    print("\n" + "="*50)
    print("Training Performance Classifier")
    print("="*50)
    
    num_labels = len(label_encoders['performance'].classes_)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels
    )
    
    # Create datasets
    train_dataset = create_simple_dataset(train_data, tokenizer, label_encoders, 'performance')
    val_dataset = create_simple_dataset(val_data, tokenizer, label_encoders, 'performance')
    
    # Training arguments
    perf_output = output_dir / "performance"
    training_args = TrainingArguments(
        output_dir=str(perf_output),
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        logging_steps=50,
        report_to="none"
    )
    
    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer
    )
    
    trainer.train()
    
    # Save
    model.save_pretrained(str(perf_output))
    tokenizer.save_pretrained(str(perf_output))
    
    # Save label encoders
    output_dir.mkdir(exist_ok=True, parents=True)
    with open(output_dir / 'label_encoders.pkl', 'wb') as f:
        pickle.dump(label_encoders, f)
    
    print(f"\n Model saved to {output_dir}")
    
    return model, tokenizer, label_encoders


def evaluate_model(model_path, test_file, label_encoders_file):
    """Evaluate the trained model"""
    # Convert to Path
    script_dir = Path(__file__).parent.parent
    model_path = script_dir / 'models' / model_path
    test_file = script_dir / 'data' / test_file
    label_encoders_file = script_dir / 'models' / label_encoders_file
    
    print("\n" + "="*50)
    print("Evaluating Model")
    print("="*50)
    
    # Load model and tokenizer
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    
    # Load label encoders
    with open(label_encoders_file, 'rb') as f:
        label_encoders = pickle.load(f)
    
    # Load test data
    with open(test_file) as f:
        test_data = json.load(f)
    
    # Make predictions
    predictions = []
    true_labels = []
    
    model.eval()
    with torch.no_grad():
        for item in test_data:
            # Tokenize
            inputs = tokenizer(
                item['text'],
                return_tensors='pt',
                max_length=128,
                padding='max_length',
                truncation=True
            )
            
            # Predict
            outputs = model(**inputs)
            pred = torch.argmax(outputs.logits, dim=1).item()
            predictions.append(pred)
            
            # True label
            true_label = item['labels']['performance']
            true_labels.append(label_encoders['performance'].transform([true_label])[0])
    
    # Calculate metrics
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    
    accuracy = accuracy_score(true_labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        true_labels, predictions, average='weighted'
    )
    
    print(f"\nPerformance Classifier Results:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    
    # Show classification report
    print("\nDetailed Classification Report:")
    print(classification_report(
        true_labels, 
        predictions,
        target_names=label_encoders['performance'].classes_
    ))
    
    return accuracy, precision, recall, f1


if __name__ == "__main__":
    # Train
    model, tokenizer, label_encoders = train_classifier(
        train_file='train_data.json',
        val_file='val_data.json',
        output_dir='workout_classifier'
    )
    
    # Evaluate
    evaluate_model(
        model_path='workout_classifier/performance',
        test_file='test_data.json',
        label_encoders_file='workout_classifier/label_encoders.pkl'
    )
