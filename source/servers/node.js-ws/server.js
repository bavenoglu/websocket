const WebSocket = require('ws');
const fs = require('fs');

/* ================= CONFIG ================= */

const MAX_PAYLOAD = 72000;
const LOG_BATCH = 100000;
const LOG_QUEUE_MAX = 1_000_000;

/* ================= ARGS ================= */

let port = 8004;
let testIdArg = '1';

const args = process.argv;
let idx = args.indexOf('--port');
if (idx !== -1 && args[idx + 1]) port = parseInt(args[idx + 1], 10);

idx = args.indexOf('--test-id');
if (idx !== -1 && args[idx + 1]) testIdArg = args[idx + 1];

/* ================= LOGGING ================= */

let logQueue = [];
let logBuffer = [];

const logStream = fs.createWriteStream(`/logs/server_log_${testIdArg}.csv`, { flags: 'w' });
logStream.write('test_id,conn_id,index,status,process_ms\n');

const logInterval = setInterval(() => {
  if (logQueue.length === 0) return;

  while (logQueue.length && logBuffer.length < LOG_BATCH) {
    logBuffer.push(logQueue.shift());
  }

  if (logBuffer.length >= LOG_BATCH) {
    for (const l of logBuffer) {
      logStream.write(
        `${l.testId},${l.clientId},${l.seq},${l.status},${l.processMs}\n`
      );
    }
    logBuffer.length = 0;
  }
}, 1);

/* ================= SERVER ================= */

const wss = new WebSocket.Server({
  port,
  path: '/ws',
  perMessageDeflate: false,
  maxPayload: MAX_PAYLOAD,
  backlog: 1024
});

wss.on('connection', (ws) => {
  ws._socket.setNoDelay(true);
  ws.on('message', (data, isBinary) => {

    if (!isBinary) {
      ws.close();
      return;
    }

    if (data.length > MAX_PAYLOAD || data.length < 8) {
      ws.close();
      return;
    }

    // START: server received
    const start = process.hrtime.bigint();

    // header parse (Big Endian)
    const buf = Buffer.from(data);
    const testId = buf.readUInt16BE(0);
    const clientId = buf.readUInt16BE(2);
    const seq = buf.readUInt32BE(4);

    let status = 'OK';
    try {
      ws.send(data, { binary: true });
    } catch (e) {
      status = 'FAIL';
    }

    // END: send finished
    const end = process.hrtime.bigint();
    const processMs = Number(end - start) / 1e6;

    if (seq >= 5 && logQueue.length < LOG_QUEUE_MAX) {
      logQueue.push({
        testId,
        clientId,
        seq,
        status,
        processMs
      });
    }
  });

  ws.on('close', () => { });
});

/* ================= SHUTDOWN ================= */

function shutdown() {
  console.log('Server stopping..');
  clearInterval(logInterval);

  for (const l of logQueue) {
    logStream.write(`${l.testId},${l.clientId},${l.seq},${l.status},${l.processMs}\n`);
  }
  for (const l of logBuffer) {
    logStream.write(`${l.testId},${l.clientId},${l.seq},${l.status},${l.processMs}\n`);
  }

  logStream.end(() => process.exit(0));
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

console.log(`Node.js ws server listening on :${port}`);
