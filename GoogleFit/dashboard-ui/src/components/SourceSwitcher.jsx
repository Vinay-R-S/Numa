import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const SourceSwitcher = ({ currentSource, onSourceChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const sources = [
    { id: 'google-fit', name: 'Google Fit', icon: '🏃' },
    { id: 'strava', name: 'Strava', icon: '🚴' }
  ];
  
  const currentSourceData = sources.find(s => s.id === currentSource);
  
  return (
    <div className="relative">
      {/* Dropdown button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsOpen(!isOpen)}
        className="glass-effect px-6 py-3 rounded-2xl shadow-neumorphic hover:shadow-neumorphic-inset transition-all duration-300 flex items-center gap-3 min-w-[200px]"
      >
        <span className="text-2xl">{currentSourceData?.icon}</span>
        <span className="text-white font-semibold flex-1 text-left">
          {currentSourceData?.name}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown className="w-5 h-5 text-slate-400" />
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
              className="absolute top-full mt-2 w-full glass-effect rounded-2xl shadow-neumorphic overflow-hidden z-20"
            >
              {sources.map((source, index) => (
                <motion.button
                  key={source.id}
                  whileHover={{ backgroundColor: 'rgba(71, 85, 105, 0.3)' }}
                  onClick={() => {
                    onSourceChange(source.id);
                    setIsOpen(false);
                  }}
                  className={`w-full px-6 py-3 flex items-center gap-3 transition-colors ${
                    currentSource === source.id ? 'bg-slate-700/30' : ''
                  } ${index > 0 ? 'border-t border-slate-700/50' : ''}`}
                >
                  <span className="text-2xl">{source.icon}</span>
                  <span className="text-white font-medium">{source.name}</span>
                  {currentSource === source.id && (
                    <span className="ml-auto text-cyan-400">✓</span>
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

export default SourceSwitcher;
