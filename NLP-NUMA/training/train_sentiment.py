"""
Sentiment Analysis for Workout Descriptions
Fine-grained sentiment: positive, negative, neutral
Plus emotion detection: motivated, frustrated, tired, proud, concerned
"""

import json
import torch
from pathlib import Path
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)
from torch.utils.data import Dataset
from sklearn.metrics import classification_report, accuracy_score
import numpy as np


class SentimentDataset(Dataset):
    """Dataset for sentiment classification"""
    
    def __init__(self, data, tokenizer, max_length=128):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Map categories to sentiment
        self.sentiment_map = {
            'success': 'positive',
            'neutral': 'neutral',
            'struggle': 'negative',
            'recovery': 'neutral',
            'fatigue': 'negative',
            'pain': 'negative'
        }
        
        self.label_to_id = {
            'positive': 0,
            'neutral': 1,
            'negative': 2
        }
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item['text']
        category = item['category']
        
        # Get sentiment label
        sentiment = self.sentiment_map[category]
        label = self.label_to_id[sentiment]
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


def train_sentiment_model(train_file, val_file, output_dir="sentiment_model"):
    """Train sentiment analysis model"""
    
    # Convert to Path objects
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
    
    # Load model and tokenizer
    print("\nLoading model...")
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=3  # positive, neutral, negative
    )
    
    # Create datasets
    train_dataset = SentimentDataset(train_data, tokenizer)
    val_dataset = SentimentDataset(val_data, tokenizer)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
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
    print("\nTraining...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer
    )
    
    trainer.train()
    
    # Save
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    
    print(f"\n Model saved to {output_dir}")
    
    return model, tokenizer


def evaluate_sentiment(model_path, test_file):
    """Evaluate sentiment model"""
    # Convert to Path objects
    script_dir = Path(__file__).parent.parent
    model_path = script_dir / 'models' / model_path
    test_file = script_dir / 'data' / test_file
    
    print("\n" + "="*50)
    print("Evaluating Sentiment Model")
    print("="*50)
    
    # Load model
    model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    
    # Load test data
    with open(test_file) as f:
        test_data = json.load(f)
    
    # Create dataset
    test_dataset = SentimentDataset(test_data, tokenizer)
    
    # Predict
    model.eval()
    predictions = []
    true_labels = []
    
    with torch.no_grad():
        for item in test_dataset:
            inputs = {
                'input_ids': item['input_ids'].unsqueeze(0),
                'attention_mask': item['attention_mask'].unsqueeze(0)
            }
            
            outputs = model(**inputs)
            pred = torch.argmax(outputs.logits, dim=1).item()
            predictions.append(pred)
            true_labels.append(item['labels'].item())
    
    # Metrics
    accuracy = accuracy_score(true_labels, predictions)
    
    id_to_label = {0: 'positive', 1: 'neutral', 2: 'negative'}
    
    print(f"\nSentiment Analysis Results:")
    print(f"  Accuracy: {accuracy:.4f}")
    
    print("\nDetailed Classification Report:")
    print(classification_report(
        true_labels,
        predictions,
        target_names=['positive', 'neutral', 'negative']
    ))
    
    # Show examples
    print("\n Example Predictions:\n")
    for i in range(min(10, len(test_data))):
        text = test_data[i]['text']
        true_label = id_to_label[true_labels[i]]
        pred_label = id_to_label[predictions[i]]
        
        print(f"{i+1}. Text: {text}")
        print(f"   True: {true_label}, Predicted: {pred_label}")
        print()
    
    return accuracy


if __name__ == "__main__":
    # Train
    model, tokenizer = train_sentiment_model(
        train_file='train_data.json',
        val_file='val_data.json',
        output_dir='sentiment_model'
    )
    
    # Evaluate
    evaluate_sentiment(
        model_path='sentiment_model',
        test_file='test_data.json'
    )
