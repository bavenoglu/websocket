import io.netty.bootstrap.ServerBootstrap;
import io.netty.buffer.ByteBuf;
import io.netty.channel.*;
import io.netty.channel.nio.NioIoHandler;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.http.HttpServerCodec;
import io.netty.handler.codec.http.websocketx.*;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

public class Server {

    // ===== LOG STRUCT (SAME AS GO) =====
    static class ServerLog {
        int testId;
        int clientId;
        long msgIndex;
        String status; // "OK" / "FAIL"
        double processMs;
    }

    // ===== LOGGING CONFIG =====
    static final int LOG_BATCH = 100_000;
    static final BlockingQueue<ServerLog> logQueue = new ArrayBlockingQueue<>(1_000_000);

    static volatile boolean running = true;
    static Thread logThread;

    // ===== LOG WRITER THREAD =====
    static void startLogWriter(String testId) {
        logThread = new Thread(() -> {
            try (BufferedWriter w = new BufferedWriter(
                    new FileWriter("/logs/server_log_" + testId + ".csv"), 4 * 1024 * 1024)) {

                w.write("test_id,conn_id,index,status,process_ms\n");

                List<ServerLog> buffer = new ArrayList<>(LOG_BATCH);

                while (running || !logQueue.isEmpty()) {
                    ServerLog l = logQueue.poll();
                    if (l == null) {
                        Thread.sleep(1);
                        continue;
                    }

                    buffer.add(l);
                    if (buffer.size() >= LOG_BATCH) {
                        flush(w, buffer);
                    }
                }

                if (!buffer.isEmpty()) {
                    flush(w, buffer);
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }, "log-writer");
        logThread.start();
    }

    static void flush(BufferedWriter w, List<ServerLog> buf) throws Exception {
        for (ServerLog l : buf) {
            w.write(l.testId + "," + l.clientId + "," + l.msgIndex + ","
                    + l.status + "," + l.processMs + "\n");
        }
        w.flush();
        buf.clear(); // IMPORTANT: reuse buffer
    }

    // ===== MAIN =====
    public static void main(String[] args) throws Exception {
        int port = 8004;
        String testId = "1";

        for (String a : args) {
            if (a.startsWith("--port=")) {
                port = Integer.parseInt(a.substring(7));
            }
            if (a.startsWith("--test-id=")) {
                testId = a.substring(10);
            }
        }

        startLogWriter(testId);

        EventLoopGroup boss =
            new MultiThreadIoEventLoopGroup(
                1, NioIoHandler.newFactory());

        EventLoopGroup worker =
            new MultiThreadIoEventLoopGroup(
                4, NioIoHandler.newFactory());

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Server stopping..");

            running = false;
            try {
                logThread.join();
            } catch (InterruptedException ignored) {
            }
            boss.shutdownGracefully();
            worker.shutdownGracefully();
        }));

        ServerBootstrap b = new ServerBootstrap();

        b.group(boss, worker)
                .channel(NioServerSocketChannel.class)
                .option(ChannelOption.SO_BACKLOG, 1024)
                .childOption(ChannelOption.TCP_NODELAY, true)
                .childHandler(new ChannelInitializer<Channel>() {
                    @Override
                    protected void initChannel(Channel ch) {
                        ChannelPipeline p = ch.pipeline();

                        p.addLast(new HttpServerCodec());
                        // compression OFF, max payload = 72K
                        p.addLast(new WebSocketServerProtocolHandler("/ws", null, false, 72000));

                        p.addLast(new SimpleChannelInboundHandler<WebSocketFrame>() {

                            @Override
                            protected void channelRead0(ChannelHandlerContext ctx, WebSocketFrame frame) {
                                if (!(frame instanceof BinaryWebSocketFrame)) {
                                    return;
                                }

                                BinaryWebSocketFrame bin = (BinaryWebSocketFrame) frame;
                                ByteBuf buf = bin.content();

                                if (buf.readableBytes() < 8) {
                                    return;
                                }

                                long start = System.nanoTime();

                                int testIdVal = buf.getUnsignedShort(0);
                                int clientIdVal = buf.getUnsignedShort(2);
                                long seq = buf.getUnsignedInt(4);

                                ChannelFuture f = ctx.writeAndFlush(bin.retain());

                                f.addListener((ChannelFutureListener) future -> {
                                    double processMs = (System.nanoTime() - start) / 1_000_000.0;

                                    String status = future.isSuccess() ? "OK" : "FAIL";

                                    if (seq >= 5) {
                                        ServerLog log = new ServerLog();
                                        log.testId = testIdVal;
                                        log.clientId = clientIdVal;
                                        log.msgIndex = seq;
                                        log.status = status;
                                        log.processMs = processMs;
                                        logQueue.offer(log);
                                    }
                                });
                            }
                        });
                    }
                });

        Channel ch = b.bind(port).sync().channel();
        System.out.println("java-netty listening on :" + port);
        ch.closeFuture().sync();

        running = false;
    }
}
