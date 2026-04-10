/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        surface: {
          DEFAULT: '#1e293b',
          light:   '#334155',
          dark:    '#0f172a',
        },
        gps: {
          idle:     '#6b7280',
          ready:    '#22c55e',
          tracking: '#22c55e',
          error:    '#ef4444',
        },
      },
      animation: {
        'pulse-gps': 'pulse-gps 1.5s ease-in-out infinite',
        'shimmer':   'shimmer 1.5s ease-in-out infinite',
        'fade-in':   'fade-in 0.3s ease-out',
        'scale-in':  'scale-in 0.2s ease-out',
      },
    },
  },
  plugins: [],
}