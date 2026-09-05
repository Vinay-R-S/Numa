"use client";
import dynamic from "next/dynamic";
import ContentBox from "./ContentBox";
import Navbar from "./Navbar";
import localFont from "next/font/local";
import { motion, useScroll, useTransform } from "framer-motion";
import { useRef, useState, useEffect } from "react";

// LaserFlow is a 628-LOC WebGL shader that only ever renders on desktop, yet a
// static import put it in the landing chunk for every visitor, mobile included
// (NUMA-140 P6, PLAN 9). Loading it on demand means the phone never downloads
// it and the desktop parses it after the page is interactive. `ssr: false`
// because it needs a canvas and a GL context, neither of which exists on the
// server; the placeholder is null so the layout is unchanged while it loads,
// exactly as it was before the beam painted its first frame.
const LaserFlow = dynamic(
  () => import("./LaserFlow").then((mod) => mod.LaserFlow),
  { ssr: false, loading: () => null },
);

const gcEpic = localFont({
  src: "../../assets/gc-epic-pro-demo/GCEpicProDemo-ExtraBold.ttf",
});

export default function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  // Responsive: detect mobile for layout adjustments
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const text = "NUMA";

  // All chars start revealing at scroll 0 simultaneously (so A is never invisible).
  // Each char completes at a staggered end point - N first, A last.
  // Full reveal done by 15% scroll progress so ContentBox appears well after.
  const useCharReveal = (index: number) => {
    const totalRevealEnd = 0.15;
    const charStep = totalRevealEnd / text.length; // 0.0375 per char
    const start = 0; // every char starts from scroll 0
    const end = (index + 1) * charStep; // N=0.0375, U=0.075, M=0.1125, A=0.15

    // Opacity: 0.2 -> 1 (start visible so A is never invisible on load)
    const opacity = useTransform(scrollYProgress, [start, end], [0.2, 1]);

    // Blur: 10px -> 0px
    const blur = useTransform(scrollYProgress, [start, end], [10, 0]);
    const filter = useTransform(blur, (v) => `blur(${v}px)`);

    return { opacity, filter };
  };

  return (
    // overflow-x:clip clips horizontal overflow WITHOUT creating a scroll container
    // so position:sticky on children still works correctly (unlike overflow:hidden)
    <div style={{ background: "#0a0a0b", overflowX: "clip", position: "relative" }}>
      <Navbar />
      <div
        ref={containerRef}
        style={{
          height: isMobile ? "220vh" : "350vh",
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
            flexDirection: "column",
            justifyContent: "center",
            alignItems: isMobile ? "center" : "flex-start",
            paddingLeft: isMobile ? "0" : "4vw",
            gap: isMobile ? "12px" : "0",
            overflow: "hidden",
          }}
        >
          {/* Small label above on mobile */}
          {isMobile && (
            <p
              style={{
                fontSize: "11px",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "rgba(134,156,243,0.8)",
                fontFamily: "sans-serif",
                fontWeight: 600,
              }}
            >
              AI-Powered Life OS
            </p>
          )}
          <div className="relative z-10 flex gap-[1.5vw] md:gap-2 pointer-events-auto select-none">
            {text.split("").map((char, index) => {
              // eslint-disable-next-line
              const style = useCharReveal(index);
              return (
                <motion.span
                  key={index}
                  className="cursor-default relative"
                  style={{
                    fontSize: isMobile ? "22vw" : "clamp(60px, 20vw, 280px)",
                    color: "#FFFFFF",
                    ...style,
                  }}
                >
                  {char}
                </motion.span>
              );
            })}
          </div>

          {/* Tagline below on mobile */}
          {isMobile && (
            <p
              style={{
                fontSize: "14px",
                color: "rgba(156,163,175,0.85)",
                fontFamily: "sans-serif",
                fontWeight: 400,
                letterSpacing: "0.02em",
                textAlign: "center",
                maxWidth: "80vw",
                lineHeight: 1.5,
              }}
            >
              Health. Productivity. All in one place.
            </p>
          )}

          {!isMobile && (
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
          )}
        </div>
      </div>
      <ContentBox />
    </div>
  );
}
