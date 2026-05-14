import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * The recommendation pipeline now lives in Python (`api/recommend.py`,
 * `api/recommend/stream.py`) and runs as a Vercel Function. For local
 * development that needs the API, use `vercel dev` instead of `vite` —
 * it boots both the Vite frontend and the Python functions together.
 */
export default defineConfig({
  plugins: [react()],
});
