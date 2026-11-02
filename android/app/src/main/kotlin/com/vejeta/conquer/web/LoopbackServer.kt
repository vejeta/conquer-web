// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.web

import android.content.res.AssetManager
import java.io.BufferedInputStream
import java.io.Closeable
import java.io.IOException
import java.io.OutputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.URLDecoder
import java.util.Locale
import java.util.concurrent.Executors

/**
 * A small HTTP server on 127.0.0.1 that serves the website copy in the app's
 * assets (assets/web/). WebAssembly streaming and service workers do not work
 * from file:// pages; http://127.0.0.1:PORT/ is a secure context, so they do.
 *
 * GET and HEAD only; every response is "Connection: close" and
 * "Cache-Control: no-cache". Paths with ".." or backslashes are refused, and a
 * request whose Host header is not this server (DNS rebinding) too.
 *
 * The page's origin includes the port, and the practice world lives in the
 * origin's IndexedDB: ask for the same [preferredPort] every run (the caller
 * saves [port]) so that the world is still there next time. A port already in
 * use falls back to a free one.
 */
class LoopbackServer(
    private val assets: AssetManager,
    preferredPort: Int = 0,
    private val root: String = "web",
) : Closeable {

    private val socket: ServerSocket = bind(preferredPort)
    private val pool = Executors.newCachedThreadPool()

    @Volatile
    private var closed = false

    val port: Int get() = socket.localPort
    val origin: String get() = "http://127.0.0.1:$port"

    fun start() {
        pool.execute {
            while (!closed) {
                val client = try {
                    socket.accept()
                } catch (e: IOException) {
                    break
                }
                pool.execute { serve(client) }
            }
        }
    }

    override fun close() {
        closed = true
        try {
            socket.close()
        } catch (e: IOException) {
        }
        pool.shutdownNow()
    }

    private fun serve(client: Socket) {
        client.use { c ->
            try {
                c.soTimeout = 10_000
                val input = BufferedInputStream(c.getInputStream())
                val out = c.getOutputStream()
                val head = readHead(input) ?: return
                respond(head, out)
                out.flush()
            } catch (e: IOException) {
                // The page went away, or was too slow: nothing to answer
            }
        }
    }

    /** The request line and the headers, or null when they are malformed or too long. */
    private fun readHead(input: BufferedInputStream): List<String>? {
        val lines = ArrayList<String>()
        val line = StringBuilder()
        var total = 0
        while (true) {
            val b = input.read()
            if (b < 0) return null
            if (++total > MAX_HEAD) return null
            if (b == '\n'.code) {
                val text = line.toString().trimEnd('\r')
                line.setLength(0)
                if (text.isEmpty()) return lines.takeIf { it.isNotEmpty() }
                lines.add(text)
            } else {
                line.append(b.toChar())
            }
        }
    }

    private fun respond(head: List<String>, out: OutputStream) {
        val parts = head[0].split(' ')
        if (parts.size != 3) return send(out, 400, "Bad Request")
        val method = parts[0]
        if (method != "GET" && method != "HEAD") return send(out, 405, "Method Not Allowed", head = true)

        val host = head.drop(1).firstOrNull { it.startsWith("host:", ignoreCase = true) }
            ?.substringAfter(':')?.trim()
        if (host != "127.0.0.1:$port" && host != "localhost:$port") return send(out, 403, "Forbidden")

        val rawPath = parts[1].substringBefore('?').substringBefore('#')
        val path = try {
            URLDecoder.decode(rawPath.replace("+", "%2B"), "UTF-8")
        } catch (e: IllegalArgumentException) {
            return send(out, 400, "Bad Request")
        }
        if (!path.startsWith("/") || path.contains('\\') || path.contains('\u0000') ||
            path.split('/').any { it == ".." }
        ) {
            return send(out, 400, "Bad Request")
        }

        var name = path.trimStart('/')
        if (name.isEmpty() || name.endsWith("/")) name += "index.html"
        val assetPath = "$root/$name"

        val body = try {
            assets.open(assetPath).use { it.readBytes() }
        } catch (e: IOException) {
            // A directory without its slash ("/try"): relative links of the
            // page need it
            if (!assets.list(assetPath).isNullOrEmpty()) {
                return send(out, 301, "Moved Permanently", location = "/$name/", head = method == "HEAD")
            }
            return send(out, 404, "Not Found", head = method == "HEAD")
        }
        send(out, 200, "OK", type = mimeType(name), body = body, head = method == "HEAD")
    }

    private fun send(
        out: OutputStream,
        status: Int,
        reason: String,
        type: String = "text/plain; charset=utf-8",
        body: ByteArray = reason.toByteArray(),
        location: String? = null,
        head: Boolean = false,
    ) {
        val header = StringBuilder()
            .append("HTTP/1.1 ").append(status).append(' ').append(reason).append("\r\n")
            .append("Content-Type: ").append(type).append("\r\n")
            .append("Content-Length: ").append(body.size).append("\r\n")
            .append("Cache-Control: no-cache\r\n")
            .append("X-Content-Type-Options: nosniff\r\n")
            .append("Connection: close\r\n")
        if (location != null) header.append("Location: ").append(location).append("\r\n")
        header.append("\r\n")
        out.write(header.toString().toByteArray(Charsets.ISO_8859_1))
        if (!head) out.write(body)
    }

    companion object {
        private const val MAX_HEAD = 16 * 1024

        private fun bind(preferredPort: Int): ServerSocket {
            val loopback = InetAddress.getByName("127.0.0.1")
            if (preferredPort in 1024..65535) {
                try {
                    return ServerSocket(preferredPort, 50, loopback)
                } catch (e: IOException) {
                    // In use: take any free port
                }
            }
            return ServerSocket(0, 50, loopback)
        }

        /** The Content-Type of a file, by its extension. */
        fun mimeType(name: String): String {
            return when (name.substringAfterLast('.', "").lowercase(Locale.ROOT)) {
                "html", "htm" -> "text/html; charset=utf-8"
                "js", "mjs" -> "text/javascript; charset=utf-8"
                "css" -> "text/css; charset=utf-8"
                "json", "map" -> "application/json; charset=utf-8"
                "wasm" -> "application/wasm"
                "txt", "cast" -> "text/plain; charset=utf-8"
                "vtt" -> "text/vtt; charset=utf-8"
                "svg" -> "image/svg+xml"
                "png" -> "image/png"
                "jpg", "jpeg" -> "image/jpeg"
                "webp" -> "image/webp"
                "gif" -> "image/gif"
                "ico" -> "image/x-icon"
                "woff2" -> "font/woff2"
                "woff" -> "font/woff"
                "ttf" -> "font/ttf"
                "otf" -> "font/otf"
                "mp4" -> "video/mp4"
                "webm" -> "video/webm"
                else -> "application/octet-stream"
            }
        }
    }
}
