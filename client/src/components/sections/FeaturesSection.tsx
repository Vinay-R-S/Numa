"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  BrainCircuit,
  BatteryCharging,
  ShieldCheck,
  ListChecks,
  Workflow,
  Link2,
} from "lucide-react";

const features = [
  {
    icon: BrainCircuit,
    title: "Multi-Agent Intelligence",
    description:
      "Dedicated AI agents for each connected service, orchestrated by a master agent that understands your complete digital context and makes smart decisions.",
    accent: "from-indigo-500/20 to-violet-500/20",
    iconBg: "bg-indigo-500/10 text-indigo-400 ring-indigo-500/20",
  },
  {
    icon: Workflow,
    title: "Unified RAG Database",
    description:
      "All your app data flows into a single vector database, giving agents deep cross-platform context across health, productivity, and communication.",
    accent: "from-purple-500/20 to-pink-500/20",
    iconBg: "bg-purple-500/10 text-purple-400 ring-purple-500/20",
  },
  {
    icon: ListChecks,
    title: "Context-Aware Todo",
    description:
      "A built-in task manager that knows your calendar, energy levels, and workload. Prioritizes what matters based on real data from all your connected apps.",
    accent: "from-emerald-500/20 to-teal-500/20",
    iconBg: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
  },
  {
    icon: BatteryCharging,
    title: "Energy-Aware Scheduling",
    description:
      "Dynamically reorders your tasks based on real-time energy, sleep quality, workout recovery, and focus patterns detected from your health data.",
    accent: "from-amber-500/20 to-orange-500/20",
    iconBg: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
  },
  {
    icon: ShieldCheck,
    title: "Privacy-First Design",
    description:
      "Your raw data stays encrypted and secure. AI agents only access aggregated, anonymized scores and never touch personal information directly.",
    accent: "from-cyan-500/20 to-blue-500/20",
    iconBg: "bg-cyan-500/10 text-cyan-400 ring-cyan-500/20",
  },
  {
    icon: Link2,
    title: "Deep Integrations",
    description:
      "Connects seamlessly with Strava, Google Fit, Calendar, GitHub, LeetCode, Slack, and includes built-in journaling, meditation, and focus tools.",
    accent: "from-rose-500/20 to-red-500/20",
    iconBg: "bg-rose-500/10 text-rose-400 ring-rose-500/20",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 24, filter: "blur(4px)" },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      delay: i * 0.08,
      duration: 0.6,
      ease: [0.23, 1, 0.32, 1] as [number, number, number, number],
    },
  }),
};

export default function FeaturesSection() {
  return (
    <section id="features" className="relative py-28 md:py-36">
      {/* Ambient glow */}
      <div className="absolute top-1/2 left-0 -translate-y-1/2 w-125 h-125 bg-indigo-500/4 rounded-full blur-[150px] pointer-events-none" />

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
            Core Features
          </motion.p>
          <motion.h2
            variants={fadeUp}
            custom={1}
            className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/60"
          >
            Everything you need, one platform
          </motion.h2>
          <motion.p
            variants={fadeUp}
            custom={2}
            className="text-gray-400 text-base md:text-lg max-w-lg"
          >
            Intelligent agents, a unified data layer, and built-in tools
            designed around how you actually live and work.
          </motion.p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group relative overflow-hidden rounded-2xl border border-white/6 bg-white/2 p-7 hover:border-white/12 transition-all duration-500"
              >
                <div
                  className={`absolute inset-0 bg-linear-to-br ${feature.accent} opacity-0 group-hover:opacity-100 transition-opacity duration-700`}
                />
                <div className="relative z-10">
                  <div
                    className={`mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl ${feature.iconBg} ring-1`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2 tracking-tight">
                    {feature.title}
                  </h3>
                  <p className="text-gray-400 leading-relaxed text-[13px]">
                    {feature.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
