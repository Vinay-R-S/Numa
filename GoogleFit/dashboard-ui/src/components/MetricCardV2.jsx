import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import CircularProgress from './CircularProgress';


/**
 * MetricCardV2 — Premium metric card with circular ring, count-up, sparkline.
 */
const MetricCardV2 = ({
  icon: Icon,
  value = 0,
  unit = '',
  label = '',
  color = {},
  goal,
  showProgress = true,
  sparklineData,
  size = 'normal',  // 'normal' | 'large'
  delay = 0,
}) => {
  const [display, setDisplay] = useState(0);
  const percentage = goal ? Math.min((value / goal) * 100, 100) : 0;

  // Count-up animation
  useEffect(() => {
    let raf;
    const duration = 1200;
    const start = Date.now();
    const from = 0;

    const tick = () => {
      const elapsed = Date.now() - start;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(from + (value - from) * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  const fmt = (v) => {
    if (v >= 10000) return Math.round(v).toLocaleString();
    if (v >= 1000)  return Math.round(v).toLocaleString();
    if (v % 1 === 0 || v >= 100) return Math.round(v).toString();
    return v.toFixed(1);
  };

  const ringSize = size === 'large' ? 120 : 88;
  const strokeWidth = size === 'large' ? 9 : 7;
  const remaining = goal ? goal - value : 0;
  const goalMet = goal && value >= goal;

  // Unique ID for gradient (use label)
  const ringId = label.replace(/\s+/g, '-').toLowerCase();

  return (
    <motion.div
      whileHover={{ y: -6, scale: 1.01 }}
      transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      className="relative group cursor-default"
    >
      <div className="glass-effect rounded-2xl p-5 shadow-neumorphic group-hover:shadow-neumorphic-hover transition-all duration-300 h-full">
        {/* Gradient hover overlay */}
        <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${color.gradient || ''} opacity-0 group-hover:opacity-[0.04] transition-opacity duration-300`} />

        <div className="relative z-10">
          {/* Label + icon */}
          <div className="flex items-center gap-2.5 mb-4">
            <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${color.gradient || 'from-cyan-500 to-cyan-600'} flex items-center justify-center shadow-md flex-shrink-0`}>
              {Icon && <Icon className="w-4 h-4 text-white" />}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-400 truncate">{label}</p>
              {goal && (
                <p className="text-[10px] text-slate-600 leading-none mt-0.5">
                  Goal: {goal >= 1000 ? goal.toLocaleString() : goal} {unit}
                </p>
              )}
            </div>
          </div>

          {/* Ring + value */}
          <div className="flex items-center gap-4">
            {showProgress && goal && (
              <div className="flex-shrink-0">
                <CircularProgress
                  value={value}
                  max={goal}
                  size={ringSize}
                  strokeWidth={strokeWidth}
                  color={color}
                  id={ringId}
                  delay={delay}
                  showPercent={false}
                >
                  <div className="flex flex-col items-center">
                    <span
                      className="font-bold text-white leading-none tabular-nums"
                      style={{ fontSize: ringSize * 0.185 }}
                    >
                      {Math.round(percentage)}
                    </span>
                    <span className="text-[9px] text-slate-500 mt-0.5">%</span>
                  </div>
                </CircularProgress>
              </div>
            )}

            {/* Value + sparkline */}
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-1 mb-1">
                <span
                  className="font-black text-white tabular-nums leading-none"
                  style={{ fontSize: '1.6rem' }}
                >
                  {fmt(display)}
                </span>
                <span className="text-sm text-slate-500 font-medium">{unit}</span>
              </div>

              {/* Goal status */}
              {goal && (
                <p className={`text-[10px] font-semibold mb-1.5 ${goalMet ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {goalMet
                    ? '✓ Goal reached!'
                    : `${remaining >= 1000 ? remaining.toLocaleString() : remaining.toFixed(remaining < 1 ? 1 : 0)} ${unit} to go`}
                </p>
              )}

              {/* Sparkline */}
              {sparklineData && (
                <Sparkline
                  data={sparklineData}
                  color={color.primary || '#06b6d4'}
                  width={90}
                  height={22}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default MetricCardV2;
