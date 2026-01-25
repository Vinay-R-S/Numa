# Antigravity AI System  
## Technical Input and Data Specification

## Overview

Antigravity is an AI-driven personal productivity, health, and wellbeing system designed around explainable, safe, and user-centric decision making.

This document serves as the **authoritative data contract** for the Antigravity platform. It defines:
- All data collected by the system
- The rationale behind each data point
- How raw user inputs are transformed into aggregates
- How aggregates power AI recommendations
- The constraints under which AI agents operate

This README is intended for:
- Backend and frontend engineers
- AI and data engineers
- Product managers and system designers

---

## Core Design Principles

- Raw data captures **user intent and subjective experience**
- Aggregated data captures **objective patterns and trends**
- AI systems **never read raw inputs**
- AI systems **never mutate user data**
- Every AI output must be **traceable to aggregate metrics**
- User control, privacy, and explainability are mandatory

---

## Table of Contents

1. Data Architecture Overview  
2. Raw Input Data Schemas  
3. Aggregated and Derived Data Schemas  
4. Use Cases and Data Utilization  
5. System Rules and Constraints  

---

## 1. Data Architecture Overview

Antigravity follows a layered data architecture:

### Layers

1. **Raw Inputs**
   - Manually entered or device-synced
   - Represent subjective state, intent, and context
   - Immutable once stored

2. **Aggregated Inputs**
   - Computed from raw inputs
   - Represent trends, ratios, baselines, and risks
   - The only data accessible to AI agents

3. **AI Decision Layer**
   - Reads aggregated data only
   - Produces recommendations, plans, and alerts
   - Fully explainable and auditable

---

## 2. Raw Input Data Schemas

### 2.1 Daily State

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `energy_level` | int | Self-reported energy level | Match task difficulty to capacity | 7 |
| `mood` | str | Current mood | Mental state modeling | calm |
| `stress_level` | int | Perceived stress | Burnout detection | 5 |
| `focus_level` | int | Ability to concentrate | Focus-aware planning | 8 |
| `day_constraints` | list[str] | Daily limitations | Prevent unrealistic plans | ["travel"] |

**Validation**
- Scores range from 1 to 10
- Constraints must match predefined enums

---

### 2.2 Tasks

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `task_id` | str | Unique identifier | Task tracking | tsk_1023 |
| `task_title` | str | Task name | User clarity | Write report |
| `task_category` | str | Task type | Categorization | work |
| `effort_level` | int | Required effort | Energy matching | 6 |
| `estimated_duration_min` | int | Time estimate | Scheduling accuracy | 90 |
| `deadline` | datetime or null | Due date | Urgency modeling | 2026-02-01 |
| `dependencies` | list[str] | Blocking tasks | Dependency resolution | ["tsk_1001"] |
| `is_recurring` | bool | Repetition flag | Routine detection | false |
| `recurrence_rule` | str or null | Recurrence logic | Automation | FREQ=WEEKLY |
| `manual_priority_override` | int or null | User priority | Respect intent | 1 |

---

### 2.3 Calendar Events

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `event_id` | str | Event ID | Tracking | evt_552 |
| `event_title` | str | Event name | Context | Team meeting |
| `start_time` | datetime | Start time | Scheduling | 10:00 |
| `end_time` | datetime | End time | Duration | 11:00 |
| `is_fixed` | bool | Movable flag | Rescheduling | true |
| `importance_level` | int | Priority | Conflict resolution | 8 |
| `travel_required` | bool | Travel needed | Buffer planning | true |

---

### 2.4 Goals

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `goal_id` | str | Goal ID | Tracking | goal_21 |
| `goal_title` | str | Goal name | Clarity | Improve fitness |
| `goal_type` | str | Time horizon | Planning scope | long_term |
| `goal_priority_weight` | float | Importance weight | AI weighting | 0.9 |
| `goal_start_date` | date | Start date | Timeline | 2026-01-01 |
| `goal_target_date` | date or null | Target date | Deadline awareness | 2026-06-01 |

---

