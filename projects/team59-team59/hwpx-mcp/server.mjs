import { createServer } from 'http';
import { spawn } from 'child_process';
import { createInterface } from 'readline';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const PORT = 3001;
const __dirname = dirname(fileURLToPath(import.meta.url));
const MCP_SCRIPT = join(__dirname, 'dist', 'index.js');

let mcpProcess = null;
const pendingRequests = new Map();
let initialized = false;

function startMcp() {
  mcpProcess = spawn('node', [MCP_SCRIPT], {
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  mcpProcess.stderr.on('data', (d) => process.stderr.write(d));

  const rl = createInterface({ input: mcpProcess.stdout });
  rl.on('line', (line) => {
    let data;
    try { data = JSON.parse(line); } catch { return; }
    const id = data.id;
    if (id !== undefined && pendingRequests.has(id)) {
      const { resolve } = pendingRequests.get(id);
      pendingRequests.delete(id);
      resolve(data);
    }
  });

  mcpProcess.on('exit', (code) => {
    console.error(`[proxy] hwpx-mcp exited (${code}), restarting...`);
    initialized = false;
    setTimeout(startMcp, 1000);
  });

  sendRpc({
    jsonrpc: '2.0',
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'http-proxy', version: '1.0.0' },
    },
    id: 0,
  }).then(() => {
    initialized = true;
    console.error('[proxy] hwpx-mcp initialized');
  }).catch((e) => console.error('[proxy] init error', e));
}

let nextId = 100;
function sendRpc(payload) {
  return new Promise((resolve, reject) => {
    const id = payload.id ?? nextId++;
    const msg = { ...payload, id };
    pendingRequests.set(id, { resolve, reject });
    const timer = setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id);
        reject(new Error(`RPC timeout for method=${msg.method}`));
      }
    }, 30000);
    pendingRequests.get(id).timer = timer;
    mcpProcess.stdin.write(JSON.stringify(msg) + '\n');
  });
}

startMcp();

createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(initialized ? 200 : 503);
    res.end(initialized ? 'ok' : 'initializing');
    return;
  }

  if (req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body);
        const result = await sendRpc(payload);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));
      } catch (e) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { code: -32000, message: e.message } }));
      }
    });
    return;
  }

  res.writeHead(404);
  res.end();
}).listen(PORT, () => {
  console.error(`[proxy] HTTP proxy listening on port ${PORT}`);
});
