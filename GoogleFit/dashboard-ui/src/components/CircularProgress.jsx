import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';

/**
 * CircularProgress — SVG ring with animated stroke, gradient, glow.
 *
 * Props:
 *   value        — current value
 *   max          — max value (100 for percentage)
 *   size         — SVG size in px (default 120)
 *   strokeWidth  — ring thickness (default 10)
 *   color        — { primary, secondary, glow } from METRIC_COLORS
 *   id           — unique string used for gradient id (required to avoid conflicts)
 *   showPercent  — show percent text in center (default true)
 *   children     — override center content
 *   delay        — animation delay (seconds)
 */
const CircularProgress = ({
  value = 0,
  max = 100,
  size = 120,
  strokeWidth = 10,
  color = {},
  id = 'ring',
  showPercent = true,
  children,
  delay = 0,
}) => {
  const [animPct, setAnimPct] = useState(0);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  // Animate pct after mount
  useEffect(() => {
    const t = setTimeout(() => setAnimPct(percentage), 150 + delay * 1000);
    return () => clearTimeout(t);
  }, [percentage, delay]);

  const strokeDashoffset = circumference - (animPct / 100) * circumference;
  const gradId = `cp-grad-${id}`;
  const filterId = `cp-glow-${id}`;
  const primary = color.primary || '#06b6d4';
  const secondary = color.secondary || primary;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-90deg)' }}
      >
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={primary} stopOpacity="1" />
            <stop offset="100%" stopColor={secondary} stopOpacity="0.7" />
          </linearGradient>
          <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(100,116,139,0.12)"
          strokeWidth={strokeWidth}
        />

        {/* Inner glow ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={primary}
          strokeWidth={strokeWidth + 4}
          strokeOpacity="0.06"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          style={{ transition: 'stroke-dashoffset 1.4s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
        />

        {/* Progress */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          style={{
            transition: 'stroke-dashoffset 1.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
            filter: `drop-shadow(0 0 8px ${primary}80)`,
          }}
        />
      </svg>

      {/* Center */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {children ?? (showPercent && (
          <span
            className="font-bold text-white tabular-nums"
            style={{ fontSize: size * 0.17 }}
          >
            {Math.round(animPct)}%
          </span>
        ))}
      </div>
    </div>
  );
};

export default CircularProgress;
