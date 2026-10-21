import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const assets = fileURLToPath(new URL('../assets', import.meta.url));

export default defineConfig({
  resolve: { alias: { '@assets': assets } },
  assetsInclude: ['**/*.glb'],
  server: { port: 5173, fs: { allow: ['..'] } },
});
