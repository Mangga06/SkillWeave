import {defineConfig,devices} from '@playwright/test';
export default defineConfig({testDir:'e2e',timeout:60000,use:{baseURL:'http://127.0.0.1:5173',...devices['Desktop Chrome'],launchOptions:{channel:'chrome'}},workers:1,reporter:'list'});
