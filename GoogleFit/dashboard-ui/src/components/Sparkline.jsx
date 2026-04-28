import React from 'react';
import { motion } from 'framer-motion';

const Sparkline = ({ data = [], color = '#06b6d4', width = 100, height = 30 }) => {
  if (!data || data.length === 0) {
    // Generate mock data for demo
    data = [40, 60, 45, 80, 55, 70, 65];
  }
  
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * height * 0.8 - height * 0.1;
    return `${x},${y}`;
  }).join(' ');
  
  const pathD = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * height * 0.8 - height * 0.1;
    return index === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
  }).join(' ');
  
  // Create area path for gradient fill
  const areaPath = `${pathD} L ${width} ${height} L 0 ${height} Z`;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={`sparkline-gradient-${color}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      
      {/* Area fill */}
      <motion.path
        d={areaPath}
        fill={`url(#sparkline-gradient-${color})`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      />
      
      {/* Line */}
      <motion.path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1, ease: "easeOut" }}
      />
      
      {/* End dot */}
      <motion.circle
        cx={(data.length - 1) / (data.length - 1) * width}
        cy={height - ((data[data.length - 1] - min) / range) * height * 0.8 - height * 0.1}
        r="3"
        fill={color}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 1, duration: 0.3 }}
      />
    </svg>
  );
};

export default Sparkline;
