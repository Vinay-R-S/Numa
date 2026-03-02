"""
Generate Combined Training Data
Merges workout text data with daily productivity summaries
BALANCED VERSION - Maps to 5 even daily labels
"""

import json
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def generate_daily_summary_from_workout(workout_category):
    """Generate a matching daily summary based on workout category"""
    
    # Mapping workout categories to daily patterns
    patterns = {
        'struggle': {
            'meetings': random.randint(4, 7),
            'meeting_hours': round(random.uniform(3.5, 6.0), 1),
            'messages': random.randint(70, 130),
            'commits': random.randint(0, 2),
            'sleep': round(random.uniform(4.5, 6.0), 1),
            'workout_min': random.randint(15, 30),
            'journal_phrases': [
                'Woke up feeling exhausted after poor sleep. The workout was particularly challenging today, and I struggled to maintain my usual pace. At work, constant meetings left me drained with little time for focused work. I\'m noticing my energy levels are consistently low this week. Need to reassess my commitments and find better balance.',
                
                'Sleep quality was terrible last night - only got about 5 hours. During my run, my body felt heavy and unresponsive, couldn\'t find any rhythm. Work was overwhelming with back-to-back coordination calls that went over time. Had trouble concentrating on deep work tasks between meetings. I need to prioritize rest and recovery or I\'ll burn out completely.',
                
                'Today was really tough physically and mentally. Didn\'t get enough rest, which affected both my morning workout and work performance throughout the day. Had too many meetings scheduled and couldn\'t find time for deep focus work. Feeling mentally and physically drained by evening. This pattern of overcommitment needs to change.',
                
                'Struggled through the entire day from start to finish. Poor sleep cascaded into a difficult workout where I had to slow down significantly and cut it shorter than planned. Work demands were relentless with urgent requests coming in constantly via Slack. I\'m noticing a concerning pattern of overcommitment that\'s affecting my health and performance.',
                
                'Exhausting day all around. Workout was a real grind - legs felt like lead and had to push through sheer willpower. Work had too many context switches between projects and urgent issues. By afternoon I was running on fumes. The combination of training load and work stress is catching up with me. Time to scale back before something breaks.'
            ]
        },
        
        'success': {
            'meetings': random.randint(1, 3),
            'meeting_hours': round(random.uniform(1.0, 2.5), 1),
            'messages': random.randint(20, 40),
            'commits': random.randint(5, 8),
            'sleep': round(random.uniform(7.5, 8.5), 1),
            'workout_min': random.randint(30, 50),
            'journal_phrases': [
                'Amazing day overall! Had a great workout this morning which set a positive tone for the rest of the day. Hit a new PR and felt strong throughout. Work was productive with good progress on my main project - knocked out three major features. Felt energized and focused from morning to evening. This is the kind of balance I want to maintain consistently.',
                
                'Everything clicked today. Slept well last night, crushed my workout with a new personal best, and had exceptional focus at work. Completed all my priority tasks and even had time for some creative exploration work I\'d been putting off. Energy levels stayed high throughout the day. Feeling accomplished and motivated to keep this momentum going.',
                
                'One of those rare days where everything aligns perfectly. Morning workout felt strong and effortless - body responded beautifully to every demand. At work, I maintained deep focus for hours and made significant progress on the complex refactoring I\'ve been working on. High energy levels throughout. Want to understand what made this work so well so I can replicate it.',
                
                'Perfect execution across the board today. Well-rested from good sleep, which translated to a strong workout performance where I felt powerful and controlled. Work was highly productive with minimal distractions - used time blocking effectively. Completed two major milestones ahead of schedule. I\'m in a good rhythm and need to protect these patterns and boundaries.',
                
                'Exceptional day that reminds me why I love this lifestyle. Workout was phenomenal - everything felt easy and smooth, hit paces that usually feel hard. Carried that energy into work where I was in flow state for most of the day. Solved a tricky bug that had been blocking progress for days. Collaborations with the team were energizing rather than draining. Days like this make all the hard work worth it.'
            ]
        },
        
        'recovery': {
            'meetings': random.randint(0, 2),
            'meeting_hours': round(random.uniform(0.0, 1.5), 1),
            'messages': random.randint(5, 20),
            'commits': random.randint(0, 1),
            'sleep': round(random.uniform(8.0, 9.0), 1),
            'workout_min': random.randint(20, 35),
            'journal_phrases': [
                'Dedicated today to rest and recovery. Did only light movement and avoided pushing myself at all. Kept the workout super easy and short. Work was minimal with no meetings scheduled - just administrative tasks and planning. Mental fog is starting to lift, and I\'m feeling more grounded. This reset was definitely needed after last week\'s heavy load.',
                
                'Recovery day as planned. Slept in until 8am, did some gentle stretching and an easy spin, and kept work commitments light. Only one standup meeting today. Spent time journaling and reflecting on recent patterns and what\'s been working versus what hasn\'t. Feeling recharged and ready to tackle next week with fresh energy and clearer priorities.',
                
                'Took the day to fully recharge both physically and mentally. No intense workouts, just restorative activities like yoga and walking. Minimal work commitments allowed for actual mental rest - no Slack notifications, no urgent emails. I can feel my energy stores rebuilding hour by hour. This kind of intentional recovery is crucial for long-term sustainability and performance.',
                
                'Complete rest day - exactly what I needed. Finally caught up on sleep with 9 hours last night. Gave my body time to recover with just light movement. Work was administrative tasks only, nothing demanding or stressful. Mental clarity has improved significantly compared to yesterday. I need to build in these recovery periods more consistently rather than waiting until I\'m completely depleted.',
                
                'Intentional recovery and restoration today. Light workout focused on mobility and blood flow rather than performance. Work was catch-up tasks and planning for next sprint - no pressure or deadlines. Took a proper lunch break and went for a walk outside. Evening yoga session helped release tension. Feeling the benefits already - body feels less beaten up and mind feels clearer. Recovery is training too.'
            ]
        },
        
        'neutral': {
            'meetings': random.randint(2, 3),
            'meeting_hours': round(random.uniform(1.5, 2.5), 1),
            'messages': random.randint(25, 45),
            'commits': random.randint(3, 5),
            'sleep': round(random.uniform(7.0, 7.5), 1),
            'workout_min': random.randint(20, 30),
            'journal_phrases': [
                'Standard day without any major highs or lows. Workout was routine maintenance, nothing special but got it done. Work progressed steadily with a mix of meetings and focused coding time. Felt neither particularly energized nor drained throughout. Just a normal, consistent day. Sometimes consistency is exactly what\'s needed for long-term progress.',
                
                'Regular workday. Morning workout was fine, not exceptional but not bad either - right in the middle of my normal range. Had my usual meetings including standup and sprint planning, made progress on ongoing projects without any major breakthroughs. Energy levels were stable throughout. Sometimes these steady days are underrated - they\'re the foundation of longer-term progress.',
                
                'Unremarkable but productive day. Workout was at my normal pace and effort level, checked all the boxes without pushing limits. Work had a good balance of collaboration in meetings and individual focus time on implementation work. Maintained steady progress without any standout moments either positive or negative. This stability feels sustainable and I\'m okay with that.',
                
                'Typical day following my established routines. Workout checked the box without pushing limits - did what was planned, no more, no less. Work tasks moved forward at a reasonable pace through a combination of solo work and team coordination. Neither inspired nor frustrated. These steady days are actually the majority and they compound over time into real progress.',
                
                'Another solid day in the books. Workout was standard training stimulus - not easy but not crushing either. Work had the usual mix of coding, code review, and team sync. Made incremental progress on several fronts. Energy and motivation were steady state. It\'s easy to overlook these days but they\'re actually what builds the foundation for the occasional breakthrough days.'
            ]
        },
        
        'fatigue': {
            'meetings': random.randint(4, 6),
            'meeting_hours': round(random.uniform(3.0, 5.0), 1),
            'messages': random.randint(60, 100),
            'commits': random.randint(1, 3),
            'sleep': round(random.uniform(5.0, 6.5), 1),
            'workout_min': random.randint(0, 20),
            'journal_phrases': [
                'Low energy throughout the entire day. Workout felt harder than it should have been - had to cut it short. At work, I found it difficult to maintain focus with constant distractions and interruptions from multiple channels. Brain felt foggy and I couldn\'t get into any kind of flow state. Need to reassess my workload and recovery balance. This isn\'t sustainable.',
                
                'Struggled with energy all day. Sleep wasn\'t great at only 6 hours, which showed in both my workout and work performance. Tried to do my usual training but body wasn\'t having it. Meetings felt draining rather than collaborative, and I was just going through the motions. Had trouble concentrating on deep work tasks between all the context switching. I\'m running on empty and need to make changes fast.',
                
                'Exhausting day marked by mental fatigue more than physical. Workout was sluggish and I had to push through with sheer willpower rather than actual energy. Work involved too much context switching between different projects and urgent requests that kept breaking my concentration. Couldn\'t find any momentum or rhythm. Feeling stretched thin across too many priorities with too little recovery time.',
                
                'Drained from start to finish. Morning workout was a struggle, lacking the usual energy and enthusiasm. Considered skipping but forced myself out, which might have been a mistake. Work was scattered with too many competing demands and not enough focus time. Found myself distracted and unable to sustain concentration for long periods. Clear signs I need better boundaries and more recovery time built into my schedule.',
                
                'Completely wiped out today. Barely dragged myself through a shortened workout - every step felt like wading through mud. Work was a blur of meetings and firefighting urgent issues with no time for planned work. By afternoon I was practically a zombie, just trying to make it to 5pm. This level of fatigue is a red flag that something needs to change in my training or work schedule or both.'
            ]
        },
        
        'pain': {
            'meetings': random.randint(3, 5),
            'meeting_hours': round(random.uniform(2.5, 4.0), 1),
            'messages': random.randint(40, 70),
            'commits': random.randint(1, 3),
            'sleep': round(random.uniform(5.5, 7.0), 1),
            'workout_min': random.randint(10, 25),
            'journal_phrases': [
                'Physical discomfort affected my entire day. Noticed pain during my workout which made me cut it short - not worth risking a more serious injury. At work, the nagging discomfort was distracting and made it hard to focus on tasks during long meetings. Need to address this before it becomes a bigger issue. Considering scheduling a physio appointment this week to get it checked out properly.',
                
                'Dealing with persistent discomfort that\'s starting to impact my routine. Had to modify my workout significantly to avoid aggravating the issue - did about half of what I planned at reduced intensity. At work, the nagging pain made it difficult to sit comfortably through back-to-back meetings. I\'m concerned this might require medical attention if it doesn\'t improve soon. Taking tomorrow off from training to let it settle.',
                
                'Pain was a constant companion today. Tried to push through my workout but had to stop early to avoid making it worse - it\'s that sharp kind of pain rather than normal soreness. Work productivity suffered as I struggled to find a comfortable position at my desk. This is affecting both my physical training and professional performance. I\'m learning the hard way that ignoring these signals makes things worse. Need to prioritize recovery over consistency right now.',
                
                'Today highlighted how much physical health impacts everything else. Workout was limited due to ongoing discomfort - tried to start but had to abort after 10 minutes. At work, I found myself distracted by pain and unable to fully engage in meetings and coding sessions. Took more breaks than usual just to move around and try to ease the discomfort. Time to take recovery seriously and possibly get professional help.',
                
                'Frustrating day dealing with injury concerns. Started my workout but the pain flared up within minutes so I stopped immediately - no point risking a major injury. Work was challenging too - hard to concentrate when you\'re uncomfortable. Had to stand during meetings and take frequent stretch breaks. This is the downside of training hard - sometimes your body demands recovery whether you\'re ready or not. Scheduling a physio appointment and taking the next few days completely off training.'
            ]
        }
    }
    
    pattern = patterns[workout_category]
    
    meetings = pattern['meetings']
    meeting_hours = pattern['meeting_hours']
    messages = pattern['messages']
    commits = pattern['commits']
    sleep = pattern['sleep']
    workout_min = pattern['workout_min']
    journal = random.choice(pattern['journal_phrases'])
    
    daily_text = (
        f"Meetings: {meetings} meetings totaling {meeting_hours} hours. "
        f"Chat: {messages} messages. "
        f"Code: {commits} commits. "
        f"Sleep: {sleep} hours. "
        f"Workout: {workout_min} minutes. "
        f"Journal: {journal}"
    )
    
    # BALANCED MAPPING - Each daily label gets equal representation
    label_mapping = {
        'success': 'High_Performance',   # 800 samples
        'struggle': 'Overloaded',        # 800 samples
        'neutral': 'Focused',            # 800 samples
        'recovery': 'Recovery',          # 400 samples
        'fatigue': 'Distracted',         # 800 samples
        'pain': 'Recovery'               # 400 samples
    }
    
    return {
        'daily_text': daily_text,
        'daily_label': label_mapping[workout_category],
        'daily_metrics': {
            'meetings': meetings,
            'meeting_hours': meeting_hours,
            'messages': messages,
            'commits': commits,
            'sleep': sleep,
            'workout_minutes': workout_min
        }
    }


