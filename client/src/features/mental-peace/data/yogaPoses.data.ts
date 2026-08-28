/**
 * Yoga pose database (NUMA-120 P4, PLAN 4 "mental-peace static data moves to
 * features/mental-peace/data/").
 *
 * Keyed by pose id; `moodConfig` references these ids so a pose is described
 * once and reused across mood sequences. Images are remote Yoga Journal URLs,
 * so every renderer guards them with a name fallback (see `PoseImage`).
 */
import type { YogaPose } from "../mentalPeace.types"

export const yogaPoses: Record<string, YogaPose> = {
  // Grounding & Calming poses
  child: {
    id: "child",
    englishName: "Child's Pose",
    sanskritName: "Balasana",
    pronunciation: "bah-LAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/10/Childs-Pose_Mod-3_Andrew-Clark_2400x1350.jpeg",
    difficulty: 1,
    duration: "1-3 min",
    instructions: [
      "Kneel on the floor with toes together and knees hip-width apart.",
      "Exhale and lower your torso between your knees.",
      "Extend your arms forward, palms down, or rest them alongside your body.",
      "Rest your forehead on the mat and breathe deeply.",
      "Hold for 1-3 minutes, breathing slowly."
    ],
    benefits: "Gently stretches the hips, thighs, and ankles. Calms the brain, relieves stress and fatigue. Helps relieve back and neck pain when done with head and torso supported."
  },
  corpse: {
    id: "corpse",
    englishName: "Corpse Pose",
    sanskritName: "Savasana",
    pronunciation: "shah-VAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/05/CCD04805-scaled.jpg",
    difficulty: 1,
    duration: "5-10 min",
    instructions: [
      "Lie flat on your back with legs extended and arms at your sides.",
      "Allow your feet to fall open naturally.",
      "Close your eyes and relax every muscle in your body.",
      "Breathe naturally and let go of all tension.",
      "Remain still for 5-10 minutes."
    ],
    benefits: "Calms the brain, relaxes the body, reduces headache, fatigue, and insomnia. Helps lower blood pressure and promotes deep relaxation and restoration."
  },
  "wind-release": {
    id: "wind-release",
    englishName: "Wind-Relieving Pose",
    sanskritName: "Pavanamuktasana",
    pronunciation: "pah-vah-nah-mook-TAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2022/04/42-yoga-journal-2022-C-andrew-clark-BC8I0032_1.jpg",
    difficulty: 1,
    duration: "30-60 sec",
    instructions: [
      "Lie on your back with legs extended.",
      "Exhale and draw both knees to your chest.",
      "Clasp your hands around your shins or thighs.",
      "Keep your back flat on the floor.",
      "Hold and breathe deeply for 30-60 seconds."
    ],
    benefits: "Releases tension in the lower back, massages abdominal organs, aids digestion, and helps release trapped gases. Calms the nervous system."
  },
  thunderbolt: {
    id: "thunderbolt",
    englishName: "Thunderbolt Pose",
    sanskritName: "Vajrasana",
    pronunciation: "vahj-RAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/12/Lotus-Pose_Mod-1_Andrew-Clark_2400x1350.jpeg",
    difficulty: 1,
    duration: "1-5 min",
    instructions: [
      "Kneel on the floor with knees together.",
      "Sit back on your heels with tops of feet flat on floor.",
      "Place your hands on your thighs, palms down.",
      "Keep your spine straight and shoulders relaxed.",
      "Breathe deeply and hold for 1-5 minutes."
    ],
    benefits: "Aids digestion, calms the mind, strengthens pelvic muscles, and promotes good posture. One of the few poses that can be practiced after eating."
  },
  "forward-fold": {
    id: "forward-fold",
    englishName: "Standing Forward Fold",
    sanskritName: "Uttanasana",
    pronunciation: "oot-tan-AHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/07/Hand-to-Big-Toe-Pose_Andrew-Clark.jpg",
    difficulty: 2,
    duration: "30-60 sec",
    instructions: [
      "Stand with feet hip-width apart.",
      "Exhale and hinge forward from the hips.",
      "Let your head hang heavy and grab opposite elbows.",
      "Keep a slight bend in your knees if needed.",
      "Hold for 30-60 seconds, breathing deeply."
    ],
    benefits: "Calms the brain and helps relieve stress and mild depression. Stimulates the liver and kidneys, stretches the hamstrings and calves."
  },

  // Energizing & Uplifting poses
  mountain: {
    id: "mountain",
    englishName: "Mountain Pose",
    sanskritName: "Tadasana",
    pronunciation: "tah-DAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/10/YJ_Mountain-Pose_Mod-1_Andrew-Clark_2400x1350.png",
    difficulty: 1,
    duration: "30-60 sec",
    instructions: [
      "Stand with feet together or hip-width apart.",
      "Ground evenly through all four corners of your feet.",
      "Engage your thighs and lift your kneecaps.",
      "Lengthen your tailbone down and lift your chest.",
      "Reach arms alongside body, palms forward."
    ],
    benefits: "Improves posture, strengthens thighs, knees, and ankles. Firms abdomen and buttocks, relieves sciatica, and creates a sense of grounding and stability."
  },
  cobra: {
    id: "cobra",
    englishName: "Cobra Pose",
    sanskritName: "Bhujangasana",
    pronunciation: "boo-jahn-GAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2007/08/Cobra-Pose_Mod-1_Andrew-Clark_2400x1350.jpeg",
    difficulty: 2,
    duration: "15-30 sec",
    instructions: [
      "Lie face down with legs extended and tops of feet on the floor.",
      "Place hands under shoulders, elbows close to body.",
      "Press into hands and lift chest off the floor.",
      "Keep elbows slightly bent and shoulders away from ears.",
      "Hold for 15-30 seconds, then release."
    ],
    benefits: "Strengthens the spine, stretches chest and shoulders, firms the buttocks. Stimulates abdominal organs, helps relieve stress and fatigue, opens the heart."
  },
  camel: {
    id: "camel",
    englishName: "Camel Pose",
    sanskritName: "Ustrasana",
    pronunciation: "oosh-TRAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/10/Camel-Pose_Mod-1_Andrew-Clark_2400x1350.jpeg",
    difficulty: 3,
    duration: "30-60 sec",
    instructions: [
      "Kneel with knees hip-width apart, thighs perpendicular to floor.",
      "Place hands on lower back, fingers pointing down.",
      "Inhale, lift your chest and lean back.",
      "If comfortable, reach back for your heels.",
      "Keep neck neutral or gently drop head back."
    ],
    benefits: "Stretches the entire front body, improves posture, strengthens back muscles. Opens the chest and heart, stimulates thyroid, and increases energy."
  },
  fish: {
    id: "fish",
    englishName: "Fish Pose",
    sanskritName: "Matsyasana",
    pronunciation: "mot-see-AHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2007/08/Fish-Pose_Andrew-Clark_2400x1350.png",
    difficulty: 2,
    duration: "15-30 sec",
    instructions: [
      "Lie on your back with legs extended.",
      "Place hands under hips, palms down.",
      "Press into elbows and lift chest toward ceiling.",
      "Let head drop back gently to rest on floor.",
      "Hold for 15-30 seconds, breathing deeply."
    ],
    benefits: "Stretches the front body and throat, stimulates thyroid gland. Improves posture, opens the heart chakra, and helps relieve fatigue and mild anxiety."
  },
  "lord-of-dance": {
    id: "lord-of-dance",
    englishName: "Lord of the Dance",
    sanskritName: "Natarajasana",
    pronunciation: "not-ah-rahj-AHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2007/08/Dancer-Pose_Mod-1_Andrew-Clark_2400x1350.jpeg",
    difficulty: 4,
    duration: "30 sec each side",
    instructions: [
      "Stand in Mountain Pose, shift weight to right foot.",
      "Bend left knee, reach back with left hand to grab ankle.",
      "Extend right arm forward for balance.",
      "Kick left foot into hand while leaning torso forward.",
      "Hold for 30 seconds, then switch sides."
    ],
    benefits: "Stretches shoulders, chest, thighs, and abdomen. Strengthens legs and ankles, improves balance, and develops concentration and grace."
  },

  // Balancing & Focus poses
  triangle: {
    id: "triangle",
    englishName: "Triangle Pose",
    sanskritName: "Trikonasana",
    pronunciation: "tree-koh-NAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/11/Extended-Triangle-Pose_Mod-1_Andrew-Clark_2400x1350.jpeg",
    difficulty: 2,
    duration: "30-60 sec each side",
    instructions: [
      "Stand with feet wide apart, arms extended to sides.",
      "Turn right foot out 90 degrees, left foot slightly in.",
      "Reach right hand toward right ankle, extending left arm up.",
      "Keep both legs straight and torso in one plane.",
      "Hold for 30-60 seconds, then switch sides."
    ],
    benefits: "Stretches and strengthens thighs, knees, and ankles. Stretches hips, groins, hamstrings, and calves. Relieves stress and improves digestion."
  },
  tree: {
    id: "tree",
    englishName: "Tree Pose",
    sanskritName: "Vrksasana",
    pronunciation: "vrk-SHAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2022/01/Tree-Pose_Mod-2_2400x1350_Andrew-Clark.jpeg",
    difficulty: 2,
    duration: "30-60 sec each side",
    instructions: [
      "Stand in Mountain Pose, shift weight to left foot.",
      "Place right foot on left inner thigh or calf (avoid knee).",
      "Bring palms together at heart or extend arms overhead.",
      "Fix your gaze on a point for balance.",
      "Hold for 30-60 seconds, then switch sides."
    ],
    benefits: "Strengthens thighs, calves, ankles, and spine. Stretches groins and inner thighs, improves balance, and calms and focuses the mind."
  },
  eagle: {
    id: "eagle",
    englishName: "Eagle Pose",
    sanskritName: "Garudasana",
    pronunciation: "gah-roo-DAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/12/Eagle-Pose_Mod-1_Andrew-Clark_2400x1350.jpeg",
    difficulty: 3,
    duration: "30 sec each side",
    instructions: [
      "Stand in Mountain Pose, bend knees slightly.",
      "Cross right thigh over left, hook right foot behind left calf.",
      "Extend arms forward, cross left over right at elbows.",
      "Wrap forearms to bring palms together.",
      "Hold for 30 seconds, then switch sides."
    ],
    benefits: "Strengthens and stretches ankles and calves. Stretches thighs, hips, shoulders, and upper back. Improves concentration and sense of balance."
  },
  "one-legged-king": {
    id: "one-legged-king",
    englishName: "One-Legged King Pigeon",
    sanskritName: "Eka Pada Rajakapotasana",
    pronunciation: "ey-kah pah-dah rah-jah-kah-poh-TAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/12/pigeon-pose_andrew-clark.jpg",
    difficulty: 4,
    duration: "1-2 min each side",
    instructions: [
      "From all fours, bring right knee forward behind right wrist.",
      "Extend left leg straight back, top of foot on floor.",
      "Square hips toward the front of the mat.",
      "Walk hands forward to fold over front leg.",
      "Hold for 1-2 minutes, then switch sides."
    ],
    benefits: "Stretches thighs, groins, and psoas. Opens chest and shoulders. Releases stored tension and emotions from the hips."
  },

  // Releasing & Awakening poses
  lion: {
    id: "lion",
    englishName: "Lion Pose",
    sanskritName: "Simhasana",
    pronunciation: "sim-HAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2007/08/liz-lion-pose.jpg",
    difficulty: 1,
    duration: "30 sec",
    instructions: [
      "Kneel and sit back on your heels.",
      "Place hands on knees, spreading fingers wide.",
      "Inhale deeply through the nose.",
      "Exhale forcefully through the mouth with a 'ha' sound.",
      "Stick out tongue, roll eyes up, roar like a lion."
    ],
    benefits: "Relieves tension in the face and chest. Stimulates the throat and vocal cords. Helps release pent-up emotions and boosts confidence."
  },
  "spinal-twist": {
    id: "spinal-twist",
    englishName: "Seated Spinal Twist",
    sanskritName: "Ardha Matsyendrasana",
    pronunciation: "ARE-dah mot-see-en-DRAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2019/03/Half-Lord-of-the-Fishes_Andrew-Clark_1.jpg",
    difficulty: 2,
    duration: "30-60 sec each side",
    instructions: [
      "Sit with legs extended, bend right knee over left leg.",
      "Place right foot flat on floor outside left thigh.",
      "Twist torso to the right, left elbow outside right knee.",
      "Place right hand on floor behind you.",
      "Hold for 30-60 seconds, then switch sides."
    ],
    benefits: "Energizes the spine, stimulates digestive fire. Stretches shoulders, hips, and neck. Relieves fatigue and backache."
  },
  "cow-face": {
    id: "cow-face",
    englishName: "Cow Face Pose",
    sanskritName: "Gomukhasana",
    pronunciation: "go-moo-KAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2022/10/Cow-Face-Pose_Andrew-Clark_2400x1350.jpeg",
    difficulty: 3,
    duration: "1 min each side",
    instructions: [
      "Sit and stack right knee over left, feet beside opposite hips.",
      "Reach right arm up, bend elbow, hand reaching down back.",
      "Reach left arm behind back, hand reaching up.",
      "Clasp fingers behind back (use strap if needed).",
      "Hold for 1 minute, then switch sides."
    ],
    benefits: "Stretches ankles, hips, thighs, shoulders, armpits, and triceps. Opens the chest and helps decompress the spine."
  },
  wheel: {
    id: "wheel",
    englishName: "Wheel Pose",
    sanskritName: "Urdhva Dhanurasana",
    pronunciation: "OORD-vah don-your-AHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2007/08/Upward-Facing-Bow-Wheel-Mod-1_Andrew-Clark.jpg",
    difficulty: 4,
    duration: "15-30 sec",
    instructions: [
      "Lie on back, bend knees, feet flat hip-width apart.",
      "Place hands beside ears, fingers pointing toward shoulders.",
      "Press into hands and feet, lift hips and chest.",
      "Straighten arms, letting head hang.",
      "Hold for 15-30 seconds, then lower slowly."
    ],
    benefits: "Strengthens arms, wrists, legs, buttocks, abdomen, and spine. Stretches the chest and lungs. Stimulates thyroid and pituitary glands, increases energy."
  },
  "shoulder-stand": {
    id: "shoulder-stand",
    englishName: "Shoulder Stand",
    sanskritName: "Sarvangasana",
    pronunciation: "sar-vahn-GAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2019/06/Shoulderstand_Andrew-Clark.jpg",
    difficulty: 3,
    duration: "30-60 sec",
    instructions: [
      "Lie on back, lift legs and hips off floor.",
      "Support lower back with hands, elbows on floor.",
      "Walk hands up back toward shoulder blades.",
      "Extend legs straight up toward ceiling.",
      "Hold for 30-60 seconds, then roll down slowly."
    ],
    benefits: "Calms the brain, stimulates thyroid and prostate glands. Stretches shoulders and neck, tones legs and buttocks. Improves digestion and reduces fatigue."
  },
  plough: {
    id: "plough",
    englishName: "Plough Pose",
    sanskritName: "Halasana",
    pronunciation: "hah-LAHS-anna",
    imageUrl: "https://cdn.yogajournal.com/wp-content/uploads/2021/12/Plow-Pose_Mod-1_Andrew-Clark_2400x1350.jpg",
    difficulty: 3,
    duration: "30-60 sec",
    instructions: [
      "From Shoulder Stand, lower legs over head.",
      "Touch toes to floor behind you.",
      "Keep legs straight, arms on floor or clasp hands.",
      "Keep weight on shoulders, not neck.",
      "Hold for 30-60 seconds, then roll out slowly."
    ],
    benefits: "Calms the brain, stimulates abdominal organs and thyroid. Stretches shoulders and spine. Helps relieve symptoms of menopause and reduces stress."
  }
}
