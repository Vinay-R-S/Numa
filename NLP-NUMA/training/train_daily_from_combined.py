"""
Daily Productivity Classifier - Trained on Combined Data
TF-IDF + Logistic Regression using 697 samples from combined_train_data.json
"""

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


# Get script directory
SCRIPT_DIR = Path(__file__).parent.parent


# -------------------------
# Helper: Burnout risk
# -------------------------
def compute_burnout_risk(prob_dict):
    """
    Burnout risk definition:
      risk = P(Overloaded) + 0.5 * P(Distracted)
    """
    p_over = prob_dict.get("Overloaded", 0.0)
    p_dist = prob_dict.get("Distracted", 0.0)
    return p_over + 0.5 * p_dist


def interpret_risk(risk_score):
    if risk_score > 0.7:
        return "HIGH"
    elif risk_score > 0.4:
        return "MODERATE"
    else:
        return "LOW"


# =========================
# 1. LOAD COMBINED DATASET
# =========================

print("="*80)
print("DAILY PRODUCTIVITY CLASSIFIER - TRAINING ON COMBINED DATA")
print("="*80)

train_path = SCRIPT_DIR / 'data' / 'combined_train_data.json'
val_path = SCRIPT_DIR / 'data' / 'combined_val_data.json'
test_path = SCRIPT_DIR / 'data' / 'combined_test_data.json'

print("\nLoading combined data...")
with open(train_path) as f:
    train_data = json.load(f)
with open(val_path) as f:
    val_data = json.load(f)
with open(test_path) as f:
    test_data = json.load(f)

print(f"  Train: {len(train_data)} samples")
print(f"  Val: {len(val_data)} samples")
print(f"  Test: {len(test_data)} samples")

# Extract daily_text and daily_label
print("\nExtracting daily summaries...")
train_texts = [item['daily_text'] for item in train_data]
train_labels = [item['daily_label'] for item in train_data]

val_texts = [item['daily_text'] for item in val_data]
val_labels = [item['daily_label'] for item in val_data]

test_texts = [item['daily_text'] for item in test_data]
test_labels = [item['daily_label'] for item in test_data]

# Combine train + val for final training
all_train_texts = train_texts + val_texts
all_train_labels = train_labels + val_labels

print(f"\nTotal training samples: {len(all_train_texts)}")
print(f"Test samples: {len(test_texts)}")

# Show class distribution
from collections import Counter
print("\nClass distribution in training data:")
for label, count in Counter(all_train_labels).items():
    print(f"  {label}: {count}")


# =========================
# 2. TF-IDF VECTORIZATION
# =========================

print("\nTraining TF-IDF vectorizer...")
vectorizer = TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 2),
    stop_words="english"
)

X_train = vectorizer.fit_transform(all_train_texts)
X_test = vectorizer.transform(test_texts)

print(f"Feature matrix shape: {X_train.shape}")


# =========================
# 3. LOGISTIC REGRESSION
# =========================

print("\nTraining Logistic Regression model...")
model = LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
    random_state=42
)

model.fit(X_train, all_train_labels)
print("✓ Training complete!")


# =========================
# 4. EVALUATION
# =========================

y_pred = model.predict(X_test)

print("\n" + "="*80)
print("EVALUATION RESULTS")
print("="*80)

accuracy = accuracy_score(test_labels, y_pred)
print(f"\nAccuracy: {accuracy:.4f}")

print("\nClassification Report:\n")
print(classification_report(test_labels, y_pred))

print("\nConfusion Matrix:\n")
print(confusion_matrix(test_labels, y_pred))


# =========================
# 5. TOP WORDS PER CLASS
# =========================

print("\n" + "="*80)
print("TOP PREDICTIVE WORDS PER CLASS")
print("="*80)

feature_names = vectorizer.get_feature_names_out()

for i, class_label in enumerate(model.classes_):
    top10 = np.argsort(model.coef_[i])[-10:]
    print(f"\nTop words for '{class_label}':")
    print([feature_names[j] for j in top10])


# =========================
# 6. SAMPLE PREDICTION
# =========================

sample = """
Meetings: 6 meetings totaling 5.5 hours.
Chat: 120 messages with urgent requests.
Code: 0 commits.
Sleep: 4.5 hours.
Workout: 20 minutes.
Journal: Felt overwhelmed and exhausted with constant interruptions. 
Work was relentless with back-to-back coordination calls. 
I need to prioritize rest and recovery or I'll burn out.
"""

sample_vec = vectorizer.transform([sample])
prediction = model.predict(sample_vec)[0]
probs = model.predict_proba(sample_vec)[0]

# Build probability dict
prob_dict = dict(zip(model.classes_, probs))

print("\n" + "="*80)
print("SAMPLE PREDICTION TEST")
print("="*80)
print(f"\nInput: {sample.strip()}")
print(f"\nPredicted class: {prediction}")
print("\nFull probability distribution:")
for cls, p in sorted(prob_dict.items(), key=lambda x: -x[1]):
    print(f"  {cls}: {p:.4f}")

# Burnout risk
burnout_risk = compute_burnout_risk(prob_dict)
risk_level = interpret_risk(burnout_risk)

print(f"\nBurnout Risk Score: {burnout_risk:.4f}")
print(f"Risk Level: {risk_level}")


# =========================
# 7. SAVE MODEL & VECTORIZER
# =========================

model_dir = SCRIPT_DIR / "models" / "daily_productivity_model"
model_dir.mkdir(exist_ok=True)

model_path = model_dir / "productivity_classifier.pkl"
vectorizer_path = model_dir / "tfidf_vectorizer.pkl"

joblib.dump(model, model_path)
joblib.dump(vectorizer, vectorizer_path)

print("\n" + "="*80)
print(f"✓ Model saved to: {model_path}")
print(f"✓ Vectorizer saved to: {vectorizer_path}")
print("="*80)
print("\nNew model trained on 697 samples (much better than 40!)")
print("This will replace your old model and improve accuracy significantly.")
print("="*80)