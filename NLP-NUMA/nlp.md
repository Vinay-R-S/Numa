# NLP-NUMA Architecture

> **What this system does:** NLP-NUMA takes raw numbers and text from your health, fitness, and productivity apps — Strava, Google Fit, Slack, GitHub, Google Calendar, a daily journal, and your sleep tracker — and translates them into a holistic daily report: _"You are showing HIGH burnout risk. Your workout struggled due to poor sleep, and your workday was Overloaded with 7 meetings. Rest tomorrow."_

---

## System Overview

```
DATA SOURCES
────────────────────────────────────────────────────────────────────
  Strava / Google Fit    ─► workout metrics   (km, pace, HR, elevation)
  Slack                  ─► messages count
  GitHub                 ─► commits count
  Google Calendar        ─► meeting count, meeting hours
  Sleep Tracker          ─► sleep hours
  Journal (text)         ─► free-form daily reflection
  User Workout Note      ─► optional free-text description of the workout

                                    │
                                    ▼
                          ┌─────────────────────┐
                          │   NLG MODULE        │
                          │  workout_nlg.py     │
                          │                     │
                          │ Converts numeric    │
                          │ metrics → natural   │
                          │ language text       │
                          └────────┬────────────┘
                                   │
                    ┌──────────────┼───────────────────┐
                    │              │                   │
                    ▼              ▼                   ▼
          ┌──────────────┐ ┌─────────────┐  ┌──────────────────┐
          │  SENTIMENT   │ │   NER MODEL │  │  PERFORMANCE     │
          │  MODEL       │ │  (spaCy)    │  │  CLASSIFIER      │
          │ DistilBERT   │ │             │  │  DistilBERT      │
          │ +/0/- mood   │ │ BODY_PART   │  │  struggle/neutral│
          │ of workout   │ │ SYMPTOM     │  │  /improvement    │
          │              │ │ DISTANCE    │  │                  │
          └──────┬───────┘ │ LOCATION    │  └────────┬─────────┘
                 │         └──────┬──────┘           │
                 └────────────────┼──────────────────┘
                                  │  Workout Text Analysis
                                  ▼
                       ┌─────────────────────┐
                       │   DAILY PRODUCTIVITY│
                       │   CLASSIFIER        │
                       │   TF-IDF + LogReg   │
                       │                     │
                       │ Focused / Overloaded│
                       │ High_Performance    │
                       │ Distracted / Recovery│
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  UNIFIED ANALYZER   │
                       │  unified_analyzer.py│
                       │                     │
                       │ • Burnout Risk Score│
                       │ • Unified Insights  │
                       │ • Recommendations   │
                       └─────────────────────┘
```

---

## Component 1 — Data Sources & Input Schema

The system receives one dictionary per day. Every key maps to exactly one real data source.

```python
data = {
    # ── From Strava / Google Fit ──────────────────────────────
    "distance_km":      10.5,     # total run/ride distance
    "duration_min":     52.0,     # total active time
    "avg_heart_rate":   162,      # average BPM during workout
    "max_heart_rate":   178,      # peak BPM
    "elevation_gain":   230,      # meters climbed
    "pace":             4.95,     # min/km
    "baseline_hr":      145,      # user's personal normal HR
    "baseline_pace":    5.5,      # user's personal normal pace

    # ── From the workout or Google Fit description ────────────
    "workout_description": "Struggled with hills, knees hurt",

    # ── From Slack ────────────────────────────────────────────
    "messages":         120,      # Slack messages sent/received

    # ── From GitHub ───────────────────────────────────────────
    "commits":          3,        # Git commits pushed

    # ── From Google Calendar ──────────────────────────────────
    "meetings":         6,        # number of calendar events
    "meeting_hours":    5.5,      # total hours in meetings

    # ── From sleep tracker (Google Fit / Fitbit / Oura) ───────
    "sleep":            5.0,      # hours of sleep last night

    # ── From the user's journal app ───────────────────────────
    "journal": "Felt overwhelmed and couldn't focus all day"
}
```

