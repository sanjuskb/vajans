import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    strictPort: false,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react":    ["react", "react-dom"],
          "vendor-router":   ["react-router-dom"],
          "vendor-query":    ["@tanstack/react-query"],
          "vendor-charts":   ["recharts"],
          "vendor-motion":   ["framer-motion"],
          "vendor-ui":       ["lucide-react", "react-hot-toast", "clsx"],
        },
      },
    },
  },
});
