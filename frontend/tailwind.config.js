/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}", // Цей рядок покриває всі підпапки в src
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}