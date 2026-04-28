import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Footprints, Activity, Flame, MapPin, Moon, RefreshCw, Wifi, WifiOff, AlertCircle } from 'lucide-react';

import MetricCardV2    from './MetricCardV2';
import HealthScore     from './HealthScore';
import WeeklyChart     from './WeeklyChart';
import InsightsPanel   from './InsightsPanel';
import ComparisonPanel from './ComparisonPanel';
import StreakBadge     from './StreakBadge';
import SmartSuggestions   from './SmartSuggestions';
import SleepVisualization from './SleepVisualization';
import ActivityTimeline   from './ActivityTimeline';

import { METRIC_COLORS } from '../utils/colors';
import { fetchGoogleFitData, fetchGoogleFitDataForDate } from '../utils/api';

// ─── Animation helpers ────────────────────────────────────────────────────────
const containerVariants = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.07 } }
};
const itemVariants = {
  hidden:  { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 120, damping: 20 } }
};

// ─── Section header ───────────────────────────────────────────────────────────
const SectionHeader = ({ title, subtitle }) => (
  <div className="mb-5">
    <h2 className="text-xl font-bold text-white">{title}</h2>
    {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
  </div>
);

// ─── Status bar ───────────────────────────────────────────────────────────────
const StatusBar = ({ live, loading, error, onRefresh }) => (
  <div className="flex items-center gap-2">
    <motion.div
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border
        ${live    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
        : error   ? 'bg-red-500/10 text-red-400 border-red-500/25'
                  : 'bg-slate-700/40 text-slate-400 border-slate-600/25'}`}
    >
      {live  ? <Wifi      className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
      {live  ? 'Live Data' : error ? 'API Error' : 'No Data'}
    </motion.div>
    <motion.button
      whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
      onClick={onRefresh} disabled={loading}
      className="w-8 h-8 rounded-full bg-slate-700/40 border border-slate-600/30 flex items-center justify-center hover:bg-slate-600/50 transition-colors disabled:opacity-40"
    >
      <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
    </motion.button>
  </div>
);

// ─── Empty state ──────────────────────────────────────────────────────────────
const NoDataState = ({ message, onRetry }) => (
  <div className="glass-effect rounded-2xl p-12 text-center">
    <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-4" />
    <p className="text-slate-400 font-medium">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="mt-4 px-4 py-2 text-sm text-cyan-400 border border-cyan-500/30 rounded-xl hover:bg-cyan-500/10 transition-colors"
      >
        Retry
      </button>
    )}
  </div>
);

// ─── Shape raw API response ───────────────────────────────────────────────────
function shapeData(raw) {
  const steps         = raw.steps?.value          ?? 0;
  const activeMinutes = raw.activeMinutes?.value   ?? 0;
  const calories      = raw.calories?.value        ?? 0;
  const distance      = raw.distance?.value        ?? 0;
  const sleepHours    = raw.sleep?.value           ?? 0;
  const sleepStages   = raw.sleep?.stages          ?? null;

  return {
    steps:         { value: steps,         unit: 'steps', label: 'Steps Today',      goal: 10000, percentage: Math.min(100, Math.round((steps / 10000) * 100)) },
    activeMinutes: { value: activeMinutes, unit: 'min',   label: 'Active Minutes',   goal: 60,    percentage: Math.min(100, Math.round((activeMinutes / 60) * 100)) },
    calories:      { value: calories,      unit: 'kcal',  label: 'Calories Burned',  goal: 2500,  percentage: Math.min(100, Math.round((calories / 2500) * 100)) },
    distance:      { value: distance,      unit: 'km',    label: 'Distance Covered', goal: 8,     percentage: Math.min(100, Math.round((distance / 8) * 100)) },
    sleep:         { value: sleepHours,    unit: 'hrs',   label: 'Sleep Duration',   goal: 8,     percentage: Math.min(100, Math.round((sleepHours / 8) * 100)), stages: sleepStages },
    activitySegments: raw.activitySegments ?? [],
  };
}

// ─── Build sleep visualization data from real API data ────────────────────────
function buildSleepVizData(sleepMetric) {
  const total  = sleepMetric?.value  ?? 0;
  const stages = sleepMetric?.stages ?? null;
  if (total <= 0) return null;

  // Use stage data if available, or estimate from total
  const deep    = stages?.deep    ?? +(total * 0.20).toFixed(1);
  const rem     = stages?.rem     ?? +(total * 0.22).toFixed(1);
  const generic = stages?.generic ?? 0;
  const light   = stages?.light   ?? +(Math.max(0, total - deep - rem - generic)).toFixed(1);

  return {
    totalHours: total,
    quality: Math.round(Math.min(100, (total / 8) * 100)),
    deepSleep:  deep,
    lightSleep: light,
    rem,
    awakeTime:  0, // excluded by backend filter
    bedTime: '—',
    wakeTime: '—',
  };
}

// ─── Main component ───────────────────────────────────────────────────────────
const GoogleFitDashboard = ({ dateRange = 'today' }) => {
  const [todayData,    setTodayData]    = useState(null);
  const [weeklyData,   setWeeklyData]   = useState([]);
  const [yesterdayData,setYesterdayData]= useState(null);
  const [loading,      setLoading]      = useState(true);
  const [weeklyLoading,setWeeklyLoading]= useState(true);
  const [isLive,       setIsLive]       = useState(false);
  const [error,        setError]        = useState(null);

  // ── Fetch today (or selected range) ───────────────────────────────────────
  const loadTodayData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchGoogleFitData(dateRange);
      if (result.success) {
        setTodayData(shapeData(result.data));
        setIsLive(true);
      } else {
        setError(result.error || 'Could not connect to Google Fit');
        setTodayData(null);
        setIsLive(false);
      }
    } catch (e) {
      setError(e.message);
      setTodayData(null);
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  }, [dateRange]);

  // ── Fetch last 7 days individually for the weekly chart ───────────────────
  const loadWeeklyData = useCallback(async () => {
    setWeeklyLoading(true);
    const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const today = new Date();
    const days  = [];

    // Build date list: 6 days ago → today
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      days.push({ date: d, label: DAY_NAMES[d.getDay()], isToday: i === 0 });
    }

    try {
      const results = await Promise.all(
        days.map(({ date }) => fetchGoogleFitDataForDate(date))
      );

      const weekRows = days.map(({ date, label, isToday }, i) => {
        const r = results[i];
        if (!r.success) return { day: label, date: date.toISOString().slice(0, 10), steps: 0, calories: 0, active: 0, isToday };
        return {
          day:      label,
          date:     date.toISOString().slice(0, 10),
          steps:    r.data.steps?.value          ?? 0,
          calories: r.data.calories?.value        ?? 0,
          active:   r.data.activeMinutes?.value   ?? 0,
          isToday,
        };
      });

      setWeeklyData(weekRows);

      // Use yesterday's row for comparison
      if (weekRows.length >= 2) {
        const yd = weekRows[weekRows.length - 2];
        setYesterdayData({ steps: { value: yd.steps }, activeMinutes: { value: yd.active }, calories: { value: yd.calories }, distance: { value: 0 }, sleep: { value: 0 } });
      }
    } catch (e) {
      console.error('Weekly load failed:', e);
      setWeeklyData([]);
    } finally {
      setWeeklyLoading(false);
    }
  }, []);

  useEffect(() => { loadTodayData();  }, [loadTodayData]);
  useEffect(() => { loadWeeklyData(); }, [loadWeeklyData]);

  // ── Streak: count consecutive days (from weekly data) where steps >= 10k ──
  const streak = React.useMemo(() => {
    if (!weeklyData.length) return 0;
    let count = 0;
    for (let i = weeklyData.length - 1; i >= 0; i--) {
      if (weeklyData[i].steps >= 10000) count++;
      else break;
    }
    return count;
  }, [weeklyData]);

  const d = todayData;

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="visible">

      {/* ── Status bar ──────────────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="flex justify-end mb-4 -mt-2">
        <StatusBar live={isLive} loading={loading} error={error} onRefresh={() => { loadTodayData(); loadWeeklyData(); }} />
      </motion.div>

      {/* ── Error banner ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="mb-6 p-4 bg-red-500/10 border border-red-500/25 rounded-2xl flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-red-400">Failed to load data</p>
              <p className="text-xs text-red-400/70 mt-0.5">{error} — Make sure the Python API server is running.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── 1. Health Score ──────────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="mb-8">
        <HealthScore data={d} />
      </motion.div>

      {/* ── 2. Streak + Comparison ───────────────────────────────────── */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <StreakBadge streak={streak} goal={10000} currentSteps={d?.steps?.value ?? 0} />
        <ComparisonPanel data={d} previousData={yesterdayData} />
      </motion.div>

      {/* ── 3. Metric cards ──────────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="mb-2">
        <SectionHeader title="Today's Metrics" subtitle="Real-time progress toward your daily goals" />
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5 mb-8">
        {[
          { icon: Footprints, key: 'steps',         colorKey: 'steps'    },
          { icon: Activity,   key: 'activeMinutes',  colorKey: 'active'   },
          { icon: Flame,      key: 'calories',       colorKey: 'calories' },
          { icon: MapPin,     key: 'distance',       colorKey: 'distance' },
          { icon: Moon,       key: 'sleep',          colorKey: 'sleep'    },
        ].map(({ icon, key, colorKey }, i) => (
          <motion.div key={key} variants={itemVariants}>
            <MetricCardV2
              icon={icon}
              value={d?.[key]?.value ?? 0}
              unit={d?.[key]?.unit   ?? ''}
              label={d?.[key]?.label  ?? key}
              color={METRIC_COLORS[colorKey]}
              goal={d?.[key]?.goal}
              sparklineData={null}   /* no sparklines — only real data */
              showProgress
              delay={i * 0.08}
            />
          </motion.div>
        ))}
      </div>

      {/* ── 4. Weekly Chart + Insights ───────────────────────────────── */}
      <motion.div variants={itemVariants} className="mb-2">
        <SectionHeader title="Weekly Overview" subtitle="Actual activity data — one API call per day" />
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
        <div className="lg:col-span-3">
          <WeeklyChart weeklyData={weeklyData} loading={weeklyLoading} />
        </div>
        <div className="lg:col-span-2">
          <InsightsPanel data={d} />
        </div>
      </div>

      {/* ── 5. Sleep + Timeline ──────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="mb-2">
        <SectionHeader title="Sleep & Activity" subtitle="Last night's real sleep stages from Google Fit" />
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <motion.div variants={itemVariants}>
          <SleepVisualization sleepData={buildSleepVizData(d?.sleep)} />
        </motion.div>
        <motion.div variants={itemVariants}>
          <ActivityTimeline activities={null} />
        </motion.div>
      </div>

      {/* ── 6. Smart Suggestions ─────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="mb-2">
        <SectionHeader title="Smart Suggestions" subtitle="Based on today's real activity" />
      </motion.div>
      <motion.div variants={itemVariants} className="mb-8">
        <SmartSuggestions data={d} />
      </motion.div>

    </motion.div>
  );
};

export default GoogleFitDashboard;