---

## Component 2 — Workout NLG (`workout_nlg.py`)

**Natural Language Generation** — converts raw numeric workout metrics into a human-readable sentence that the NLP models can understand and classify.

**Why it exists:** The sentiment and performance ML models expect _text_ as input. When a user hasn't written anything about their workout, the NLG module fills that gap by auto-generating a descriptive sentence from the numbers.

### How It Determines Tone

| Condition                                                   | Tone          |
| ----------------------------------------------------------- | ------------- |
| pace < 90% of baseline AND sleep ≥ 7.5h                     | `excellent`   |
| pace < 95% of baseline                                      | `good`        |
| pace > 125% of baseline OR HR > 120% baseline OR sleep < 6h | `struggle`    |
| pace > 115% OR HR > 115%                                    | `challenging` |
| otherwise                                                   | `normal`      |

### Input → Output Example

```python
# Input (from Strava + Sleep tracker)
metrics = {
    "distance_km": 5.0,
    "duration_min": 40.0,
    "avg_heart_rate": 175,   # baseline is 145 → ratio 1.21 → elevated!
    "max_heart_rate": 185,
    "pace": 8.0,             # baseline is 5.5 → ratio 1.45 → very slow!
    "sleep": 5.0,            # very poor
    "baseline_hr": 145,
    "baseline_pace": 5.5
}

# Output (auto-generated text)
"Struggled through 5.0km, not my best day. \
 Really slow pace at 8.0 min/km, legs felt heavy and unresponsive. \
 Heart rate was really elevated at 175 bpm (max 185), felt like I was working too hard. \
 Terrible sleep last night (5.0h) - felt exhausted and struggled through the whole workout. \
 Body clearly needs more recovery. Going to prioritize rest."
```

This generated text is then passed into the three NLP models below.

---

## Component 3 — Sentiment Analysis Model (`train_sentiment.py` → loaded in `workout_analyzer.py`)

**What it does:** Classifies the _emotional tone_ of the workout text as `positive`, `neutral`, or `negative`.

**Architecture:** Fine-tuned `distilbert-base-uncased` — a lightweight transformer pre-trained on English text. It has a 3-class classification head on top.

**Training Labels:**

| Workout Category              | Sentiment Label |
| ----------------------------- | --------------- |
| `success`                     | `positive`      |
| `neutral`, `recovery`         | `neutral`       |
| `struggle`, `fatigue`, `pain` | `negative`      |

### Input → Output Example

```python
text = "PR on 10K! Felt amazing, perfect weather conditions today."

# Output
{
    "sentiment": "positive",
    "confidence": 0.94,
    "scores": {
        "positive": 0.94,
        "neutral":  0.04,
        "negative": 0.02
    }
}
```

```python
text = "Struggled with the hills, knees were painful throughout the run."

# Output
{
    "sentiment": "negative",
    "confidence": 0.91,
    "scores": {
        "positive": 0.03,
        "neutral":  0.06,
        "negative": 0.91
    }
}
```

---

## Component 4 — Named Entity Recognition Model (`train_ner.py` → loaded in `workout_analyzer.py`)

**What it does:** Extracts structured medical/fitness entities from the workout text. This lets the system know _which body parts hurt_, _what symptoms are present_, _what distances were covered_, and _where the workout took place_.

**Architecture:** A custom `spaCy` NER model trained from blank English on synthetic workout data. Recognizes 4 entity types:

| Entity Label | What It Captures     | Examples                                       |
| ------------ | -------------------- | ---------------------------------------------- |
| `BODY_PART`  | Anatomical locations | `knees`, `ankles`, `lower back`, `IT band`     |
| `SYMPTOM`    | Physical sensations  | `sore`, `painful`, `tight`, `burning`, `sharp` |
| `DISTANCE`   | Race/run distances   | `10K`, `5 miles`, `half marathon`              |
| `LOCATION`   | Terrain types        | `hills`, `trails`, `track`, `treadmill`        |

