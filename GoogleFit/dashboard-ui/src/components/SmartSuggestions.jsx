import React from 'react';
import { motion } from 'framer-motion';
import { Target, Footprints, Activity, Flame, Moon, MapPin } from 'lucide-react';

const SmartSuggestions = ({ data }) => {
  // Generate suggestions based on current progress
  const generateSuggestions = () => {
    const suggestions = [];
    
    if (!data) return suggestions;
    
    const steps = data.steps?.value || 0;
    const stepsGoal = 8000;
    const activeMinutes = data.activeMinutes?.value || 0;
    const activeGoal = 60;
    const sleep = data.sleep?.value || 0;
    const sleepGoal = 7;
    const calories = data.calories?.value || 0;
    
    // Steps suggestion
    if (steps < stepsGoal) {
      const remaining = stepsGoal - steps;
      const walkingMinutes = Math.round(remaining / 100); // ~100 steps per minute
      suggestions.push({
        icon: Footprints,
        color: 'cyan',
        title: `Walk ${remaining.toLocaleString()} more steps`,
        subtitle: `About ${walkingMinutes} minutes of walking`,
        priority: stepsGoal - steps > 5000 ? 'high' : 'medium'
      });
    }
    
    // Active minutes suggestion
    if (activeMinutes < activeGoal) {
      const remaining = activeGoal - activeMinutes;
      suggestions.push({
        icon: Activity,
        color: 'emerald',
        title: `Get ${remaining} more active minutes`,
        subtitle: 'Try a quick workout or brisk walk',
        priority: remaining > 30 ? 'high' : 'medium'
      });
    }
    
    // Calories suggestion
    if (calories < 1500) {
      suggestions.push({
        icon: Flame,
        color: 'orange',
        title: 'Boost your calorie burn',
        subtitle: 'Consider adding cardio to your routine',
        priority: 'low'
      });
    }
    
    // Sleep suggestion
    if (sleep > 0 && sleep < 6) {
      suggestions.push({
        icon: Moon,
        color: 'indigo',
        title: 'Aim for earlier bedtime',
        subtitle: 'Try sleeping 1 hour earlier tonight',
        priority: 'high'
      });
    } else if (sleep === 0) {
      suggestions.push({
        icon: Moon,
        color: 'indigo',
        title: 'Track your sleep',
        subtitle: 'Good sleep is essential for recovery',
        priority: 'medium'
      });
    }
    
    // General encouragement if doing well
    if (steps >= stepsGoal && activeMinutes >= activeGoal) {
      suggestions.push({
        icon: Target,
        color: 'purple',
        title: "You're doing great!",
        subtitle: 'Keep up the excellent work',
        priority: 'low'
      });
    }
    
    // Sort by priority
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return suggestions.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]).slice(0, 4);
  };
  
  const suggestions = generateSuggestions();
  
  const getPriorityStyle = (priority) => {
    switch (priority) {
      case 'high':
        return 'border-l-4 border-l-red-500';
      case 'medium':
        return 'border-l-4 border-l-yellow-500';
      default:
        return 'border-l-4 border-l-green-500';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center">
          <Target className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Smart Suggestions</h3>
          <p className="text-xs text-slate-400">Personalized actions for today</p>
        </div>
      </div>
      
      <div className="space-y-3">
        {suggestions.map((suggestion, index) => {
          const Icon = suggestion.icon;
          
          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.02, x: 4 }}
              className={`
                bg-slate-800/40 rounded-xl p-4
                ${getPriorityStyle(suggestion.priority)}
                cursor-pointer transition-all duration-300
                hover:bg-slate-800/60
              `}
            >
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl bg-${suggestion.color}-500/20 flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 text-${suggestion.color}-400`} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{suggestion.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{suggestion.subtitle}</p>
                </div>
                
                {suggestion.priority === 'high' && (
                  <div className="px-2 py-1 bg-red-500/20 rounded-full">
                    <span className="text-xs text-red-400 font-medium">Priority</span>
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
      
      {suggestions.length === 0 && (
        <div className="text-center py-8">
          <p className="text-slate-400">No suggestions right now</p>
          <p className="text-sm text-slate-500">You're on track!</p>
        </div>
      )}
    </motion.div>
  );
};

export default SmartSuggestions;
