// DEPRECATED: This file is no longer used. Real pose images are now displayed instead of SVG stick figures.
// Safe to delete this file.
    </motion.g>
  )
}

// Corpse Pose - lying flat
function CorpsePose() {
  return (
    <motion.g
      animate={{ opacity: [1, 0.7, 1] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head */}
      <circle cx="80" cy="200" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body horizontal */}
      <line x1="98" y1="200" x2="200" y2="200" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms slightly away */}
      <line x1="120" y1="200" x2="110" y2="240" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="160" y1="200" x2="150" y2="240" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs */}
      <line x1="200" y1="200" x2="240" y2="210" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="200" y1="200" x2="240" y2="190" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Mountain Pose - standing upright
function MountainPose() {
  return (
    <g>
      {/* Head */}
      <circle cx="150" cy="70" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body */}
      <line x1="150" y1="88" x2="150" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms with slight movement */}
      <motion.g
        animate={{ rotate: [-5, 5, -5] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        style={{ transformOrigin: "150px 100px" }}
      >
        <line x1="150" y1="100" x2="115" y2="150" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
        <line x1="150" y1="100" x2="185" y2="150" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      </motion.g>
      {/* Legs */}
      <line x1="150" y1="180" x2="140" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="180" x2="160" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </g>
  )
}

// Cobra Pose - lying, upper body arched up
function CobraPose() {
  return (
    <motion.g
      animate={{ y: [-5, 5, -5] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head tilted back */}
      <circle cx="100" cy="120" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Upper body arched */}
      <path d="M 100 138 Q 130 160, 160 200 Q 190 240, 240 250" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms straight down */}
      <line x1="130" y1="170" x2="120" y2="250" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="190" x2="145" y2="250" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs on ground */}
      <line x1="240" y1="250" x2="280" y2="260" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Triangle Pose - wide legs, one arm up, one down
function TrianglePose() {
  return (
    <motion.g
      animate={{ rotate: [-2, 2, -2] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformOrigin: "150px 180px" }}
    >
      {/* Head */}
      <circle cx="100" cy="140" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body tilted */}
      <line x1="115" y1="150" x2="170" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm down to ankle */}
      <line x1="115" y1="150" x2="80" y2="250" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm up */}
      <line x1="140" y1="160" x2="180" y2="80" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Wide legs */}
      <line x1="170" y1="180" x2="80" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="170" y1="180" x2="250" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Tree Pose - one leg, arms up
function TreePose() {
  return (
    <motion.g
      animate={{ rotate: [-3, 3, -3] }}
      transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformOrigin: "150px 280px" }}
    >
      {/* Head */}
      <circle cx="150" cy="60" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body */}
      <line x1="150" y1="78" x2="150" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms raised overhead together */}
      <path d="M 150 100 Q 120 60, 145 30" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 100 Q 180 60, 155 30" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Standing leg */}
      <line x1="150" y1="180" x2="150" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Raised foot against thigh */}
      <path d="M 150 180 Q 130 200, 120 180 L 115 200" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Camel Pose - kneeling, arched backward
function CamelPose() {
  return (
    <motion.g
      animate={{ y: [-3, 3, -3] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head tilted back */}
      <circle cx="180" cy="100" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body arched backward */}
      <path d="M 170 115 Q 140 140, 150 200" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms reaching back to heels */}
      <path d="M 155 150 Q 130 180, 100 220" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 165 140 Q 200 180, 200 220" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Kneeling legs */}
      <line x1="150" y1="200" x2="100" y2="220" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="100" y1="220" x2="100" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="200" x2="200" y2="220" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="200" y1="220" x2="200" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Fish Pose - lying back, chest arched
function FishPose() {
  return (
    <motion.g
      animate={{ y: [-3, 3, -3] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head tilted back */}
      <circle cx="80" cy="150" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Chest arched up */}
      <path d="M 95 160 Q 130 120, 180 180 L 250 190" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms at sides */}
      <line x1="120" y1="150" x2="110" y2="200" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="160" y1="170" x2="155" y2="200" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs */}
      <line x1="250" y1="190" x2="280" y2="195" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Spinal Twist - seated, twisted
function SpinalTwistPose() {
  return (
    <motion.g
      animate={{ rotate: [-3, 3, -3] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformOrigin: "150px 180px" }}
    >
      {/* Head turned */}
      <circle cx="180" cy="100" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body twisted */}
      <path d="M 170 115 Q 160 140, 150 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm behind */}
      <line x1="160" y1="140" x2="200" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm across knee */}
      <line x1="155" y1="150" x2="100" y2="200" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Seated legs */}
      <path d="M 150 180 Q 120 200, 80 190 L 60 200" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 180 Q 180 220, 200 250" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Eagle Pose - standing, limbs wrapped
