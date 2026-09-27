/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0F19',
        surface: '#1A233A',
        surfaceHighlight: '#2A344F',
        textMain: '#E2E8F0',
        textMuted: '#94A3B8',
        tier: {
          green: '#2E7D32',
          yellow: '#F9A825',
          orange: '#EF6C00',
          red: '#C62828',
        },
        model: {
          gfs: '#1f77b4',
          ecmwf: '#ff7f0e',
          graphcast: '#2ca02c',
          pangu: '#d62728',
        }
      }
    },
  },
  plugins: [],
}
