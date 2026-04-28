import React, { useState } from 'react';
import { ChevronDown, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { DATE_RANGES, DATE_RANGE_LABELS, formatDateRange } from '../utils/dateUtils';

const DateRangePicker = ({ currentRange, onRangeChange, dateRange }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const rangeOptions = [
    { id: DATE_RANGES.TODAY, label: DATE_RANGE_LABELS[DATE_RANGES.TODAY], icon: '📅' },
    { id: DATE_RANGES.YESTERDAY, label: DATE_RANGE_LABELS[DATE_RANGES.YESTERDAY], icon: '📆' },
    { id: DATE_RANGES.LAST_7_DAYS, label: DATE_RANGE_LABELS[DATE_RANGES.LAST_7_DAYS], icon: '📊' },
    { id: DATE_RANGES.LAST_30_DAYS, label: DATE_RANGE_LABELS[DATE_RANGES.LAST_30_DAYS], icon: '📈' },
    { id: DATE_RANGES.THIS_WEEK, label: DATE_RANGE_LABELS[DATE_RANGES.THIS_WEEK], icon: '🗓️' },
    { id: DATE_RANGES.THIS_MONTH, label: DATE_RANGE_LABELS[DATE_RANGES.THIS_MONTH], icon: '📋' }
  ];
  
  const currentOption = rangeOptions.find(opt => opt.id === currentRange);
  const displayText = dateRange ? formatDateRange(dateRange.start, dateRange.end) : currentOption?.label;
  
  return (
    <div className="relative">
      {/* Dropdown button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsOpen(!isOpen)}
        className="glass-effect px-4 py-2.5 rounded-xl shadow-neumorphic hover:shadow-neumorphic-inset transition-all duration-300 flex items-center gap-2 min-w-[180px]"
      >
        <Calendar className="w-4 h-4 text-cyan-400" />
        <span className="text-white font-medium text-sm flex-1 text-left">
          {displayText}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </motion.div>
      </motion.button>
      
      {/* Dropdown menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div 
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            
            {/* Menu */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="absolute top-full mt-2 w-full glass-effect rounded-xl shadow-neumorphic overflow-hidden z-20"
            >
              {rangeOptions.map((option, index) => (
                <motion.button
                  key={option.id}
                  whileHover={{ backgroundColor: 'rgba(71, 85, 105, 0.3)' }}
                  onClick={() => {
                    onRangeChange(option.id);
                    setIsOpen(false);
                  }}
                  className={`w-full px-4 py-2.5 flex items-center gap-2 transition-colors ${
                    currentRange === option.id ? 'bg-slate-700/30' : ''
                  } ${index > 0 ? 'border-t border-slate-700/50' : ''}`}
                >
                  <span className="text-lg">{option.icon}</span>
                  <span className="text-white font-medium text-sm">{option.label}</span>
                  {currentRange === option.id && (
                    <span className="ml-auto text-cyan-400 text-sm">✓</span>
                  )}
                </motion.button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DateRangePicker;
