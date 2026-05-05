"use client";

import React from "react";
import { motion } from "framer-motion";

interface OrbitIcon {
  label: string;
  svg: React.ReactNode;
}

const innerOrbit: OrbitIcon[] = [
  { label: "Google Calendar", svg: <GoogleCalendarIcon /> },
  { label: "Slack", svg: <SlackIcon /> },
  { label: "GitHub", svg: <GitHubIcon /> },
  { label: "Google Fit", svg: <GoogleFitIcon /> },
];

const outerOrbit: OrbitIcon[] = [
  { label: "Strava", svg: <StravaIcon /> },
  { label: "LeetCode", svg: <LeetCodeIcon /> },
  { label: "Journal", svg: <JournalIcon /> },
  { label: "Meditation", svg: <MeditationIcon /> },
  { label: "Timer", svg: <TimerIcon /> },
  { label: "Todo", svg: <TodoIcon /> },
];

export default function OrbitingIntegrations() {
  return (
    <div className="relative w-full aspect-square max-w-[85vw] sm:max-w-sm md:max-w-135 mx-auto">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-65 h-65 bg-indigo-500/8 rounded-full blur-[80px] pointer-events-none" />

      {/* Outer orbit ring */}
      <div className="absolute inset-0">
        <div className="absolute inset-[8%] rounded-full border border-white/4" />
        <motion.div
          className="absolute inset-[8%]"
          animate={{ rotate: 360 }}
          transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
        >
          {outerOrbit.map((icon, i) => (
            <OrbitNode
              key={icon.label}
              icon={icon}
              angle={(360 / outerOrbit.length) * i}
              radius={50}
              counterRotateDuration={60}
              size="sm"
            />
          ))}
        </motion.div>
      </div>

      {/* Inner orbit ring */}
      <div className="absolute inset-0">
        <div className="absolute inset-[28%] rounded-full border border-white/6" />
        <motion.div
          className="absolute inset-[28%]"
          animate={{ rotate: -360 }}
          transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
        >
          {innerOrbit.map((icon, i) => (
            <OrbitNode
              key={icon.label}
              icon={icon}
              angle={(360 / innerOrbit.length) * i}
              radius={50}
              counterRotateDuration={40}
              counterRotateReverse
              size="md"
            />
          ))}
        </motion.div>
      </div>

      {/* Center hub */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
        <div className="relative">
          <motion.div
            className="absolute inset-0 rounded-full border border-indigo-400/30"
            animate={{ scale: [1, 1.5, 1], opacity: [0.4, 0, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            style={{ margin: "-8px" }}
          />
          <div className="relative h-20 w-20 rounded-full bg-linear-to-br from-indigo-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center backdrop-blur-sm">
            <span className="text-white font-bold text-sm tracking-wider">NUMA</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function OrbitNode({
  icon,
  angle,
  radius,
  counterRotateDuration,
  counterRotateReverse = false,
  size = "md",
}: {
  icon: OrbitIcon;
  angle: number;
  radius: number;
  counterRotateDuration: number;
  counterRotateReverse?: boolean;
  size?: "sm" | "md";
}) {
  const rad = (angle * Math.PI) / 180;
  const x = parseFloat((50 + radius * Math.cos(rad)).toFixed(4));
  const y = parseFloat((50 + radius * Math.sin(rad)).toFixed(4));
  const sz = size === "sm" ? "h-10 w-10" : "h-12 w-12";

  return (
    <div
      className="absolute"
      style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}
    >
      <motion.div
        animate={{ rotate: counterRotateReverse ? -360 : 360 }}
        transition={{ duration: counterRotateDuration, repeat: Infinity, ease: "linear" }}
      >
        <div
          className={`group relative ${sz} rounded-full border border-white/10 bg-[#0a0a0b] flex items-center justify-center hover:border-white/25 hover:bg-white/6 transition-all duration-300 cursor-default`}
        >
          {icon.svg}
          <div className="absolute -bottom-7 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap">
            <span className="text-[10px] text-gray-400 bg-[#0a0a0b]/90 border border-white/8 rounded-md px-2 py-0.5">
              {icon.label}
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

/* -- Brand Icons (dark-themed) ----------------------------------------- */

function GoogleCalendarIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#111827] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="4" width="18" height="18" rx="2" stroke="#4285F4" strokeWidth="1.5" />
        <path d="M3 9h18" stroke="#4285F4" strokeWidth="1.5" />
        <path d="M9 4V2" stroke="#4285F4" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M15 4V2" stroke="#4285F4" strokeWidth="1.5" strokeLinecap="round" />
        <rect x="7" y="12" width="3" height="3" rx="0.5" fill="#EA4335" />
        <rect x="14" y="12" width="3" height="3" rx="0.5" fill="#34A853" />
        <rect x="7" y="17" width="3" height="2" rx="0.5" fill="#FBBC05" />
        <rect x="14" y="17" width="3" height="2" rx="0.5" fill="#4285F4" />
      </svg>
    </div>
  );
}

function SlackIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#111827] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none">
        <path d="M6 15a2 2 0 0 1-2 2 2 2 0 0 1-2-2 2 2 0 0 1 2-2h2v2Z" fill="#E01E5A" />
        <path d="M7 15a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-5Z" fill="#E01E5A" />
        <path d="M9 6a2 2 0 0 1-2-2 2 2 0 0 1 2-2 2 2 0 0 1 2 2v2H9Z" fill="#36C5F0" />
        <path d="M9 7a2 2 0 0 1 2 2 2 2 0 0 1-2 2H4a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5Z" fill="#36C5F0" />
        <path d="M18 9a2 2 0 0 1 2-2 2 2 0 0 1 2 2 2 2 0 0 1-2 2h-2V9Z" fill="#2EB67D" />
        <path d="M17 9a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5Z" fill="#2EB67D" />
        <path d="M15 18a2 2 0 0 1 2 2 2 2 0 0 1-2 2 2 2 0 0 1-2-2v-2h2Z" fill="#ECB22E" />
        <path d="M15 17a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-5Z" fill="#ECB22E" />
      </svg>
    </div>
  );
}

function GitHubIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#111827] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.1.39-1.99 1.03-2.69-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.8c.85.004 1.7.114 2.5.34 1.9-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.4.1 2.64.64.7 1.03 1.6 1.03 2.69 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.16.59.67.5A10.003 10.003 0 0 0 22 12c0-5.523-4.477-10-10-10Z" fill="#e2e8f0" />
      </svg>
    </div>
  );
}

function GoogleFitIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#111827] p-2.5">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none">
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35Z" fill="none" stroke="#EA4335" strokeWidth="1.5" />
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09" stroke="#4285F4" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M12 5.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35" stroke="#34A853" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function StravaIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#1a1210] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none">
        <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066l-2.084 4.116Z" fill="#FC4C02" />
        <path d="M10.233 13.828L7.164 7.912 4.1 13.828h3.064l-3.064 0h6.133Z" fill="#FC4C02" opacity="0.6" />
        <path d="M7.168 0l5.154 10.172h3.064L7.168 0Z" fill="#FC4C02" />
      </svg>
    </div>
  );
}

function LeetCodeIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#1a1a10] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none">
        <path d="M13.483 0a1.374 1.374 0 0 0-.961.438L7.116 6.226l-3.854 4.126a5.266 5.266 0 0 0-1.209 2.104 5.35 5.35 0 0 0-.125.513 5.527 5.527 0 0 0 .062 2.362 5.83 5.83 0 0 0 .349 1.017 5.938 5.938 0 0 0 1.271 1.818l4.277 4.193.039.038c2.248 2.165 5.852 2.133 8.063-.074l2.396-2.392c.54-.54.54-1.414.003-1.955a1.378 1.378 0 0 0-1.951-.003l-2.396 2.392a3.021 3.021 0 0 1-4.205.038l-.02-.019-4.276-4.193c-.652-.64-.972-1.469-.948-2.263a2.68 2.68 0 0 1 .066-.523 2.545 2.545 0 0 1 .619-1.164L9.13 8.114c1.058-1.134 3.204-1.27 4.43-.278l3.501 2.831c.593.48 1.461.387 1.94-.207a1.384 1.384 0 0 0-.207-1.943l-3.5-2.831c-.8-.647-1.766-1.045-2.774-1.202l2.015-2.158A1.384 1.384 0 0 0 13.483 0ZM8.075 15.053h6.538c.563 0 1.021-.382 1.14-.89a1.17 1.17 0 0 0-.106-.823 1.12 1.12 0 0 0-1.034-.607H8.075a1.12 1.12 0 0 0-1.034.607 1.17 1.17 0 0 0-.106.823c.119.508.577.89 1.14.89Z" fill="#FFA116" />
      </svg>
    </div>
  );
}

/* -- Built-in Feature Icons --------------------------------------------- */

function JournalIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#1a1a2e] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
        <path d="M8 7h6" />
        <path d="M8 11h8" />
      </svg>
    </div>
  );
}

function MeditationIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#1a1a2e] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="5" r="2" />
        <path d="M12 7v3" />
        <path d="M8 14c-2 0-3 1-3 3" />
        <path d="M16 14c2 0 3 1 3 3" />
        <path d="M12 10c-2.5 1-4 3-4 4h8c0-1-1.5-3-4-4Z" />
        <path d="M7 21c1-1 2.5-2 5-2s4 1 5 2" />
      </svg>
    </div>
  );
}

function TimerIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#1a2e1a] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="13" r="8" />
        <path d="M12 9v4l2 2" />
        <path d="M10 2h4" />
        <path d="M12 2v2" />
      </svg>
    </div>
  );
}

function TodoIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-[#2e1a1a] p-2">
      <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    </div>
  );
}
