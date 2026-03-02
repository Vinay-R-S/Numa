"""
Natural Language Generation for Workout Data
Converts numeric workout metrics into descriptive text
"""

def generate_workout_text(data):
    """
    Generate natural language description from workout metrics
    NOW WITH EMOTIONAL/HUMAN-LIKE LANGUAGE
    """
    
    if not data:
        return ""
    
    # Extract metrics
    distance = data.get('distance_km', 0)
    duration = data.get('duration_min', 0)
    avg_hr = data.get('avg_heart_rate', 0)
    max_hr = data.get('max_heart_rate', 0)
    elevation = data.get('elevation_gain', 0)
    pace = data.get('pace', 0)
    sleep = data.get('sleep', 7)
    
    # Baselines for comparison
    baseline_hr = data.get('baseline_hr', 145)
    baseline_pace = data.get('baseline_pace', 5.5)
    
    # Calculate ratios
    pace_ratio = pace / baseline_pace if pace > 0 and baseline_pace > 0 else 1.0
    hr_ratio = avg_hr / baseline_hr if avg_hr > 0 and baseline_hr > 0 else 1.0
    
    # Determine overall tone based on metrics
    if pace_ratio < 0.9 and hr_ratio < 1.05 and sleep >= 7.5:
        tone = "excellent"
    elif pace_ratio < 0.95 and hr_ratio < 1.1:
        tone = "good"
    elif pace_ratio > 1.25 or hr_ratio > 1.2 or sleep < 6:
        tone = "struggle"
    elif pace_ratio > 1.15 or hr_ratio > 1.15:
        tone = "challenging"
    else:
        tone = "normal"
    
    # Start building description with emotional language
    parts = []
    
    # 1. Opening with emotional context
    if tone == "excellent":
        if distance >= 10:
            parts.append(f"Amazing {distance:.1f}km run today! Felt strong and energized throughout")
        else:
            parts.append(f"Great {distance:.1f}km workout! Everything clicked perfectly")
    
    elif tone == "good":
        if distance >= 10:
            parts.append(f"Solid {distance:.1f}km effort today")
        else:
            parts.append(f"Good {distance:.1f}km session, felt pretty strong")
    
    elif tone == "struggle":
        if distance >= 10:
            parts.append(f"Tough {distance:.1f}km today, really struggled")
        else:
            parts.append(f"Struggled through {distance:.1f}km, not my best day")
    
    elif tone == "challenging":
        parts.append(f"Challenging {distance:.1f}km workout, had to push hard")
    
    else:
        parts.append(f"Standard {distance:.1f}km run today")
    
    # 2. Pace commentary with emotion
    if pace > 0 and baseline_pace > 0:
        if pace_ratio < 0.85:
            parts.append(f"Crushed my usual pace at {pace:.1f} min/km - felt fast and controlled!")
        elif pace_ratio < 0.95:
            parts.append(f"Faster than normal at {pace:.1f} min/km, maintained good form")
        elif pace_ratio > 1.3:
            parts.append(f"Really slow pace at {pace:.1f} min/km, legs felt heavy and unresponsive")
        elif pace_ratio > 1.15:
            parts.append(f"Slower than usual at {pace:.1f} min/km, struggled to find rhythm")
        else:
            parts.append(f"Maintained consistent {pace:.1f} min/km pace")
    
    # 3. Heart rate with physical feelings
    if avg_hr > 0 and baseline_hr > 0:
        if hr_ratio > 1.2:
            parts.append(f"Heart rate was really elevated at {avg_hr} bpm (max {max_hr}), felt like I was working too hard")
        elif hr_ratio > 1.1:
            parts.append(f"HR higher than normal at {avg_hr} bpm, breathing was labored")
        elif hr_ratio < 0.9:
            parts.append(f"Heart rate felt comfortable at {avg_hr} bpm, good aerobic control")
    
    # 4. Elevation with effort description
    if elevation > 200:
        parts.append(f"The {elevation}m of climbing really tested me, quads were burning on the uphills")
    elif elevation > 100:
        parts.append(f"Some decent hills today ({elevation}m elevation), felt the effort in my legs")
    
    # 5. Sleep impact with emotional state
    if sleep < 5.5:
        parts.append(f"Terrible sleep last night ({sleep:.1f}h) - felt exhausted and struggled through the whole workout")
    elif sleep < 6.5:
        parts.append(f"Poor sleep ({sleep:.1f}h) definitely affected my energy levels today")
    elif sleep >= 8.5:
        parts.append(f"Slept great ({sleep:.1f}h) and it showed - had tons of energy!")
    elif sleep >= 7.5:
        parts.append(f"Well rested with {sleep:.1f}h sleep, felt good throughout")
    
    # 6. Overall assessment with clear emotion
    if tone == "excellent":
        parts.append("One of those perfect days where everything just flows. Need to remember what I did right!")
    elif tone == "good":
        parts.append("Felt strong and confident. Good day overall")
    elif tone == "struggle":
        if sleep < 6:
            parts.append("Body clearly needs more recovery. Going to prioritize rest")
        else:
            parts.append("Off day - it happens. Will bounce back")
    elif tone == "challenging":
        parts.append("Had to dig deep but got it done")
    
    # Join with proper punctuation
    description = ". ".join(parts)
    if not description.endswith('.') and not description.endswith('!'):
        description += "."
    
    return description


