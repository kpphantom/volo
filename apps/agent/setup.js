#!/usr/bin/env node
/**
 * Volo Desktop Agent — Quick Setup
 * Run: node setup.js
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise((r) => rl.question(q, r));

async function main() {
  console.log('');
  console.log('🚀 Volo Desktop Agent Setup');
  console.log('───────────────────────────');
  console.log('');

  const agentKey = await ask('Paste your Agent Key from the Volo app: ');
  if (!agentKey.trim()) {
    console.log('❌ No key provided. Exiting.');
    process.exit(1);
  }

  const serverUrl = await ask('Server URL (press Enter for ws://localhost:8000): ');
  const workDir = await ask('Work directory (press Enter for ~/Projects): ');

  const env = [
    `VOLO_AGENT_KEY=${agentKey.trim()}`,
    `VOLO_SERVER_URL=${serverUrl.trim() || 'ws://localhost:8000'}`,
    `WORK_DIR=${workDir.trim() || '~/Projects'}`,
  ].join('\n');

  fs.writeFileSync(path.join(__dirname, '.env'), env + '\n');

  console.log('');
  console.log('✅ Configuration saved to .env');
  console.log('');
  console.log('Start the agent with:');
  console.log('  npm start');
  console.log('');

  rl.close();
}

main();
