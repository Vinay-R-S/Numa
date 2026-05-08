"use client";

import React from "react";
import { motion } from "framer-motion";
import { HardHat, ArrowLeft, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function UnderConstructionPage() {
  return (
    <div className="min-h-screen bg-[#080809] flex flex-col items-center justify-center px-6 py-16 relative overflow-hidden">
      {/* Ambient glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-150 h-100 bg-indigo-500/8 rounded-full blur-[160px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-100 h-75 bg-purple-500/6 rounded-full blur-[140px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 30, filter: "blur(8px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
        className="flex flex-col items-center text-center max-w-lg w-full gap-8"
      >
        {/* Icon badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15, duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
          className="relative"
        >
          <div className="h-20 w-20 md:h-24 md:w-24 rounded-3xl bg-white/4 border border-white/8 flex items-center justify-center shadow-[0_0_60px_rgba(99,102,241,0.15)]">
            <HardHat className="h-9 w-9 md:h-11 md:w-11 text-indigo-400" />
          </div>
          <span className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-amber-400/15 border border-amber-400/30 ring-4 ring-[#080809]">
            <Sparkles className="h-3 w-3 text-amber-400" />
          </span>
        </motion.div>

        {/* Heading */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.7, ease: [0.23, 1, 0.32, 1] }}
          className="flex flex-col gap-3"
        >
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight text-transparent bg-clip-text bg-linear-to-b from-white via-white/90 to-white/50 leading-tight">
            Page Under
            <br />
            Construction
          </h1>
          <p className="text-sm sm:text-base text-gray-400 leading-relaxed max-w-sm mx-auto">
            We&apos;re working hard to bring this page to life. Check back soon
            - great things are on the way.
          </p>
        </motion.div>

        {/* Progress bar decoration */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: 0.4, duration: 1.2, ease: [0.23, 1, 0.32, 1] }}
          className="w-full max-w-xs origin-left"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-gray-600 uppercase tracking-widest font-medium">
              Progress
            </span>
            <span className="text-[11px] text-indigo-400 font-semibold">
              Coming Soon
            </span>
          </div>
          <div className="h-1.5 w-full bg-white/4 rounded-full overflow-hidden border border-white/4">
            <motion.div
              initial={{ width: "0%" }}
              animate={{ width: "60%" }}
              transition={{ delay: 0.6, duration: 1.5, ease: [0.23, 1, 0.32, 1] }}
              className="h-full bg-linear-to-r from-indigo-500 to-violet-500 rounded-full"
            />
          </div>
        </motion.div>

        {/* Pill tags */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
          className="flex flex-wrap justify-center gap-2"
        >
          {["Design", "Development", "Testing"].map((tag, i) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-white/6 bg-white/3 text-[12px] text-gray-500"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  i === 0
                    ? "bg-green-400"
                    : i === 1
                    ? "bg-amber-400"
                    : "bg-gray-600"
                }`}
              />
              {tag}
            </span>
          ))}
        </motion.div>

        {/* Back button */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
        >
          <Link href="/">
            <Button
              variant="outline"
              className="border-white/10 text-gray-300 hover:text-white hover:bg-white/6 hover:border-white/20 rounded-xl px-6 h-11 text-sm transition-all gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Button>
          </Link>
        </motion.div>
      </motion.div>

      {/* Bottom NUMA brand */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 0.8 }}
        className="absolute bottom-8 text-[11px] text-gray-700 tracking-widest uppercase font-medium"
      >
        NUMA &mdash; AI-Powered Life OS
      </motion.p>
    </div>
  );
}
