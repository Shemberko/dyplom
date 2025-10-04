import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
    build: {
        rollupOptions: {
            input: {
                background: resolve(__dirname, 'src/background.js'),
                content: resolve(__dirname, 'src/content.js'),
                click_detector: resolve(__dirname, 'src/services/click_detector.js'),
                page_analyzer: resolve(__dirname, 'src/services/page_analyzer.js'),
            },
            output: {
                entryFileNames: (chunk) => {
                    if (chunk.name === 'background') return 'background.js'
                    if (chunk.name === 'content') return 'content.js'
                    if (chunk.name === 'click_detector') return 'services/click_detector.js'
                    if (chunk.name === 'page_analyzer') return 'services/page_analyzer.js'
                    return '[name]/[name].js'
                }
            }
        },
        outDir: 'dist',
        emptyOutDir: true
    },
    publicDir: 'public'
})

