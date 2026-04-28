import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Lightbulb, Award, AlertTriangle, Zap } from 'lucide-react';

const InsightCard = ({ type, message, metric, change, icon: CustomIcon }) => {
  const getInsightStyle = () => {
    switch (type) {
      case 'positive':
        return {
          icon: TrendingUp,
          gradient: 'from-emerald-500/20 to-emerald-600/10',
          border: 'border-emerald-500/30',
          iconBg: 'from-emerald-500 to-emerald-600',
          text: 'text-emerald-400'
        };
      case 'negative':
        return {
          icon: TrendingDown,
          gradient: 'from-red-500/20 to-red-600/10',
          border: 'border-red-500/30',
          iconBg: 'from-red-500 to-red-600',
          text: 'text-red-400'
        };
      case 'achievement':
        return {
          icon: Award,
          gradient: 'from-yellow-500/20 to-amber-600/10',
          border: 'border-yellow-500/30',
          iconBg: 'from-yellow-500 to-amber-600',
          text: 'text-yellow-400'
        };
      case 'warning':
        return {
          icon: AlertTriangle,
          gradient: 'from-orange-500/20 to-orange-600/10',
          border: 'border-orange-500/30',
          iconBg: 'from-orange-500 to-orange-600',
          text: 'text-orange-400'
        };
      case 'tip':
        return {
          icon: Lightbulb,
          gradient: 'from-cyan-500/20 to-blue-600/10',
          border: 'border-cyan-500/30',
          iconBg: 'from-cyan-500 to-blue-600',
          text: 'text-cyan-400'
        };
      default:
        return {
          icon: Zap,
          gradient: 'from-purple-500/20 to-purple-600/10',
          border: 'border-purple-500/30',
          iconBg: 'from-purple-500 to-purple-600',
          text: 'text-purple-400'
        };
    }
  };
  
  const style = getInsightStyle();
  const Icon = CustomIcon || style.icon;
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      whileHover={{ scale: 1.02, x: 4 }}
      className={`
        bg-gradient-to-r ${style.gradient}
        border ${style.border}
        rounded-xl p-4 flex items-center gap-4
        transition-all duration-300 cursor-pointer
      `}
    >
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${style.iconBg} flex items-center justify-center flex-shrink-0`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white font-medium">{message}</p>
        {metric && (
          <p className="text-xs text-slate-400 mt-1">
            {metric}
            {change && (
              <span className={`ml-2 font-semibold ${style.text}`}>
                {change > 0 ? '+' : ''}{change}%
              </span>
            )}
          </p>
        )}
      </div>
    </motion.div>
  );
};

export default InsightCard;