function EaglePose() {
  return (
    <motion.g
      animate={{ y: [-5, 5, -5] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head */}
      <circle cx="150" cy="70" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body slightly bent */}
      <line x1="150" y1="88" x2="150" y2="170" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms crossed and wrapped */}
      <path d="M 150 110 Q 120 120, 130 140 Q 140 150, 125 165" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 110 Q 180 120, 160 150 Q 145 160, 155 170" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs crossed */}
      <path d="M 150 170 Q 140 200, 145 250 L 130 280" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 190 Q 165 220, 155 260" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// One-Legged King Pigeon
function OneLeggePose() {
  return (
    <motion.g
      animate={{ rotate: [-2, 2, -2] }}
      transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformOrigin: "150px 200px" }}
    >
      {/* Head */}
      <circle cx="100" cy="100" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body leaning forward */}
      <path d="M 115 110 L 180 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms forward */}
      <line x1="130" y1="130" x2="80" y2="120" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="130" y1="130" x2="70" y2="140" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Standing leg */}
      <line x1="180" y1="180" x2="180" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Back leg extended */}
      <line x1="180" y1="180" x2="260" y2="160" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// King of Dance - Natarajasana
function KingOfDancePose() {
  return (
    <motion.g
      animate={{ y: [-3, 3, -3] }}
      transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head */}
      <circle cx="130" cy="80" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body leaning slightly */}
      <path d="M 135 95 L 150 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm extended forward */}
      <line x1="140" y1="110" x2="80" y2="90" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm holding back foot */}
      <path d="M 145 120 Q 180 100, 220 140" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Standing leg */}
      <line x1="150" y1="180" x2="145" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Kicked back leg */}
      <motion.path
        d="M 150 180 Q 200 150, 230 130"
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        animate={{ d: ["M 150 180 Q 200 150, 230 130", "M 150 180 Q 200 140, 240 120", "M 150 180 Q 200 150, 230 130"] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />
    </motion.g>
  )
}

// Wind-Relieving Pose
function WindReleasePose() {
  return (
    <motion.g
      animate={{ scale: [1, 0.98, 1] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformOrigin: "150px 180px" }}
    >
      {/* Head */}
      <circle cx="100" cy="160" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body on back */}
      <line x1="118" y1="160" x2="200" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms hugging knees */}
      <path d="M 130 165 Q 150 120, 180 140" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 140 175 Q 160 130, 185 150" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Knees drawn up */}
      <path d="M 200 180 Q 180 150, 170 130" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 200 180 Q 190 140, 175 125" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Thunderbolt Pose - kneeling seated
function ThunderboltPose() {
  return (
    <motion.g
      animate={{ y: [-2, 2, -2] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head */}
      <circle cx="150" cy="80" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body upright */}
      <line x1="150" y1="98" x2="150" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms on thighs */}
      <line x1="150" y1="140" x2="120" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="140" x2="180" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Kneeling legs */}
      <path d="M 150 180 L 120 220 L 120 280" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 180 L 180 220 L 180 280" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Forward Fold
function ForwardFoldPose() {
  return (
    <motion.g
      animate={{ y: [-3, 3, -3] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head down */}
      <circle cx="150" cy="200" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body folded */}
      <path d="M 150 182 Q 150 150, 150 100" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms hanging */}
      <line x1="150" y1="130" x2="130" y2="220" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="130" x2="170" y2="220" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs */}
      <line x1="150" y1="100" x2="130" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="100" x2="170" y2="280" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Shoulder Stand
