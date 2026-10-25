import org.java_websocket.WebSocket;
import org.java_websocket.handshake.ClientHandshake;
import org.java_websocket.server.WebSocketServer;

import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.util.Collections;
import org.java_websocket.drafts.Draft;
import org.java_websocket.drafts.Draft_6455;

public class Server extends WebSocketServer {

    private static final int MAX_PAYLOAD = 72_000;
    private static String TEST_ID = "1";

    static class ServerLog {
        int testId;
        int clientId;
        long msgIndex;
        String status; // "OK" / "FAIL"
        double processMs;
    }

    static final int LOG_BATCH = 100_000;
    static final java.util.concurrent.BlockingQueue<ServerLog> logQueue = new java.util.concurrent.ArrayBlockingQueue<>(
            1_000_000);

    static volatile boolean running = true;
    static Thread logThread;


    public Server(int port, int workers) {
        super(
            new InetSocketAddress(port),
            workers,
            Collections.<Draft>singletonList(
                new Draft_6455(Collections.emptyList(), MAX_PAYLOAD)
            )
        );
    }

    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        // nothing
    }

    @Override
    public void onClose(WebSocket conn, int code, String reason, boolean remote) {
        // nothing
    }

    @Override
    public void onMessage(WebSocket conn, String message) {
        // TEXT NOT ALLOWED (Go & Netty ile aynı)
        conn.close(1003, "Text frames not allowed");
    }

    @Override
    public void onMessage(WebSocket conn, ByteBuffer message) {

        // ===== MAX PAYLOAD CHECK (java-websocket way) =====
        if (message.remaining() > MAX_PAYLOAD) {
            conn.close(1009, "Payload too large");
            return;
        }

        // ===== HEADER CHECK =====
        if (message.remaining() < 8) {
            return;
        }

        long start = System.nanoTime();

        message.rewind();

        int testId = message.getShort() & 0xFFFF;
        int clientId = message.getShort() & 0xFFFF;
        long seq = message.getInt() & 0xFFFFFFFFL;

        // ===== ECHO (BLOCKING WRITE) =====
        String status = "OK";
        try {
            conn.send(message);
        } catch (Exception e) {
            status = "FAIL";
        }
        double processMs = (System.nanoTime() - start) / 1_000_000.0;

        if (seq >= 5) {
            ServerLog log = new ServerLog();
            log.testId = testId;
            log.clientId = clientId;
            log.msgIndex = seq;
            log.status = status;
            log.processMs = processMs;
            logQueue.offer(log);
        }
    }

    @Override
    public void onError(WebSocket conn, Exception ex) {
        // ignore
    }

    @Override
    public void onStart() {
        System.out.println("java-websocket listening on :" + getPort());
    }

    static void startLogWriter(String testId) {
        logThread = new Thread(() -> {
            try (java.io.BufferedWriter w = new java.io.BufferedWriter(
                    new java.io.FileWriter("/logs/server_log_" + testId + ".csv"), 4 * 1024 * 1024)) {

                w.write("test_id,conn_id,index,status,process_ms\n");
                java.util.List<ServerLog> buffer = new java.util.ArrayList<>(LOG_BATCH);

                while (running || !logQueue.isEmpty()) {
                    ServerLog l = logQueue.poll();
                    if (l == null) {
                        Thread.sleep(1);
                        continue;
                    }
                    buffer.add(l);
                    if (buffer.size() >= LOG_BATCH) {
                        for (ServerLog x : buffer) {
                            w.write(x.testId + "," + x.clientId + "," + x.msgIndex + ","
                                    + x.status + "," + x.processMs + "\n");
                        }
                        w.flush();
                        buffer.clear();
                    }
                }

                if (!buffer.isEmpty()) {
                    for (ServerLog x : buffer) {
                        w.write(x.testId + "," + x.clientId + "," + x.msgIndex + ","
                                + x.status + "," + x.processMs + "\n");
                    }
                    w.flush();
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }, "log-writer");
        logThread.start();
    }

    public static void main(String[] args) throws Exception {
        int port = 8002;

        for (String a : args) {
            if (a.startsWith("--port=")) {
                port = Integer.parseInt(a.substring(7));
            }
            if (a.startsWith("--test-id=")) {
                TEST_ID = a.substring(10);
            }
        }

        Server server = new Server(port, 4);
        server.setMaxPendingConnections(1024);
        server.setTcpNoDelay(true);
        startLogWriter(TEST_ID);
        server.start();

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Server stopping..");
            running = false;
            try {
                logThread.join();
            } catch (InterruptedException ignored) {
            }
        }));
    }
}
