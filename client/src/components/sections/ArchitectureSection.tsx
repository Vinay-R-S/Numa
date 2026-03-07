"use client";

import React from "react";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { Database, Lock, Cpu } from "lucide-react";

const layers = [
  {
    icon: Database,
    title: "Data Sources",
    badge: "Layer 1",
    accent: "border-emerald-500/20",
    iconBg: "bg-emerald-500/10 text-emerald-400",
    dotColor: "bg-emerald-500/60",
    items: [
      "Strava & Google Fit health data",
      "Google Calendar events & schedules",
      "GitHub commits & LeetCode progress",
      "Slack messages & communication logs",
      "Built-in journal entries & notes",
    ],
    note: "All connected apps feed data into the system continuously.",
  },
  {
    icon: Lock,
    title: "RAG Database",
    badge: "Layer 2",
    accent: "border-indigo-500/20",
    iconBg: "bg-indigo-500/10 text-indigo-400",
    dotColor: "bg-indigo-500/60",
    items: [
      "Unified vector storage for all sources",
      "Cross-platform contextual embeddings",
      "Real-time indexing and retrieval",
      "Privacy-first encrypted storage",
      "Aggregated scores and trend analysis",
    ],
    note: "The central knowledge layer that powers all agent intelligence.",
  },
  {
    icon: Cpu,
    title: "Agent Network",
    badge: "Layer 3",
    accent: "border-purple-500/20",
    iconBg: "bg-purple-500/10 text-purple-400",
    dotColor: "bg-purple-500/60",
    items: [
      "Individual agents per connected app",
      "Master agent for orchestration",
      "Cross-agent decision coordination",
      "Automated workflow execution",
      "Natural language assistant interface",
    ],
    note: "Isolated agents controlled by a master orchestrator for smart decisions.",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 24, filter: "blur(4px)" },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      delay: i * 0.12,
      duration: 0.6,
      ease: [0.23, 1, 0.32, 1] as [number, number, number, number],
    },
  }),
};

export default function ArchitectureSection() {
  return (
    <section id="architecture" className="relative py-28 md:py-36">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="flex flex-col items-center text-center gap-4 mb-20"
        >
          <motion.p
            variants={fadeUp}
            custom={0}
            className="text-[13px] font-semibold uppercase tracking-[0.2em] text-indigo-400"
          >
            Architecture
          </motion.p>
          <motion.h2
            variants={fadeUp}
            custom={1}
            className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/60"
          >
            Three-layer intelligence stack
          </motion.h2>
          <motion.p
            variants={fadeUp}
            custom={2}
            className="text-gray-400 text-base md:text-lg max-w-lg"
          >
            Data sources feed into a RAG database, which powers isolated
            agents coordinated by a master orchestrator.
          </motion.p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {layers.map((layer, i) => {
            const Icon = layer.icon;
            return (
              <div
                key={layer.title}
                className={`relative rounded-2xl border border-white/6 bg-white/2 p-8 flex flex-col hover:border-white/10 transition-all duration-500`}
              >
                {/* Top accent line */}
                <div className={`absolute top-0 left-6 right-6 h-px ${layer.accent} bg-current opacity-40`} />

                <div className="flex items-center gap-3 mb-6">
                  <div
                    className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${layer.iconBg}`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-[11px] font-mono text-gray-500 uppercase tracking-[0.2em]">
                    {layer.badge}
                  </span>
                </div>

                <h3 className="text-xl font-semibold text-white mb-5">
                  {layer.title}
                </h3>

                <ul className="space-y-3 mb-6 flex-1">
                  {layer.items.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-2.5 text-[13px] text-gray-400"
                    >
                      <span
                        className={`mt-1.5 h-1.5 w-1.5 rounded-full ${layer.dotColor} shrink-0`}
                      />
                      {item}
                    </li>
                  ))}
                </ul>

                <Separator className="bg-white/6 mb-4" />

                <p className="text-xs text-gray-500 italic">{layer.note}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
