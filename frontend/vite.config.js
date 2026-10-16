import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served behind the nginx gateway, so allow proxied Host headers and
// expose on 0.0.0.0 inside the container.
//
// The `proxy` block only matters when hitting the Vite dev server DIRECTLY
// (standalone local dev / preview). In Docker the browser talks to the nginx
// gateway same-origin, so these rules are never exercised there.
const API_TARGET = process.env.VITE_PROXY_TARGET || "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: true,
    strictPort: true,
    proxy: {
      "/auth": API_TARGET,
      "/booking": API_TARGET,
      "/analytics": API_TARGET,
      "/calendar": API_TARGET,
    },
  },
});
