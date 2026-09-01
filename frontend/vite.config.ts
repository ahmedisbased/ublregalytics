import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// IMPORTANT: the dev server (`npm run dev`) serves raw source files and the
// full import.meta.env object - never run it in production. For production,
// build with `npm run build` and serve the static `dist/` folder behind a
// hardened web server / reverse proxy (see nginx.conf.sample).
export default defineConfig({
  plugins: [react()],
  // server: {
  //   host: '127.0.0.1',
  //   port: 8082,
  //   allowedHosts: ['regalyticshub.ubl.com.pk'],
  // },
  server: {
  host: '127.0.0.1',
  port: 8082,
  allowedHosts: ['regalyticshub.ubl.com.pk'],
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
},
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Do NOT ship source maps to production: they expose original source code
    // and internal file paths (part of the Information Disclosure finding).
    sourcemap: false,
  },
});
