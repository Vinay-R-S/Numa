"use client"

import { useBreathingGuide } from "../useBreathingGuide"

interface BreathingGuideProps {
  isActive?: boolean
}

const ORB_ANIMATION = {
  inhale: "breathe-inhale",
  hold: "breathe-hold",
  exhale: "breathe-exhale",
} as const

export function BreathingGuide({ isActive = true }: BreathingGuideProps) {
  const { phase, phaseIndex, label } = useBreathingGuide(isActive)

  return (
    <div className="flex flex-col items-center">
      <style jsx>{`
        @keyframes breathe-inhale {
          0% { transform: scale(0.7); opacity: 0.5; }
          100% { transform: scale(1); opacity: 0.8; }
        }
        @keyframes breathe-hold {
          0%, 100% { transform: scale(1); opacity: 0.8; }
        }
        @keyframes breathe-exhale {
          0% { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(0.7); opacity: 0.5; }
        }
        .breathe-inhale {
          animation: breathe-inhale 4s ease-in-out forwards;
        }
        .breathe-hold {
          animation: breathe-hold 2s ease-in-out forwards;
        }
        .breathe-exhale {
          animation: breathe-exhale 4s ease-in-out forwards;
        }
      `}</style>

      <div className="relative mb-4 flex items-center justify-center" style={{ width: 120, height: 120 }}>
        <div
          key={`${phase}-${phaseIndex}`}
          className={`rounded-full bg-primary ${ORB_ANIMATION[phase]}`}
          style={{ width: 80, height: 80 }}
        />
      </div>

      <p className="text-sm sm:text-base text-primary italic">
        {label}
      </p>
    </div>
  )
}