function ShoulderStandPose() {
  return (
    <motion.g
      animate={{ x: [-2, 2, -2] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head on ground */}
      <circle cx="150" cy="260" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Neck and shoulders */}
      <line x1="150" y1="242" x2="150" y2="220" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Body vertical */}
      <line x1="150" y1="220" x2="150" y2="100" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms supporting back */}
      <path d="M 150 220 L 120 230 L 130 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 220 L 180 230 L 170 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs up */}
      <line x1="150" y1="100" x2="140" y2="50" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="100" x2="160" y2="50" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Plough Pose
function PloughPose() {
  return (
    <motion.g
      animate={{ y: [-2, 2, -2] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head on ground */}
      <circle cx="200" cy="200" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Shoulders and back curved */}
      <path d="M 185 190 Q 150 160, 140 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Legs over head */}
      <path d="M 140 180 Q 100 150, 80 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Feet touching ground behind head */}
      <line x1="80" y1="180" x2="60" y2="200" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms on ground */}
      <line x1="200" y1="210" x2="250" y2="220" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Lion Pose
function LionPose() {
  return (
    <motion.g
      animate={{ scale: [1, 1.03, 1] }}
      transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      style={{ transformOrigin: "150px 150px" }}
    >
      {/* Head with open mouth */}
      <circle cx="150" cy="80" r="20" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Open mouth */}
      <path d="M 140 90 Q 150 100, 160 90" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Tongue out */}
      <line x1="150" y1="95" x2="150" y2="105" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Body kneeling */}
      <line x1="150" y1="100" x2="150" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms on knees */}
      <line x1="150" y1="140" x2="110" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="150" y1="140" x2="190" y2="180" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Kneeling legs */}
      <path d="M 150 180 Q 130 220, 110 250" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 180 Q 170 220, 190 250" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Cow Face Pose
function CowFacePose() {
  return (
    <motion.g
      animate={{ y: [-2, 2, -2] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head */}
      <circle cx="150" cy="70" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Body seated */}
      <line x1="150" y1="88" x2="150" y2="170" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm up and behind */}
      <path d="M 150 100 Q 180 60, 160 120" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arm behind back from below */}
      <path d="M 150 140 Q 120 170, 140 130" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Crossed legs */}
      <path d="M 150 170 Q 120 190, 100 170 L 80 180" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M 150 170 Q 180 200, 200 180 L 220 190" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Wheel Pose
function WheelPose() {
  return (
    <motion.g
      animate={{ y: [-3, 3, -3] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
    >
      {/* Head hanging */}
      <circle cx="150" cy="180" r="16" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
      {/* Arched body */}
      <path d="M 80 250 Q 100 150, 150 160 Q 200 150, 220 250" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      {/* Arms straight */}
      <line x1="100" y1="180" x2="80" y2="250" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
      <line x1="200" y1="180" x2="220" y2="250" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" />
    </motion.g>
  )
}

// Map pose IDs to components
const poseComponents: Record<string, React.FC> = {
  child: ChildPose,
  corpse: CorpsePose,
  mountain: MountainPose,
  cobra: CobraPose,
  triangle: TrianglePose,
  tree: TreePose,
  camel: CamelPose,
  fish: FishPose,
  "spinal-twist": SpinalTwistPose,
  eagle: EaglePose,
  "one-legged-king": OneLeggePose,
  "lord-of-dance": KingOfDancePose,
  "wind-release": WindReleasePose,
  thunderbolt: ThunderboltPose,
  "forward-fold": ForwardFoldPose,
  "shoulder-stand": ShoulderStandPose,
  plough: PloughPose,
  lion: LionPose,
  "cow-face": CowFacePose,
  wheel: WheelPose,
}

export function PoseSVG({ poseId }: PoseSVGProps) {
  const PoseComponent = poseComponents[poseId] || MountainPose

  return (
    <div className="relative flex items-center justify-center">
      {/* Warm ambient glow behind figure */}
      <div
        className="absolute w-[250px] h-[250px] rounded-full blur-[80px]"
        style={{ backgroundColor: "rgba(232,137,12,0.06)" }}
      />

      {/* SVG figure */}
      <svg
        viewBox="0 0 300 320"
        className="w-[300px] h-[400px] relative z-10"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <PoseComponent />
      </svg>
    </div>
  )
}
