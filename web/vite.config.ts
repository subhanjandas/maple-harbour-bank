import {defineConfig} from 'vite';
export default defineConfig({base:process.env.VITE_BASE_PATH||'/',server:{port:5173,proxy:{'/api':'http://127.0.0.1:8000'}},build:{outDir:'dist'}});
