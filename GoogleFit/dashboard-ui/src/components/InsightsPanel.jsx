import React from 'react';
import { motion } from 'framer-motion';
import { Lightbulb } from 'lucide-react';
import InsightCard from './InsightCard';

const InsightsPanel = ({ data }) => {
  // Generate insights based on data
  const generateInsights = () => {
    const insights = [];

    if (!data) return insights;

    const steps = data.steps?.value || 0;
    const stepsGoal = 8000;
    const activeMinutes = data.activeMinutes?.value || 0;
    const activeGoal = 60;
    const sleep = data.sleep?.value || 0;
    const sleepGoal = 7;
    const calories = data.calories?.value || 0;

    // Only generate insights if we have at least some real data
    const hasAnyData = steps > 0 || activeMinutes > 0 || calories > 0;
    if (!hasAnyData) return insights;

    
    // Steps insights
    if (steps >= stepsGoal) {
      insights.push({
        type: 'achievement',
        message: '🎉 You reached your daily step goal!',
        metric: `${steps.toLocaleString()} steps today`
      });
    } else {
      const remaining = stepsGoal - steps;
      insights.push({
        type: 'tip',
        message: `Walk ${remaining.toLocaleString()} more steps to reach your goal`,
        metric: `${Math.round((steps / stepsGoal) * 100)}% complete`
      });
    }
    
    // Active minutes insights
    if (activeMinutes >= activeGoal) {
      insights.push({
        type: 'positive',
        message: 'Great job staying active today!',
        metric: `${activeMinutes} active minutes`,
        change: Math.round(((activeMinutes - activeGoal) / activeGoal) * 100)
      });
    } else if (activeMinutes < 30) {
      insights.push({
        type: 'warning',
        message: 'Try to move more today',
        metric: `Only ${activeMinutes} active minutes so far`
      });
    }
    
    // Sleep insights
    if (sleep > 0) {
      if (sleep >= sleepGoal) {
        insights.push({
          type: 'positive',
          message: 'Well rested! Great sleep duration',
          metric: `${sleep.toFixed(1)} hours of sleep`
        });
      } else if (sleep < 6) {
        insights.push({
          type: 'negative',
          message: 'Consider getting more sleep tonight',
          metric: `Only ${sleep.toFixed(1)} hours last night`
        });
      }
    }
    
    // Calories insight
    if (calories > 0) {
      if (calories >= 2000) {
        insights.push({
          type: 'positive',
          message: 'Good calorie burn today!',
          metric: `${calories.toLocaleString()} kcal burned`
        });
      }
    }
    
    // Best day suggestion (mock)
    insights.push({
      type: 'achievement',
      message: '🏆 Best day this week: Thursday with 9,500 steps',
      metric: 'Keep up the momentum!'
    });
    
    return insights.slice(0, 5); // Limit to 5 insights
  };
  
  const insights = generateInsights();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
          <Lightbulb className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Today's Insights</h3>
          <p className="text-xs text-slate-400">Personalized recommendations</p>
        </div>
      </div>
      
      <div className="space-y-3">
        {insights.length > 0 ? insights.map((insight, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <InsightCard {...insight} />
          </motion.div>
        )) : (
          <div className="text-center py-8">
            <p className="text-slate-500 text-sm">Waiting for data…</p>
            <p className="text-xs text-slate-600 mt-1">Insights appear once Google Fit syncs activity.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default InsightsPanel;
