"use client";

import React, { useEffect, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface RotatingTextProps {
  words: string[];
  interval?: number;
  className?: string;
  boxClassName?: string;
  prefix?: string;
  suffix?: string;
}

export const RotatingText = ({
  words,
  interval = 3000,
  className,
  boxClassName,
  prefix,
  suffix,
}: RotatingTextProps) => {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1); // 1 = forward, -1 = backward

  const next = useCallback(() => {
    setDirection(1);
    setIndex((prev) => (prev + 1) % words.length);
  }, [words.length]);

  useEffect(() => {
    const timer = setInterval(next, interval);
    return () => clearInterval(timer);
  }, [next, interval]);

  const variants = {
    enter: (dir: number) => ({
      y: dir > 0 ? "100%" : "-100%",
      opacity: 0,
      filter: "blur(8px)",
      scale: 0.95,
    }),
    center: {
      y: "0%",
      opacity: 1,
      filter: "blur(0px)",
      scale: 1,
    },
    exit: (dir: number) => ({
      y: dir > 0 ? "-100%" : "100%",
      opacity: 0,
      filter: "blur(8px)",
      scale: 0.95,
    }),
  };

  return (
    <span className={cn("inline-flex items-center gap-3", className)}>
      {prefix && <span>{prefix}</span>}
      <span
        className={cn(
          "relative inline-flex items-center justify-center overflow-hidden rounded-xl bg-white text-black px-5 py-1",
          boxClassName
        )}
        style={{ minWidth: "200px" }}
      >
        <AnimatePresence mode="wait" custom={direction}>
          <motion.span
            key={words[index]}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              y: { type: "spring", stiffness: 300, damping: 30, mass: 0.8 },
              opacity: { duration: 0.25, ease: "easeInOut" },
              filter: { duration: 0.3, ease: "easeOut" },
              scale: { duration: 0.3, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] },
            }}
            className="inline-block whitespace-nowrap font-bold"
          >
            {words[index]}
          </motion.span>
        </AnimatePresence>
      </span>
      {suffix && <span>{suffix}</span>}
    </span>
  );
};
