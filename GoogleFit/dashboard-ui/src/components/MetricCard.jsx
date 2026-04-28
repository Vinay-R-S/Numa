import React from 'react';
import { motion } from 'framer-motion';

const MetricCard = ({ icon: Icon, value, unit, label, color, percentage }) => {
  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      className="relative group"
    >
      <div className="glass-effect rounded-2xl p-6 shadow-neumorphic hover:shadow-neumorphic-inset transition-all duration-300">
        {/* Gradient overlay */}
        <div 
          className={`absolute inset-0 bg-gradient-to-br ${color.gradient} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-300`}
        />
        
        {/* Content */}
        <div className="relative z-10">
          {/* Icon */}
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color.gradient} flex items-center justify-center mb-4 shadow-lg ${color.glow}`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          
          {/* Value */}
          <div className="mb-2">
            <span className="text-4xl font-bold text-white">
              {value.toLocaleString()}
            </span>
            <span className="text-lg text-slate-400 ml-2">{unit}</span>
          </div>
          
          {/* Label */}
          <div className="text-slate-400 text-sm font-medium mb-3">
            {label}
          </div>
          
          {/* Progress bar (if percentage provided) */}
          {percentage !== undefined && (
            <div className="relative w-full h-2 bg-slate-700 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${percentage}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
                className={`absolute top-0 left-0 h-full bg-gradient-to-r ${color.gradient} rounded-full`}
              />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default MetricCard;
