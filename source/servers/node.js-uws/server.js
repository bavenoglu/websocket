// server.js
const uWS = require('./uws.js');
const fs = require('fs');

const MAX_PAYLOAD = 72000;
const LOG_BATCH = 100000;
const LOG_QUEUE_MAX = 1_000_000;

let logQueue = [];
let logBuffer = [];

let testIdArg = '1';
const idxTid = process.argv.indexOf('--test-id');
if (idxTid !== -1 && process.argv[idxTid + 1]) {
    testIdArg = process.argv[idxTid + 1];
}

let port = 8003;
const args = process.argv;
const idx = args.indexOf('--port');
if (idx !== -1 && args[idx + 1]) {
    port = parseInt(args[idx + 1], 10);
}

const logStream = fs.createWriteStream(`/logs/server_log_${testIdArg}.csv`, { flags: 'w' });
logStream.write('test_id,conn_id,index,status,process_ms\n');

const logInterval = setInterval(() => {
    if (logQueue.length === 0) return;

    while (logQueue.length && logBuffer.length < LOG_BATCH) {
        logBuffer.push(logQueue.shift());
    }

    if (logBuffer.length >= LOG_BATCH) {
        for (const l of logBuffer) {
            logStream.write(`${l.testId},${l.clientId},${l.seq},${l.status},${l.processMs}\n`);
        }
        logBuffer.length = 0;
    }
}, 1);

uWS.App()
    .ws('/ws', {
        compression: 0,
        maxPayloadLength: MAX_PAYLOAD,
        open: (ws) => {
        },
        message: (ws, message, isBinary) => {
            if (!isBinary) {
                ws.close();
                return;
            }

            if (message.byteLength > MAX_PAYLOAD) {
                ws.close();
                return;
            }

            // START: server received
            const start = process.hrtime.bigint();

            // header parse
            const buf = Buffer.from(message);
            const testId = buf.readUInt16BE(0);
            const clientId = buf.readUInt16BE(2);
            const seq = buf.readUInt32BE(4);

            let status = 'OK';
            try {
                const ok = ws.send(message, true);
                if (!ok) status = 'FAIL';
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
        },
        close: (ws, code, message) => {
        }
    })
    .listen(port, (token) => {
        if (token) console.log(`uWS echo server listening on :${port}`);
        else console.log('Failed to listen');
    });

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