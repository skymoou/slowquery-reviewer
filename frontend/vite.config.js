import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:5172',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      }
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 3000
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser', // 使用terser进行更好的压缩
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['react-bootstrap', 'bootstrap'],
          charts: ['recharts'], // 图表库单独分包
          utils: ['axios', 'react-icons']
        },
        // 优化文件名，启用内容哈希
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    },
    // 压缩选项
    terserOptions: {
      compress: {
        drop_console: true, // 生产环境移除console
        drop_debugger: true,
        dead_code: true,
        unused: true
      },
      mangle: {
        safari10: true
      }
    },
    // 优化依赖预构建
    optimizeDeps: {
      include: [
        'react', 
        'react-dom', 
        'react-router-dom', 
        'react-bootstrap', 
        'axios',
        'recharts'
      ],
      exclude: ['@tanstack/react-table'] // 不再使用的依赖
    }
  },
  // 性能优化
  esbuild: {
    // 移除生产环境的console和debugger
    drop: ['console', 'debugger']
  }
})