/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'metric-steps': '#06b6d4',
        'metric-active': '#10b981',
        'metric-calories': '#f97316',
        'metric-distance': '#a855f7',
        'metric-sleep': '#6366f1',
      },
      boxShadow: {
        'inner-lg': 'inset 0 2px 4px 0 rgb(0 0 0 / 0.2)',
        'neumorphic': '0 20px 60px rgba(0,0,0,0.5), 0 8px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)',
        'neumorphic-hover': '0 30px 80px rgba(0,0,0,0.6), 0 12px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06)',
        'neumorphic-inset': 'inset 0 2px 8px rgba(0,0,0,0.5), inset 0 1px 3px rgba(0,0,0,0.3)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      screens: {
        '2xl': '1536px',
        '3xl': '1920px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
