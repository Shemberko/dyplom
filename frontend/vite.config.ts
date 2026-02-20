import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import tailwindcss from '@tailwindcss/postcss' // Оновлений імпорт
import autoprefixer from 'autoprefixer'

export default defineConfig({
  plugins: [vue()],
  css: {
    postcss: {
      plugins: [
        tailwindcss(), // Використовуємо новий плагін
        autoprefixer(),
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@entry': path.resolve(__dirname, './src/entrypoints')
    }
  }
})