import React from 'react';
import { motion } from 'framer-motion';
import { Clock, Footprints, Bike, Moon, Dumbbell, Waves } from 'lucide-react';

const ActivityTimeline = ({ activities }) => {
  // Mock activities if not provided
  const mockActivities = [
    { type: 'Sleep', startTime: '00:00', endTime: '07:30', duration: 450, icon: Moon, color: 'indigo' },
    { type: 'Walking', startTime: '08:00', endTime: '08:30', duration: 30, icon: Footprints, color: 'cyan' },
    { type: 'Workout', startTime: '12:00', endTime: '13:00', duration: 60, icon: Dumbbell, color: 'orange' },
    { type: 'Cycling', startTime: '17:30', endTime: '18:15', duration: 45, icon: Bike, color: 'emerald' },
    { type: 'Walking', startTime: '19:00', endTime: '19:45', duration: 45, icon: Footprints, color: 'cyan' },
  ];
  
  const activityData = activities || mockActivities;
  
  // Calculate total tracked time
  const totalMinutes = activityData.reduce((sum, a) => sum + a.duration, 0);
  
  // Calculate percentage width for each activity
  const dayMinutes = 24 * 60; // Total minutes in a day
  
  const getTimePosition = (time) => {
    const [hours, minutes] = time.split(':').map(Number);
    return ((hours * 60 + minutes) / dayMinutes) * 100;
  };
  
  const getDurationWidth = (duration) => {
    return (duration / dayMinutes) * 100;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
            <Clock className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Activity Timeline</h3>
            <p className="text-xs text-slate-400">Today's activities</p>
          </div>
        </div>
        
        <div className="text-right">
          <p className="text-sm text-slate-400">Total Active</p>
          <p className="text-xl font-bold text-purple-400">
            {Math.floor(totalMinutes / 60)}h {totalMinutes % 60}m
          </p>
        </div>
      </div>
      
      {/* Timeline bar */}
      <div className="relative h-12 bg-slate-800/50 rounded-xl overflow-hidden mb-4">
        {/* Time markers */}
        <div className="absolute inset-0 flex justify-between items-center px-2">
          {[0, 6, 12, 18, 24].map((hour) => (
            <div key={hour} className="h-full flex flex-col justify-between py-1">
              <div className="w-px h-2 bg-slate-600" />
              <span className="text-[10px] text-slate-500">{hour}:00</span>
            </div>
          ))}
        </div>
        
        {/* Activity blocks */}
        {activityData.map((activity, index) => {
          const left = getTimePosition(activity.startTime);
          const width = getDurationWidth(activity.duration);
          const Icon = activity.icon;
          
          return (
            <motion.div
              key={index}
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 1 }}
              transition={{ delay: index * 0.1, duration: 0.5 }}
              style={{ 
                left: `${left}%`, 
                width: `${Math.max(width, 2)}%` 
              }}
              className={`
                absolute top-1 bottom-6 rounded-md
                bg-${activity.color}-500
                cursor-pointer group
                origin-left
              `}
              title={`${activity.type}: ${activity.startTime} - ${activity.endTime}`}
            >
              {/* Hover tooltip */}
              <div className="absolute -top-14 left-1/2 -translate-x-1/2 bg-slate-800 px-3 py-2 rounded-lg text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20 shadow-xl">
                <p className="font-semibold">{activity.type}</p>
                <p className="text-slate-400">{activity.startTime} - {activity.endTime}</p>
              </div>
            </motion.div>
          );
        })}
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {activityData.map((activity, index) => {
          const Icon = activity.icon;
          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.05 }}
              className="flex items-center gap-2"
            >
              <div className={`w-6 h-6 rounded-lg bg-${activity.color}-500/20 flex items-center justify-center`}>
                <Icon className={`w-3 h-3 text-${activity.color}-400`} />
              </div>
              <span className="text-xs text-slate-400">{activity.type}</span>
              <span className="text-xs font-medium text-slate-300">
                {activity.duration >= 60 
                  ? `${Math.floor(activity.duration / 60)}h ${activity.duration % 60}m`
                  : `${activity.duration}m`}
              </span>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};

export default ActivityTimeline;
