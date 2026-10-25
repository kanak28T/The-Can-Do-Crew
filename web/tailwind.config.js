/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        page: '#0F1720',
        surface: '#151F2B',
        raised: '#1B2735',
        border: '#2A3849',
        accent: '#6CA6E0',
        'text-primary': '#E6EDF3',
        'text-secondary': '#9FB0C0',
        muted: '#7F90A3',
        low: '#5FA8A0',
        watch: '#E3B341',
        high: '#E8704F',
        unknown: '#8A97A6',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
