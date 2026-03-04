"use client";

import React from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

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

export default function CTASection() {
  return (
    <section className="relative py-28 md:py-36">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="relative overflow-hidden rounded-3xl border border-white/6 bg-white/2 p-12 md:p-20 text-center"
        >
          {/* Top accent line */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2/3 h-px bg-linear-to-r from-transparent via-indigo-500/60 to-transparent" />

          {/* Glow */}
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-125 h-100 bg-indigo-500/7 rounded-full blur-[150px] pointer-events-none" />

          <motion.p
            variants={fadeUp}
            custom={0}
            className="text-[13px] font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-6"
          >
            One Platform, Everything Connected
          </motion.p>

          <motion.h2
            variants={fadeUp}
            custom={1}
            className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight mb-6 text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/60"
          >
            Your entire digital life, unified
          </motion.h2>

          <motion.p
            variants={fadeUp}
            custom={2}
            className="text-lg text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed"
          >
            Connect your health trackers, calendars, repos, and communication
            tools. Intelligent agents do the rest — surfacing insights and
            automating your workflows across every platform.
          </motion.p>

          <motion.div variants={fadeUp} custom={3}>
            <a href="/auth">
              <Button
                size="lg"
                className="bg-white text-black hover:bg-gray-100 font-semibold rounded-xl px-10 py-6 text-base shadow-[0_0_40px_rgba(255,255,255,0.1)] hover:shadow-[0_0_60px_rgba(255,255,255,0.18)] transition-all duration-500"
              >
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </a>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
