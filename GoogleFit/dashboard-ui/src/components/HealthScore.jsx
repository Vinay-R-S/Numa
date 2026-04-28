import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, Zap, TrendingUp } from 'lucide-react';
import CircularProgress from './CircularProgress';

const GOALS = {
  steps:         8000,
  activeMinutes: 60,
  calories:      2000,
  sleep:         7,
};

const SCORE_COLORS = {
  excellent: { primary: '#10b981', secondary: '#34d399', gradient: 'from-emerald-400 to-green-500',  text: 'text-emerald-400',  label: 'Excellent',  bg: 'bg-emerald-500/10 border-emerald-500/20' },
  good:      { primary: '#eab308', secondary: '#facc15', gradient: 'from-yellow-400 to-amber-500',   text: 'text-yellow-400',   label: 'Good',       bg: 'bg-yellow-500/10 border-yellow-500/20' },
  fair:      { primary: '#f97316', secondary: '#fb923c', gradient: 'from-orange-400 to-orange-500',  text: 'text-orange-400',   label: 'Fair',       bg: 'bg-orange-500/10 border-orange-500/20' },
  low:       { primary: '#ef4444', secondary: '#f87171', gradient: 'from-red-400 to-red-500',        text: 'text-red-400',      label: 'Needs Work', bg: 'bg-red-500/10 border-red-500/20' },
};

const getScoreLevel = (s) => s >= 75 ? 'excellent' : s >= 50 ? 'good' : s >= 25 ? 'fair' : 'low';

const HealthScore = ({ data }) => {
  const [animScore, setAnimScore] = useState(0);

  const calcScore = () => {
    if (!data) return 0;
    const w = (key, goal) => Math.min((data[key]?.value || 0) / goal, 1) * 25;
    return Math.round(w('steps', GOALS.steps) + w('activeMinutes', GOALS.activeMinutes) + w('calories', GOALS.calories) + w('sleep', GOALS.sleep));
  };

  const score = calcScore();
  const level = getScoreLevel(score);
  const sc = SCORE_COLORS[level];

  // Count-up
  useEffect(() => {
    let raf;
    const dur = 1600;
    const start = Date.now();
    const tick = () => {
      const t = Math.min((Date.now() - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setAnimScore(Math.round(score * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    const tid = setTimeout(() => { raf = requestAnimationFrame(tick); }, 200);
    return () => { clearTimeout(tid); cancelAnimationFrame(raf); };
  }, [score]);

  const breakdown = [
    { label: 'Steps',   key: 'steps',         goal: GOALS.steps,         unit: '',    color: '#06b6d4' },
    { label: 'Active',  key: 'activeMinutes',  goal: GOALS.activeMinutes, unit: 'min', color: '#10b981' },
    { label: 'Calories',key: 'calories',       goal: GOALS.calories,      unit: 'kcal',color: '#f97316' },
    { label: 'Sleep',   key: 'sleep',          goal: GOALS.sleep,         unit: 'hrs', color: '#6366f1' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-effect rounded-3xl p-8 shadow-neumorphic relative overflow-hidden"
    >
      {/* Ambient glow */}
      <div className={`absolute -top-24 -right-24 w-80 h-80 bg-gradient-to-br ${sc.gradient} opacity-[0.07] rounded-full blur-3xl pointer-events-none`} />
      <div className={`absolute -bottom-16 -left-16 w-64 h-64 bg-gradient-to-tr ${sc.gradient} opacity-[0.04] rounded-full blur-3xl pointer-events-none`} />

      <div className="relative z-10 flex flex-col lg:flex-row items-center gap-8 lg:gap-12">

        {/* ── Score ring ── */}
        <div className="relative flex-shrink-0">
          {/* Outer decorative pulse */}
          <div
            className="absolute inset-0 rounded-full opacity-20 blur-xl pointer-events-none"
            style={{ background: `radial-gradient(circle, ${sc.primary}60 0%, transparent 70%)` }}
          />
          <CircularProgress
            value={score}
            max={100}
            size={200}
            strokeWidth={14}
            color={{ primary: sc.primary, secondary: sc.secondary }}
            id="health-score-main"
            showPercent={false}
          >
            <div className="flex flex-col items-center gap-1">
              <span className={`text-6xl font-black ${sc.text} tabular-nums leading-none`}>
                {animScore}
              </span>
              <span className="text-xs text-slate-500 font-medium tracking-wider uppercase">Health Score</span>
              <span className={`text-sm font-bold px-3 py-0.5 rounded-full border ${sc.bg} ${sc.text} mt-1`}>
                {sc.label}
              </span>
            </div>
          </CircularProgress>
        </div>

        {/* ── Right panel ── */}
        <div className="flex-1 w-full">
          {/* Title row */}
          <div className="flex items-center gap-3 mb-6">
            <div className={`w-11 h-11 rounded-2xl bg-gradient-to-br ${sc.gradient} flex items-center justify-center shadow-lg`}>
              <Heart className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-extrabold text-white leading-none">Your Daily Health</h2>
              <p className="text-sm text-slate-500 mt-0.5">Based on today's activity data</p>
            </div>

            {score >= 75 && (
              <motion.div
                initial={{ scale: 0, rotate: -20 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 1.2, type: 'spring', stiffness: 200 }}
                className="ml-auto bg-yellow-500/15 border border-yellow-500/30 px-3 py-1.5 rounded-full flex items-center gap-1.5"
              >
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-xs font-bold text-yellow-400">On Fire!</span>
              </motion.div>
            )}
          </div>

          {/* Breakdown cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {breakdown.map(({ label, key, goal, unit, color }, i) => {
              const val = data?.[key]?.value || 0;
              const pct = Math.min((val / goal) * 100, 100);
              return (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className="bg-slate-800/40 rounded-2xl p-4 border border-slate-700/40 hover:border-slate-600/40 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wide">{label}</span>
                    <span className="text-xs font-bold" style={{ color }}>{Math.round(pct)}%</span>
                  </div>
                  <div className="text-base font-bold text-white mb-2">
                    {val >= 1000 ? val.toLocaleString() : (Number.isInteger(val) ? val : val.toFixed(1))}
                    {unit && <span className="text-xs text-slate-500 ml-1">{unit}</span>}
                  </div>
                  {/* Mini bar */}
                  <div className="w-full h-1.5 bg-slate-700/60 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 1.2, delay: 0.5 + i * 0.1, ease: 'easeOut' }}
                      className="h-full rounded-full"
                      style={{ background: color }}
                    />
                  </div>
                  <div className="text-[10px] text-slate-600 mt-1">
                    Goal: {goal >= 1000 ? goal.toLocaleString() : goal} {unit}
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* XP / progress bar */}
          <div className="mt-5">
            <div className="flex justify-between text-xs text-slate-500 mb-1.5">
              <span className="flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> Overall progress
              </span>
              <span className={`font-bold ${sc.text}`}>{score}/100</span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${score}%` }}
                transition={{ duration: 1.6, delay: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
                className={`h-full rounded-full bg-gradient-to-r ${sc.gradient}`}
                style={{ boxShadow: `0 0 12px ${sc.primary}60` }}
              />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default HealthScore;
