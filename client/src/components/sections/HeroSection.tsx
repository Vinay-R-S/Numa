"use client";

import React from "react";
import { motion } from "framer-motion";
import { RotatingText } from "@/components/ui/rotating-text";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles } from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 24, filter: "blur(4px)" },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      delay: i * 0.12,
      duration: 0.7,
      ease: [0.23, 1, 0.32, 1] as [number, number, number, number],
    },
  }),
};

export default function HeroSection() {
  return (
    <section className="relative py-28 md:py-40 overflow-hidden">
      {/* Ambient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-200 h-125 bg-indigo-500/7 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute top-40 right-0 w-100 h-100 bg-purple-500/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-5xl mx-auto px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="flex flex-col items-center text-center gap-8"
        >
          <motion.div variants={fadeUp} custom={0}>
            <Badge
              variant="outline"
              className="border-white/8 text-gray-400 bg-white/4 backdrop-blur-sm px-4 py-1.5 text-[13px] rounded-full gap-1.5 font-medium"
            >
              <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              AI-Powered Life Operating System
            </Badge>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            custom={1}
            className="text-4xl md:text-5xl lg:text-[4.5rem] font-semibold tracking-tight leading-[1.08] font-sans"
          >
            <span className="text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/50">
              One Platform for
            </span>
            <br />
            <div className="mt-2 flex items-center justify-center gap-3">
              <span className="text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/60">
                All Your
              </span>
              <RotatingText
                words={[
                  "Productivity",
                  "Wellbeing",
                  "Health",
                  "Workflows",
                ]}
                className="text-white"
                boxClassName="bg-white text-black px-5 py-1 rounded-xl"
              />
            </div>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            custom={2}
            className="text-base md:text-lg text-gray-400 max-w-xl leading-relaxed"
          >
            NUMA connects your health, productivity, and communication apps
            into a unified AI-powered workspace. Intelligent agents work across
            your data to automate tasks, surface insights, and keep you in flow.
          </motion.p>

          <motion.div
            variants={fadeUp}
            custom={3}
            className="flex flex-wrap justify-center gap-3 mt-2"
          >
            <a href="/auth">
              <Button
                size="lg"
                className="bg-white text-black hover:bg-gray-100 font-semibold rounded-xl px-8 h-12 text-sm shadow-[0_0_30px_rgba(255,255,255,0.1)] transition-shadow hover:shadow-[0_0_40px_rgba(255,255,255,0.2)]"
              >
                Sign In
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </a>
            <Button
              size="lg"
              variant="outline"
              className="border-white/12 text-gray-300 hover:text-white hover:bg-white/6 hover:border-white/20 rounded-xl px-8 h-12 text-sm transition-all"
            >
              Learn More
            </Button>
          </motion.div>

          {/* Stat pills */}
          <motion.div
            variants={fadeUp}
            custom={4}
            className="flex flex-wrap justify-center gap-3 mt-6"
          >
            {[
              { value: "10+", label: "Integrations" },
              { value: "Multi-Agent", label: "AI System" },
              { value: "Real-time", label: "Data Sync" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="border border-white/8 rounded-xl px-5 py-3 bg-white/3 hover:bg-white/5 hover:border-white/12 transition-all duration-300"
              >
                <div className="text-base font-semibold text-white leading-tight">
                  {stat.value}
                </div>
                <div className="text-[11px] text-gray-500 uppercase font-medium tracking-wider mt-0.5">
                  {stat.label}
                </div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
