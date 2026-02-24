#!/usr/bin/env node
/**
 * VOLO Desktop Agent v2.0 — Rock-Solid Connection
 * 
 * Runs on your laptop/desktop. Connects to the Volo server via WebSocket
 * and executes commands (terminal, file read/write, open VS Code) so you
 * can code from your phone through Volo's chat interface.
 * 
 * Connection reliability features:
 * - Native WebSocket ping/pong (RFC 6455)
 * - Application-level heartbeats as fallback
 * - Dead connection detection (no pong within timeout)
 * - Exponential backoff reconnection (1s → 30s max)
 * - Graceful close vs unexpected disconnect handling
 * - Connection state machine
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

// Connection tuning
const PING_INTERVAL = 20_000;      // Send ping every 20s
const PONG_TIMEOUT = 10_000;       // If no pong within 10s, connection is dead
const HEARTBEAT_INTERVAL = 15_000; // App-level heartbeat every 15s
const MIN_RECONNECT_DELAY = 1_000; // Start reconnect at 1s
const MAX_RECONNECT_DELAY = 30_000;// Cap at 30s
const CONNECT_TIMEOUT = 15_000;    // 15s to establish connection

if (!AGENT_KEY || AGENT_KEY === 'your-agent-key-here') {
  console.error('❌ No agent key configured.');
  console.error('   1. Open Volo on your phone');
  console.error('   2. Go to Code tab → copy your setup command');
  console.error('   3. Or paste agent key in .env as VOLO_AGENT_KEY=...');
  process.exit(1);
}

// Ensure work directory exists
if (!fs.existsSync(WORK_DIR)) {
  fs.mkdirSync(WORK_DIR, { recursive: true });
}

// ── Connection State Machine ────────────────────────────────
const State = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
};

let ws = null;
let state = State.DISCONNECTED;
let pingTimer = null;
let heartbeatTimer = null;
let pongTimer = null;
let reconnectTimer = null;
let connectTimer = null;
let reconnectAttempts = 0;
let intentionalClose = false;
let lastPongTime = Date.now();

// Multi-session: track per-session working directories
const sessions = new Map();
// File backups for Keep/Undo support
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

// ── WebSocket Connection (Rock-Solid) ───────────────────────

function connect() {
  if (state === State.CONNECTING || state === State.CONNECTED) return;
  
  state = State.CONNECTING;
  intentionalClose = false;
  const url = `${SERVER_URL}/api/remote/ws/${AGENT_KEY}`;
  
  if (reconnectAttempts === 0) {
    console.log(`\n🔌 Connecting to Volo server...`);
    console.log(`   ${url.replace(AGENT_KEY, AGENT_KEY.slice(0, 20) + '...')}`);
  } else {
    console.log(`🔄 Reconnect attempt #${reconnectAttempts}...`);
  }

  // Connection timeout — if handshake doesn't complete in time, force retry
  connectTimer = setTimeout(() => {
    if (state === State.CONNECTING) {
      console.log('⏰ Connection timeout. Retrying...');
      destroyConnection();
      scheduleReconnect();
    }
  }, CONNECT_TIMEOUT);

  try {
    ws = new WebSocket(url, {
      handshakeTimeout: CONNECT_TIMEOUT,
      // Keep TCP alive at OS level
      perMessageDeflate: false,
    });
  } catch (err) {
    console.error(`❌ Failed to create WebSocket: ${err.message}`);
    state = State.DISCONNECTED;
    scheduleReconnect();
    return;
  }

  ws.on('open', () => {
    clearTimeout(connectTimer);
    connectTimer = null;
    state = State.CONNECTED;
    reconnectAttempts = 0;
    lastPongTime = Date.now();
    
    console.log('✅ Connected to Volo server');
    console.log(`📂 Work directory: ${WORK_DIR}`);
    console.log('⏳ Waiting for commands from your phone...\n');

    // Start native WebSocket ping/pong (RFC 6455)
    startPing();
    
    // Start application-level heartbeat as backup
    startHeartbeat();
  });

  ws.on('pong', () => {
    // Server responded to our ping — connection is alive
    lastPongTime = Date.now();
    clearTimeout(pongTimer);
    pongTimer = null;
  });

  ws.on('ping', () => {
    // Server sent us a ping — respond with pong (ws lib does this automatically)
    // But update our last-known-alive timestamp
    lastPongTime = Date.now();
  });

  ws.on('message', async (data) => {
    try {
      const msg = JSON.parse(data.toString());

      if (msg.type === 'connected') {
        console.log(`🟢 ${msg.message}`);
        return;
      }

      if (msg.type === 'heartbeat_ack') {
        lastPongTime = Date.now();
        return;
      }

      // Server-sent application-level ping — respond with pong
      if (msg.type === 'ping') {
        lastPongTime = Date.now();
        safeSend({ type: 'pong', timestamp: Date.now() });
        return;
      }

      // Server-sent pong (response to our heartbeat)
      if (msg.type === 'pong') {
        lastPongTime = Date.now();
        return;
      }

      if (msg.type === 'command') {
        const { command_id, command_type, payload, session_id } = msg;
        console.log(`📨 Command: ${command_type}${session_id ? ` [session:${session_id.slice(0,8)}]` : ''}`, payload?.command?.slice?.(0, 60) || '');

        const handler = handlers[command_type];
        if (!handler) {
          safeSend({
            type: 'command_result',
            command_id,
            result: { error: `Unknown command: ${command_type}` },
          });
          return;
        }

        try {
          const result = await handler(payload, session_id);
          console.log(`✅ ${command_type} completed`);
          safeSend({
            type: 'command_result',
            command_id,
            result,
          });
        } catch (e) {
          console.error(`❌ ${command_type} failed: ${e.message}`);
          safeSend({
            type: 'command_result',
            command_id,
            result: { error: e.message },
          });
        }
      }
    } catch (e) {
      // Don't crash on parse errors — just log and continue
      console.error('⚠️  Failed to parse message:', e.message);
    }
  });

  ws.on('close', (code, reason) => {
    const reasonStr = reason ? reason.toString() : '';
    clearTimeout(connectTimer);
    connectTimer = null;
    
    if (intentionalClose) {
      console.log('👋 Connection closed (intentional)');
      state = State.DISCONNECTED;
      cleanup();
      return;
    }
    
    if (code === 4001) {
      console.log('❌ Invalid agent key. Please check your key and restart.');
      state = State.DISCONNECTED;
      cleanup();
      process.exit(1);
      return;
    }
    
    console.log(`🔌 Disconnected (code: ${code}${reasonStr ? ', reason: ' + reasonStr : ''})`);
    state = State.DISCONNECTED;
    cleanup();
    scheduleReconnect();
  });

  ws.on('error', (err) => {
    // Don't log ECONNREFUSED spam during reconnection
    if (err.code === 'ECONNREFUSED' && reconnectAttempts > 0) {
      return;
    }
    if (err.code !== 'ECONNRESET') {
      console.error(`❌ WebSocket error: ${err.message}`);
    }
  });
}

/**
 * Safely send a message, handling connection errors gracefully.
 */
