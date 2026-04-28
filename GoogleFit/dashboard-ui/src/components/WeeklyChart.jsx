import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart3, Loader2 } from 'lucide-react';

const METRICS = [
  { key: 'steps',    label: 'Steps',    color: '#06b6d4', gradientEnd: '#0ea5e9', unit: ''     },
  { key: 'calories', label: 'Calories', color: '#f97316', gradientEnd: '#ef4444', unit: 'kcal' },
  { key: 'active',   label: 'Active',   color: '#10b981', gradientEnd: '#059669', unit: 'min'  },
];

// SVG viewport
const vW = 480, vH = 130;
const PAD = { top: 28, right: 12, bottom: 20, left: 8 };
const CW  = vW - PAD.left - PAD.right;
const CH  = vH - PAD.top  - PAD.bottom;

const getX = (i, n) => PAD.left + (n <= 1 ? CW / 2 : (i / (n - 1)) * CW);
const getY = (v, max) => PAD.top + CH - (max > 0 ? (v / max) * CH : 0);

// Smooth bezier path through points
function buildPath(pts) {
  if (!pts.length) return '';
  return pts.map(([x, y], i) => {
    if (i === 0) return `M ${x.toFixed(1)} ${y.toFixed(1)}`;
    const [px, py] = pts[i - 1];
    const cx = ((px + x) / 2).toFixed(1);
    return `C ${cx} ${py.toFixed(1)}, ${cx} ${y.toFixed(1)}, ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
}

function buildAreaPath(pts, bottom) {
  if (!pts.length) return '';
  const line = buildPath(pts);
  const [lx, ] = pts[pts.length - 1];
  const [fx, ] = pts[0];
  return `${line} L ${lx.toFixed(1)} ${bottom} L ${fx.toFixed(1)} ${bottom} Z`;
}

const WeeklyChart = ({ weeklyData = [], loading = false }) => {
  const [activeMetric, setActiveMetric] = useState('steps');
  const [hovered, setHovered] = useState(null);

  const metric  = METRICS.find(m => m.key === activeMetric);
  const values  = weeklyData.map(d => Number(d[activeMetric]) || 0);
  const maxVal  = Math.max(...values, 1);
  const avgVal  = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  const maxIdx  = values.indexOf(Math.max(...values));
  const todayIdx= weeklyData.findLastIndex(d => d.isToday) ?? weeklyData.length - 1;

  const pts     = weeklyData.map((_, i) => [getX(i, weeklyData.length), getY(values[i], maxVal)]);
  const linePath = buildPath(pts);
  const areaPath = buildAreaPath(pts, PAD.top + CH);

  const gradLine = `wc-line-${activeMetric}`;
  const gradFill = `wc-fill-${activeMetric}`;

  const fmt = (v) => {
    if (v === 0) return '0';
    if (v >= 1000) return `${(v / 1000).toFixed(1)}k`;
    return Math.round(v).toString();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-effect rounded-2xl p-6 shadow-neumorphic h-full flex flex-col"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-md">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Weekly Activity</h3>
            <p className="text-xs text-slate-500">Last 7 days — real data</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold">Avg / day</p>
          <p className="text-xl font-black" style={{ color: metric.color }}>
            {avgVal > 0 ? fmt(avgVal) : '—'}
            {metric.unit ? <span className="text-sm font-medium ml-1 text-slate-400">{metric.unit}</span> : null}
          </p>
        </div>
      </div>

      {/* Metric toggle */}
      <div className="flex gap-1 mb-4 bg-slate-800/60 rounded-xl p-1 flex-shrink-0">
        {METRICS.map(m => (
          <button
            key={m.key}
            onClick={() => setActiveMetric(m.key)}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-semibold transition-all duration-200
              ${activeMetric === m.key ? 'text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
            style={activeMetric === m.key
              ? { background: `${m.color}22`, boxShadow: `0 0 14px ${m.color}30` }
              : {}}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Chart area */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-6 h-6 text-cyan-500 animate-spin" />
            <p className="text-xs text-slate-500">Fetching 7 days of real data…</p>
          </div>
        ) : weeklyData.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-slate-500">No weekly data available</p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeMetric}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.25 }}
              className="w-full h-full"
            >
              <svg
                viewBox={`0 0 ${vW} ${vH + 4}`}
                className="w-full"
                style={{ height: '155px', overflow: 'visible' }}
              >
                <defs>
                  <linearGradient id={gradLine} x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%"   stopColor={metric.color}       />
                    <stop offset="100%" stopColor={metric.gradientEnd} />
                  </linearGradient>
                  <linearGradient id={gradFill} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor={metric.color} stopOpacity="0.25" />
                    <stop offset="100%" stopColor={metric.color} stopOpacity="0.01" />
                  </linearGradient>
                </defs>

                {/* Horizontal grid lines */}
                {[0.25, 0.5, 0.75, 1].map(pct => {
                  const y = PAD.top + CH * (1 - pct);
                  return (
                    <g key={pct}>
                      <line x1={PAD.left} y1={y} x2={vW - PAD.right} y2={y}
                            stroke="rgba(100,116,139,0.1)" strokeWidth="1" strokeDasharray="3 5" />
                      <text x={PAD.left - 2} y={y + 3} fontSize="8" fill="rgba(100,116,139,0.5)" textAnchor="end">
                        {fmt(maxVal * pct)}
                      </text>
                    </g>
                  );
                })}

                {/* Area fill */}
                <motion.path
                  d={areaPath}
                  fill={`url(#${gradFill})`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5 }}
                />

                {/* Line */}
                <motion.path
                  d={linePath}
                  fill="none"
                  stroke={`url(#${gradLine})`}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 1.2, ease: 'easeInOut' }}
                  style={{ filter: `drop-shadow(0 0 5px ${metric.color}55)` }}
                />

                {/* Data points + trophy + tooltips */}
                {weeklyData.map((d, i) => {
                  const [x, y] = pts[i];
                  const isBest  = i === maxIdx && values[i] > 0;
                  const isToday = i === todayIdx;
                  const isHov   = hovered === i;
                  const v       = values[i];

                  return (
                    <g key={i}
                       onMouseEnter={() => setHovered(i)}
                       onMouseLeave={() => setHovered(null)}
                       style={{ cursor: 'crosshair' }}
                    >
                      {/* Trophy emoji above best point */}
                      {isBest && (
                        <motion.text
                          x={x} y={y - 22}
                          textAnchor="middle" fontSize="15"
                          initial={{ opacity: 0, y: y - 14 }}
                          animate={{ opacity: 1,  y: y - 22 }}
                          transition={{ delay: 1.1, type: 'spring', stiffness: 200 }}
                        >
                          🏆
                        </motion.text>
                      )}

                      {/* Outer pulse circle */}
                      <motion.circle
                        cx={x} cy={y}
                        r={isBest ? 11 : isToday ? 8 : 6}
                        fill={isBest ? '#fbbf2418' : metric.color + '15'}
                        initial={{ r: 0 }} animate={{ r: isBest ? 11 : isToday ? 8 : 6 }}
                        transition={{ delay: 0.9 + i * 0.04 }}
                      />

                      {/* Main dot */}
                      <motion.circle
                        cx={x} cy={y}
                        r={isBest ? 6 : isToday ? 5 : 4}
                        fill={isBest ? '#fbbf24' : isToday ? metric.color : 'rgba(10,20,35,0.95)'}
                        stroke={isBest ? '#f59e0b' : metric.color}
                        strokeWidth={isBest ? 2.5 : 2}
                        initial={{ scale: 0 }} animate={{ scale: 1 }}
                        transition={{ delay: 0.95 + i * 0.04, type: 'spring', stiffness: 280 }}
                        style={{ filter: isBest ? 'drop-shadow(0 0 8px #f59e0b99)' : isToday ? `drop-shadow(0 0 5px ${metric.color}88)` : 'none' }}
                      />

                      {/* Hover tooltip */}
                      {(isHov || isBest) && v > 0 && (
                        <g>
                          <rect
                            x={Math.min(x - 24, vW - PAD.right - 50)}
                            y={y - 36} width="50" height="18" rx="7"
                            fill="rgba(10,20,35,0.95)"
                            stroke="rgba(148,163,184,0.15)" strokeWidth="1"
                          />
                          <text
                            x={Math.min(x - 24, vW - PAD.right - 50) + 25}
                            y={y - 24}
                            textAnchor="middle" fontSize="9.5" fill="white" fontWeight="700"
                          >
                            {v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v} {metric.unit}
                          </text>
                        </g>
                      )}

                      {/* Day label */}
                      <text
                        x={x} y={vH + 2}
                        textAnchor="middle" fontSize="9.5"
                        fill={isBest ? '#fbbf24' : isToday ? 'white' : 'rgba(100,116,139,0.7)'}
                        fontWeight={isToday || isBest ? '700' : '500'}
                      >
                        {d.day}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Legend */}
      {!loading && weeklyData.length > 0 && (
        <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-700/40 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="text-sm">🏆</span>
            <span className="text-[10px] text-slate-400">
              Best: <span className="text-yellow-400 font-bold">{weeklyData[maxIdx]?.day ?? '—'}</span>
              {values[maxIdx] > 0 && (
                <span className="text-slate-500 ml-1">({fmt(values[maxIdx])})</span>
              )}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: metric.color }} />
            <span className="text-[10px] text-slate-400">Today</span>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default WeeklyChart;
