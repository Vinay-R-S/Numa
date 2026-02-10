"use client";

import React, { forwardRef, useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { User } from "lucide-react";

// Circle component - moved z-index to className to be overridable, default is high
const Circle = forwardRef<
  HTMLDivElement,
  { className?: string; children?: React.ReactNode }
>(({ className, children }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "z-10 flex size-12 items-center justify-center rounded-full border-2 border-white/20 bg-black/40 backdrop-blur-sm p-3 shadow-[0_0_20px_-12px_rgba(134,156,243,0.8)]",
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

  // Refs for icons
  const div1Ref = useRef<HTMLDivElement>(null);
  const div2Ref = useRef<HTMLDivElement>(null);
  const div3Ref = useRef<HTMLDivElement>(null);
  const div4Ref = useRef<HTMLDivElement>(null);
  const div5Ref = useRef<HTMLDivElement>(null);
  const div6Ref = useRef<HTMLDivElement>(null);
  const div7Ref = useRef<HTMLDivElement>(null);

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
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div1Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div2Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div3Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div4Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div5Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div6Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />
          <AnimatedBeam
            containerRef={containerRef}
            fromRef={div7Ref}
            toRef={div8Ref}
            gradientStartColor="#869cf3"
            gradientStopColor="#6d53ff"
            curvature={0}
            pathColor="#ffffff"
            pathOpacity={0.1}
          />

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
          <Circle ref={div8Ref} className="size-20 bg-black/80 z-20">
            <Icons.numa />
          </Circle>
        </div>

        {/* Bottom - User Icon */}
        {/* Moved slightly lower to give space */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(0px, 180px)" }}
        >
          <Circle ref={div9Ref} className="size-16 z-20">
            <User className="size-8 text-white" />
          </Circle>
        </div>

        {/* Service Icons Positioned in a Top Arc (180 deg to 0 deg) */}
        {/* Radius: 200px (Close to NUMA) */}

        {/* Icon 1: Left (180 deg) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(-200px, 0px)" }}
        >
          <Circle ref={div1Ref} className="size-16">
            <Icons.slack />
          </Circle>
        </div>

        {/* Icon 2 (210 deg) - approx (-173, -100) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(-173px, -100px)" }}
        >
          <Circle ref={div2Ref} className="size-16">
            <Icons.strava />
          </Circle>
        </div>

        {/* Icon 3 (240 deg) - approx (-100, -173) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(-100px, -173px)" }}
        >
          <Circle ref={div3Ref} className="size-16">
            <Icons.googleFit />
          </Circle>
        </div>

        {/* Icon 4: Top (270 deg) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(0px, -200px)" }}
        >
          <Circle ref={div4Ref} className="size-16">
            <Icons.googleCalendar />
          </Circle>
        </div>

        {/* Icon 5 (300 deg) - approx (100, -173) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(100px, -173px)" }}
        >
          <Circle ref={div5Ref} className="size-16">
            <Icons.leetcode />
          </Circle>
        </div>

        {/* Icon 6 (330 deg) - approx (173, -100) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(173px, -100px)" }}
        >
          <Circle ref={div6Ref} className="size-16">
            <Icons.github />
          </Circle>
        </div>

        {/* Icon 7: Right (0/360 deg) */}
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ transform: "translate(200px, 0px)" }}
        >
          <Circle ref={div7Ref} className="size-16">
            <Icons.googleDocs />
          </Circle>
        </div>
      </div>
    </div>
  );
}

// Icon Components (Unchanged)
const Icons = {
  slack: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 127 127"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
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
  strava: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"
        fill="#FC4C02"
      />
    </svg>
  ),
  googleFit: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M24 4C12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20S35.05 4 24 4zm-4 30c-3.31 0-6-2.69-6-6V20c0-3.31 2.69-6 6-6h8c3.31 0 6 2.69 6 6v8c0 3.31-2.69 6-6 6h-8z"
        fill="#4285F4"
      />
      <circle cx="20" cy="24" r="4" fill="#FBBC04" />
      <circle cx="28" cy="24" r="4" fill="#34A853" />
    </svg>
  ),
  googleCalendar: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M38 6H34V4H30V6H18V4H14V6H10C7.79 6 6 7.79 6 10V38C6 40.21 7.79 42 10 42H38C40.21 42 42 40.21 42 38V10C42 7.79 40.21 6 38 6Z"
        fill="#1976D2"
      />
      <path
        d="M6 16H42V38C42 40.21 40.21 42 38 42H10C7.79 42 6 40.21 6 38V16Z"
        fill="#FFFFFF"
      />
      <text
        x="24"
        y="32"
        fontSize="16"
        fontWeight="bold"
        textAnchor="middle"
        fill="#1976D2"
      >
        31
      </text>
    </svg>
  ),
  leetcode: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M13.483 0a1.374 1.374 0 0 0-.961.438L7.116 6.226l-3.854 4.126a5.266 5.266 0 0 0-1.209 2.104 5.35 5.35 0 0 0-.125.513 5.527 5.527 0 0 0 .062 2.362 5.83 5.83 0 0 0 .349 1.017 5.938 5.938 0 0 0 1.271 1.818l4.277 4.193.039.038c2.248 2.165 5.852 2.133 8.063-.074l2.396-2.392c.54-.54.54-1.414.003-1.955a1.378 1.378 0 0 0-1.951-.003l-2.396 2.392a3.021 3.021 0 0 1-4.205.038l-.02-.019-4.276-4.193c-.652-.64-.972-1.469-.948-2.263a2.68 2.68 0 0 1 .066-.523 2.545 2.545 0 0 1 .619-1.164L9.13 8.114c1.058-1.134 3.204-1.27 4.43-.278l3.501 2.831c.593.48 1.461.387 1.94-.207a1.384 1.384 0 0 0-.207-1.943l-3.5-2.831c-.8-.647-1.766-1.045-2.774-1.202l2.015-2.158A1.384 1.384 0 0 0 13.483 0zm-2.866 12.815a1.38 1.38 0 0 0-1.38 1.382 1.38 1.38 0 0 0 1.38 1.382H20.79a1.38 1.38 0 0 0 1.38-1.382 1.38 1.38 0 0 0-1.38-1.382z"
        fill="#FFA116"
      />
    </svg>
  ),
  github: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"
        fill="#FFFFFF"
      />
    </svg>
  ),
  googleDocs: () => (
    <svg
      width="24"
      height="24"
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M30 4H14C11.79 4 10 5.79 10 8V40C10 42.21 11.79 44 14 44H34C36.21 44 38 42.21 38 40V12L30 4Z"
        fill="#4285F4"
      />
      <path d="M30 4V12H38L30 4Z" fill="#A1C2FA" />
      <path
        d="M16 22H32V24H16V22ZM16 26H32V28H16V26ZM16 30H26V32H16V30Z"
        fill="#FFFFFF"
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