### Input → Output Example

```python
text = "Struggled with the hills, knees felt sore and painful"

# Output (list of entity dicts)
[
    {"text": "hills",   "label": "LOCATION",  "start": 18, "end": 23},
    {"text": "knees",   "label": "BODY_PART", "start": 25, "end": 30},
    {"text": "sore",    "label": "SYMPTOM",   "start": 36, "end": 40},
    {"text": "painful", "label": "SYMPTOM",   "start": 45, "end": 52}
]
```

```python
text = "Sharp pain in lower back around mile 3, had to stop"

# Output
[
    {"text": "lower back", "label": "BODY_PART", "start": 14, "end": 24},
    {"text": "sharp",      "label": "SYMPTOM",   "start": 0,  "end": 5}
]
```

---

## Component 5 — Performance Classifier (`train_classifier.py` → loaded in `workout_analyzer.py`)

**What it does:** Classifies the _objective fitness outcome_ of a workout, independent of emotional tone.

**Architecture:** Fine-tuned `distilbert-base-uncased` with a 3-class head.

**Output Classes:**

| Class         | Meaning                                                  |
| ------------- | -------------------------------------------------------- |
| `improvement` | A personal best or notably good session                  |
| `neutral`     | A normal, maintenance workout                            |
| `struggle`    | A session impacted by fatigue, pain, or poor performance |

### Input → Output Example

```python
text = "PR on 10K! Felt amazing"

# Output
{
    "performance": "improvement",
    "confidence": 0.92
}
```

```python
text = "Barely made it through, hamstrings aching and energy was low"

# Output
{
    "performance": "struggle",
    "confidence": 0.88
}
```

### WorkoutAnalyzer — Combined Workout NLP (`workout_analyzer.py`)

`WorkoutAnalyzer` is the class that bundles Model 3 + 4 + 5 together for single-call workout text analysis:

```python
analyzer = WorkoutAnalyzer()
result = analyzer.analyze("Struggled with the hills, knees were painful throughout the run.")

# Full output
{
    "text": "Struggled with the hills, knees were painful throughout the run.",
    "sentiment": {
        "sentiment": "negative",
        "confidence": 0.91,
        "scores": {"positive": 0.03, "neutral": 0.06, "negative": 0.91}
    },
    "performance": {
        "performance": "struggle",
        "confidence": 0.88
    },
    "entities": [
        {"text": "hills",   "label": "LOCATION",  "start": 18, "end": 23},
        {"text": "knees",   "label": "BODY_PART", "start": 25, "end": 30},
        {"text": "painful", "label": "SYMPTOM",   "start": 36, "end": 43}
    ],
    "summary": "Performance: struggle | Sentiment: negative (0.91 confidence) | Body parts mentioned: knees | Symptoms: painful"
}
```

---

## Component 6 — Daily Productivity Classifier (`train_daily_from_combined.py`)

**What it does:** Classifies the _overall state of the entire day_ by analyzing a structured daily summary built from all the productivity + health data sources.

**Architecture:** `TF-IDF Vectorizer` (up to 5,000 features, 1-gram + 2-gram) feeding into a `Logistic Regression` classifier. This is intentionally lightweight — it runs fast with no GPU and generalizes well to the structured keyword-heavy input.

**Output Classes (5):**

| Class              | What It Means              | Key Signals                                              |
| ------------------ | -------------------------- | -------------------------------------------------------- |
| `High_Performance` | Peak output day            | Few meetings, high commits, good sleep, positive workout |
| `Focused`          | Solid, productive day      | Moderate meetings, decent commits, normal sleep          |
| `Overloaded`       | Way too much on plate      | 5+ meetings, high hours, many messages, few commits      |
| `Distracted`       | Low engagement / scattered | Medium meetings but low output, poor sleep, fatigue      |
| `Recovery`         | Intentional rest day       | Very few meetings, minimal activity, high sleep          |

### How the Input Text Is Built

The daily summary is assembled automatically from all the raw numbers:

