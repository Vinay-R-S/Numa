import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Activity } from 'lucide-react';
import SourceSwitcher from './SourceSwitcher';
import DateRangePicker from './DateRangePicker';
import GoogleFitDashboard from './GoogleFitDashboard';
import StravaDashboard from './StravaDashboard';
import { DATE_RANGES } from '../utils/dateUtils';

const Dashboard = () => {
  const [currentSource, setCurrentSource] = useState('google-fit');
  const [dateRange, setDateRange] = useState(DATE_RANGES.TODAY);

  const pageVariants = {
    initial: { opacity: 0, x: -16 },
    animate: { opacity: 1, x: 0 },
    exit:    { opacity: 0, x: 16 }
  };

  return (
    <div className="min-h-screen">
      {/* ── Ambient top blobs ────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
        <div className="absolute -top-20 right-10 w-80 h-80 bg-indigo-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-1/3 w-64 h-64 bg-purple-500/4 rounded-full blur-3xl" />
      </div>

      <div className="relative max-w-screen-2xl mx-auto px-6 pb-16 pt-8">

        {/* ── Header ──────────────────────────────────────── */}
        <motion.header
          initial={{ opacity: 0, y: -24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-10"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            {/* Logo + title */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                  <Activity className="w-7 h-7 text-white" />
                </div>
                {/* Live dot */}
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#080d14] pulse-glow" />
              </div>
              <div>
                <h1 className="text-4xl font-black text-gradient leading-none tracking-tight">
                  Health Dashboard
                </h1>
                <p className="text-slate-500 text-sm mt-1 font-medium">
                  {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3">
              <DateRangePicker
                currentRange={dateRange}
                onRangeChange={setDateRange}
              />
              <SourceSwitcher
                currentSource={currentSource}
                onSourceChange={setCurrentSource}
              />
            </div>
          </div>

          {/* Divider */}
          <div className="mt-8 h-px bg-gradient-to-r from-transparent via-slate-700/60 to-transparent" />
        </motion.header>

        {/* ── Page content ──────────────────────────────── */}
        <AnimatePresence mode="wait">
          {currentSource === 'google-fit' ? (
            <motion.div
              key="google-fit"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.25 }}
            >
              <GoogleFitDashboard dateRange={dateRange} />
            </motion.div>
          ) : (
            <motion.div
              key="strava"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.25 }}
            >
              <StravaDashboard dateRange={dateRange} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Dashboard;
