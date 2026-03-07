"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Link2,
  Database,
  Bot,
  Crown,
} from "lucide-react";

const steps = [
  {
    icon: Link2,
    step: "01",
    title: "Connect Your Apps",
    description:
      "Link your health trackers, calendars, code repos, communication tools, and more. Setup takes seconds.",
  },
  {
    icon: Database,
    step: "02",
    title: "Data Flows to RAG",
    description:
      "All information is processed and stored in a unified vector database, building rich contextual understanding of your life.",
  },
  {
    icon: Bot,
    step: "03",
    title: "Agents Take Action",
    description:
      "Individual AI agents interact with each connected service on your behalf. They fetch, analyze, and control their respective apps.",
  },
  {
    icon: Crown,
    step: "04",
    title: "Master Agent Orchestrates",
    description:
      "A central orchestrator coordinates all agents, delivering intelligent suggestions and automated cross-app workflows.",
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

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="relative py-28 md:py-36">
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
            How It Works
          </motion.p>
          <motion.h2
            variants={fadeUp}
            custom={1}
            className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/60"
          >
            From connected apps to intelligent action
          </motion.h2>
          <motion.p
            variants={fadeUp}
            custom={2}
            className="text-gray-400 text-base md:text-lg max-w-lg"
          >
            A multi-agent architecture that connects your digital life and
            turns raw data into smart, automated workflows.
          </motion.p>
        </motion.div>

        <div className="relative grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <div
                key={step.step}
                className="relative flex flex-col items-center text-center group"
              >
                <div className="relative z-10 mb-6">
                  <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-white/4 border border-white/8 text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/20 transition-all duration-500">
                    <Icon className="h-6 w-6" />
                  </div>
                  <span className="absolute -top-2 -right-2 text-[10px] font-mono text-gray-600 bg-[#0a0a0b] border border-white/8 rounded-full h-5 w-5 flex items-center justify-center">
                    {step.step}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2 tracking-tight">
                  {step.title}
                </h3>
                <p className="text-gray-400 text-[13px] leading-relaxed max-w-60">
                  {step.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
