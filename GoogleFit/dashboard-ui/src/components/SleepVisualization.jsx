import React from 'react';
import { motion } from 'framer-motion';
import { Moon, Sun, BedDouble, Bed } from 'lucide-react';

/**
 * SleepVisualization — renders real Google Fit sleep data.
 *
 * sleepData prop (from buildSleepVizData in GoogleFitDashboard):
 *   { totalHours, quality, deepSleep, lightSleep, rem, awakeTime, bedTime, wakeTime }
 *
 * When sleepData is null (no data), shows a clear empty state — no fake numbers.
 */
const SleepVisualization = ({ sleepData }) => {
  // ── Empty state ────────────────────────────────────────────────────────────
  if (!sleepData || sleepData.totalHours <= 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-effect rounded-2xl p-6 shadow-neumorphic flex flex-col items-center justify-center min-h-[260px]"
      >
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 flex items-center justify-center mb-4">
          <Moon className="w-7 h-7 text-indigo-400/50" />
        </div>
        <p className="text-slate-400 font-semibold">No sleep data</p>
        <p className="text-xs text-slate-600 mt-1 text-center max-w-[200px]">
          Sleep tracking must be enabled in Google Fit or a connected wearable.
        </p>
      </motion.div>
    );
  }

  const { totalHours, quality, deepSleep, lightSleep, rem, bedTime, wakeTime } = sleepData;
  const sleepGoal = 8;
  const sleepPct  = Math.min((totalHours / sleepGoal) * 100, 100);

  // Only show stages that have real data
  const stages = [
    { name: 'Deep Sleep',  hours: deepSleep,  color: 'indigo', hex: '#6366f1' },
    { name: 'Light Sleep', hours: lightSleep, color: 'blue',   hex: '#3b82f6' },
    { name: 'REM',         hours: rem,        color: 'purple', hex: '#a855f7' },
  ].filter(s => s.hours > 0);

  // If no stage breakdown (only generic sleep from Google Fit),
  // just show total without stages
  const hasStages = stages.length > 0 && stages.reduce((a, s) => a + s.hours, 0) > 0.1;

  const getQualityLabel = () => {
    if (quality >= 80) return { text: 'Great',   color: 'emerald', bg: 'bg-emerald-500/15 border-emerald-500/25' };
    if (quality >= 60) return { text: 'Good',    color: 'yellow',  bg: 'bg-yellow-500/15 border-yellow-500/25'  };
    if (quality >= 40) return { text: 'Fair',    color: 'orange',  bg: 'bg-orange-500/15 border-orange-500/25'  };
    return                    { text: 'Low',     color: 'red',     bg: 'bg-red-500/15 border-red-500/25'        };
  };
  const ql = getQualityLabel();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic h-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-md">
            <Moon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Sleep Analysis</h3>
            <p className="text-xs text-slate-500">Last night — real Google Fit data</p>
          </div>
        </div>

        <div className={`px-3 py-1 rounded-full border text-xs font-bold text-${ql.color}-400 ${ql.bg}`}>
          {quality}% · {ql.text}
        </div>
      </div>

      {/* Main sleep duration */}
      <div className="flex items-end gap-6 mb-5">
        <div className="flex-1">
          <div className="flex items-baseline gap-1 mb-2">
            <motion.span
              className="text-5xl font-black text-indigo-400 tabular-nums"
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              {Math.floor(totalHours)}
            </motion.span>
            <span className="text-xl text-slate-400 font-medium">h</span>
            <motion.span
              className="text-4xl font-black text-indigo-400 tabular-nums"
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
            >
              {Math.round((totalHours % 1) * 60)}
            </motion.span>
            <span className="text-lg text-slate-400 font-medium">m</span>
          </div>

          {/* Goal bar */}
          <div className="flex items-center gap-2 mb-1">
            <div className="flex-1 h-2 bg-slate-700/60 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${sleepPct}%` }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
              />
            </div>
            <span className="text-xs text-slate-500 whitespace-nowrap">{sleepGoal}h goal</span>
          </div>
          <p className="text-xs text-slate-600">
            {totalHours >= sleepGoal
              ? `✓ Goal met — ${(totalHours - sleepGoal).toFixed(1)}h over`
              : `${(sleepGoal - totalHours).toFixed(1)}h short of goal`}
          </p>
        </div>

        {/* Bed / wake times */}
        <div className="flex gap-3 flex-shrink-0">
          {bedTime && bedTime !== '—' && (
            <div className="text-center">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/15 flex items-center justify-center mb-1">
                <Bed className="w-5 h-5 text-indigo-400" />
              </div>
              <p className="text-[10px] text-slate-500">Bed</p>
              <p className="text-xs font-bold text-white">{bedTime}</p>
            </div>
          )}
          {wakeTime && wakeTime !== '—' && (
            <div className="text-center">
              <div className="w-10 h-10 rounded-xl bg-orange-500/15 flex items-center justify-center mb-1">
                <Sun className="w-5 h-5 text-orange-400" />
              </div>
              <p className="text-[10px] text-slate-500">Wake</p>
              <p className="text-xs font-bold text-white">{wakeTime}</p>
            </div>
          )}
        </div>
      </div>

      {/* Sleep stages — only if real breakdown is available */}
      {hasStages ? (
        <>
          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-2">Sleep Stages</p>

          {/* Stacked bar */}
          <div className="h-6 rounded-xl overflow-hidden flex mb-3">
            {stages.map((stage, i) => {
              const pct = (stage.hours / totalHours) * 100;
              return (
                <motion.div
                  key={stage.name}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.8, delay: i * 0.12 }}
                  className="h-full"
                  style={{ background: stage.hex }}
                  title={`${stage.name}: ${stage.hours}h`}
                />
              );
            })}
          </div>

          {/* Stage breakdown cards */}
          <div className="grid grid-cols-3 gap-2">
            {stages.map((stage, i) => (
              <motion.div
                key={stage.name}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.1 }}
                className="bg-slate-800/40 rounded-xl p-2.5 border border-slate-700/40"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: stage.hex }} />
                  <p className="text-[10px] text-slate-500 truncate">{stage.name}</p>
                </div>
                <p className="text-sm font-bold" style={{ color: stage.hex }}>
                  {stage.hours.toFixed(1)}h
                  <span className="text-[10px] text-slate-500 font-normal ml-1">
                    ({Math.round((stage.hours / totalHours) * 100)}%)
                  </span>
                </p>
              </motion.div>
            ))}
          </div>
        </>
      ) : (
        <div className="bg-slate-800/30 rounded-xl p-3 border border-slate-700/30 mt-1">
          <p className="text-xs text-slate-500 text-center">
            Detailed sleep stages unavailable — upgrade to a wearable for deep/REM breakdown.
          </p>
        </div>
      )}
    </motion.div>
  );
};

export default SleepVisualization;
