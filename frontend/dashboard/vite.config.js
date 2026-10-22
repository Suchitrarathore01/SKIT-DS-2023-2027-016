import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend during development.
    // This avoids CORS issues when running frontend on :5173 and
    // backend on :8000 simultaneously.
    proxy: {
      "/scan": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
