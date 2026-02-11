"use client";

import React, { forwardRef, useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { User } from "lucide-react";
import Image from "next/image";

import GithubLogo from "../../assets/Images/GitHub-logo.webp";
import GoogleCalendarLogo from "../../assets/Images/GoogleCalendar-logo.webp";
import GoogleDocsLogo from "../../assets/Images/GoogleDocs-logo.webp";
import GoogleFitLogo from "../../assets/Images/GoogleFit-logo.webp";
import LeetCodeLogo from "../../assets/Images/LeetCode-logo.webp";
import StravaLogo from "../../assets/Images/Strava-logo.webp";

// Circle component - Updated to black bg, white border (border-white), and default border
const Circle = forwardRef<
  HTMLDivElement,
  { className?: string; children?: React.ReactNode }
>(({ className, children }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "z-10 flex size-12 items-center justify-center rounded-full border border-white bg-black p-2 shadow-[0_0_20px_-12px_rgba(134,156,243,0.8)]",
        className,
      )}
    >
      {children}
    </div>
  );
});

Circle.displayName = "Circle";

export function AnimatedBeamMultipleInputs({
  className,
}: {
  className?: string;
}) {
  const [isClient, setIsClient] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Refs for icons - Sorted Alphabetically
  const div1Ref = useRef<HTMLDivElement>(null); // GitHub
  const div2Ref = useRef<HTMLDivElement>(null); // Google Calendar
  const div3Ref = useRef<HTMLDivElement>(null); // Google Docs
  const div4Ref = useRef<HTMLDivElement>(null); // Google Fit
  const div5Ref = useRef<HTMLDivElement>(null); // LeetCode
  const div6Ref = useRef<HTMLDivElement>(null); // Slack
  const div7Ref = useRef<HTMLDivElement>(null); // Strava

  const div8Ref = useRef<HTMLDivElement>(null); // NUMA logo (center)
  const div9Ref = useRef<HTMLDivElement>(null); // User (bottom)

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    <div
      className={cn(
        "relative flex h-full w-full items-center justify-center",
        className,
      )}
      ref={containerRef}
    >
      {/* Animated Beams - Rendered FIRST so they are BEHIND the icons */}
      {isClient && (
        <div className="absolute inset-0 pointer-events-none z-0">
          {/* Beams from services to NUMA */}
          {[div1Ref, div2Ref, div3Ref, div4Ref, div5Ref, div6Ref, div7Ref].map(
            (ref, index) => (
              <AnimatedBeam
                key={index}
                containerRef={containerRef}
                fromRef={ref}
                toRef={div8Ref}
                gradientStartColor="#869cf3"
                gradientStopColor="#6d53ff"
                curvature={0} // Straight lines as requested in previous task
                pathColor="#ffffff"
                pathOpacity={0.1}
              />
            ),
          )}

          {/* Beam from NUMA to User */}
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div8Ref}
            toRef={div9Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
        </div>
      )}

      {/* Container for Icons - Higher Z-Index implied by order, but explicit z-10 on Circle */}
      <div className="relative flex size-full max-w-4xl items-center justify-center">
        {/* Center - NUMA Logo */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col justify-center">
          <Circle
            ref={div8Ref}
            className="size-20 bg-black/80 z-20 border-white/10"
          >
            <Icons.numa />
          </Circle>
        </div>

        {/* Bottom - User Icon */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(0px, 180px)" }}
        >
          <Circle
            ref={div9Ref}
            className="size-16 z-20 bg-black/80 border-white/10"
          >
            <User className="size-8 text-white" />
          </Circle>
        </div>

        {/* Service Icons Positioned in a Top Arc (180 deg to 0 deg) */}
        {/* Sorted Alphabetically Left to Right */}

        {/* 1. GitHub: Left (180 deg) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(-200px, 0px)" }}
        >
          <Circle ref={div1Ref} className="size-16 overflow-hidden">
            <Image
              src={GithubLogo}
              alt="GitHub"
              className="w-full h-full object-contain rounded-[500px]"
            />
          </Circle>
        </div>

        {/* 2. Google Calendar (210 deg) - (-173, -100) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(-173px, -100px)" }}
        >
          <Circle ref={div2Ref} className="size-16 overflow-hidden">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-white p-1.5">
              <Image
                src={GoogleCalendarLogo}
                alt="Google Calendar"
                className="h-full w-full object-contain"
              />
            </div>
          </Circle>
        </div>

        {/* 3. Google Docs (240 deg) - (-100, -173) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(-100px, -173px)" }}
        >
          <Circle ref={div3Ref} className="size-16 overflow-hidden">
            <Image
              src={GoogleDocsLogo}
              alt="Google Docs"
              className="w-full h-full object-contain rounded-[500px]"
            />
          </Circle>
        </div>

        {/* 4. Google Fit: Top (270 deg) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(0px, -200px)" }}
        >
          <Circle ref={div4Ref} className="size-16 overflow-hidden">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-white p-1.5">
              <Image
                src={GoogleFitLogo}
                alt="Google Fit"
                className="h-full w-full object-contain"
              />
            </div>
          </Circle>
        </div>

        {/* 5. LeetCode (300 deg) - (100, -173) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(100px, -173px)" }}
        >
          <Circle ref={div5Ref} className="size-16 overflow-hidden">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-white p-1.5">
              <Image
                src={LeetCodeLogo}
                alt="LeetCode"
                className="h-full w-full object-contain"
              />
            </div>
          </Circle>
        </div>

        {/* 6. Slack (330 deg) - (173, -100) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(173px, -100px)" }}
        >
          <Circle ref={div6Ref} className="size-16 overflow-hidden">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-white p-2">
              <Icons.slack />
            </div>
          </Circle>
        </div>

        {/* 7. Strava: Right (0/360 deg) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(200px, 0px)" }}
        >
          <Circle ref={div7Ref} className="size-16 overflow-hidden">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-white p-1.5">
              <Image
                src={StravaLogo}
                alt="Strava"
                className="h-full w-full object-contain"
              />
            </div>
          </Circle>
        </div>
      </div>
    </div>
  );
}

// Icon Components (Keeping Numa and Slack, removing others as they are replaced by images)
const Icons = {
  slack: () => (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 127 127"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="p-1" // Add padding to match the image-based icons
    >
      <path
        d="M27.2 80c0 7.3-5.9 13.2-13.2 13.2C6.7 93.2.8 87.3.8 80c0-7.3 5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V80z"
        fill="#E01E5A"
      />
      <path
        d="M47 27c-7.3 0-13.2-5.9-13.2-13.2C33.8 6.5 39.7.6 47 .6c7.3 0 13.2 5.9 13.2 13.2V27H47zm0 6.7c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H13.9C6.6 60.1.7 54.2.7 46.9c0-7.3 5.9-13.2 13.2-13.2H47z"
        fill="#36C5F0"
      />
      <path
        d="M99.9 46.9c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H99.9V46.9zm-6.6 0c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V13.8C66.9 6.5 72.8.6 80.1.6c7.3 0 13.2 5.9 13.2 13.2v33.1z"
        fill="#2EB67D"
      />
      <path
        d="M80.1 99.8c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V99.8h13.2zm0-6.6c-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33.1c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H80.1z"
        fill="#ECB22E"
      />
    </svg>
  ),
  numa: () => (
    <svg
      width="48"
      height="48"
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="50" cy="50" r="45" fill="#869cf3" opacity="0.2" />
      <text
        x="50"
        y="60"
        fontSize="32"
        fontWeight="bold"
        textAnchor="middle"
        fill="#FFFFFF"
        fontFamily="Arial, sans-serif"
      >
        NUMA
      </text>
    </svg>
  ),
};
