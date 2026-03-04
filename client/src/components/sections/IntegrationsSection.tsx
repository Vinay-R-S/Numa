"use client";

import React from "react";
import { motion } from "framer-motion";
import OrbitingIntegrations from "@/components/OrbitingIntegrations";
import { Badge } from "@/components/ui/badge";

const fadeUp = {
  hidden: { opacity: 0, y: 24, filter: "blur(4px)" },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      delay: i * 0.1,
      duration: 0.6,
      ease: [0.23, 1, 0.32, 1] as [number, number, number, number],
    },
  }),
};

const integrations = [
  { name: "Google Calendar", desc: "Smart scheduling", tag: "Calendar" },
  { name: "Strava", desc: "Workout tracking", tag: "Fitness" },
  { name: "Google Fit", desc: "Health metrics", tag: "Health" },
  { name: "GitHub", desc: "Code activity", tag: "Dev" },
  { name: "LeetCode", desc: "Progress tracking", tag: "Dev" },
  { name: "Slack", desc: "Team communication", tag: "Comms" },
  { name: "Journal", desc: "Notes & reflections", tag: "Built-in" },
  { name: "Meditation", desc: "Mindfulness sessions", tag: "Built-in" },
  { name: "Focus Timer", desc: "Deep work sessions", tag: "Built-in" },
  { name: "Todo List", desc: "Context-aware tasks", tag: "Built-in" },
];

export default function IntegrationsSection() {
  return (
    <section id="integrations" className="relative py-28 md:py-36">
      {/* Ambient glow */}
      <div className="absolute top-1/2 right-0 -translate-y-1/2 w-125 h-125 bg-purple-500/4 rounded-full blur-[150px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Text side */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            className="flex flex-col gap-6"
          >
            <motion.p
              variants={fadeUp}
              custom={0}
              className="text-[13px] font-semibold uppercase tracking-[0.2em] text-indigo-400"
            >
              Integrations
            </motion.p>
            <motion.h2
              variants={fadeUp}
              custom={1}
              className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/60"
            >
              Plugs into the tools you already use
            </motion.h2>
            <motion.p
              variants={fadeUp}
              custom={2}
              className="text-gray-400 text-base md:text-lg leading-relaxed"
            >
              NUMA connects to your existing ecosystem, from calendars and
              fitness trackers to code repositories and communication platforms,
              plus built-in tools for journaling, meditation, and focus.
            </motion.p>

            <motion.div
              variants={fadeUp}
              custom={3}
              className="grid grid-cols-2 gap-3 mt-4"
            >
              {integrations.slice(0, 6).map((item) => (
                <div
                  key={item.name}
                  className="group border border-white/6 rounded-xl p-4 bg-white/2 hover:bg-white/4 hover:border-white/10 transition-all duration-300"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-white text-sm">
                      {item.name}
                    </span>
                    <Badge
                      variant="outline"
                      className="text-[10px] border-white/8 text-gray-500 px-1.5 py-0 h-4 rounded-md font-normal"
                    >
                      {item.tag}
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-500">{item.desc}</div>
                </div>
              ))}
            </motion.div>

            {/* Built-in tools row */}
            <motion.div
              variants={fadeUp}
              custom={4}
              className="grid grid-cols-2 gap-3"
            >
              {integrations.slice(6).map((item) => (
                <div
                  key={item.name}
                  className="group border border-white/6 rounded-xl p-4 bg-white/2 hover:bg-white/4 hover:border-white/10 transition-all duration-300"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-white text-sm">
                      {item.name}
                    </span>
                    <Badge
                      variant="outline"
                      className="text-[10px] border-indigo-500/20 text-indigo-400 px-1.5 py-0 h-4 rounded-md font-normal"
                    >
                      {item.tag}
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-500">{item.desc}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Orbital visualization */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
            className="relative w-full flex items-center justify-center max-h-72 sm:max-h-96 lg:max-h-none"
          >
            <OrbitingIntegrations />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