def _generate_overall_assessment(pace_ratio, hr_ratio, sleep):
    """Generate overall performance assessment"""
    
    # Struggle indicators
    if pace_ratio > 1.25 and hr_ratio > 1.15:
        return "Signs of overexertion and fatigue"
    
    if pace_ratio > 1.2 and sleep < 6:
        return "Sleep deprivation clearly impacting performance"
    
    if hr_ratio > 1.2 and pace_ratio > 1.15:
        return "Working hard but struggling with pace"
    
    # Positive indicators
    if pace_ratio < 0.95 and hr_ratio < 1.0:
        return "Strong performance with good efficiency"
    
    if pace_ratio < 0.9:
        return "Excellent pace achieved"
    
    # Neutral
    if 0.95 <= pace_ratio <= 1.1 and 0.95 <= hr_ratio <= 1.1:
        return "Consistent performance maintained"
    
    return ""


def generate_workout_with_injury(data, injury_indicators):
    """
    Generate text that includes injury/pain indicators
    
    injury_indicators: {
        'body_parts': ['knees', 'ankles'],
        'symptoms': ['pain', 'sore'],
        'severity': 'moderate'  # 'mild', 'moderate', 'severe'
    }
    """
    
    base_text = generate_workout_text(data)
    
    if not injury_indicators:
        return base_text
    
    body_parts = injury_indicators.get('body_parts', [])
    symptoms = injury_indicators.get('symptoms', [])
    severity = injury_indicators.get('severity', 'moderate')
    
    if not body_parts and not symptoms:
        return base_text
    
    # Build injury description
    injury_parts = []
    
    if body_parts:
        bp_text = ', '.join(body_parts)
        if symptoms:
            symptom_text = ' and '.join(symptoms)
            if severity == 'severe':
                injury_parts.append(f"Significant {symptom_text} in {bp_text}")
            elif severity == 'moderate':
                injury_parts.append(f"{bp_text.capitalize()} felt {symptom_text}")
            else:
                injury_parts.append(f"Mild discomfort in {bp_text}")
        else:
            injury_parts.append(f"Issues with {bp_text}")
    
    # Combine with base text
    if injury_parts:
        injury_text = ". ".join(injury_parts)
        return f"{base_text} {injury_text}. May require rest or attention."
    
    return base_text


# Example usage and testing
if __name__ == "__main__":
    print("="*80)
    print("WORKOUT NLG - TEXT GENERATION EXAMPLES")
    print("="*80)
    
    # Test 1: Struggling workout
    test1 = {
        'distance_km': 5.0,
        'duration_min': 40.0,
        'avg_heart_rate': 175,
        'max_heart_rate': 185,
        'pace': 8.0,
        'sleep': 5.0,
        'baseline_hr': 145,
        'baseline_pace': 5.5
    }
    
    print("\nTest 1: Struggling Workout")
    print("-" * 80)
    print(generate_workout_text(test1))
    
    # Test 2: Great performance
    test2 = {
        'distance_km': 10.0,
        'duration_min': 45.0,
        'avg_heart_rate': 155,
        'max_heart_rate': 170,
        'pace': 4.5,
        'sleep': 8.0,
        'baseline_hr': 145,
        'baseline_pace': 5.5
    }
    
    print("\nTest 2: Strong Performance")
    print("-" * 80)
    print(generate_workout_text(test2))
    
    # Test 3: With injury
    test3 = {
        'distance_km': 8.0,
        'duration_min': 50.0,
        'avg_heart_rate': 170,
        'pace': 6.2,
        'sleep': 6.5,
        'baseline_hr': 145,
        'baseline_pace': 5.5
    }
    
    injury_info = {
        'body_parts': ['knees', 'ankles'],
        'symptoms': ['sore', 'painful'],
        'severity': 'moderate'
    }
    
    print("\nTest 3: With Injury Indicators")
    print("-" * 80)
    print(generate_workout_with_injury(test3, injury_info))
    
    print("\n" + "="*80)