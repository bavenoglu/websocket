import asyncio
import websockets
import sys
import signal
import time
import struct
from collections import deque

# ================= CONFIG =================

MAX_PAYLOAD = 72000
LOG_BATCH = 100_000
LOG_QUEUE_MAX = 1_000_000

# ================= ARGS =================

port = 8006
test_id_arg = "1"

for a in sys.argv:
    if a.startswith("--port="):
        port = int(a[7:])
    if a.startswith("--test-id="):
        test_id_arg = a[10:]

# ================= LOGGING =================

log_queue = deque()
log_buffer = []

log_file = open(f"/logs/server_log_{test_id_arg}.csv", "w", buffering=4 * 1024 * 1024)
log_file.write("test_id,conn_id,index,status,process_ms\n")

async def log_writer(stop_event: asyncio.Event):
    while not stop_event.is_set() or log_queue:
        while log_queue and len(log_buffer) < LOG_BATCH:
            log_buffer.append(log_queue.popleft())

        if len(log_buffer) >= LOG_BATCH:
            for l in log_buffer:
                log_file.write(
                    f"{l['testId']},{l['clientId']},{l['seq']},{l['status']},{l['processMs']}\n"
                )
            log_buffer.clear()

        await asyncio.sleep(0.001)

    # flush kalanlar
    for l in log_buffer:
        log_file.write(
            f"{l['testId']},{l['clientId']},{l['seq']},{l['status']},{l['processMs']}\n"
        )
    log_file.flush()
    log_file.close()

# ================= SERVER =================

stop_event = asyncio.Event()

async def handler(ws):
    try:
        async for msg in ws:
            if not isinstance(msg, (bytes, bytearray)):
                await ws.close()
                return

            if len(msg) < 8 or len(msg) > MAX_PAYLOAD:
                await ws.close()
                return

            start = time.perf_counter_ns()

            # header parse (Big Endian)
            test_id, client_id, seq = struct.unpack(">HHI", msg[:8])

            status = "OK"
            try:
                await ws.send(msg)
            except Exception:
                status = "FAIL"

            process_ms = (time.perf_counter_ns() - start) / 1e6

            if seq >= 5 and len(log_queue) < LOG_QUEUE_MAX:
                log_queue.append({
                    "testId": test_id,
                    "clientId": client_id,
                    "seq": seq,
                    "status": status,
                    "processMs": process_ms
                })
    except:
        pass

async def main():
    loop = asyncio.get_running_loop()

    def shutdown():
        print("Server stopping..", flush=True)
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT, shutdown)
    loop.add_signal_handler(signal.SIGTERM, shutdown)

    writer_task = asyncio.create_task(log_writer(stop_event))

    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        max_size=MAX_PAYLOAD,
        compression=None,
        backlog=1024,
    ):
        print(f"python-websockets listening on :{port}", flush=True)
        await stop_event.wait()

    await writer_task

asyncio.run(main())
