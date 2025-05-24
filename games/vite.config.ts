import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ }) => {
    return {
      plugins: [react()],
      base: '/Opossum/opossum-xenzia/',
      server: {
        port: 3001,
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});