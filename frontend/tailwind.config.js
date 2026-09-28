/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#FAFAF7',
        surface: '#FFFFFF',
        surfaceHighlight: '#F4F1E8',
        surfaceHover: '#EDE9DD',
        border: '#E2DFD5',
        borderLight: '#EDEBE4',
        textMain: '#1A1A1A',
        textSecondary: '#3D3D3D',
        textMuted: '#536273',
        textLight: '#8A9AAE',
        brand: {
          forest: '#174A35',
          forestLight: '#1E5A42',
          leaf: '#4F7D5C',
          leafLight: '#6B9B78',
          leafPale: '#E8F0EB',
          sand: '#F4F1E8',
          navy: '#14253D',
          slate: '#536273',
          rain: '#2878B5',
          rainLight: '#3B8BC8',
          rainPale: '#EBF4FA',
        },
        tier: {
          green: '#2E7D32',
          greenBg: '#E8F5E9',
          yellow: '#F9A825',
          yellowBg: '#FFF8E1',
          orange: '#EF6C00',
          orangeBg: '#FFF3E0',
          red: '#C62828',
          redBg: '#FFEBEE',
        },
        model: {
          blend: '#174A35',
          hres: '#2878B5',
          ens: '#7B61FF',
          graphcast: '#EF6C00',
          baseline: '#536273',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      borderRadius: {
        'card': '10px',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'cardHover': '0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)',
        'panel': '0 2px 8px rgba(0,0,0,0.06)',
        'header': '0 1px 4px rgba(0,0,0,0.08)',
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'progress': 'progress 4s ease-in-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        progress: {
          '0%': { width: '0%' },
          '100%': { width: '100%' },
        },
      },
    },
  },
  plugins: [],
}
