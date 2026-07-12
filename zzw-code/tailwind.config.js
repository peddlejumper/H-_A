/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'zzw-bg': '#0A0E17',
        'zzw-surface': '#111827',
        'zzw-surface2': '#1A2235',
        'zzw-border': '#1E293B',
        'zzw-cyan': '#00E5FF',
        'zzw-cyan-dim': '#00B8D4',
        'zzw-purple': '#7C3AED',
        'zzw-text': '#E2E8F0',
        'zzw-text-dim': '#8899AA',
        'zzw-green': '#10B981',
        'zzw-red': '#EF4444',
        'zzw-yellow': '#F59E0B',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}