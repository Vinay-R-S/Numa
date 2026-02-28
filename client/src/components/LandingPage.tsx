"use client";
import { LaserFlow } from "./LaserFlow";
import ContentBox from "./ContentBox";
import Navbar from "./Navbar";
import localFont from "next/font/local";
import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

const gcEpic = localFont({
  src: "../../assets/gc-epic-pro-demo/GCEpicProDemo-ExtraBold.ttf",
});

export default function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  const text = "NUMA";

  // Helper to create staggered transforms based on scroll PROGRESS (0 to 1)
  const useCharReveal = (index: number) => {
    // Container = 350vh → scroll distance = 250vh.
    // All 4 chars complete in first 12% = 30vh of scrolling → very fast reveal.
    // ContentBox appears at ~(250-15)/250 = 94% → massive "all bright" buffer.
    const revealEnd = 0.12;
    const charStep = revealEnd / text.length; // 0.03 per char
    const start = index * charStep;
    const end = start + charStep;

    // Opacity: 0.05 -> 1
    const opacity = useTransform(scrollYProgress, [start, end], [0.05, 1]);

    // Blur: 14px -> 0px
    const blur = useTransform(scrollYProgress, [start, end], [14, 0]);
    const filter = useTransform(blur, (v) => `blur(${v}px)`);

    return { opacity, filter };
  };

  return (
    // Outer container - 300vh vertical space.
    // REMOVED 'overflowX: hidden' to fix 'position: sticky'
    <div style={{ background: "#0a0a0b" }}>
      <Navbar />
      <div
        ref={containerRef}
        style={{
          height: "350vh",
          background: "#0a0a0b",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* Sticky container - stays pinned at top */}
        <div
          className={`${gcEpic.className}`}
          style={{
            position: "sticky",
            top: 0,
            width: "100%",
            height: "100vh",
            background: "#0a0a0b",
            display: "flex",
            justifyContent: "flex-start",
            alignItems: "center",
            paddingLeft: "4vw",
            overflow: "hidden", // Internal overflow hidden is okay
          }}
        >
          <div className="relative z-10 flex gap-2 pointer-events-auto select-none">
            {text.split("").map((char, index) => {
              // eslint-disable-next-line
              const style = useCharReveal(index);
              return (
                <motion.span
                  key={index}
                  className="cursor-default relative"
                  style={{
                    fontSize: "20vw",
                    color: "#FFFFFF",
                    ...style,
                  }}
                >
                  {char}
                </motion.span>
              );
            })}
          </div>

          <div
            className="absolute inset-0 pointer-events-none"
            style={{ zIndex: 20 }}
          >
            <LaserFlow
              color="#869cf3"
              wispDensity={2}
              flowSpeed={0.5}
              verticalSizing={5}
              horizontalSizing={3}
              fogIntensity={0.15}
              fogScale={0.3}
              wispSpeed={15}
              wispIntensity={8}
              flowStrength={0}
              decay={1.7}
              horizontalBeamOffset={0.35}
              verticalBeamOffset={-0.5}
            />
          </div>
        </div>
      </div>
      <ContentBox />
    </div>
  );
}