function safeSend(msg) {
  try {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  } catch (e) {
    console.error('⚠️  Send failed:', e.message);
  }
}

/**
 * Native WebSocket ping/pong for reliable keep-alive.
 * If server doesn't respond with pong within PONG_TIMEOUT, connection is dead.
 */
function startPing() {
  clearInterval(pingTimer);
  pingTimer = setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    // Check if we've heard from server recently
    const silenceMs = Date.now() - lastPongTime;
    if (silenceMs > PING_INTERVAL + PONG_TIMEOUT) {
      console.log(`💀 No response from server for ${Math.round(silenceMs / 1000)}s. Reconnecting...`);
      destroyConnection();
      scheduleReconnect();
      return;
    }
    
    // Send native WS ping
    try {
      ws.ping();
    } catch (e) {
      // ping failed — connection is dead
      destroyConnection();
      scheduleReconnect();
      return;
    }
    
    // Set a timeout — if no pong comes back, connection is dead
    clearTimeout(pongTimer);
    pongTimer = setTimeout(() => {
      if (state === State.CONNECTED) {
        console.log('💀 Pong timeout — server not responding. Reconnecting...');
        destroyConnection();
        scheduleReconnect();
      }
    }, PONG_TIMEOUT);
  }, PING_INTERVAL);
}

/**
 * Application-level heartbeat as a backup to native ping/pong.
 * Some proxies/load balancers strip WS ping frames.
 */
function startHeartbeat() {
  clearInterval(heartbeatTimer);
  heartbeatTimer = setInterval(() => {
    safeSend({ type: 'heartbeat', timestamp: Date.now() });
  }, HEARTBEAT_INTERVAL);
}

/**
 * Force-destroy the WebSocket without waiting for close handshake.
 */
function destroyConnection() {
  cleanup();
  if (ws) {
    try {
      ws.removeAllListeners();
      ws.terminate(); // Hard kill, don't wait for close handshake
    } catch (e) {}
    ws = null;
  }
  state = State.DISCONNECTED;
}

function cleanup() {
  clearInterval(pingTimer);
  clearInterval(heartbeatTimer);
  clearTimeout(pongTimer);
  clearTimeout(connectTimer);
  pingTimer = null;
  heartbeatTimer = null;
  pongTimer = null;
  connectTimer = null;
}

/**
 * Exponential backoff reconnection: 1s → 2s → 4s → 8s → 16s → 30s (cap)
 */
function scheduleReconnect() {
  if (reconnectTimer) return;
  if (intentionalClose) return;
  
  state = State.RECONNECTING;
  reconnectAttempts++;
  
  const delay = Math.min(
    MIN_RECONNECT_DELAY * Math.pow(2, reconnectAttempts - 1),
    MAX_RECONNECT_DELAY
  );
  
  console.log(`   Reconnecting in ${(delay / 1000).toFixed(1)}s... (attempt #${reconnectAttempts})`);
  
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

// ── Startup ─────────────────────────────────────────────────

console.log('');
console.log('╔═══════════════════════════════════════════╗');
console.log('║      🚀 VOLO Desktop Agent v2.0          ║');
console.log('║                                           ║');
console.log('║  Code from your phone, build on your      ║');
console.log('║  machine. Rock-solid connection.           ║');
console.log('╚═══════════════════════════════════════════╝');
console.log('');

connect();

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down agent...');
  intentionalClose = true;
  cleanup();
  clearTimeout(reconnectTimer);
  if (ws) {
    ws.close(1000, 'Agent shutting down');
    // Give it a moment to close cleanly, then force exit
    setTimeout(() => process.exit(0), 500);
  } else {
    process.exit(0);
  }
});

process.on('SIGTERM', () => {
  intentionalClose = true;
  cleanup();
  clearTimeout(reconnectTimer);
  if (ws) ws.close(1000, 'Agent shutting down');
  setTimeout(() => process.exit(0), 500);
});

// Prevent crashes from unhandled errors
process.on('uncaughtException', (err) => {
  console.error('⚠️  Uncaught exception:', err.message);
  // Don't exit — try to reconnect
  if (state !== State.RECONNECTING) {
    destroyConnection();
    scheduleReconnect();
  }
});

process.on('unhandledRejection', (reason) => {
  console.error('⚠️  Unhandled rejection:', reason);
});
