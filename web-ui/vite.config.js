import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
                changeOrigin: true,
            },
        },
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    react: ["react", "react-dom", "react-router-dom"],
                    query: ["@tanstack/react-query"],
                    charts: ["recharts"],
                    vendor: ["axios", "zustand", "lucide-react", "clsx", "tailwind-merge"],
                },
            },
        },
    },
});
