import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // host: true binds to 0.0.0.0 so GitHub Codespaces can forward the port.
    host: true,
    port: 5173,
    // Don't try to auto-open a browser inside the headless Codespace container.
    open: false,
  },
});
