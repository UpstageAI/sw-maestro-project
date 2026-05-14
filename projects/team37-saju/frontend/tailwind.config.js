/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#7C3AED',
          light: '#A78BFA',
          dark: '#5B21B6',
        },
        cream: {
          DEFAULT: '#FAF5FF',
          dark: '#F3E8FF',
        },
        gold: {
          DEFAULT: '#F59E0B',
          light: '#FCD34D',
        },
      },
      fontFamily: {
        sans: ['Pretendard', 'Apple SD Gothic Neo', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 4px 20px rgba(124, 58, 237, 0.08)',
        card: '0 2px 12px rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