### 2.5 Routines

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `routine_id` | str | Routine ID | Tracking | rtn_07 |
| `routine_name` | str | Routine name | UX clarity | Morning workout |
| `routine_type` | str | Routine category | Analysis | physical |
| `routine_tasks` | list[str] | Linked tasks | Execution mapping | ["tsk_500"] |
| `skip_reason` | str or null | Skip cause | Optimization | low energy |

---

### 2.6 Physical Inputs

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `sleep_duration_hours` | float | Sleep hours | Recovery modeling | 6.5 |
| `sleep_quality_score` | int | Sleep quality | Fatigue estimation | 7 |
| `steps_count` | int | Daily steps | Activity tracking | 8200 |
| `workout_done` | bool | Workout completed | Habit tracking | true |
| `fatigue_level` | int | Physical fatigue | Load adjustment | 6 |

---

### 2.7 Mental Inputs

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `mood_label` | str | Emotional state | Sentiment modeling | anxious |
| `stress_score` | int | Stress intensity | Burnout detection | 7 |
| `anxiety_score` | int | Anxiety level | Risk modeling | 6 |
| `mental_load_score` | int | Cognitive load | Task throttling | 8 |

---

### 2.8 Journal Entries

| Field Name | Data Type | Description | Rationale | Example |
|-----------|----------|------------|-----------|--------|
| `journal_entry_id` | str | Entry ID | Traceability | jrnl_901 |
| `journal_text` | str | Journal content | Sentiment analysis | Felt overwhelmed |
| `journal_tags` | list[str] | Topic tags | Pattern detection | ["stress"] |
| `is_private` | bool | Privacy flag | Data protection | true |

---

## 3. Aggregated and Derived Data Schemas

Aggregates are **computed outputs** derived from raw inputs.

### Key Aggregate Categories
- Daily Aggregates
- Task Aggregates
- Calendar Aggregates
- Goal Aggregates
- Routine Aggregates
- Physical Aggregates
- Mental Aggregates
- Journal Aggregates
- Weekly and Risk Aggregates
- User Baselines

### Aggregate Characteristics
- Normalized scores and ratios
- Trend indicators
- Rolling windows (7d, 30d)
- Risk and recovery metrics

**Only aggregates are accessible to AI agents.**

---

## 4. Use Cases and Data Utilization

### Use Case 1: User Profile Creation and Capacity Modeling
**Data Sources**: User Profile, Physical Inputs  
**Purpose**: Establish baselines  
**Output**: Personalized daily capacity model  

---

### Use Case 2: Smartwatch Integration
**Data Sources**: Physical Inputs, Physical Aggregates  
**Purpose**: Detect fatigue and recovery needs  
**Output**: Recovery or load reduction recommendations  

---

### Use Case 3: Energy-Based Task Prioritization
**Data Sources**: Daily State, Task Aggregates  
**Purpose**: Prevent overload  
**Output**: Optimized task order  

---

### Use Case 4: Calendar Optimization
**Data Sources**: Calendar Aggregates, Mental Aggregates  
**Purpose**: Reduce burnout  
**Output**: Rescheduling suggestions  

---

### Use Case 5: Burnout Prevention
**Data Sources**: Weekly and Risk Aggregates  
**Purpose**: Early risk detection  
**Output**: Rest and recovery plans  

---

### Use Case 6: Routine Optimization
**Data Sources**: Routine Aggregates  
**Purpose**: Improve consistency  
**Output**: Routine timing and load adjustments  

---

### Use Case 7: Goal Progress Tracking
**Data Sources**: Goal Aggregates  
**Purpose**: Maintain alignment  
**Output**: Goal reprioritization  

---

### Use Case 8: Sleep Debt Management
**Data Sources**: Physical Aggregates, User Baselines  
**Purpose**: Restore energy  
**Output**: Sleep recovery schedule  

---

## 5. System Rules and Constraints

- AI reads aggregated data only
- AI cannot modify raw or aggregate data
- All recommendations must be explainable
- User permissions strictly gate AI autonomy
- Privacy rules override optimization goals
- All metrics must be auditable

---

## Status

This README represents the **single source of truth** for Antigravity data modeling and AI behavior.

Any changes to data structures or rules must be reflected here before implementation.

---