```python
# From: meetings=6, meeting_hours=5.5, messages=120, commits=0,
#       sleep=4.5, workout_minutes=20, journal="felt overwhelmed..."

daily_text = (
    "Meetings: 6 meetings totaling 5.5 hours. "
    "Chat: 120 messages. "
    "Code: 0 commits. "
    "Sleep: 4.5 hours. "
    "Workout: 20 minutes. "
    "Journal: Felt overwhelmed and exhausted with constant interruptions. "
    "Work was relentless with back-to-back coordination calls. "
    "I need to prioritize rest and recovery or I'll burn out."
)
```

### Input → Output Example

```python
# Overloaded day
daily_text = "Meetings: 6 meetings totaling 5.5 hours. Chat: 120 messages. Code: 0 commits. Sleep: 4.5 hours. Workout: 20 minutes. Journal: Felt overwhelmed..."

# Output
{
    "daily_state": "Overloaded",
    "confidence": 0.83,
    "probabilities": {
        "Distracted":       0.07,
        "Focused":          0.03,
        "High_Performance": 0.01,
        "Overloaded":       0.83,
        "Recovery":         0.06
    },
    "burnout_risk": 0.83,     # = P(Overloaded) + 0.5 * P(Distracted) = 0.83 + 0.035
    "risk_level": "HIGH"
}
```

```python
# Peak performance day
daily_text = "Meetings: 2 meetings totaling 1.5 hours. Chat: 30 messages. Code: 8 commits. Sleep: 7.8 hours. Workout: 45 minutes. Journal: Hit all my goals, great energy..."

# Output
{
    "daily_state": "High_Performance",
    "confidence": 0.91,
    "probabilities": {
        "Distracted":       0.02,
        "Focused":          0.05,
        "High_Performance": 0.91,
        "Overloaded":       0.01,
        "Recovery":         0.01
    },
    "burnout_risk": 0.02,
    "risk_level": "LOW"
}
```

### Burnout Risk Score Formula

```
burnout_risk = P(Overloaded) + 0.5 × P(Distracted)

Overloaded gets full weight → it's serious
Distracted gets half weight → it's a warning sign
```

| Score       | Level    |
| ----------- | -------- |
| > 0.70      | HIGH     |
| 0.40 – 0.70 | MODERATE |
| < 0.40      | LOW      |

---

## Component 7 — Hybrid Workout Analyzer (`hybrid_analyzer.py`)

**What it does:** Cross-validates what you _said_ about your workout (NLP text analysis) against what the _numbers actually show_ (rule-based numeric analysis of pace, HR, sleep). It detects contradictions, confirms signals, and generates alerts.

**This is important because:**

- People sometimes say "felt great!" when their HR was dangerously high and their pace was their slowest ever (overconfidence / delayed fatigue awareness).
- Conversely, people sometimes feel mentally low but their body performed perfectly fine (mental barrier, not physical).

### Numeric Performance Rules

```python
# Input raw metrics from Strava + Sleep tracker
workout_data = {
    "distance":         8000,    # meters
    "moving_time":      3600,    # seconds
    "average_heartrate": 172,
    "sleep_hours":       5.5,
    "baseline_hr":       145,
    "baseline_pace":     5.5     # min/km
}

# Computed internally
distance_km     = 8.0
duration_min    = 60.0
pace_min_per_km = 7.5           # very slow (baseline = 5.5)
hr_ratio        = 172 / 145 = 1.19    # elevated (> 1.1)
pace_ratio      = 7.5 / 5.5 = 1.36   # very slow (> 1.3)

# → numeric_sentiment = "struggling"
```

### Cross-Validation Logic (Contradictions & Confirmations)

