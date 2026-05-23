import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // Auto-reload is OFF BY DEFAULT so agent edits don't nuke app state.
      // To turn live reload back on: set ENABLE_HMR=true in the environment.
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8600',
          changeOrigin: true,
          // Audio processing (effects, generate) can take minutes for large
          // files. The default proxy timeout closes the socket and the browser
          // shows "Failed to fetch". Disable both timeouts.
          timeout: 0,
          proxyTimeout: 0,
        },
      },
      hmr: process.env.ENABLE_HMR === 'true',
      watch: process.env.ENABLE_HMR === 'true' ? undefined : null,
    },
  };
});
