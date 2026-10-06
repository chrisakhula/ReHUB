import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return;
          if (id.includes("react-bootstrap")) return "bootstrap";
          if (
            id.includes("react-hook-form") ||
            id.includes("@hookform") ||
            id.includes("/zod/")
          )
            return "forms";
          if (id.includes("@tanstack")) return "query";
          if (
            id.includes("/react/") ||
            id.includes("react-dom") ||
            id.includes("react-router")
          )
            return "react";
        },
      },
    },
  },
  server: {
    proxy: {
      "/api":
        loadEnv(mode, process.cwd(), "").BACKEND_PROXY_URL ||
        "http://127.0.0.1:8000",
    },
  },
  test: { environment: "jsdom", setupFiles: ["./src/tests/setup.ts"] },
}));