| Text Says            | Metrics Say       | Detected Insight                                  | Confidence |
| -------------------- | ----------------- | ------------------------------------------------- | ---------- |
| `negative`           | `struggling`      | `confirmed_struggle`                              | very_high  |
| `positive`           | `performing_well` | `confirmed_success`                               | very_high  |
| `positive`           | `struggling`      | `contradiction_warning` — overconfidence          | high       |
| `negative`           | `performing_well` | `mental_barrier` — mental issue                   | high       |
| mentions `BODY_PART` | pace slow         | `injury_performance_correlation`                  | very_high  |
| mentions `BODY_PART` | pace normal       | `injury_mention_without_impact` — monitor closely | medium     |

### Input → Output Example

```python
workout_data = {
    "description":       "Felt great today!",  # positive text
    "distance":          5000,
    "moving_time":       2100,                 # 7:00 min/km — slow
    "average_heartrate": 175,                  # high HR
    "sleep_hours":       5.0,
    "baseline_hr":       145,
    "baseline_pace":     5.5
}

result = analyzer.analyze_complete_workout(workout_data)

# Output
{
    "numeric_analysis": {
        "metrics": {"distance_km": 5.0, "pace_min_per_km": 7.0, "avg_hr": 175, "sleep_hours": 5.0},
        "numeric_sentiment": "struggling"
    },
    "text_analysis": {
        "sentiment": {"sentiment": "positive", "confidence": 0.78},
        "performance": {"performance": "improvement", "confidence": 0.65}
    },
    "combined_insights": [
        {
            "type": "contradiction_warning",
            "confidence": "high",
            "message": "Positive text but struggling metrics - possible overconfidence or delayed fatigue"
        }
    ],
    "alerts": [
        {"severity": "info", "message": "ℹ️ Text and metrics show different signals - review workout context"}
    ],
    "recommendations": [
        {"priority": "medium", "action": "Prioritize 7-9 hours of sleep tonight",
         "reason": "Only 5.0 hours of sleep"}
    ]
}
```

---

## Component 8 — Unified Analyzer (`unified_analyzer.py`)

**What it does:** This is the top-level orchestrator. It coordinates all previous components and produces the final, complete holistic daily analysis. It's the main entry point for NUMA.

### Processing Flow

```python
def analyze_complete_day(data: dict) -> dict:

    # Step 1: Generate NLG text from workout metrics
    nlg_text = generate_workout_text(workout_metrics)

    # Step 2: Combine user text + NLG text + journal into one rich passage
    workout_text = user_description + NLG_text + "Personal reflection: " + journal

    # Step 3: NLP analysis on the combined workout text
    workout_analysis = {
        "sentiment":    sentiment_model(workout_text),     # +/0/-
        "performance":  classifier_model(workout_text),    # improve/neutral/struggle
        "entities":     ner_model(workout_text)            # BODY_PART, SYMPTOM…
    }

    # Step 4: Build daily summary from all productivity numbers
    daily_text = f"Meetings: {meetings} totaling {meeting_hours} hours. Chat: {messages} messages. Code: {commits} commits. Sleep: {sleep}h. Workout: {workout_minutes}min. Journal: {journal}"

    # Step 5: Classify daily state
    daily_analysis = {
        "daily_state":  tfidf_logreg(daily_text),        # Focused / Overloaded / …
        "burnout_risk": P(Overloaded) + 0.5*P(Distracted),
        "risk_level":   HIGH / MODERATE / LOW
    }

    # Step 6: Cross-reference to generate unified insights
    insights = cross_reference(workout_analysis, daily_analysis, raw_data)

    # Step 7: Generate prioritized recommendations
    recommendations = generate_recommendations(insights, daily_analysis, workout_analysis)
```

### Unified Insights Logic

| Condition                                                        | Insight Type             |
| ---------------------------------------------------------------- | ------------------------ |
| burnout_risk > 0.6 AND workout = `struggle`                      | `critical_overload`      |
| daily_state = `Overloaded` AND BODY_PART entities detected       | `injury_during_overload` |
| sleep < 6h AND workout sentiment = `negative`                    | `sleep_impact_both`      |
| daily_state = `High_Performance` AND performance = `improvement` | `peak_performance`       |
| daily_state = `Recovery` AND workout not negative                | `successful_recovery`    |

