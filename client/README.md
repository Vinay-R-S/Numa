# NUMA - Client

The frontend for NUMA, built with **Next.js 16**, **React 19**, **TypeScript**, and **Tailwind CSS v4**.

## Tech Stack

- **Framework**: Next.js 16.1.1 (App Router, Turbopack)
- **Styling**: Tailwind CSS v4, tw-animate-css
- **UI Components**: shadcn/ui (Radix UI + CVA)
- **Animations**: Framer Motion, Three.js (LaserFlow background)
- **Font**: GC Epic Pro Demo (ExtraBold)

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

## Project Structure

```
src/
├── app/
│   ├── auth/page.tsx          # Sign in / sign up
│   ├── globals.css            # Global styles
│   ├── layout.tsx             # Root layout
│   └── page.tsx               # Landing page entry
├── components/
│   ├── sections/              # Landing page sections
│   │   ├── HeroSection.tsx
│   │   ├── FeaturesSection.tsx
│   │   ├── HowItWorksSection.tsx
│   │   ├── IntegrationsSection.tsx
│   │   ├── ArchitectureSection.tsx
│   │   ├── CTASection.tsx
│   │   └── Footer.tsx
│   ├── ui/                    # Reusable UI primitives
│   ├── ContentBox.tsx         # Section container
│   ├── LandingPage.tsx        # Landing page layout
│   ├── LaserFlow.tsx          # Three.js background effect
│   ├── Navbar.tsx             # Navigation bar
│   └── OrbitingIntegrations.tsx
└── lib/
    └── utils.ts               # Tailwind merge helper
```

## Scripts

| Command         | Description               |
| --------------- | ------------------------- |
| `npm run dev`   | Start dev server          |
| `npm run build` | Production build          |
| `npm run start` | Serve production build    |
| `npm run lint`  | Run ESLint                |
