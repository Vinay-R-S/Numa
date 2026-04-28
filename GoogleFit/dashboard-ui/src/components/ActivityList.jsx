import React from 'react';
import { motion } from 'framer-motion';
import { Clock, Flame, TrendingUp } from 'lucide-react';

const ActivityList = ({ activities }) => {
  const getActivityIcon = (type) => {
    switch (type) {
      case 'Run':
        return '🏃';
      case 'Ride':
        return '🚴';
      default:
        return '🏋️';
    }
  };

  return (
    <div className="glass-effect rounded-2xl p-6 shadow-neumorphic">
      <h3 className="text-xl font-bold text-white mb-4">Recent Activities</h3>
      
      <div className="space-y-3">
        {activities.map((activity, index) => (
          <motion.div
            key={activity.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.01, x: 4 }}
            className="bg-slate-800/40 rounded-xl p-4 border border-slate-700/50 hover:border-slate-600/50 transition-all cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{getActivityIcon(activity.type)}</span>
                <div>
                  <h4 className="text-white font-semibold">{activity.name}</h4>
                  <p className="text-slate-400 text-sm">{activity.time}</p>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-3 mt-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-purple-400" />
                <div>
                  <p className="text-xs text-slate-400">Distance</p>
                  <p className="text-sm font-semibold text-white">{activity.distance}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <div>
                  <p className="text-xs text-slate-400">Duration</p>
                  <p className="text-sm font-semibold text-white">{activity.duration}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-orange-400" />
                <div>
                  <p className="text-xs text-slate-400">Calories</p>
                  <p className="text-sm font-semibold text-white">{activity.calories}</p>
                </div>
              </div>
            </div>
            
            <div className="mt-2 text-xs text-slate-500">
              Pace: <span className="text-slate-400 font-medium">{activity.pace}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default ActivityList;
