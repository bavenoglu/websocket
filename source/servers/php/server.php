<?php

use Swoole\WebSocket\Server;

$port = 8005;
$testIdArg = '1';

foreach ($argv as $a) {
    if (str_starts_with($a, '--port=')) {
        $port = intval(substr($a, 7));
    }
    if (str_starts_with($a, '--test-id=')) {
        $testIdArg = substr($a, 10);
    }
}

const MAX_PAYLOAD = 72000;
const LOG_BATCH = 50000;
const LOG_QUEUE_MAX = 1000000;

$logQueue = [];
$logBuffer = [];

$logFile = "/logs/server_log_{$testIdArg}.csv";
$logFp = fopen($logFile, 'w');
fwrite($logFp, "test_id,conn_id,index,status,process_ms\n");

$server = new Server("0.0.0.0", $port);

$server->set([
    'websocket_compression' => false,
    // Worker processes
    'worker_num' => 4,
    // Reactor threads
    'reactor_num' => 1,
    // Connection backlog
    'backlog' => 1024,
    // Disable Nagle's algorithm
    'open_tcp_nodelay' => true,
    'package_max_length' => MAX_PAYLOAD,
]);

$server->on("start", function (Server $server) use ($port) {
    echo "php-swoole listening on :{$port}\n";
});

$server->on("message", function (Server $server, $frame) use (&$logQueue) {

    if (!$server->isEstablished($frame->fd)) {
        return;
    }

    $data = $frame->data;
    $len = strlen($data);

    if ($len < 8 || $len > MAX_PAYLOAD) {
        $server->disconnect($frame->fd, 1009, "Invalid payload");
        return;
    }

    // START: server received
    $start = hrtime(true);

    // header parse
    $testId   = unpack('n', substr($data, 0, 2))[1];
    $clientId = unpack('n', substr($data, 2, 2))[1];
    $seq      = unpack('N', substr($data, 4, 4))[1];

    $status = "OK";
    try {
        $server->push($frame->fd, $data, SWOOLE_WEBSOCKET_OPCODE_BINARY);
    } catch (Throwable $e) {
        $status = "FAIL";
    }

    // END: send finished
    $processMs = (hrtime(true) - $start) / 1e6;

    if ($seq >= 5 && count($logQueue) < LOG_QUEUE_MAX) {
        $logQueue[] = [
            'testId' => $testId,
            'clientId' => $clientId,
            'seq' => $seq,
            'status' => $status,
            'processMs' => $processMs,
        ];
    }
});

$server->on('Shutdown', function () use (&$logQueue, &$logBuffer, $logFp) {
    echo "Server stopping..\n";

    foreach ($logQueue as $l) {
        fwrite($logFp, "{$l['testId']},{$l['clientId']},{$l['seq']},{$l['status']},{$l['processMs']}\n");
    }
    foreach ($logBuffer as $l) {
        fwrite($logFp, "{$l['testId']},{$l['clientId']},{$l['seq']},{$l['status']},{$l['processMs']}\n");
    }
    fclose($logFp);

    \Swoole\Event::Exit();
});

$server->on('WorkerStart', function (Server $server, int $workerId) use (&$logQueue, &$logBuffer, $logFp) {
    /* ===== LOG WRITER (timer ile batch flush) ===== */
    \Swoole\Timer::tick(1, function () use (&$logQueue, &$logBuffer, $logFp) {
        if (empty($logQueue)) return;

        while (!empty($logQueue) && count($logBuffer) < LOG_BATCH) {
            $logBuffer[] = array_shift($logQueue);
        }

        if (count($logBuffer) >= LOG_BATCH) {
            flock($logFp, LOCK_EX);
            foreach ($logBuffer as $l) {
                fwrite(
                    $logFp,
                    "{$l['testId']},{$l['clientId']},{$l['seq']},{$l['status']},{$l['processMs']}\n"
                );
            }
            flock($logFp, LOCK_UN);
            $logBuffer = [];
        }
    });

    if ($workerId == 0) {
        \Swoole\Process::signal(SIGINT, function () use ($server) {
            $server->shutdown();
        });
    }
});

$server->on('WorkerStop', function (Server $server, int $workerId) use (&$logQueue, &$logBuffer, $logFp) {
    \Swoole\Timer::clearAll();

    flock($logFp, LOCK_EX);
    foreach ($logQueue as $l) {
        fwrite($logFp, "{$l['testId']},{$l['clientId']},{$l['seq']},{$l['status']},{$l['processMs']}\n");
    }
    foreach ($logBuffer as $l) {
        fwrite($logFp, "{$l['testId']},{$l['clientId']},{$l['seq']},{$l['status']},{$l['processMs']}\n");
    }
    flock($logFp, LOCK_UN);
});

$server->on('WorkerExit', function (Server $server, int $workerId) {
    \Swoole\Timer::clearAll();
});

$server->start();