### Full End-to-End Example

**Input (assembled from your apps):**

```python
data = {
    "workout_description": "Struggled with hills, knees hurt badly",
    "distance_km":      5.0,
    "duration_min":     40.0,
    "avg_heart_rate":   175,
    "max_heart_rate":   188,
    "elevation_gain":   300,
    "pace":             8.0,
    "baseline_hr":      145,
    "baseline_pace":    5.5,
    "meetings":         7,
    "meeting_hours":    6.2,
    "messages":         140,
    "commits":          0,
    "sleep":            4.5,
    "workout_minutes":  20,
    "journal":          "completely exhausted and overwhelmed"
}
```

**Output:**

```python
{
    "has_workout_text": True,
    "text_source":      "user_nlg_journal",   # all three text sources combined

    "workout_analysis": {
        "sentiment":    {"sentiment": "negative",  "confidence": 0.94},
        "performance":  {"performance": "struggle", "confidence": 0.91},
        "entities": [
            {"text": "hills", "label": "LOCATION"},
            {"text": "knees", "label": "BODY_PART"},
            {"text": "hurt",  "label": "SYMPTOM"}
        ]
    },

    "daily_analysis": {
        "daily_state":  "Overloaded",
        "confidence":   0.86,
        "burnout_risk": 0.89,
        "risk_level":   "HIGH"
    },

    "unified_insights": [
        {
            "type":       "critical_overload",
            "confidence": "very_high",
            "message":    "Critical: Overloaded day with workout struggle and HIGH burnout risk"
        },
        {
            "type":       "injury_during_overload",
            "confidence": "high",
            "message":    "Injury concerns (knees) during overloaded day - high risk"
        },
        {
            "type":       "sleep_impact_both",
            "confidence": "high",
            "message":    "Poor sleep (4.5h) affecting both workout and productivity"
        }
    ],

    "recommendations": [
        {
            "priority": "critical",
            "action":   "MANDATORY rest day tomorrow - cancel non-essential meetings",
            "reason":   "HIGH burnout risk detected (0.89)"
        },
        {
            "priority": "high",
            "action":   "Monitor knees and consider physio consultation",
            "reason":   "Physical concerns mentioned in workout"
        },
        {
            "priority": "high",
            "action":   "Delegate tasks, block focus time, limit meetings",
            "reason":   "Overloaded state detected"
        }
    ]
}
```

---

## Component 9 — Training Data Pipeline

All models are trained on **synthetically generated data** that mirrors the structure of real-world inputs from Strava, Slack, GitHub, Google Calendar, and journal entries.

### Step 1 — Workout Data Generation (`generate_training_data.py`)

Generates **4,000 workout description samples** by filling natural-language templates with randomized vocabulary.

**Category Distribution (balanced for 5 daily labels):**

| Category   | Count | Maps To Daily Label |
| ---------- | ----- | ------------------- |
| `success`  | 800   | `High_Performance`  |
| `struggle` | 800   | `Overloaded`        |
| `neutral`  | 800   | `Focused`           |
| `fatigue`  | 800   | `Distracted`        |
| `recovery` | 400   | `Recovery`          |
| `pain`     | 400   | `Recovery`          |

**Example generated workout:**

```
Template: "Struggled with the {terrain} today, {body_part} felt {symptom}"
Filled:   "Struggled with the hills today, knees felt painful"

Labels:   { performance: "struggle", physical_state: "fatigued",
            mental_state: "frustrated", pain_present: True }

Entities: [
    { text: "knees",   label: "BODY_PART" },
    { text: "painful", label: "SYMPTOM"  },
    { text: "hills",   label: "LOCATION" }
]
```

**Split:** 70% Train / 15% Validation / 15% Test → saved to `data/train_data.json` etc.

### Step 2 — Combined Data Generation (`generate_combined_data.py`)

For each workout sample, generates a matching **daily productivity summary** from the same category (so the workout category and daily state are correlated, just like in real life).

