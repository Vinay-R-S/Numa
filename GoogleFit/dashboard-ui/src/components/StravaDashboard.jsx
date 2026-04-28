import React from 'react';
import { motion } from 'framer-motion';
import { Activity, MapPin, Clock, Flame } from 'lucide-react';
import MetricCard from './MetricCard';
import ActivityList from './ActivityList';
import { METRIC_COLORS } from '../utils/colors';
import { stravaData } from '../data/mockData';

const StravaDashboard = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        stiffness: 100
      }
    }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      exit="hidden"
    >
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <motion.div variants={itemVariants}>
          <div className="glass-effect rounded-2xl p-6 shadow-neumorphic">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center mb-4 shadow-lg shadow-cyan-500/50">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div className="mb-2">
              <span className="text-4xl font-bold text-white">
                {stravaData.activities.value}
              </span>
              <span className="text-lg text-slate-400 ml-2">{stravaData.activities.unit}</span>
            </div>
            <div className="text-slate-400 text-sm font-medium mb-2">
              {stravaData.activities.label}
            </div>
            <div className="text-emerald-400 text-sm font-semibold">
              {stravaData.activities.change}
            </div>
          </div>
        </motion.div>

        <motion.div variants={itemVariants}>
          <div className="glass-effect rounded-2xl p-6 shadow-neumorphic">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-4 shadow-lg shadow-purple-500/50">
              <MapPin className="w-6 h-6 text-white" />
            </div>
            <div className="mb-2">
              <span className="text-4xl font-bold text-white">
                {stravaData.distance.value}
              </span>
              <span className="text-lg text-slate-400 ml-2">{stravaData.distance.unit}</span>
            </div>
            <div className="text-slate-400 text-sm font-medium mb-2">
              {stravaData.distance.label}
            </div>
            <div className="text-emerald-400 text-sm font-semibold">
              {stravaData.distance.change}
            </div>
          </div>
        </motion.div>

        <motion.div variants={itemVariants}>
          <div className="glass-effect rounded-2xl p-6 shadow-neumorphic">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center mb-4 shadow-lg shadow-emerald-500/50">
              <Clock className="w-6 h-6 text-white" />
            </div>
            <div className="mb-2">
              <span className="text-4xl font-bold text-white">
                {stravaData.duration.value}
              </span>
              <span className="text-lg text-slate-400 ml-2">{stravaData.duration.unit}</span>
            </div>
            <div className="text-slate-400 text-sm font-medium mb-2">
              {stravaData.duration.label}
            </div>
            <div className="text-emerald-400 text-sm font-semibold">
              {stravaData.duration.change}
            </div>
          </div>
        </motion.div>

        <motion.div variants={itemVariants}>
          <div className="glass-effect rounded-2xl p-6 shadow-neumorphic">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center mb-4 shadow-lg shadow-orange-500/50">
              <Flame className="w-6 h-6 text-white" />
            </div>
            <div className="mb-2">
              <span className="text-4xl font-bold text-white">
                {stravaData.calories.value}
              </span>
              <span className="text-lg text-slate-400 ml-2">{stravaData.calories.unit}</span>
            </div>
            <div className="text-slate-400 text-sm font-medium mb-2">
              {stravaData.calories.label}
            </div>
            <div className="text-emerald-400 text-sm font-semibold">
              {stravaData.calories.change}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recent Activities */}
      <motion.div variants={itemVariants}>
        <ActivityList activities={stravaData.recentActivities} />
      </motion.div>
    </motion.div>
  );
};

export default StravaDashboard;
