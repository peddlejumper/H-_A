
package com.hsharp.runtime

import java.io.File
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.net.URLEncoder
import java.sql.Connection
import java.sql.DriverManager
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Base64
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

object HNativeBridge {

    /** Built-in functions, callable directly from H# code. */
    val builtins: Map<String, HNative> = linkedMapOf(
        // ── Core ──
        "len" to HNative("len", 1) { args ->
            val v = args[0]
            val n = when (v) {
                is HString -> v.value.length
                is HList -> v.items.size
                is HDict -> v.entries.size
                else -> throw HSharpRuntimeError("len() not supported on ${v.type}")
            }
            HNumber(n.toDouble())
        },
        "push" to HNative("push", 2) { args ->
            val arr = args[0] as? HList ?: throw HSharpRuntimeError("push() requires a list")
            arr.items.add(args[1])
            HNull
        },
        "pop" to HNative("pop", 1) { args ->
            val arr = args[0] as? HList ?: throw HSharpRuntimeError("pop() requires a list")
            if (arr.items.isEmpty()) throw HSharpRuntimeError("pop() on empty list")
            arr.items.removeAt(arr.items.size - 1)
        },
        "read_file" to HNative("read_file", 1) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("read_file path must be string")
            HString(File(path).readText(Charsets.UTF_8))
        },
        "write_file" to HNative("write_file", 2) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("write_file path must be string")
            val txt = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            File(path).writeText(txt, Charsets.UTF_8)
            HNull
        },
        "str" to HNative("str", 1) { args -> HString(args[0].toDisplayString()) },
        "int" to HNative("int", 1) { args -> HNumber(HValueOps.toDouble(args[0]).toLong().toDouble()) },
        "float" to HNative("float", 1) { args -> HNumber(HValueOps.toDouble(args[0])) },
        "type" to HNative("type", 1) { args -> HString(args[0].type.name.lowercase()) },
        "typeof" to HNative("typeof", 1) { args -> HString(args[0].type.name.lowercase()) },
        "input" to HNative("input", 1) { args ->
            val prompt = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            print(prompt)
            System.out.flush()
            HString(readlnOrNull() ?: "")
        },
        "abs" to HNative("abs", 1) { args -> HNumber(abs(HValueOps.toDouble(args[0]))) },
        "min" to HNative("min", 1) { args ->
            val lst = args[0] as? HList ?: throw HSharpRuntimeError("min() requires a list")
            if (lst.items.isEmpty()) throw HSharpRuntimeError("min() on empty list")
            var best = lst.items[0]
            for (i in 1 until lst.items.size) {
                if (HValueOps.toDouble(lst.items[i]) < HValueOps.toDouble(best)) best = lst.items[i]
            }
            best
        },
        "max" to HNative("max", 1) { args ->
            val lst = args[0] as? HList ?: throw HSharpRuntimeError("max() requires a list")
            if (lst.items.isEmpty()) throw HSharpRuntimeError("max() on empty list")
            var best = lst.items[0]
            for (i in 1 until lst.items.size) {
                if (HValueOps.toDouble(lst.items[i]) > HValueOps.toDouble(best)) best = lst.items[i]
            }
            best
        },
        "range" to HNative("range", -1) { args ->
            val items = ArrayList<HValue>()
            when (args.size) {
                1 -> for (i in 0 until HValueOps.toLong(args[0]).toInt()) items.add(HNumber(i.toDouble()))
                2 -> for (i in HValueOps.toLong(args[0]).toInt() until HValueOps.toLong(args[1]).toInt())
                    items.add(HNumber(i.toDouble()))
                else -> throw HSharpRuntimeError("range() takes 1 or 2 args")
            }
            HList(items)
        },
        "keys" to HNative("keys", 1) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("keys() requires a dict")
            HList(d.entries.keys.map { HString(it) }.toMutableList())
        },
        "values" to HNative("values", 1) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("values() requires a dict")
            HList(d.entries.values.toMutableList())
        },
        "items" to HNative("items", 1) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("items() requires a dict")
            val out = ArrayList<HValue>()
            for ((k, v) in d.entries) {
                val pair = HList(mutableListOf(HString(k), v))
                out.add(pair)
            }
            HList(out)
        },
        "has_key" to HNative("has_key", 2) { args ->
            val d = args[1] as? HDict ?: throw HSharpRuntimeError("has_key() 2nd arg must be a dict")
            val key = when (val k = args[0]) {
                is HString -> k.value
                is HNumber -> k.toDisplayString()
                else -> k.toDisplayString()
            }
            HBool(key in d.entries)
        },

        // ── Threading ──
        "thread_spawn" to HNative("thread_spawn", 1) { args ->
            val fn = args[0]
            val t = Thread {
                try {
                    if (fn is HFunction) {
                        val vm = HVM(EMPTY_FILE)
                        val frame = HFrame(fn, fn.consts, fn.instructions, mutableMapOf(), null)
                        vm.resetEntry(frame)
                        vm.run()
                    }
                } catch (e: Throwable) {
                    System.err.println("Thread error: ${e.message}")
                }
            }
            t.isDaemon = true
            t.start()
            HDict(mutableMapOf("_joinable" to HBool(true)))
        },
        "thread_join" to HNative("thread_join", 1) { _ -> HNull },

        // ── String ──
        "substring" to HNative("substring", 3) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val start = HValueOps.toLong(args[1]).toInt()
            val len = HValueOps.toLong(args[2]).toInt()
            val end = (start + len).coerceAtMost(s.length)
            HString(s.substring(start.coerceIn(0, s.length), end.coerceIn(0, s.length)))
        },
        "ord" to HNative("ord", 1) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HNumber(if (s.isEmpty()) 0.0 else s[0].code.toDouble())
        },
        "chr" to HNative("chr", 1) { args ->
            HString(HValueOps.toLong(args[0]).toInt().toChar().toString())
        },

        // ── Time & Date ──
        "time_now" to HNative("time_now", 0) { _ ->
            HNumber((System.currentTimeMillis().toDouble()))
        },
        "date_now" to HNative("date_now", 0) { _ ->
            HString(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")))
        },
        "date_timestamp" to HNative("date_timestamp", 0) { _ ->
            HNumber(Instant.now().epochSecond.toDouble() + Instant.now().nano / 1e9)
        },
        "date_format" to HNative("date_format", 2) { args ->
            val ts = HValueOps.toDouble(args[0]).toLong()
            var fmt = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            fmt = fmt.replace("YYYY", "yyyy")
                .replace("MM", "MM").replace("DD", "dd")
                .replace("HH", "HH").replace("mm", "mm").replace("SS", "ss")
            val dt = LocalDateTime.ofInstant(Instant.ofEpochSecond(ts), ZoneId.systemDefault())
            HString(dt.format(DateTimeFormatter.ofPattern(fmt)))
        },
        "date_parse" to HNative("date_parse", 1) { args ->
            val dateStr = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val patterns = listOf("yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd", "yyyy/MM/dd", "dd/MM/yyyy")
            for (pat in patterns) {
                try {
                    val dt = LocalDateTime.parse(dateStr, DateTimeFormatter.ofPattern(pat))
                    val ts = dt.atZone(ZoneId.systemDefault()).toEpochSecond()
                    HDict(linkedMapOf<String, HValue>(
                        "year" to HNumber(dt.year.toDouble()),
                        "month" to HNumber(dt.monthValue.toDouble()),
                        "day" to HNumber(dt.dayOfMonth.toDouble()),
                        "hour" to HNumber(dt.hour.toDouble()),
                        "minute" to HNumber(dt.minute.toDouble()),
                        "second" to HNumber(dt.second.toDouble()),
                        "timestamp" to HNumber(ts.toDouble())
                    ).toMutableMap())
                } catch (_: Throwable) { continue }
            }
            throw HSharpRuntimeError("Cannot parse date: $dateStr")
        },

        // ── File System ──
        "fs_exists" to HNative("fs_exists", 1) { args ->
            HBool(File((args[0] as? HString)?.value ?: args[0].toDisplayString()).exists())
        },
        "fs_is_file" to HNative("fs_is_file", 1) { args ->
            HBool(File((args[0] as? HString)?.value ?: args[0].toDisplayString()).isFile)
        },
        "fs_is_dir" to HNative("fs_is_dir", 1) { args ->
            HBool(File((args[0] as? HString)?.value ?: args[0].toDisplayString()).isDirectory)
        },
        "fs_mkdir" to HNative("fs_mkdir", 1) { args ->
            File((args[0] as? HString)?.value ?: args[0].toDisplayString()).mkdirs()
            HNull
        },
        "fs_remove" to HNative("fs_remove", 1) { args ->
            File((args[0] as? HString)?.value ?: args[0].toDisplayString()).delete()
            HNull
        },
        "fs_list_dir" to HNative("fs_list_dir", 1) { args ->
            val files = File((args[0] as? HString)?.value ?: args[0].toDisplayString()).list()
            if (files == null) HList(mutableListOf())
            else HList(files.map { HString(it) }.toMutableList())
        },
        "fs_get_cwd" to HNative("fs_get_cwd", 0) { _ ->
            HString(System.getProperty("user.dir"))
        },
        "fs_chdir" to HNative("fs_chdir", 1) { args ->
            System.setProperty("user.dir", (args[0] as? HString)?.value ?: args[0].toDisplayString())
            HNull
        },
        "fs_join_path" to HNative("fs_join_path", -1) { args ->
            val parts = args.map { (it as? HString)?.value ?: it.toDisplayString() }
            HString(parts.joinToString(File.separator))
        },
        "fs_get_ext" to HNative("fs_get_ext", 1) { args ->
            val path = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val dot = path.lastIndexOf('.')
            HString(if (dot >= 0) path.substring(dot) else "")
        },
        "fs_get_basename" to HNative("fs_get_basename", 1) { args ->
            HString(File((args[0] as? HString)?.value ?: args[0].toDisplayString()).name)
        },
        "fs_get_dirname" to HNative("fs_get_dirname", 1) { args ->
            val parent = File((args[0] as? HString)?.value ?: args[0].toDisplayString()).parent
            HString(parent ?: ".")
        },

        // ── IO ──
        "io_append_file" to HNative("io_append_file", 2) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("append_file: path must be string")
            val content = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            File(path).appendText(content, Charsets.UTF_8)
            HNull
        },
        "io_read_lines" to HNative("io_read_lines", 1) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("read_lines: path must be string")
            HList(File(path).readLines(Charsets.UTF_8).map { HString(it) }.toMutableList())
        },
        "io_write_lines" to HNative("io_write_lines", 2) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("write_lines: path must be string")
            val lines = args[1] as? HList ?: throw HSharpRuntimeError("write_lines: lines must be a list")
            File(path).writeText(lines.items.joinToString("\n") { (it as? HString)?.value ?: it.toDisplayString() }, Charsets.UTF_8)
            HNull
        },

        // ── Network: HTTP ──
        "net_http_get" to HNative("net_http_get", -1) { args ->
            val url = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("http_get: url must be string")
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 30_000
                conn.readTimeout = 30_000
                val status = conn.responseCode
                val body = (if (status in 200..299) conn.inputStream else conn.errorStream)
                    ?.bufferedReader()?.readText() ?: ""
                conn.disconnect()
                HDict(linkedMapOf<String, HValue>(
                    "status" to HNumber(status.toDouble()),
                    "body" to HString(body),
                    "success" to HBool(status in 200..299)
                ).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf<String, HValue>(
                    "status" to HNumber(0.0), "body" to HString(""),
                    "success" to HBool(false), "error" to HString(e.message ?: "unknown")
                ).toMutableMap())
            }
        },
        "net_http_post" to HNative("net_http_post", -1) { args ->
            val url = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("http_post: url must be string")
            val data = args.getOrElse(1) { HString("") }
            val bodyStr = when (data) {
                is HString -> data.value
                is HDict -> data.toDisplayString()
                else -> data.toDisplayString()
            }
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                conn.connectTimeout = 30_000
                conn.readTimeout = 30_000
                conn.outputStream.write(bodyStr.toByteArray(Charsets.UTF_8))
                val status = conn.responseCode
                val respBody = (if (status in 200..299) conn.inputStream else conn.errorStream)
                    ?.bufferedReader()?.readText() ?: ""
                conn.disconnect()
                HDict(linkedMapOf<String, HValue>(
                    "status" to HNumber(status.toDouble()),
                    "body" to HString(respBody),
                    "success" to HBool(status in 200..299)
                ).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf<String, HValue>(
                    "status" to HNumber(0.0), "body" to HString(""),
                    "success" to HBool(false), "error" to HString(e.message ?: "unknown")
                ).toMutableMap())
            }
        },
        "net_url_parse" to HNative("net_url_parse", 1) { args ->
            try {
                val urlStr = (args[0] as? HString)?.value ?: args[0].toDisplayString()
                val u = URI(urlStr)
                val params = u.query?.split("&")?.filter { it.contains("=") }?.map {
                    val kv = it.split("=", limit = 2)
                    HList(mutableListOf(HString(kv[0]), HString(kv.getOrElse(1) { "" })))
                } ?: emptyList()
                HList(mutableListOf(
                    HList(mutableListOf(HString("scheme"), HString(u.scheme ?: ""))),
                    HList(mutableListOf(HString("netloc"), HString(u.host ?: ""))),
                    HList(mutableListOf(HString("path"), HString(u.path ?: ""))),
                    HList(mutableListOf(HString("query"), HString(u.query ?: ""))),
                    HList(mutableListOf(HString("fragment"), HString(u.fragment ?: ""))),
                    HList(mutableListOf(HString("params"), HList(params.toMutableList())))
                ))
            } catch (e: Throwable) {
                HList(mutableListOf(
                    HList(mutableListOf(HString("error"), HString(e.message ?: "unknown")))
                ))
            }
        },
        "net_url_build" to HNative("net_url_build", -1) { args ->
            val scheme = (args[0] as? HString)?.value ?: "https"
            val host = (args[1] as? HString)?.value ?: ""
            val path = if (args.size > 2) (args[2] as? HString)?.value ?: "" else ""
            HString("$scheme://$host$path")
        },

        // ── Network: TCP/UDP ──
        "net_tcp_connect" to HNative("net_tcp_connect", 2) { args ->
            val host = (args[0] as? HString)?.value ?: "localhost"
            val port = HValueOps.toLong(args[1]).toInt()
            try {
                val sock = java.net.Socket(host, port)
                sock.soTimeout = 10_000
                val id = TCPSockets.register(sock)
                HDict(linkedMapOf<String, HValue>(
                    "connected" to HBool(true), "socket_id" to HNumber(id.toDouble())
                ).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf<String, HValue>(
                    "connected" to HBool(false), "socket_id" to HNumber(0.0),
                    "error" to HString(e.message ?: "unknown")
                ).toMutableMap())
            }
        },
        "net_tcp_send" to HNative("net_tcp_send", 2) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val data = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            val sock = TCPSockets.get(id) ?: throw HSharpRuntimeError("Invalid socket")
            try {
                val sent = sock.getOutputStream().apply { write(data.toByteArray(Charsets.UTF_8)); flush() }
                HDict(linkedMapOf("sent" to HNumber(data.length.toDouble()), "success" to HBool(true)).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf("sent" to HNumber(0.0), "success" to HBool(false), "error" to HString(e.message ?: "unknown")).toMutableMap())
            }
        },
        "net_tcp_recv" to HNative("net_tcp_recv", -1) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val bufSize = if (args.size > 1) HValueOps.toLong(args[1]).toInt() else 4096
            val sock = TCPSockets.get(id) ?: throw HSharpRuntimeError("Invalid socket")
            try {
                val buf = ByteArray(bufSize)
                val n = sock.getInputStream().read(buf)
                if (n <= 0) HDict(linkedMapOf("data" to HString(""), "success" to HBool(false)).toMutableMap())
                else HDict(linkedMapOf("data" to HString(String(buf, 0, n, Charsets.UTF_8)), "success" to HBool(true)).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf("data" to HString(""), "success" to HBool(false), "error" to HString(e.message ?: "unknown")).toMutableMap())
            }
        },
        "net_tcp_close" to HNative("net_tcp_close", 1) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            TCPSockets.remove(id)?.close()
            HDict(linkedMapOf("success" to HBool(true)).toMutableMap())
        },

        "net_udp_create" to HNative("net_udp_create", 0) { _ ->
            try {
                val sock = java.net.DatagramSocket()
                sock.soTimeout = 10_000
                val id = UDPSockets.register(sock)
                HDict(linkedMapOf("created" to HBool(true), "socket_id" to HNumber(id.toDouble())).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf("created" to HBool(false), "socket_id" to HNumber(0.0), "error" to HString(e.message ?: "unknown")).toMutableMap())
            }
        },
        "net_udp_send" to HNative("net_udp_send", 4) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val data = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            val host = (args[2] as? HString)?.value ?: "localhost"
            val port = HValueOps.toLong(args[3]).toInt()
            val sock = UDPSockets.get(id) ?: throw HSharpRuntimeError("Invalid UDP socket")
            try {
                val bytes = data.toByteArray(Charsets.UTF_8)
                val pkt = java.net.DatagramPacket(bytes, bytes.size, java.net.InetAddress.getByName(host), port)
                sock.send(pkt)
                HDict(linkedMapOf("sent" to HNumber(bytes.size.toDouble()), "success" to HBool(true)).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf("sent" to HNumber(0.0), "success" to HBool(false), "error" to HString(e.message ?: "unknown")).toMutableMap())
            }
        },
        "net_udp_recv" to HNative("net_udp_recv", -1) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val bufSize = if (args.size > 1) HValueOps.toLong(args[1]).toInt() else 4096
            val sock = UDPSockets.get(id) ?: throw HSharpRuntimeError("Invalid UDP socket")
            try {
                val buf = ByteArray(bufSize)
                val pkt = java.net.DatagramPacket(buf, buf.size)
                sock.receive(pkt)
                HDict(linkedMapOf<String, HValue>(
                    "data" to HString(String(pkt.data, pkt.offset, pkt.length, Charsets.UTF_8)),
                    "from_host" to HString(pkt.address.hostAddress),
                    "from_port" to HNumber(pkt.port.toDouble()),
                    "success" to HBool(true)
                ).toMutableMap())
            } catch (e: Throwable) {
                HDict(linkedMapOf("data" to HString(""), "success" to HBool(false), "error" to HString(e.message ?: "unknown")).toMutableMap())
            }
        },

        // ── Network: Encoding ──
        "net_base64_encode" to HNative("net_base64_encode", 1) { args ->
            val data = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HString(Base64.getEncoder().encodeToString(data.toByteArray(Charsets.UTF_8)))
        },
        "net_base64_decode" to HNative("net_base64_decode", 1) { args ->
            val data = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            try {
                HString(String(Base64.getDecoder().decode(data), Charsets.UTF_8))
            } catch (_: Throwable) { HString("") }
        },
        "net_json_stringify" to HNative("net_json_stringify", 1) { args ->
            HString(args[0].toDisplayString())
        },
        "net_json_parse" to HNative("net_json_parse", 1) { _ ->
            HList(mutableListOf()) // stub: full JSON parse needs a real parser
        },

        // ── Database: SQLite ──
        "db_connect" to HNative("db_connect", 1) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("db_connect: path must be string")
            try {
                val conn = DriverManager.getConnection("jdbc:sqlite:$path")
                val id = DBConnections.register(conn)
                HList(mutableListOf(
                    HList(mutableListOf(HString("connected"), HBool(true))),
                    HList(mutableListOf(HString("connection_id"), HString(id))),
                    HList(mutableListOf(HString("path"), HString(path)))
                ))
            } catch (e: Throwable) {
                HList(mutableListOf(
                    HList(mutableListOf(HString("connected"), HBool(false))),
                    HList(mutableListOf(HString("connection_id"), HString(""))),
                    HList(mutableListOf(HString("error"), HString(e.message ?: "unknown")))
                ))
            }
        },
        "db_close" to HNative("db_close", 1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            DBConnections.remove(id)?.close()
            HList(mutableListOf(HList(mutableListOf(HString("success"), HBool(true)))))
        },
        "db_execute" to HNative("db_execute", -1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val sql = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("db_execute: sql must be string")
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            try {
                val stmt = conn.createStatement()
                if (sql.trim().uppercase().startsWith("SELECT") || sql.trim().uppercase().startsWith("PRAGMA")) {
                    val rs = stmt.executeQuery(sql)
                    val cols = (1..rs.metaData.columnCount).map { rs.metaData.getColumnName(it) }
                    val rows = ArrayList<HValue>()
                    while (rs.next()) {
                        val row = ArrayList<HValue>()
                        for (c in cols) row.add(HList(mutableListOf(HString(c), HString(rs.getString(c) ?: ""))))
                        rows.add(HList(row))
                    }
                    rs.close()
                    HList(mutableListOf(
                        HList(mutableListOf(HString("success"), HBool(true))),
                        HList(mutableListOf(HString("rows"), HList(rows))),
                        HList(mutableListOf(HString("columns"), HList(cols.map { HString(it) }.toMutableList()))),
                        HList(mutableListOf(HString("row_count"), HNumber(rows.size.toDouble())))
                    ))
                } else {
                    val rowsAffected = stmt.executeUpdate(sql)
                    HList(mutableListOf(
                        HList(mutableListOf(HString("success"), HBool(true))),
                        HList(mutableListOf(HString("rows_affected"), HNumber(rowsAffected.toDouble()))),
                        HList(mutableListOf(HString("last_insert_id"), HNumber(0.0)))
                    ))
                }
            } catch (e: Throwable) {
                HList(mutableListOf(
                    HList(mutableListOf(HString("success"), HBool(false))),
                    HList(mutableListOf(HString("error"), HString(e.message ?: "unknown")))
                ))
            }
        },
        "db_query" to HNative("db_query", -1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val sql = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("db_query: sql must be string")
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            try {
                val rs = conn.createStatement().executeQuery(sql)
                val cols = (1..rs.metaData.columnCount).map { rs.metaData.getColumnName(it) }
                val rows = ArrayList<HValue>()
                while (rs.next()) {
                    val row = ArrayList<HValue>()
                    for (c in cols) row.add(HList(mutableListOf(HString(c), HString(rs.getString(c) ?: ""))))
                    rows.add(HList(row))
                }
                rs.close()
                HList(mutableListOf(
                    HList(mutableListOf(HString("success"), HBool(true))),
                    HList(mutableListOf(HString("rows"), HList(rows))),
                    HList(mutableListOf(HString("columns"), HList(cols.map { HString(it) }.toMutableList()))),
                    HList(mutableListOf(HString("row_count"), HNumber(rows.size.toDouble())))
                ))
            } catch (e: Throwable) {
                HList(mutableListOf(
                    HList(mutableListOf(HString("success"), HBool(false))),
                    HList(mutableListOf(HString("error"), HString(e.message ?: "unknown"))),
                    HList(mutableListOf(HString("rows"), HList(mutableListOf()))),
                    HList(mutableListOf(HString("columns"), HList(mutableListOf()))),
                    HList(mutableListOf(HString("row_count"), HNumber(0.0)))
                ))
            }
        },
        "db_query_one" to HNative("db_query_one", -1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val sql = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("db_query_one: sql must be string")
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            try {
                val rs = conn.createStatement().executeQuery(sql)
                if (rs.next()) {
                    val cols = (1..rs.metaData.columnCount).map { rs.metaData.getColumnName(it) }
                    val row = ArrayList<HValue>()
                    for (c in cols) row.add(HList(mutableListOf(HString(c), HString(rs.getString(c) ?: ""))))
                    rs.close()
                    HList(mutableListOf(
                        HList(mutableListOf(HString("success"), HBool(true))),
                        HList(mutableListOf(HString("row"), HList(row)))
                    ))
                } else {
                    rs.close()
                    HList(mutableListOf(
                        HList(mutableListOf(HString("success"), HBool(true))),
                        HList(mutableListOf(HString("row"), HList(mutableListOf())))
                    ))
                }
            } catch (e: Throwable) {
                HList(mutableListOf(
                    HList(mutableListOf(HString("success"), HBool(false))),
                    HList(mutableListOf(HString("error"), HString(e.message ?: "unknown"))),
                    HList(mutableListOf(HString("row"), HList(mutableListOf())))
                ))
            }
        },
        "db_begin_transaction" to HNative("db_begin_transaction", 1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            conn.autoCommit = false
            HList(mutableListOf(HList(mutableListOf(HString("success"), HBool(true)))))
        },
        "db_commit" to HNative("db_commit", 1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            conn.commit()
            conn.autoCommit = true
            HList(mutableListOf(HList(mutableListOf(HString("success"), HBool(true)))))
        },
        "db_rollback" to HNative("db_rollback", 1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            conn.rollback()
            conn.autoCommit = true
            HList(mutableListOf(HList(mutableListOf(HString("success"), HBool(true)))))
        },
        "db_create_table" to HNative("db_create_table", -1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val tableName = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("db_create_table: table name must be string")
            val cols = args[2] as? HList ?: throw HSharpRuntimeError("db_create_table: columns must be a list")
            val colDefs = cols.items.joinToString(", ") { col ->
                val pair = col as? HList ?: throw HSharpRuntimeError("column must be [name, type]")
                "${(pair.items[0] as? HString)?.value ?: pair.items[0].toDisplayString()} ${(pair.items[1] as? HString)?.value ?: "TEXT"}"
            }
            val sql = "CREATE TABLE IF NOT EXISTS $tableName ($colDefs)"
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            conn.createStatement().execute(sql)
            HList(mutableListOf(HList(mutableListOf(HString("success"), HBool(true)))))
        },
        "db_drop_table" to HNative("db_drop_table", 2) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val tableName = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("db_drop_table: table name must be string")
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            conn.createStatement().execute("DROP TABLE IF EXISTS $tableName")
            HList(mutableListOf(HList(mutableListOf(HString("success"), HBool(true)))))
        },
        "db_get_tables" to HNative("db_get_tables", 1) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            val rs = conn.createStatement().executeQuery("SELECT name FROM sqlite_master WHERE type='table'")
            val tables = ArrayList<HValue>()
            while (rs.next()) tables.add(HString(rs.getString("name")))
            rs.close()
            HList(mutableListOf(
                HList(mutableListOf(HString("success"), HBool(true))),
                HList(mutableListOf(HString("tables"), HList(tables)))
            ))
        },
        "db_get_table_info" to HNative("db_get_table_info", 2) { args ->
            val id = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val tableName = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("db_get_table_info: table name must be string")
            val conn = DBConnections.get(id) ?: throw HSharpRuntimeError("Connection not found: $id")
            val rs = conn.createStatement().executeQuery("PRAGMA table_info($tableName)")
            val columns = ArrayList<HValue>()
            while (rs.next()) {
                val col = HList(mutableListOf(
                    HList(mutableListOf(HString("name"), HString(rs.getString("name") ?: ""))),
                    HList(mutableListOf(HString("type"), HString(rs.getString("type") ?: ""))),
                    HList(mutableListOf(HString("not_null"), HBool(rs.getBoolean("notnull")))),
                    HList(mutableListOf(HString("default_value"), HString(rs.getString("dflt_value") ?: ""))),
                    HList(mutableListOf(HString("primary_key"), HBool(rs.getBoolean("pk"))))
                ))
                columns.add(col)
            }
            rs.close()
            HList(mutableListOf(
                HList(mutableListOf(HString("success"), HBool(true))),
                HList(mutableListOf(HString("columns"), HList(columns)))
            ))
        },

        // ── Hash Table ──
        "htable_create" to HNative("htable_create", 0) { _ -> HDict(mutableMapOf()) },
        "htable_set" to HNative("htable_set", 3) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_set: first arg must be a dict")
            val key = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            table.entries[key] = args[2]
            table
        },
        "htable_get" to HNative("htable_get", 2) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_get: first arg must be a dict")
            val key = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            table.entries[key] ?: HNull
        },
        "htable_has" to HNative("htable_has", 2) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_has: first arg must be a dict")
            val key = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            HBool(key in table.entries)
        },
        "htable_delete" to HNative("htable_delete", 2) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_delete: first arg must be a dict")
            val key = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            HBool(table.entries.remove(key) != null)
        },
        "htable_size" to HNative("htable_size", 1) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_size: arg must be a dict")
            HNumber(table.entries.size.toDouble())
        },
        "htable_keys" to HNative("htable_keys", 1) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_keys: arg must be a dict")
            HList(table.entries.keys.map { HString(it) }.toMutableList())
        },
        "htable_values" to HNative("htable_values", 1) { args ->
            val table = args[0] as? HDict ?: throw HSharpRuntimeError("htable_values: arg must be a dict")
            HList(table.entries.values.toMutableList())
        },

        // ── Python VM builtins (not in C VM) ──
        "keys" to HNative("keys", 1) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("keys: arg must be a dict")
            HList(d.entries.keys.map { HString(it) }.toMutableList())
        },
        "values" to HNative("values", 1) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("values: arg must be a dict")
            HList(d.entries.values.toMutableList())
        },
        "items" to HNative("items", 2) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("items: arg must be a dict")
            HList(d.entries.map { (k, v) -> HList(mutableListOf(HString(k), v)) }.toMutableList())
        },
        "has_key" to HNative("has_key", 2) { args ->
            val d = args[0] as? HDict ?: throw HSharpRuntimeError("has_key: arg 0 must be a dict")
            val key = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            HBool(key in d.entries)
        },

        // ── C VM naming aliases (short names without net_ prefix) ──
        // The C VM uses short names (http_get, tcp_connect, etc.) while the
        // Kotlin VM uses the net_ prefix. These aliases ensure bytecode
        // compiled for the C VM works on the JVM without changes.
        "http_get" to HNative("http_get", -1) { args ->
            val url = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val headers = (args.getOrNull(1) as? HDict)?.entries?.mapValues { (it.value as? HString)?.value ?: it.value.toDisplayString() } ?: emptyMap()
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.requestMethod = "GET"; conn.connectTimeout = 5000; conn.readTimeout = 5000
                headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
                val body = conn.inputStream.bufferedReader().readText()
                val status = conn.responseCode; conn.disconnect()
                HDict(mutableMapOf("status" to HNumber(status.toDouble()), "body" to HString(body)))
            } catch (e: Throwable) { HDict(mutableMapOf("status" to HNumber(0.0), "body" to HString(e.message ?: ""))) }
        },
        "http_post" to HNative("http_post", -1) { args ->
            val url = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val body = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            val headers = (args.getOrNull(2) as? HDict)?.entries?.mapValues { (it.value as? HString)?.value ?: it.value.toDisplayString() } ?: emptyMap()
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.requestMethod = "POST"; conn.doOutput = true; conn.connectTimeout = 5000; conn.readTimeout = 5000
                headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
                conn.outputStream.write(body.toByteArray(Charsets.UTF_8))
                val respBody = conn.inputStream.bufferedReader().readText()
                val status = conn.responseCode; conn.disconnect()
                HDict(mutableMapOf("status" to HNumber(status.toDouble()), "body" to HString(respBody)))
            } catch (e: Throwable) { HDict(mutableMapOf("status" to HNumber(0.0), "body" to HString(e.message ?: ""))) }
        },
        "url_parse" to HNative("url_parse", 1) { args ->
            val url = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            try {
                val u = URI(url)
                HDict(mutableMapOf(
                    "scheme" to HString(u.scheme ?: ""), "host" to HString(u.host ?: ""),
                    "port" to HNumber((if (u.port >= 0) u.port else when (u.scheme) { "https" -> 443 else -> 80 }).toDouble()),
                    "path" to HString(u.path ?: ""), "query" to HString(u.query ?: ""), "fragment" to HString(u.fragment ?: "")
                ))
            } catch (e: Throwable) { HDict(mutableMapOf("error" to HString(e.message ?: ""))) }
        },
        "url_build" to HNative("url_build", 1) { args ->
            val parts = args[0] as? HDict ?: throw HSharpRuntimeError("url_build: arg must be a dict")
            val scheme = (parts.entries["scheme"] as? HString)?.value ?: "http"
            val host = (parts.entries["host"] as? HString)?.value ?: "localhost"
            val port = (parts.entries["port"] as? HNumber)?.value?.toInt() ?: -1
            val path = (parts.entries["path"] as? HString)?.value ?: ""
            val query = (parts.entries["query"] as? HString)?.value
            val fragment = (parts.entries["fragment"] as? HString)?.value
            val sb = StringBuilder("$scheme://$host")
            if (port > 0) sb.append(":$port")
            sb.append(if (path.startsWith("/")) path else "/$path")
            if (!query.isNullOrEmpty()) sb.append("?$query")
            if (!fragment.isNullOrEmpty()) sb.append("#$fragment")
            HString(sb.toString())
        },
        "tcp_connect" to HNative("tcp_connect", 2) { args ->
            val host = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("tcp_connect: host must be string")
            val port = HValueOps.toLong(args[1]).toInt()
            try {
                val sock = java.net.Socket(host, port)
                HNumber(TCPSockets.register(sock).toDouble())
            } catch (e: Throwable) { throw HSharpRuntimeError("tcp_connect: ${e.message}") }
        },
        "tcp_send" to HNative("tcp_send", 2) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val data = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            val sock = TCPSockets.get(id) ?: throw HSharpRuntimeError("tcp_send: invalid socket $id")
            sock.getOutputStream().write(data.toByteArray(Charsets.UTF_8))
            HNull
        },
        "tcp_recv" to HNative("tcp_recv", 2) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val bufsize = HValueOps.toLong(args[1]).toInt()
            val sock = TCPSockets.get(id) ?: throw HSharpRuntimeError("tcp_recv: invalid socket $id")
            val buf = ByteArray(bufsize)
            val n = sock.getInputStream().read(buf)
            HString(if (n > 0) String(buf, 0, n, Charsets.UTF_8) else "")
        },
        "tcp_close" to HNative("tcp_close", 1) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            TCPSockets.get(id)?.close()
            TCPSockets.remove(id)
            HNull
        },
        "udp_create" to HNative("udp_create", 0) {
            try {
                val sock = java.net.DatagramSocket()
                HNumber(UDPSockets.register(sock).toDouble())
            } catch (e: Throwable) { throw HSharpRuntimeError("udp_create: ${e.message}") }
        },
        "udp_send" to HNative("udp_send", 3) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val host = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("udp_send: host must be string")
            val port = HValueOps.toLong(args[2]).toInt()
            val data = (args.getOrNull(3) as? HString)?.value ?: args.getOrNull(3)?.toDisplayString() ?: ""
            val sock = UDPSockets.get(id) ?: throw HSharpRuntimeError("udp_send: invalid socket $id")
            val buf = data.toByteArray(Charsets.UTF_8)
            val packet = java.net.DatagramPacket(buf, buf.size, java.net.InetAddress.getByName(host), port)
            sock.send(packet)
            HNull
        },
        "udp_recv" to HNative("udp_recv", 2) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val bufsize = HValueOps.toLong(args[1]).toInt()
            val sock = UDPSockets.get(id) ?: throw HSharpRuntimeError("udp_recv: invalid socket $id")
            val buf = ByteArray(bufsize)
            val packet = java.net.DatagramPacket(buf, buf.size)
            sock.receive(packet)
            HString(String(packet.data, 0, packet.length, Charsets.UTF_8))
        },
        "base64_encode" to HNative("base64_encode", 1) { args ->
            val data = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HString(Base64.getEncoder().encodeToString(data.toByteArray(Charsets.UTF_8)))
        },
        "base64_decode" to HNative("base64_decode", 1) { args ->
            val data = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            try { HString(String(Base64.getDecoder().decode(data), Charsets.UTF_8)) }
            catch (e: Throwable) { throw HSharpRuntimeError("base64_decode: ${e.message}") }
        },
        "json_stringify" to HNative("json_stringify", 1) { args -> HString(args[0].toDisplayString()) },
        "json_parse" to HNative("json_parse", 1) { _ -> HList(mutableListOf()) },

        // ── DZZW parallel computation framework (stubs) ──
        // DZZW is a native parallel-computation engine in the C VM.
        // These stubs allow H# programs that reference DZZW to compile/run
        // on the JVM without crashing, returning dummy values.
        "dzzw_spawn" to HNative("dzzw_spawn", 2) { HNumber(0.0) },
        "dzzw_await" to HNative("dzzw_await", 1) { _ -> HNull },
        "dzzw_parallel_map" to HNative("dzzw_parallel_map", 2) { args ->
            HList((args[1] as? HList)?.items?.toMutableList() ?: mutableListOf())
        },
        "dzzw_worker_count" to HNative("dzzw_worker_count", 0) {
            HNumber(Runtime.getRuntime().availableProcessors().toDouble())
        },
        "dzzw_pending_count" to HNative("dzzw_pending_count", 0) { HNumber(0.0) },
        "dzzw_channel_create" to HNative("dzzw_channel_create", 0) { HNumber(0.0) },
        "dzzw_channel_send" to HNative("dzzw_channel_send", 2) { _ -> HNull },
        "dzzw_channel_recv" to HNative("dzzw_channel_recv", 1) { _ -> HNull },
        "dzzw_channel_free" to HNative("dzzw_channel_free", 1) { _ -> HNull },
        "dzzw_mutex_create" to HNative("dzzw_mutex_create", 0) { HNumber(0.0) },
        "dzzw_mutex_lock" to HNative("dzzw_mutex_lock", 1) { _ -> HNull },
        "dzzw_mutex_unlock" to HNative("dzzw_mutex_unlock", 1) { _ -> HNull },
        "dzzw_mutex_free" to HNative("dzzw_mutex_free", 1) { _ -> HNull },
        "dzzw_try_await" to HNative("dzzw_try_await", 1) { _ -> HBool(true) },
        "dzzw_await_any" to HNative("dzzw_await_any", 1) { _ -> HNull },
        "dzzw_await_all" to HNative("dzzw_await_all", 1) { _ -> HNull },
        "dzzw_total_completed" to HNative("dzzw_total_completed", 0) { HNumber(0.0) },
        "dzzw_total_submitted" to HNative("dzzw_total_submitted", 0) { HNumber(0.0) },
        "dzzw_dump_stats" to HNative("dzzw_dump_stats", 0) { HString("{}") },

        // ── zzwUI / zzw_render GUI stubs ──
        // The real C VM uses tkinter / native rendering; on the JVM we expose
        // these as deterministic no-op stubs so the *library* layer (widget
        // trees, themes, renderers, hit-testing, layout) can still be tested
        // without an X server. Each stub returns a sensible default value
        // (zero, empty list, blank string, etc.) that keeps downstream code
        // well-typed.
        "gui_create_window" to HNative("gui_create_window", 4) { args ->
            // Allocate a synthetic win_id; nothing else needs to be tracked.
            val id = GUIWindows.register(0)
            HNumber(id.toDouble())
        },
        "gui_destroy_window" to HNative("gui_destroy_window", 1) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            GUIWindows.remove(id)
            HNumber(0.0)
        },
        "gui_show_window" to HNative("gui_show_window", 1) { _ -> HNumber(0.0) },
        "gui_hide_window" to HNative("gui_hide_window", 1) { _ -> HNumber(0.0) },
        "gui_set_window_title" to HNative("gui_set_window_title", 2) { _ -> HNumber(0.0) },
        "gui_set_window_size" to HNative("gui_set_window_size", 3) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val w = HValueOps.toLong(args[1]).toInt()
            val h = HValueOps.toLong(args[2]).toInt()
            GUIWindows.setSize(id, w, h)
            HNumber(0.0)
        },
        "gui_get_window_size" to HNative("gui_get_window_size", 1) { args ->
            val id = HValueOps.toLong(args[0]).toInt()
            val (w, h) = GUIWindows.sizeOf(id)
            HList(mutableListOf(HNumber(w.toDouble()), HNumber(h.toDouble())))
        },
        "gui_clear" to HNative("gui_clear", 2) { _ -> HNumber(0.0) },
        "gui_draw_rect" to HNative("gui_draw_rect", -1) { _ -> HNumber(0.0) },
        "gui_draw_rounded_rect" to HNative("gui_draw_rounded_rect", -1) { _ -> HNumber(0.0) },
        "gui_draw_line" to HNative("gui_draw_line", -1) { _ -> HNumber(0.0) },
        "gui_draw_circle" to HNative("gui_draw_circle", -1) { _ -> HNumber(0.0) },
        "gui_draw_arc" to HNative("gui_draw_arc", -1) { _ -> HNumber(0.0) },
        "gui_draw_polygon" to HNative("gui_draw_polygon", -1) { _ -> HNumber(0.0) },
        "gui_draw_text" to HNative("gui_draw_text", -1) { _ -> HNumber(0.0) },
        "gui_draw_text_centered" to HNative("gui_draw_text_centered", -1) { _ -> HNumber(0.0) },
        "gui_measure_text" to HNative("gui_measure_text", 3) { args ->
            // Deterministic stub: width ~ chars * font_size * 0.6, height ~ font_size
            val text = (args[0] as? HString)?.value ?: ""
            val fs = if (args.size > 1) HValueOps.toLong(args[1]).toInt() else 12
            val w = (text.length * (fs * 6) / 10).coerceAtLeast(1)
            val h = (fs + 4).coerceAtLeast(8)
            HList(mutableListOf(HNumber(w.toDouble()), HNumber(h.toDouble())))
        },
        "gui_draw_image" to HNative("gui_draw_image", -1) { _ -> HNumber(0.0) },
        "gui_set_clip" to HNative("gui_set_clip", -1) { _ -> HNumber(0.0) },
        "gui_clear_clip" to HNative("gui_clear_clip", 1) { _ -> HNumber(0.0) },
        "gui_get_events" to HNative("gui_get_events", 1) { _ -> HList(mutableListOf()) },
        "gui_update" to HNative("gui_update", 1) { _ -> HNumber(0.0) },
        "gui_start_event_loop" to HNative("gui_start_event_loop", 0) { _ -> HNumber(0.0) },
        "gui_stop_event_loop" to HNative("gui_stop_event_loop", 0) { _ -> HNumber(0.0) },
        "gui_poll_events" to HNative("gui_poll_events", 0) { _ -> HNumber(0.0) },
        "gui_set_timer" to HNative("gui_set_timer", -1) { _ -> HNumber(0.0) },
        "gui_clear_timer" to HNative("gui_clear_timer", 2) { _ -> HNumber(0.0) },
        "gui_get_screen_size" to HNative("gui_get_screen_size", 0) { _ ->
            HList(mutableListOf(HNumber(1920.0), HNumber(1080.0)))
        },
        "gui_get_mouse_pos" to HNative("gui_get_mouse_pos", 0) { _ ->
            HList(mutableListOf(HNumber(0.0), HNumber(0.0)))
        },
        "gui_beep" to HNative("gui_beep", 0) { _ -> HNumber(0.0) },
        "gui_clipboard_copy" to HNative("gui_clipboard_copy", 1) { _ -> HNumber(0.0) },
        "gui_clipboard_paste" to HNative("gui_clipboard_paste", 0) { _ -> HString("") },
        "gui_parse_color" to HNative("gui_parse_color", 1) { args ->
            val s = (args[0] as? HString)?.value ?: ""
            val hex = s.removePrefix("#")
            val r = if (hex.length >= 2) hex.substring(0, 2).toInt(16) else 0
            val g = if (hex.length >= 4) hex.substring(2, 4).toInt(16) else 0
            val b = if (hex.length >= 6) hex.substring(4, 6).toInt(16) else 0
            HList(mutableListOf(HNumber(r.toDouble()), HNumber(g.toDouble()), HNumber(b.toDouble())))
        },
        "gui_color_to_hex" to HNative("gui_color_to_hex", 3) { args ->
            val r = HValueOps.toLong(args[0]).toInt().coerceIn(0, 255)
            val g = HValueOps.toLong(args[1]).toInt().coerceIn(0, 255)
            val b = HValueOps.toLong(args[2]).toInt().coerceIn(0, 255)
            HString("#%02x%02x%02x".format(r, g, b))
        },
        "gui_lerp_color" to HNative("gui_lerp_color", 3) { args ->
            val c1 = (args[0] as? HString)?.value ?: "#000000"
            val c2 = (args[1] as? HString)?.value ?: "#000000"
            val t = HValueOps.toDouble(args[2]).coerceIn(0.0, 1.0)
            fun parse(s: String): Triple<Int, Int, Int> {
                val h = s.removePrefix("#")
                return Triple(
                    if (h.length >= 2) h.substring(0, 2).toInt(16) else 0,
                    if (h.length >= 4) h.substring(2, 4).toInt(16) else 0,
                    if (h.length >= 6) h.substring(4, 6).toInt(16) else 0,
                )
            }
            val (r1, g1, b1) = parse(c1)
            val (r2, g2, b2) = parse(c2)
            val r = (r1 + (r2 - r1) * t).toInt()
            val g = (g1 + (g2 - g1) * t).toInt()
            val b = (b1 + (b2 - b1) * t).toInt()
            HString("#%02x%02x%02x".format(r, g, b))
        }
    )

    // ── Socket / DB registries ──
    private object TCPSockets {
        private val map = mutableMapOf<Int, java.net.Socket>()
        private var nextId = 1
        fun register(sock: java.net.Socket): Int = (nextId++).also { map[it] = sock }
        fun get(id: Int) = map[id]
        fun remove(id: Int) = map.remove(id)
    }
    private object UDPSockets {
        private val map = mutableMapOf<Int, java.net.DatagramSocket>()
        private var nextId = 1
        fun register(sock: java.net.DatagramSocket): Int = (nextId++).also { map[it] = sock }
        fun get(id: Int) = map[id]
    }
    private object DBConnections {
        private val map = mutableMapOf<String, Connection>()
        private var nextId = 1
        fun register(conn: Connection): String = "db_${nextId++}".also { map[it] = conn }
        fun get(id: String) = map[id]
        fun remove(id: String) = map.remove(id)
    }
    private object GUIWindows {
        // We track width/height for gui_get_window_size and use an auto-incrementing
        // id. The "size" entry is updated by gui_set_window_size (when callers
        // remember to do so); default 0x0 is fine because zzw_render just uses
        // the values the user has set on the ZzwWindow.
        private val sizes = mutableMapOf<Int, Pair<Int, Int>>()
        private var nextId = 1
        fun register(size: Int): Int = (nextId++).also { sizes[it] = size to size }
        fun remove(id: Int) { sizes.remove(id) }
        fun sizeOf(id: Int): Pair<Int, Int> = sizes[id] ?: (0 to 0)
        fun setSize(id: Int, w: Int, h: Int) { sizes[id] = w to h }
    }

    /**
     * import <python_module> — we try the JVM classpath first (if the user
     * bundles Python-style modules as text resources), then fall back to a
     * "module not found" dict so the script can probe gracefully.
     */
    fun importPython(modname: String): HDict {
        val resource = "/python_modules/$modname.hsm"
        val url = HNativeBridge::class.java.getResource(resource)
        if (url != null) {
            val text = url.readText(Charsets.UTF_8)
            return HDict(linkedMapOf<String, HValue>(
                "__source__" to HString(text),
                "name" to HString(modname)
            ).toMutableMap())
        }
        return HDict(mutableMapOf("name" to HString(modname), "available" to HBool(false)))
    }

    /**
     * import '<file>' — loads .hbc or .hto files at runtime.
     * For .hbc files, parses and runs the bytecode; for .hto, treats as string source.
     */
    fun importHFile(path: String, vm: HVM) {
        // Search paths: relative to the .hbc file's directory, then current dir, then absolute
        val searchDirs = listOfNotNull(
            vm.hbcDir?.absolutePath,
            System.getProperty("user.dir")
        )
        val searchPaths = searchDirs.flatMap { dir ->
            listOf(File(dir, path), File(dir, "$path.hbc"), File(dir, "$path.hto"))
        } + listOf(File(path), File("$path.hbc"), File("$path.hto"))
        val f = searchPaths.firstOrNull { it.exists() }
            ?: throw HSharpRuntimeError("Import file not found: $path (tried ${searchPaths.take(6).joinToString(", ")})")
        if (f.extension == "hbc" || f.path.endsWith(".hbc")) {
            try {
                val hbc = com.hsharp.compiler.HbcReader().read(f)
                for ((mname, mod) in hbc.modules) {
                    if (mname == hbc.mainModule().name) continue
                    val subVM = HVM(hbc, mname)
                    subVM.globals.putAll(vm.globals)
                    subVM.run()
                    for ((k, v) in subVM.current.env) {
                        vm.globals[k] = v
                    }
                }
                val entryVM = HVM(hbc, hbc.mainModule().name)
                entryVM.globals.putAll(vm.globals)
                entryVM.run()
                for ((k, v) in entryVM.current.env) {
                    vm.globals[k] = v
                }
                vm.globals[f.nameWithoutExtension] = HDict(vm.globals.toMutableMap())
                return
            } catch (e: Throwable) {
                vm.globals[f.nameWithoutExtension] = HString(f.readText(Charsets.UTF_8))
                return
            }
        }
        vm.globals[f.nameWithoutExtension] = HString(f.readText(Charsets.UTF_8))
    }

    private val EMPTY_FILE = com.hsharp.compiler.HbcFile(
        "v0.4", linkedMapOf("__empty__" to
            com.hsharp.compiler.HbcModule("__empty__", listOf("HALT" to null), emptyList())), 0L)
}