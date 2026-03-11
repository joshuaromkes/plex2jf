/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme - primary colors
        'bg-primary': '#1a1a1a',
        'bg-secondary': '#252525',
        'bg-tertiary': '#2d2d2d',
        // Text colors
        'text-primary': '#e5e5e5',
        'text-secondary': '#a0a0a0',
        'text-muted': '#6b6b6b',
        // Status colors
        'success': '#4ade80',
        'warning': '#fbbf24',
        'error': '#f87171',
        'info': '#60a5fa',
        // Accent colors
        'accent-primary': '#3b82f6',
        'accent-hover': '#2563eb',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}