```python
# For a 'struggle' workout, the matching daily summary looks like:
{
    "daily_text": "Meetings: 6 meetings totaling 5.2 hours. Chat: 95 messages. Code: 1 commits. Sleep: 5.5 hours. Workout: 25 minutes. Journal: Woke up feeling exhausted after poor sleep. The workout was particularly challenging today...",
    "daily_label": "Overloaded"
}
```

Output: `data/combined_train_data.json`, `combined_val_data.json`, `combined_test_data.json`

### Step 3 — Model Training

| Script                         | Model                        | Framework               | Trains On                  |
| ------------------------------ | ---------------------------- | ----------------------- | -------------------------- |
| `train_sentiment.py`           | Sentiment (3-class)          | 🤗 DistilBERT + Trainer | `train_data.json`          |
| `train_ner.py`                 | NER (4 entity types)         | spaCy blank NER         | `train_data.json`          |
| `train_classifier.py`          | Performance (3-class)        | 🤗 DistilBERT + Trainer | `train_data.json`          |
| `train_daily_from_combined.py` | Daily Productivity (5-class) | TF-IDF + LogReg         | `combined_train_data.json` |

All models saved to `models/` directory tree.

---

## Data Flow Summary

```
Strava/Google Fit (numeric) ─────────────┐
                                         ▼
                                   workout_nlg.py
                                   (NLG text generation)
                                         │
User workout description (text) ─────────┤
Journal (text) ───────────────────────── ├──► Combined workout text
                                         │
                    ┌────────────────────┤
                    ▼                    ▼
            Sentiment Model      NER Model + Performance Classifier
            (DistilBERT)         (spaCy + DistilBERT)
                    │                    │
                    └────────────────────┘
                              │
                              ▼ workout_analysis
                      ┌───────────────┐
Slack (messages) ─────►              │
GitHub (commits) ─────► Daily Text   │
Calendar (meetings) ──► Assembly     │
Sleep tracker ─────────►             │
Journal ───────────────►             │
                      └──────┬────────┘
                             ▼
                   TF-IDF + Logistic Regression
                   (Daily Productivity Classifier)
                             │
                             ▼ daily_analysis (state + burnout risk)
                      ┌──────────────┐
                      │  Unified     │
                      │  Analyzer    │
                      │  + Insights  │
                      │  + Recs      │
                      └──────────────┘
                             │
                             ▼
             Final Report: state, burnout risk,
             insights, recommendations
```

---

## File Reference

```
NLP-NUMA/
├── core/
│   ├── workout_analyzer.py      # WorkoutAnalyzer class (sentiment + NER + perf)
│   ├── workout_nlg.py           # NLG: numeric metrics → natural language text
│   ├── hybrid_analyzer.py       # HybridWorkoutAnalyzer (text vs numeric cross-validation)
│   └── unified_analyzer.py      # UnifiedAnalyzer (full daily orchestrator)
├── training/
│   ├── generate_training_data.py    # Generates 4,000 workout samples
│   ├── generate_combined_data.py    # Adds daily productivity summaries
│   ├── train_sentiment.py           # Fine-tunes DistilBERT for sentiment
│   ├── train_ner.py                 # Trains spaCy NER model
│   ├── train_classifier.py          # Fine-tunes DistilBERT for performance
│   └── train_daily_from_combined.py # Trains TF-IDF + LogReg daily classifier
├── data/
│   ├── train_data.json          # 2,800 workout samples (70%)
│   ├── val_data.json            # 600 workout samples (15%)
│   ├── test_data.json           # 600 workout samples (15%)
│   ├── combined_train_data.json # Workout + daily combined train set
│   ├── combined_val_data.json
│   └── combined_test_data.json
└── models/                      # Saved trained models (gitignored)
    ├── sentiment_model/
    ├── ner_model/
    ├── workout_classifier/
    │   ├── performance/
    │   └── label_encoders.pkl
    └── daily_productivity_model/
        ├── productivity_classifier.pkl
        └── tfidf_vectorizer.pkl
```
