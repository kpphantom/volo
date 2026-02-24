#!/usr/bin/env node
/**
 * VOLO Desktop Agent
 * 
 * Runs on your laptop/desktop. Connects to the Volo server via WebSocket
 * and executes commands (terminal, file read/write, open VS Code) so you
 * can code from your phone through Volo's chat interface.
 * 
 * Usage:
 *   1. Copy .env.example to .env
 *   2. Paste your agent key from the Volo app
 *   3. npm install && npm start
 */

require('dotenv').config();
const WebSocket = require('ws');
const { exec, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ── Config ──────────────────────────────────────────────────
const AGENT_KEY = process.env.VOLO_AGENT_KEY;
const SERVER_URL = process.env.VOLO_SERVER_URL || 'ws://localhost:8000';
const WORK_DIR = (process.env.WORK_DIR || '~/Projects').replace('~', os.homedir());
const HEARTBEAT_INTERVAL = 10_000; // 10s
const RECONNECT_DELAY = 5_000; // 5s

if (!AGENT_KEY || AGENT_KEY === 'your-agent-key-here') {
  console.error('❌ No agent key configured.');
  console.error('   1. Open Volo on your phone');
  console.error('   2. Go to VS Code page → copy your agent key');
  console.error('   3. Paste it in .env as VOLO_AGENT_KEY=...');
  process.exit(1);
}

// Ensure work directory exists
if (!fs.existsSync(WORK_DIR)) {
  fs.mkdirSync(WORK_DIR, { recursive: true });
}

let ws = null;
let heartbeatTimer = null;
let reconnectTimer = null;

// Multi-session: track per-session working directories
// session_id -> { repo, workDir }
const sessions = new Map();
// File backups for Keep/Undo support (backup_id -> backup info)
const fileBackups = new Map();
let defaultWorkDir = WORK_DIR;

/**
 * Get the working directory for a command, scoped to its session.
 */
function getWorkDir(sessionId) {
  if (sessionId && sessions.has(sessionId)) {
    return sessions.get(sessionId).workDir;
  }
  return defaultWorkDir;
}

// ── Command Handlers ────────────────────────────────────────

const handlers = {
  /**
   * Run a shell command in the session's working directory.
   */
  async run_command({ command, cwd }, sessionId) {
    const workDir = cwd || getWorkDir(sessionId);
    return new Promise((resolve) => {
      const child = exec(command, {
        cwd: workDir,
        timeout: 120_000, // 2 min max
        maxBuffer: 1024 * 1024 * 5, // 5MB
        env: { ...process.env, FORCE_COLOR: '0' },
      }, (error, stdout, stderr) => {
        resolve({
          stdout: stdout?.slice(-10000) || '', // Last 10KB
          stderr: stderr?.slice(-5000) || '',
          exit_code: error ? error.code || 1 : 0,
          cwd: workDir,
        });
      });
    });
  },

  /**
   * Read a file's contents.
   */
  async read_file({ file_path, start_line, end_line }, sessionId) {
    try {
      const fullPath = path.resolve(getWorkDir(sessionId), file_path);
      
      // Security: don't allow reading outside work dir
      if (!fullPath.startsWith(path.resolve(WORK_DIR))) {
        return { error: 'Access denied: path outside work directory' };
      }

      const content = fs.readFileSync(fullPath, 'utf-8');
      
      if (start_line || end_line) {
        const lines = content.split('\n');
        const start = (start_line || 1) - 1;
        const end = end_line || lines.length;
        return {
          content: lines.slice(start, end).join('\n'),
          total_lines: lines.length,
          file_path: fullPath,
        };
      }

      return { content, total_lines: content.split('\n').length, file_path: fullPath };
    } catch (e) {
      return { error: e.message };
    }
  },

  /**
   * Write content to a file (create or overwrite).
   * Backs up the original for Keep/Undo support.
   */
  async write_file({ file_path, content }, sessionId) {
    try {
      const fullPath = path.resolve(getWorkDir(sessionId), file_path);
      
      if (!fullPath.startsWith(path.resolve(WORK_DIR))) {
        return { error: 'Access denied: path outside work directory' };
      }

      // Backup original if it exists (for undo support)
      let had_original = false;
      let original_content = null;
      let lines_added = content.split('\n').length;
      let lines_removed = 0;

      if (fs.existsSync(fullPath)) {
        had_original = true;
        original_content = fs.readFileSync(fullPath, 'utf-8');
        // Compute simple diff stats
        const oldLines = original_content.split('\n');
        const newLines = content.split('\n');
        const maxLen = Math.max(oldLines.length, newLines.length);
        lines_added = 0;
        lines_removed = 0;
        for (let i = 0; i < maxLen; i++) {
          if (i >= oldLines.length) lines_added++;
          else if (i >= newLines.length) lines_removed++;
          else if (oldLines[i] !== newLines[i]) { lines_added++; lines_removed++; }
        }
        if (lines_added === 0 && lines_removed === 0) lines_added = 1;
      }

      // Ensure directory exists
      const dir = path.dirname(fullPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      // Write new content
      fs.writeFileSync(fullPath, content, 'utf-8');

      // Store backup for undo
      const crypto = require('crypto');
      const backupId = crypto.randomBytes(8).toString('hex');
      fileBackups.set(backupId, {
        original_path: fullPath,
        had_original,
        original_content,
        timestamp: Date.now(),
      });

      // Clean old backups (keep last 50)
      if (fileBackups.size > 50) {
        const oldest = fileBackups.keys().next().value;
        fileBackups.delete(oldest);
      }

      return {
        success: true,
        file_path: fullPath,
        bytes: Buffer.byteLength(content),
        backup_id: backupId,
        had_original,
        lines_added,
        lines_removed,
      };
    } catch (e) {
      return { error: e.message };
    }
  },

  /**
   * List directory contents.
   */
  async list_dir({ dir_path }, sessionId) {
    try {
      const fullPath = path.resolve(getWorkDir(sessionId), dir_path || '.');
      
      if (!fullPath.startsWith(path.resolve(WORK_DIR))) {
        return { error: 'Access denied: path outside work directory' };
      }

      const entries = fs.readdirSync(fullPath, { withFileTypes: true });
      return {
        path: fullPath,
        entries: entries.map(e => ({
          name: e.name,
          type: e.isDirectory() ? 'directory' : 'file',
          size: e.isFile() ? fs.statSync(path.join(fullPath, e.name)).size : null,
        })).slice(0, 200), // Cap at 200 entries
      };
    } catch (e) {
      return { error: e.message };
    }
  },

  /**
   * Undo a file write by restoring from backup.
   */
  async undo_write({ backup_id }) {
    try {
      const backup = fileBackups.get(backup_id);
      if (!backup) {
        return { error: 'Backup not found or expired' };
      }

      if (backup.had_original) {
        fs.writeFileSync(backup.original_path, backup.original_content, 'utf-8');
      } else {
        // File didn't exist before — delete it
        if (fs.existsSync(backup.original_path)) {
          fs.unlinkSync(backup.original_path);
        }
      }

      fileBackups.delete(backup_id);
      console.log(`↩️  Undo: restored ${backup.original_path}`);
      return { success: true, restored: backup.original_path, had_original: backup.had_original };
    } catch (e) {
      return { error: e.message };
    }
  },

  /**
   * Open a repo in VS Code and register it as a session.
   * Multiple repos can be open simultaneously.
   */
  async open_repo({ repo, clone_url, session_id }) {
    const repoName = repo.split('/').pop();
    const repoPath = path.join(WORK_DIR, repoName);

    // Clone if not exists
    if (!fs.existsSync(repoPath)) {
      console.log(`📥 Cloning ${repo}...`);
      await new Promise((resolve) => {
        exec(`git clone ${clone_url} "${repoPath}"`, { timeout: 120_000 }, (error, stdout, stderr) => {
          if (error) {
            console.error(`   Clone error: ${error.message}`);
          }
          resolve();
        });
      });
    } else {
      // Pull latest
      console.log(`🔄 Pulling latest for ${repo}...`);
      await new Promise((resolve) => {
        exec('git pull', { cwd: repoPath, timeout: 30_000 }, () => resolve());
      });
    }

    // Register this session's working directory
    if (session_id) {
      sessions.set(session_id, { repo, workDir: repoPath });
      console.log(`📂 Session ${session_id.slice(0, 8)}... → ${repoName}`);
    }

    // Open in VS Code (each repo gets its own window)
    console.log(`💻 Opening ${repoName} in VS Code...`);
    exec(`code "${repoPath}"`);

    return {
      success: true,
      repo,
      path: repoPath,
      session_id,
      active_sessions: sessions.size,
      message: `Opened ${repoName} in VS Code`,
    };
  },

  /**
   * Close a session (remove its working directory mapping).
   */
  async close_session({ session_id }) {
    if (session_id && sessions.has(session_id)) {
      const info = sessions.get(session_id);
      sessions.delete(session_id);
      console.log(`🔒 Closed session ${session_id.slice(0, 8)}... (${info.repo})`);
      return { success: true, closed: session_id, remaining: sessions.size };
    }
    return { success: false, error: 'Session not found' };
  },

  /**
   * Open VS Code to a specific file.
   */
  async open_vscode({ file_path, line }, sessionId) {
    const fullPath = path.resolve(getWorkDir(sessionId), file_path);
    const target = line ? `${fullPath}:${line}` : fullPath;
    exec(`code -g "${target}"`);
    return { success: true, opened: target };
  },
};

// ── WebSocket Connection ────────────────────────────────────

function connect() {
  const url = `${SERVER_URL}/api/remote/ws/${AGENT_KEY}`;
  console.log(`\n🔌 Connecting to Volo server...`);
  console.log(`   ${url.replace(AGENT_KEY, AGENT_KEY.slice(0, 20) + '...')}`);

  ws = new WebSocket(url);

  ws.on('open', () => {
    console.log('✅ Connected to Volo server');
    console.log(`📂 Work directory: ${WORK_DIR}`);
    console.log('⏳ Waiting for commands from your phone...\n');

    // Start heartbeat
    heartbeatTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
      }
    }, HEARTBEAT_INTERVAL);
  });

  ws.on('message', async (data) => {
    try {
      const msg = JSON.parse(data.toString());

      if (msg.type === 'connected') {
        console.log(`🟢 ${msg.message}`);
        return;
      }

      if (msg.type === 'heartbeat_ack') return;

      if (msg.type === 'command') {
        const { command_id, command_type, payload, session_id } = msg;
        console.log(`📨 Command: ${command_type}${session_id ? ` [session:${session_id.slice(0,8)}]` : ''}`, payload?.command?.slice?.(0, 60) || '');

        const handler = handlers[command_type];
        if (!handler) {
          ws.send(JSON.stringify({
            type: 'command_result',
            command_id,
            result: { error: `Unknown command: ${command_type}` },
          }));
          return;
        }

        try {
          const result = await handler(payload, session_id);
          console.log(`✅ ${command_type} completed`);
          ws.send(JSON.stringify({
            type: 'command_result',
            command_id,
            result,
          }));
        } catch (e) {
          console.error(`❌ ${command_type} failed: ${e.message}`);
          ws.send(JSON.stringify({
            type: 'command_result',
            command_id,
            result: { error: e.message },
          }));
        }
      }
    } catch (e) {
      console.error('Failed to parse message:', e.message);
    }
  });

  ws.on('close', (code, reason) => {
    console.log(`\n🔌 Disconnected (code: ${code})`);
    cleanup();
    scheduleReconnect();
  });

  ws.on('error', (err) => {
    console.error(`❌ WebSocket error: ${err.message}`);
  });
}

function cleanup() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  console.log(`   Reconnecting in ${RECONNECT_DELAY / 1000}s...`);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_DELAY);
}

// ── Startup ─────────────────────────────────────────────────

console.log('');
console.log('╔═══════════════════════════════════════════╗');
console.log('║      🚀 VOLO Desktop Agent v1.0          ║');
console.log('║                                           ║');
console.log('║  Code from your phone, build on your      ║');
console.log('║  machine. VS Code + Claude, mobile.       ║');
console.log('╚═══════════════════════════════════════════╝');
console.log('');

connect();

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down agent...');
  cleanup();
  if (ws) ws.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  cleanup();
  if (ws) ws.close();
  process.exit(0);
});
