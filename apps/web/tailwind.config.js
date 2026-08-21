/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          alto: "#dc2626",
          medio: "#d97706",
          baixo: "#16a34a",
        },
      },
    },
  },
  plugins: [],
};