def main():
    print("="*80)
    print("GENERATING COMBINED TRAINING DATA (BALANCED)")
    print("="*80)
    
    # Load existing workout data
    data_dir = SCRIPT_DIR / 'data'
    train_path = data_dir / 'train_data.json'
    val_path = data_dir / 'val_data.json'
    test_path = data_dir / 'test_data.json'
    
    print("\nLoading workout data...")
    with open(train_path) as f:
        train_workout = json.load(f)
    with open(val_path) as f:
        val_workout = json.load(f)
    with open(test_path) as f:
        test_workout = json.load(f)
    
    print(f"  Train: {len(train_workout)} samples")
    print(f"  Val: {len(val_workout)} samples")
    print(f"  Test: {len(test_workout)} samples")
    
    # Generate combined data
    print("\nGenerating daily summaries for each workout...")
    
    def combine_data(workout_list):
        combined = []
        for workout in workout_list:
            daily = generate_daily_summary_from_workout(workout['category'])
            
            combined_sample = {
                'workout_text': workout['text'],
                'workout_category': workout['category'],
                'workout_labels': workout['labels'],
                'workout_entities': workout['entities'],
                'daily_text': daily['daily_text'],
                'daily_label': daily['daily_label'],
                'daily_metrics': daily['daily_metrics']
            }
            combined.append(combined_sample)
        return combined
    
    train_combined = combine_data(train_workout)
    val_combined = combine_data(val_workout)
    test_combined = combine_data(test_workout)
    
    # Show daily label distribution
    from collections import Counter
    all_combined = train_combined + val_combined + test_combined
    daily_labels = [s['daily_label'] for s in all_combined]
    
    print("\n✓ Daily label distribution:")
    for label, count in Counter(daily_labels).items():
        print(f"   {label}: {count}")
    
    # Save combined data
    output_train = data_dir / 'combined_train_data.json'
    output_val = data_dir / 'combined_val_data.json'
    output_test = data_dir / 'combined_test_data.json'
    
    with open(output_train, 'w') as f:
        json.dump(train_combined, f, indent=2)
    with open(output_val, 'w') as f:
        json.dump(val_combined, f, indent=2)
    with open(output_test, 'w') as f:
        json.dump(test_combined, f, indent=2)
    
    print("\n" + "="*80)
    print("✓ Combined data generated successfully!")
    print("="*80)
    print(f"\nTrain: {len(train_combined)} samples → {output_train.name}")
    print(f"Val: {len(val_combined)} samples → {output_val.name}")
    print(f"Test: {len(test_combined)} samples → {output_test.name}")
    
    # Show sample
    print("\n" + "="*80)
    print("SAMPLE COMBINED DATA")
    print("="*80)
    sample = random.choice(train_combined)
    print(f"\nWorkout text: {sample['workout_text']}")
    print(f"Workout category: {sample['workout_category']}")
    print(f"Workout performance: {sample['workout_labels']['performance']}")
    print(f"\nDaily label: {sample['daily_label']}")
    print(f"Daily journal (first 100 chars): {sample['daily_text'][sample['daily_text'].index('Journal:')+9:][:100]}...")


if __name__ == "__main__":
    main()