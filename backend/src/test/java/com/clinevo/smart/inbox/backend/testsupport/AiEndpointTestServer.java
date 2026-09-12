package com.clinevo.smart.inbox.backend.testsupport;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.atomic.AtomicBoolean;

public final class AiEndpointTestServer {

    private static final AtomicBoolean STARTED = new AtomicBoolean(false);
    private static HttpServer server;

    private AiEndpointTestServer() {
    }

    public static synchronized void ensureStarted() {
        if (STARTED.get()) {
            return;
        }
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", 8000), 0);
            server.setExecutor(null);
            server.start();
            STARTED.set(true);
        } catch (IOException e) {
            throw new IllegalStateException("Unable to start test AI server", e);
        }
    }

    public static synchronized void bind(String path, com.sun.net.httpserver.HttpHandler handler) {
        if (server == null) {
            ensureStarted();
        }
        try {
            server.removeContext(path);
        } catch (IllegalArgumentException ignored) {
            // no-op: the context did not exist yet
        }
        server.createContext(path, handler);
    }

    public static synchronized void stop() {
        if (server != null) {
            server.stop(0);
            server = null;
            STARTED.set(false);
        }
    }
}
