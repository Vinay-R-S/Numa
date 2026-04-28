import React from 'react';
import { motion } from 'framer-motion';
import { Flame, Calendar, CheckCircle2 } from 'lucide-react';

const StreakBadge = ({ streak = 7, goal = 10000, currentSteps = 0 }) => {
  const pct = Math.min((currentSteps / goal) * 100, 100);
  const isActive = currentSteps >= goal;
  const remaining = Math.max(goal - currentSteps, 0);

  // Generate mini dot calendar for last 7 days (mock)
  const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const hits  = [true, true, true, true, true, true, isActive];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.01 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic relative overflow-hidden h-full"
    >
      {/* Background glow */}
      {isActive && (
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-gradient-to-br from-orange-500 to-red-500 opacity-[0.08] rounded-full blur-3xl pointer-events-none" />
      )}

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <motion.div
              animate={isActive ? { scale: [1, 1.12, 1] } : {}}
              transition={{ repeat: Infinity, duration: 1.8, ease: 'easeInOut' }}
              className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                isActive
                  ? 'bg-gradient-to-br from-orange-500 to-red-500 shadow-lg shadow-orange-500/30'
                  : 'bg-slate-700/50'
              }`}
            >
              <Flame className={`w-6 h-6 ${isActive ? 'text-white' : 'text-slate-500'}`} />
            </motion.div>
            <div>
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Streak</p>
              <div className="flex items-baseline gap-1">
                <motion.span
                  key={streak}
                  initial={{ scale: 1.3 }}
                  animate={{ scale: 1 }}
                  className={`text-3xl font-black ${isActive ? 'text-orange-400' : 'text-slate-400'}`}
                >
                  {streak}
                </motion.span>
                <span className="text-sm text-slate-500 font-medium">days</span>
              </div>
            </div>
          </div>

          {isActive ? (
            <div className="flex items-center gap-1.5 bg-emerald-500/15 border border-emerald-500/30 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-bold text-emerald-400">Goal met!</span>
            </div>
          ) : (
            <div className="text-right">
              <p className="text-xs text-slate-500">Steps left</p>
              <p className="text-sm font-bold text-slate-300">{remaining.toLocaleString()}</p>
            </div>
          )}
        </div>

        {/* Weekly dot calendar */}
        <div className="flex items-center gap-1.5 mb-4">
          {days.map((day, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: i * 0.06 }}
                className={`w-full aspect-square rounded-lg flex items-center justify-center max-w-[36px] ${
                  hits[i]
                    ? 'bg-gradient-to-br from-orange-500 to-red-500 shadow-sm shadow-orange-500/30'
                    : 'bg-slate-800/60 border border-slate-700/50'
                }`}
              >
                {hits[i] && <Flame className="w-3 h-3 text-white" />}
              </motion.div>
              <span className="text-[9px] text-slate-600 font-medium">{day}</span>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-slate-500">Today's goal</span>
            <span className={`font-bold ${isActive ? 'text-emerald-400' : 'text-slate-400'}`}>
              {Math.round(pct)}%
            </span>
          </div>
          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 1.2, ease: [0.34, 1.56, 0.64, 1] }}
              className="h-full rounded-full bg-gradient-to-r from-orange-500 to-red-500"
              style={{ boxShadow: isActive ? '0 0 12px rgba(249,115,22,0.5)' : 'none' }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-600 mt-1">
            <span>{currentSteps.toLocaleString()} steps</span>
            <span>{goal.toLocaleString()} goal</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default StreakBadge;
