import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus, ArrowRight } from 'lucide-react';

const ComparisonPanel = ({ data, previousData }) => {
  // Mock previous data if not provided
  const mockPrevious = {
    steps: { value: 6500 },
    activeMinutes: { value: 45 },
    calories: { value: 1800 },
    distance: { value: 4.2 },
    sleep: { value: 6.5 }
  };
  
  const prev = previousData || mockPrevious;
  
  const comparisons = [
    {
      label: 'Steps',
      current: data?.steps?.value || 0,
      previous: prev.steps?.value || 0,
      color: 'cyan'
    },
    {
      label: 'Active',
      current: data?.activeMinutes?.value || 0,
      previous: prev.activeMinutes?.value || 0,
      unit: 'min',
      color: 'emerald'
    },
    {
      label: 'Calories',
      current: data?.calories?.value || 0,
      previous: prev.calories?.value || 0,
      unit: 'kcal',
      color: 'orange'
    },
    {
      label: 'Sleep',
      current: data?.sleep?.value || 0,
      previous: prev.sleep?.value || 0,
      unit: 'hrs',
      color: 'indigo',
      decimals: 1
    }
  ];
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
          <ArrowRight className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Today vs Yesterday</h3>
          <p className="text-xs text-slate-400">Daily comparison</p>
        </div>
      </div>
      
      <div className="space-y-4">
        {comparisons.map((item, index) => {
          const diff = item.current - item.previous;
          const percentChange = item.previous > 0 
            ? ((diff / item.previous) * 100).toFixed(0)
            : 0;
          const isPositive = diff > 0;
          const isNeutral = diff === 0;
          
          return (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-slate-800/40 rounded-xl p-4 border border-slate-700/50"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-8 rounded-full bg-${item.color}-500`} />
                  <div>
                    <p className="text-sm text-slate-400">{item.label}</p>
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-bold text-${item.color}-400`}>
                        {item.decimals 
                          ? item.current.toFixed(item.decimals)
                          : item.current.toLocaleString()}
                        {item.unit && <span className="text-sm ml-1">{item.unit}</span>}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="flex flex-col items-end">
                  <div className={`
                    flex items-center gap-1 px-2 py-1 rounded-lg
                    ${isPositive ? 'bg-emerald-500/20 text-emerald-400' : 
                      isNeutral ? 'bg-slate-500/20 text-slate-400' : 
                      'bg-red-500/20 text-red-400'}
                  `}>
                    {isPositive ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : isNeutral ? (
                      <Minus className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    <span className="text-sm font-semibold">
                      {isPositive ? '+' : ''}{percentChange}%
                    </span>
                  </div>
                  
                  <span className="text-xs text-slate-500 mt-1">
                    {isPositive ? '+' : ''}{item.decimals 
                      ? diff.toFixed(item.decimals)
                      : diff.toLocaleString()} {item.unit || ''}
                  </span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};

export default ComparisonPanel;
