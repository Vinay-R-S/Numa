"use client";

import React from "react";
import { motion } from "framer-motion";
import Image from "next/image";

import GithubLogo from "../../assets/Images/GitHub-logo.webp";
import GoogleCalendarLogo from "../../assets/Images/GoogleCalendar-logo.webp";
import GoogleFitLogo from "../../assets/Images/GoogleFit-logo.webp";
import LeetCodeLogo from "../../assets/Images/LeetCode-logo.webp";
import StravaLogo from "../../assets/Images/Strava-logo.webp";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface OrbitIcon {
  label: string;
  type: "image" | "svg" | "emoji";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  src?: any;
  svg?: React.ReactNode;
  emoji?: string;
  bg?: string; // optional white bg for logos that need it
}

const innerOrbit: OrbitIcon[] = [
  { label: "Google Calendar", type: "image", src: GoogleCalendarLogo, bg: "bg-white" },
  { label: "Slack", type: "svg", svg: <SlackIcon /> },
  { label: "GitHub", type: "image", src: GithubLogo },
  { label: "Google Fit", type: "image", src: GoogleFitLogo, bg: "bg-white" },
];

const outerOrbit: OrbitIcon[] = [
  { label: "Strava", type: "image", src: StravaLogo, bg: "bg-white" },
  { label: "LeetCode", type: "image", src: LeetCodeLogo, bg: "bg-white" },
  { label: "Journal", type: "emoji", emoji: "📓" },
  { label: "Meditation", type: "emoji", emoji: "🧘" },
  { label: "Timer", type: "emoji", emoji: "⏱️" },
  { label: "Todo", type: "emoji", emoji: "✅" },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function OrbitingIntegrations() {
  return (
    <div className="relative w-full aspect-square max-w-135 mx-auto">
      {/* Ambient glow behind center */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-65 h-65 bg-indigo-500/8 rounded-full blur-[80px] pointer-events-none" />

      {/* Outer orbit ring */}
      <div className="absolute inset-0">
        <div className="absolute inset-[8%] rounded-full border border-white/4" />
        <motion.div
          className="absolute inset-[8%]"
          animate={{ rotate: 360 }}
          transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
        >
          {outerOrbit.map((icon, i) => {
            const angle = (360 / outerOrbit.length) * i;
            return (
              <OrbitNode
                key={icon.label}
                icon={icon}
                angle={angle}
                radius={50}
                counterRotateDuration={60}
                size="sm"
              />
            );
          })}
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
          {innerOrbit.map((icon, i) => {
            const angle = (360 / innerOrbit.length) * i;
            return (
              <OrbitNode
                key={icon.label}
                icon={icon}
                angle={angle}
                radius={50}
                counterRotateDuration={40}
                counterRotateReverse
                size="md"
              />
            );
          })}
        </motion.div>
      </div>

      {/* Center hub */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
        <div className="relative">
          {/* Pulse ring */}
          <motion.div
            className="absolute inset-0 rounded-full border border-indigo-400/30"
            animate={{ scale: [1, 1.5, 1], opacity: [0.4, 0, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            style={{ margin: "-8px" }}
          />
          <div className="relative h-20 w-20 rounded-full bg-linear-to-br from-indigo-500/20 to-purple-500/20 border border-white/10 flex items-center justify-center backdrop-blur-sm">
            <span className="text-white font-bold text-sm tracking-wider">
              NUMA
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Orbit node                                                         */
/* ------------------------------------------------------------------ */

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
  const x = 50 + radius * Math.cos(rad);
  const y = 50 + radius * Math.sin(rad);

  const sizeClasses = size === "sm" ? "h-10 w-10" : "h-12 w-12";
  const imgPad = size === "sm" ? "p-1.5" : "p-2";

  return (
    <div
      className="absolute"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        transform: "translate(-50%, -50%)",
      }}
    >
      <motion.div
        animate={{ rotate: counterRotateReverse ? -360 : 360 }}
        transition={{
          duration: counterRotateDuration,
          repeat: Infinity,
          ease: "linear",
        }}
      >
        <div
          className={`group relative ${sizeClasses} rounded-full border border-white/10 bg-[#0a0a0b] flex items-center justify-center hover:border-white/25 hover:bg-white/6 transition-all duration-300 cursor-default`}
        >
          {icon.type === "image" && icon.src && (
            <div
              className={`flex items-center justify-center rounded-full ${icon.bg || ""} ${imgPad} w-full h-full overflow-hidden`}
            >
              <Image
                src={icon.src}
                alt={icon.label}
                className="w-full h-full object-contain rounded-full"
              />
            </div>
          )}
          {icon.type === "svg" && icon.svg}
          {icon.type === "emoji" && (
            <span className={size === "sm" ? "text-base" : "text-lg"}>
              {icon.emoji}
            </span>
          )}

          {/* Tooltip */}
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

/* ------------------------------------------------------------------ */
/*  Inline SVG icons                                                   */
/* ------------------------------------------------------------------ */

function SlackIcon() {
  return (
    <div className="flex items-center justify-center w-full h-full rounded-full bg-white p-1.5">
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 127 127"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M27.2 80c0 7.3-5.9 13.2-13.2 13.2C6.7 93.2.8 87.3.8 80c0-7.3 5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V80z"
          fill="#E01E5A"
        />
        <path
          d="M47 27c-7.3 0-13.2-5.9-13.2-13.2C33.8 6.5 39.7.6 47 .6c7.3 0 13.2 5.9 13.2 13.2V27H47zm0 6.7c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H13.9C6.6 60.1.7 54.2.7 46.9c0-7.3 5.9-13.2 13.2-13.2H47z"
          fill="#36C5F0"
        />
        <path
          d="M99.9 46.9c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H99.9V46.9zm-6.6 0c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V13.8C66.9 6.5 72.8.6 80.1.6c7.3 0 13.2 5.9 13.2 13.2v33.1z"
          fill="#2EB67D"
        />
        <path
          d="M80.1 99.8c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V99.8h13.2zm0-6.6c-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33.1c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H80.1z"
          fill="#ECB22E"
        />
      </svg>
    </div>
  );
}
