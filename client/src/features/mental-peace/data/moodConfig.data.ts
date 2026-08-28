/**
 * Mood configuration (NUMA-120 P4, PLAN 4).
 *
 * Each mood maps to a unique, non-overlapping sequence of pose ids plus the
 * copy the session screens render. Pose ids resolve against `yogaPoses`.
 */
import type { MoodConfig, MoodType } from "../mentalPeace.types"

export const moodConfig: Record<MoodType, MoodConfig> = {
  overwhelmed: {
    label: "Overwhelmed",
    color: "#7ec8c8",
    gradient: "from-[#7ec8c8] to-[#4a9494]",
    sequenceName: "Grounding Flow",
    flowSubtitle: "Release & Surrender",
    therapeuticReason: "When overwhelmed, the nervous system is in overdrive. These poses activate the parasympathetic response through forward folds and restorative positions. Child's Pose creates a cocoon of safety, while the grounding sequence helps discharge excess cortisol and brings you back to your body's natural rhythm.",
    poses: [
      { poseId: "child", moodReason: "Creates a protective cocoon, signaling safety to your nervous system" },
      { poseId: "corpse", moodReason: "Complete surrender allows the body to reset and release held tension" },
      { poseId: "wind-release", moodReason: "Releases physical tension stored in the lower back and abdomen" },
      { poseId: "thunderbolt", moodReason: "Grounds energy downward, promoting mental stillness" },
      { poseId: "forward-fold", moodReason: "Inverts perspective and calms racing thoughts" }
    ]
  },
  low: {
    label: "Low Energy",
    color: "#a78bfa",
    gradient: "from-[#a78bfa] to-[#7c5fc4]",
    sequenceName: "Heart-Opening Flow",
    flowSubtitle: "Uplift & Energize",
    therapeuticReason: "Low energy often manifests as collapsed posture and shallow breathing. These backbends and heart-openers physically expand the chest, allowing deeper breaths and stimulating the thyroid. The sequence progressively builds energy while opening channels of vitality through the spine.",
    poses: [
      { poseId: "mountain", moodReason: "Establishes dignified posture and awakens body awareness" },
      { poseId: "cobra", moodReason: "Opens the heart center and stimulates adrenal glands" },
      { poseId: "camel", moodReason: "Deep heart opener that releases emotional energy and boosts mood" },
      { poseId: "fish", moodReason: "Stimulates thyroid and opens throat chakra for self-expression" },
      { poseId: "lord-of-dance", moodReason: "Cultivates joy, grace, and dynamic life force energy" }
    ]
  },
  restless: {
    label: "Restless",
    color: "#f59e0b",
    gradient: "from-[#f59e0b] to-[#d97706]",
    sequenceName: "Focused Balance Flow",
    flowSubtitle: "Channel & Center",
    therapeuticReason: "Restless energy needs direction, not suppression. These balancing poses require such concentration that the scattered mind has no choice but to focus. The sequence channels excess energy through challenging holds while progressively deepening hip openers to release stored tension.",
    poses: [
      { poseId: "triangle", moodReason: "Creates structure and stability through geometric alignment" },
      { poseId: "tree", moodReason: "Demands singular focus, anchoring wandering attention" },
      { poseId: "eagle", moodReason: "Wrapping limbs binds scattered energy into unified focus" },
      { poseId: "lord-of-dance", moodReason: "Transforms restless energy into grace and poise" },
      { poseId: "one-legged-king", moodReason: "Deep hip release unlocks where restless energy is stored" }
    ]
  },
  numb: {
    label: "Disconnected",
    color: "#ec4899",
    gradient: "from-[#ec4899] to-[#be185d]",
    sequenceName: "Awakening Flow",
    flowSubtitle: "Feel & Connect",
    therapeuticReason: "Numbness is the body's protective response to overwhelm. These poses are intentionally intense-Lion's breath breaks through emotional walls, while deep stretches and inversions flood the body with sensation. The sequence gently but firmly invites you back into feeling.",
    poses: [
      { poseId: "lion", moodReason: "Forceful breath and expression breaks through emotional numbness" },
      { poseId: "spinal-twist", moodReason: "Wrings out stagnation and awakens the spine's energy channels" },
      { poseId: "cow-face", moodReason: "Intense shoulder and hip stretch demands present-moment awareness" },
      { poseId: "wheel", moodReason: "Full-body opener that floods system with awakening energy" },
      { poseId: "shoulder-stand", moodReason: "Inverted perspective shifts brain chemistry and perception" }
    ]
  },
  exhausted: {
    label: "Exhausted",
    color: "#06b6d4",
    gradient: "from-[#06b6d4] to-[#0891b2]",
    sequenceName: "Restorative Flow",
    flowSubtitle: "Rest & Restore",
    therapeuticReason: "Exhaustion requires restoration, not stimulation. These supported inversions and gentle poses encourage the body's natural healing response. The sequence prioritizes poses where gravity does the work, allowing depleted energy reserves to naturally replenish.",
    poses: [
      { poseId: "wind-release", moodReason: "Gentle compression soothes the nervous system without effort" },
      { poseId: "fish", moodReason: "Supported heart opener that restores without depleting" },
      { poseId: "plough", moodReason: "Calms the brain and stimulates restoration hormones" },
      { poseId: "shoulder-stand", moodReason: "Reverses blood flow to refresh tired organs and mind" },
      { poseId: "corpse", moodReason: "Final integration allows deep cellular restoration" }
    ]
  }
}
