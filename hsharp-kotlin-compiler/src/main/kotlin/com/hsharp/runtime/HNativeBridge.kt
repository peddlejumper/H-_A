/*
 * H# native bridge
 * ----------------
 * Implements the built-in functions that H# code expects, plus a fallback
 * module-loader (which in pure-JVM mode can only read classpath resources).
 *
 * The original Python VM exposed these globals to user programs (see
 * bytecode.py:22-42 and host_functions.py). We re-implement them in Kotlin
 * so an .hbc compiled with this toolchain remains self-contained.
 */
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

    /** Convert a parsed JSON value (from [com.hsharp.compiler.MiniJson])
     *  into the equivalent H# [HValue].  Used by `json_parse`. */
    internal fun jsonToHValue(v: Any?): HValue = when (v) {
        null -> HNull
        is Boolean -> HBool(v)
        is Int -> HNumber(v.toDouble())
        is Long -> HNumber(v.toDouble())
        is Number -> HNumber(v.toDouble())
        is String -> HString(v)
        is List<*> -> HList(v.map { jsonToHValue(it) }.toMutableList())
        is Map<*, *> -> {
            val d = LinkedHashMap<String, HValue>()
            for ((k, vv) in v) d[k.toString()] = jsonToHValue(vv)
            HDict(d)
        }
        else -> HString(v.toString())
    }

    /** Module cache for importHFile: absolute file path -> module value. */
    private val loadedModules = mutableMapOf<String, HValue>()
    /** Modules currently being loaded (for circular-import detection). */
    private val loadingModules = mutableSetOf<String>()

    /** Convert a code-point index into a UTF-16 char index. */
    private fun codePointToCharIndex(s: String, cpIndex: Int): Int {
        var idx = 0
        var cp = 0
        while (idx < s.length && cp < cpIndex) {
            idx += if (s[idx].isHighSurrogate() && idx + 1 < s.length && s[idx + 1].isLowSurrogate()) 2 else 1
            cp++
        }
        return idx
    }

    /** Escape a string for embedding inside a JSON string literal. */
    private fun escapeJsonString(s: String): String {
        val sb = StringBuilder(s.length + 2)
        for (c in s) {
            when (c) {
                '"' -> sb.append("\\\"")
                '\\' -> sb.append("\\\\")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                '\b' -> sb.append("\\b")
                '\u000C' -> sb.append("\\f")
                else -> if (c.code < 0x20) sb.append("\\u%04x".format(c.code)) else sb.append(c)
            }
        }
        return sb.toString()
    }

    /** Recursively serialise an H# value to a valid JSON string. */
    private fun toJsonString(value: HValue): String = when (value) {
        HNull -> "null"
        is HBool -> if (value.value) "true" else "false"
        is HNumber -> {
            val v = value.value
            if (v == v.toLong().toDouble() && !v.isInfinite() && !v.isNaN()) v.toLong().toString() else v.toString()
        }
        is HString -> "\"" + escapeJsonString(value.value) + "\""
        is HList -> "[" + value.items.joinToString(",") { toJsonString(it) } + "]"
        is HDict -> "{" + value.entries.entries.joinToString(",") { "\"" + escapeJsonString(it.key) + "\":" + toJsonString(it.value) } + "}"
        else -> "\"" + escapeJsonString(value.toDisplayString()) + "\""
    }

    /** Generic comparison of two H# values; returns negative/zero/positive. */
    private fun compareValues(a: HValue, b: HValue): Int = when {
        a is HNumber && b is HNumber -> a.value.compareTo(b.value)
        a is HString && b is HString -> a.value.compareTo(b.value)
        a is HBool && b is HBool -> a.value.compareTo(b.value)
        else -> a.toDisplayString().compareTo(b.toDisplayString())
    }

    /** Built-in functions, callable directly from H# code. */
    val builtins: Map<String, HNative> = linkedMapOf(
        // ── Core ──
        "len" to HNative("len", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("len() requires 1 argument")
            val v = args[0]
            val n = when (v) {
                is HString -> v.value.codePointCount(0, v.value.length)
                is HList -> v.items.size
                is HDict -> v.entries.size
                else -> throw HSharpRuntimeError("len() not supported on ${v.type}")
            }
            HNumber(n.toDouble())
        },
        "push" to HNative("push", 2) { args ->
            if (args.size < 2) throw HSharpRuntimeError("push() expects 2 args, got ${args.size}")
            val arr = args[0] as? HList ?: throw HSharpRuntimeError("push() requires a list")
            arr.items.add(args[1])
            HNull
        },
        "pop" to HNative("pop", 1) { args ->
            val arr = args[0] as? HList ?: throw HSharpRuntimeError("pop() requires a list")
            if (arr.items.isEmpty()) throw HSharpRuntimeError("pop() on empty list")
            arr.items.removeAt(arr.items.size - 1)
        },

        // ── Type conversions & misc builtins ──
        "assert" to HNative("assert", 1) { args ->
            val cond = HValueOps.truthy(args[0])
            if (!cond) {
                val msg = if (args.size > 1) (args[1] as? HString)?.value ?: "assertion failed"
                          else "assertion failed"
                throw HSharpException(HString(msg))
            }
            HNull
        },
        "sum" to HNative("sum", -1) { args ->
            // Variadic: sum() == 0, sum(list) == sum of items,
            // sum(a, b, c) == a+b+c.  Builtins are looked up before
            // user functions, so this also serves `fn sum(...nums)`.
            val items: List<HValue> = if (args.size == 1 && args[0] is HList) (args[0] as HList).items else args
            var total = 0.0
            for (item in items) total += HValueOps.toDouble(item)
            HNumber(total)
        },
        "hex" to HNative("hex", 1) { args -> HString(HValueOps.toLong(args[0]).toString(16)) },
        "bin" to HNative("bin", 1) { args -> HString(HValueOps.toLong(args[0]).toString(2)) },
        "oct" to HNative("oct", 1) { args -> HString(HValueOps.toLong(args[0]).toString(8)) },
        "bool" to HNative("bool", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("bool() expects 1 arg, got 0")
            HBool(HValueOps.truthy(args[0]))
        },
        "list" to HNative("list", 1) { args ->
            if (args.isEmpty()) return@HNative HList(mutableListOf())
            when (val v = args[0]) {
                is HList -> HList(v.items.toMutableList())
                is HString -> HList(v.value.map { HString(it.toString()) }.toMutableList())
                is HDict -> HList(v.entries.keys.map { HString(it) }.toMutableList())
                else -> throw HSharpRuntimeError("list() not supported on ${v.type}")
            }
        },
        "dict" to HNative("dict", 0) { args ->
            if (args.isEmpty()) return@HNative HDict(mutableMapOf())
            val arg = args[0]
            when (arg) {
                is HDict -> HDict(arg.entries.toMutableMap())
                is HList -> {
                    val d = LinkedHashMap<String, HValue>()
                    for (item in arg.items) {
                        val pair = item as? HList ?: throw HSharpRuntimeError("dict() requires list of pairs")
                        if (pair.items.size != 2) throw HSharpRuntimeError("dict() pair must have 2 elements")
                        val key = (pair.items[0] as? HString)?.value ?: pair.items[0].toDisplayString()
                        d[key] = pair.items[1]
                    }
                    HDict(d)
                }
                else -> throw HSharpRuntimeError("dict() not supported on ${arg.type}")
            }
        },

        // ── DZZW channels ──
        // `chan_new(capacity)` is the user-facing way to create a channel.
        // A capacity of 0 means unbounded (LinkedBlockingQueue); a positive
        // capacity gives a bounded channel (ArrayBlockingQueue) that blocks
        // senders once full.  The `chan T` surface type is just a
        // documentation hint; the runtime type is HChannel.
        "chan_new" to HNative("chan_new", 1) { args ->
            val cap = HValueOps.toLong(args[0]).toInt()
            HChannel(if (cap < 0) 0 else cap)
        },
        // `chan_send(ch, v)` — push `v` onto the channel.  Blocking on a
        // bounded channel; the runtime parks the calling thread (which may
        // be a DZZW worker or the main thread) until space is available.
        "chan_send" to HNative("chan_send", 2) { args ->
            if (args.size < 2) throw HSharpRuntimeError("chan_send() expects 2 arguments, got ${args.size}")
            val ch = args[0] as? HChannel ?: throw HSharpRuntimeError("chan_send() 1st arg must be a channel")
            ch.send(args[1])
            HNull
        },
        // `chan_try_send(ch, v)` — non-blocking send.  Returns true if
        // the value was queued, false if the channel is at capacity
        // (bounded only; unbounded always succeeds).  Sends on a closed
        // channel raise.
        "chan_try_send" to HNative("chan_try_send", 2) { args ->
            if (args.size < 2) throw HSharpRuntimeError("chan_try_send() expects 2 arguments, got ${args.size}")
            val ch = args[0] as? HChannel ?: throw HSharpRuntimeError("chan_try_send() 1st arg must be a channel")
            HBool(ch.trySend(args[1]))
        },
        // `chan_recv(ch)` — pop the next value.  Blocking when the queue
        // is empty (until a sender produces one or the channel is closed
        // and drained).
        "chan_recv" to HNative("chan_recv", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("chan_recv() expects 1 argument, got 0")
            val ch = args[0] as? HChannel ?: throw HSharpRuntimeError("chan_recv() arg must be a channel")
            ch.recv()
        },
        // `chan_try_recv(ch)` — non-blocking receive.  Returns the next
        // value or HNull if the queue is empty (and the channel isn't
        // closed).  Useful for polling.
        "chan_try_recv" to HNative("chan_try_recv", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("chan_try_recv() expects 1 argument, got 0")
            val ch = args[0] as? HChannel ?: throw HSharpRuntimeError("chan_try_recv() arg must be a channel")
            ch.tryRecv() ?: HNull
        },
        // `chan_close(ch)` — mark the channel as closed.  Further sends
        // raise; receives drain and then raise.
        "chan_close" to HNative("chan_close", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("chan_close() expects 1 argument, got 0")
            val ch = args[0] as? HChannel ?: throw HSharpRuntimeError("chan_close() arg must be a channel")
            ch.close()
            HNull
        },
        // `chan_size(ch)` — number of items currently buffered.  Mostly
        // for tests and instrumentation.
        "chan_size" to HNative("chan_size", 1) { args ->
            val ch = args[0] as? HChannel ?: throw HSharpRuntimeError("chan_size() arg must be a channel")
            HNumber(ch.size().toDouble())
        },
        // `parallelism()` — how many worker threads the DZZW pool has.
        // Used by tests to confirm the pool is sized to the host cores.
        "parallelism" to HNative("parallelism", 0) { _ ->
            HNumber(WorkerPool.defaultPool().parallelism.toDouble())
        },
        // `time_ms()` — milliseconds since the epoch.  Useful in
        // benchmarks (and elsewhere) as a portable monotonic-ish clock.
        // Mirrors the existing time_now but with a clearer name.
        "time_ms" to HNative("time_ms", 0) { _ ->
            HNumber(System.currentTimeMillis().toDouble())
        },
        "read_file" to HNative("read_file", 1) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("read_file path must be string")
            try { HString(File(path).readText(Charsets.UTF_8)) }
            catch (e: java.io.IOException) { throw HSharpRuntimeError("read_file: ${e.message ?: "I/O error"}") }
        },
        "write_file" to HNative("write_file", 2) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("write_file path must be string")
            val txt = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            File(path).writeText(txt, Charsets.UTF_8)
            HNull
        },
        "str" to HNative("str", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("str() requires 1 argument")
            HString(args[0].toDisplayString())
        },
        "fmt" to HNative("fmt", -1) { args ->
            // String formatting: fmt("Hello {0}, {1}", a, b)
            // Supports {N} positional placeholders.  Any braces in the
            // format string that are not followed by a digit are left
            // as-is.  Extra arguments beyond the highest {N} are
            // ignored; missing arguments render as the literal placeholder.
            if (args.isEmpty()) return@HNative HString("")
            val format = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val rest = args.drop(1)
            val sb = StringBuilder()
            var i = 0
            while (i < format.length) {
                val c = format[i]
                if (c == '{' && i + 1 < format.length && format[i + 1].isDigit()) {
                    // Parse placeholder number
                    var j = i + 1
                    while (j < format.length && format[j].isDigit()) j++
                    if (j < format.length && format[j] == '}') {
                        val idx = format.substring(i + 1, j).toInt()
                        if (idx < rest.size) {
                            sb.append(rest[idx].toDisplayString())
                        } else {
                            sb.append(format, i, j + 1)
                        }
                        i = j + 1
                        continue
                    }
                }
                sb.append(c)
                i++
            }
            HString(sb.toString())
        },
        "int" to HNative("int", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("int() requires 1 argument")
            if (args[0] is HNull) throw HSharpRuntimeError("int() cannot convert null to number")
            HNumber(HValueOps.toDouble(args[0]).toLong().toDouble())
        },
        "float" to HNative("float", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("float() requires 1 argument")
            if (args[0] is HNull) throw HSharpRuntimeError("float() cannot convert null to number")
            HNumber(HValueOps.toDouble(args[0]))
        },
        "type" to HNative("type", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("type() requires 1 argument")
            val v = args[0]
            when (v) {
                is HInstance -> HString(v.klass?.name ?: "instance")
                is HFunction -> HString("function")
                is HChannel -> HString("channel")
                else -> HString(v.type.name.lowercase())
            }
        },
        "typeof" to HNative("typeof", 1) { args -> HString(args[0].type.name.lowercase()) },
        "input" to HNative("input", 1) { args ->
            val prompt = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            print(prompt)
            System.out.flush()
            HString(readlnOrNull() ?: "")
        },
        "abs" to HNative("abs", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("abs() requires 1 argument")
            val v = args[0]
            if (v !is HNumber) throw HSharpRuntimeError("abs() expects number, got ${v.type.name.lowercase()}")
            HNumber(abs(HValueOps.toDouble(v)))
        },
        "sqrt" to HNative("sqrt", 1) { args -> if (args.isEmpty()) throw HSharpRuntimeError("sqrt() expects 1 argument, got 0"); HNumber(Math.sqrt(HValueOps.toDouble(args[0]))) },
        "pow"  to HNative("pow", 2)  { args -> if (args.size < 2) throw HSharpRuntimeError("pow() expects 2 arguments, got ${args.size}"); HNumber(Math.pow(HValueOps.toDouble(args[0]), HValueOps.toDouble(args[1]))) },
        "sin"  to HNative("sin", 1)  { args -> HNumber(Math.sin(HValueOps.toDouble(args[0]))) },
        "cos"  to HNative("cos", 1)  { args -> HNumber(Math.cos(HValueOps.toDouble(args[0]))) },
        "tan"  to HNative("tan", 1)  { args -> HNumber(Math.tan(HValueOps.toDouble(args[0]))) },
        "atan2" to HNative("atan2", 2) { args -> HNumber(Math.atan2(HValueOps.toDouble(args[0]), HValueOps.toDouble(args[1]))) },
        "pi"   to HNative("pi", 0)   { HNumber(Math.PI) },
        "floor" to HNative("floor", 1) { args -> HNumber(Math.floor(HValueOps.toDouble(args[0]))) },
        "ceil"  to HNative("ceil", 1)  { args -> HNumber(Math.ceil(HValueOps.toDouble(args[0]))) },
        "round" to HNative("round", 1) { args -> HNumber(Math.round(HValueOps.toDouble(args[0])).toDouble()) },
        "log"   to HNative("log", 1)   { args -> HNumber(Math.log(HValueOps.toDouble(args[0]))) },
        "exp"   to HNative("exp", 1)   { args -> HNumber(Math.exp(HValueOps.toDouble(args[0]))) },
        "sgn"   to HNative("sgn", 1)   { args ->
            val v = HValueOps.toDouble(args[0])
            HNumber(if (v > 0.0) 1.0 else if (v < 0.0) -1.0 else 0.0)
        },
        "clamp" to HNative("clamp", 3) { args ->
            val v = HValueOps.toDouble(args[0])
            val lo = HValueOps.toDouble(args[1])
            val hi = HValueOps.toDouble(args[2])
            HNumber(if (v < lo) lo else if (v > hi) hi else v)
        },
        "lerp"  to HNative("lerp", 3) { args ->
            val a = HValueOps.toDouble(args[0])
            val b = HValueOps.toDouble(args[1])
            val t = HValueOps.toDouble(args[2])
            HNumber(a + (b - a) * t)
        },
        "min_num" to HNative("min_num", 2) { args -> HNumber(minOf(HValueOps.toDouble(args[0]), HValueOps.toDouble(args[1]))) },
        "max_num" to HNative("max_num", 2) { args -> HNumber(maxOf(HValueOps.toDouble(args[0]), HValueOps.toDouble(args[1]))) },
        // `fdiv(a, b)` — true float division (the BINARY_DIV
        // opcode floors; this one returns the IEEE-754 quotient
        // as-is, which is what the raytracer wants when
        // normalising vectors).
        "fdiv" to HNative("fdiv", 2) { args ->
            val a = HValueOps.toDouble(args[0])
            val b = HValueOps.toDouble(args[1])
            if (b == 0.0) throw HSharpRuntimeError("fdiv: divide by zero")
            HNumber(a / b)
        },
        "min" to HNative("min", -1) { args ->
            val items: List<HValue> = if (args.size == 1 && args[0] is HList) (args[0] as HList).items else args
            if (items.isEmpty()) throw HSharpRuntimeError("min() of empty sequence")
            var best = items[0]
            for (i in 1 until items.size) {
                if (compareValues(items[i], best) < 0) best = items[i]
            }
            best
        },
        "max" to HNative("max", -1) { args ->
            val items: List<HValue> = if (args.size == 1 && args[0] is HList) (args[0] as HList).items else args
            if (items.isEmpty()) throw HSharpRuntimeError("max() of empty sequence")
            var best = items[0]
            for (i in 1 until items.size) {
                if (compareValues(items[i], best) > 0) best = items[i]
            }
            best
        },
        "range" to HNative("range", -1) { args ->
            val items = ArrayList<HValue>()
            when (args.size) {
                1 -> for (i in 0 until HValueOps.toLong(args[0]).toInt()) items.add(HNumber(i.toDouble()))
                2 -> for (i in HValueOps.toLong(args[0]).toInt() until HValueOps.toLong(args[1]).toInt())
                    items.add(HNumber(i.toDouble()))
                3 -> {
                    val a = HValueOps.toLong(args[0]).toInt()
                    val b = HValueOps.toLong(args[1]).toInt()
                    val stepDouble = HValueOps.toDouble(args[2])
                    if (stepDouble % 1.0 != 0.0) throw HSharpRuntimeError("range() step must be integer, got $stepDouble")
                    val step = stepDouble.toLong().toInt()
                    if (step == 0) throw HSharpRuntimeError("range() step cannot be zero")
                    var i = a
                    if (step > 0) {
                        while (i < b) { items.add(HNumber(i.toDouble())); i += step }
                    } else {
                        while (i > b) { items.add(HNumber(i.toDouble())); i += step }
                    }
                }
                else -> throw HSharpRuntimeError("range() takes 1, 2, or 3 args")
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
            if (args.size < 3) throw HSharpRuntimeError("substring() expects 3 arguments, got ${args.size}")
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val cpStart = HValueOps.toLong(args[1]).toInt().coerceIn(0, s.codePointCount(0, s.length))
            val cpLen = HValueOps.toLong(args[2]).toInt()
            if (cpLen < 0) throw HSharpRuntimeError("substring length must be non-negative: $cpLen")
            val charStart = codePointToCharIndex(s, cpStart)
            val charEnd = codePointToCharIndex(s, cpStart + cpLen).coerceAtMost(s.length)
            HString(if (charStart > charEnd) "" else s.substring(charStart, charEnd))
        },
        "ord" to HNative("ord", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("ord() requires 1 argument")
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            if (s.isEmpty()) throw HSharpRuntimeError("ord() expected a non-empty character string")
            if (s.length > 1 && !s[0].isSurrogate()) throw HSharpRuntimeError("ord() expected a single character, got string of length ${s.length}")
            HNumber(s.codePointAt(0).toDouble())
        },
        "chr" to HNative("chr", 1) { args ->
            if (args.isEmpty()) throw HSharpRuntimeError("chr() requires 1 argument")
            val cp = HValueOps.toLong(args[0]).toInt()
            if (cp < 0 || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) throw HSharpRuntimeError("chr() argument out of range: $cp")
            HString(Character.toChars(cp).concatToString())
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

        // ── Path / FS additions (v0.4.1) ─────────────────────────
        "path_separator" to HNative("path_separator", 0) { _ ->
            HString(File.separator)
        },
        "path_list_separator" to HNative("path_list_separator", 0) { _ ->
            HString(File.pathSeparator)
        },
        "path_is_absolute" to HNative("path_is_absolute", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HBool(File(p).isAbsolute)
        },
        "path_normalize" to HNative("path_normalize", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HString(File(p).normalize().path)
        },
        "path_split" to HNative("path_split", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val f = File(p)
            HList(mutableListOf(
                HString(f.parent ?: ""),
                HString(f.name)
            ))
        },
        "path_components" to HNative("path_components", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val parts = File(p).normalize().path.split(File.separatorChar)
                .filter { it.isNotEmpty() }
            HList(parts.map { HString(it) }.toMutableList())
        },
        "file_size" to HNative("file_size", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HNumber(File(p).length().toDouble())
        },
        "file_mtime" to HNative("file_mtime", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HNumber(File(p).lastModified().toDouble())
        },
        "file_atime" to HNative("file_atime", 1) { args ->
            // Java's File doesn't expose atime; use ctime as a best-effort.
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HNumber(File(p).lastModified().toDouble())
        },
        "file_delete" to HNative("file_delete", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            File(p).delete()
            HNull
        },
        "file_info" to HNative("file_info", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val f = File(p)
            if (!f.exists()) HNull
            else HDict(linkedMapOf<String, HValue>(
                "path" to HString(f.path),
                "size" to HNumber(f.length().toDouble()),
                "is_dir" to HBool(f.isDirectory),
                "is_file" to HBool(f.isFile),
                "mtime" to HNumber(f.lastModified().toDouble())
            ).toMutableMap())
        },
        "file_read_bytes" to HNative("file_read_bytes", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val bytes = File(p).readBytes()
            HList(bytes.map { HNumber((it.toInt() and 0xFF).toDouble()) }.toMutableList())
        },
        "temp_file" to HNative("temp_file", 1) { args ->
            val prefix = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val f = File.createTempFile(prefix, ".tmp")
            f.deleteOnExit()
            HString(f.absolutePath)
        },
        "file_is_readable" to HNative("file_is_readable", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HBool(File(p).canRead())
        },
        "file_is_writable" to HNative("file_is_writable", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HBool(File(p).canWrite())
        },
        "file_rename" to HNative("file_rename", 2) { args ->
            val src = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("rename: src must be string")
            val dst = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("rename: dst must be string")
            val ok = File(src).renameTo(File(dst))
            if (!ok) throw HSharpRuntimeError("rename failed: $src -> $dst")
            HNull
        },
        "file_copy" to HNative("file_copy", 2) { args ->
            val src = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("copy: src must be string")
            val dst = (args[1] as? HString)?.value ?: throw HSharpRuntimeError("copy: dst must be string")
            File(src).copyTo(File(dst), overwrite = true)
            HNull
        },
        "file_remove_recursive" to HNative("file_remove_recursive", 1) { args ->
            val p = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            fun rm(f: File): Boolean {
                if (f.isDirectory) {
                    f.listFiles()?.forEach { if (!rm(it)) return false }
                }
                return f.delete()
            }
            rm(File(p))
            HNull
        },
        "fs_walk" to HNative("fs_walk", 1) { args ->
            val root = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val out = mutableListOf<HValue>()
            fun walk(f: File) {
                if (f.isFile) {
                    out.add(HString(f.path))
                } else if (f.isDirectory) {
                    f.listFiles()?.forEach { walk(it) }
                }
            }
            walk(File(root))
            HList(out)
        },

        // ── Regex (v0.4.1) ─────────────────────────────────────
        // The regex_match native (and all the others) construct a
        // java.util.regex.Pattern from the pattern string.  An
        // invalid pattern throws PatternSyntaxException; we want
        // that to surface as an H# exception (caller-try/catchable)
        // rather than crash the VM, so we wrap the construction
        // in a try/catch and rethrow as HSharpRuntimeError.
        "regex_match" to HNative("regex_match", 2) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_match: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_match: text must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            HBool(r.containsMatchIn(text))
        },
        "regex_search" to HNative("regex_search", 2) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_search: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_search: text must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            val m = r.find(text)
            HString(m?.value ?: "")
        },
        "regex_find_all" to HNative("regex_find_all", 2) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_find_all: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_find_all: text must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            HList(r.findAll(text).map { HString(it.value) }.toMutableList())
        },
        "regex_replace" to HNative("regex_replace", 3) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_replace: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_replace: text must be string")
            val repl = (args[2] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_replace: replacement must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            HString(r.replace(text, repl))
        },
        "regex_split" to HNative("regex_split", 2) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_split: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_split: text must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            HList(r.split(text).map { HString(it) }.toMutableList())
        },
        "regex_groups" to HNative("regex_groups", 2) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_groups: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_groups: text must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            val m = r.find(text)
            if (m == null) {
                HList(mutableListOf())
            } else {
                val out = mutableListOf<HValue>()
                for (i in 0 until m.groups.size) {
                    out.add(HString(m.groups[i]?.value ?: ""))
                }
                HList(out)
            }
        },
        "regex_named_groups" to HNative("regex_named_groups", 2) { args ->
            val pat = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_named_groups: pattern must be string")
            val text = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("regex_named_groups: text must be string")
            val r = try {
                Regex(pat)
            } catch (e: java.util.regex.PatternSyntaxException) {
                throw HSharpRuntimeError("invalid regex: ${e.message}")
            }
            val m = r.find(text)
            if (m == null) {
                return@HNative HDict(linkedMapOf())
            }
            val d = linkedMapOf<String, HValue>()
            // Iterate groups by index; pick out any whose name
            // is non-null (named capture groups).  We use the
            // pattern's groupNames to find the names; this is
            // the most portable way across Kotlin versions.
            val groupNames = r.pattern
                .let { p ->
                    val names = mutableListOf<String?>()
                    // Build the list of group names by scanning
                    // for "(?<name>..." patterns.
                    var i = 0
                    while (i < p.length) {
                        if (p[i] == '(' && i + 2 < p.length && p[i + 1] == '?') {
                            if (i + 3 < p.length && p[i + 2] == '<') {
                                val end = p.indexOf('>', i + 3)
                                if (end > i) {
                                    names.add(p.substring(i + 3, end))
                                    i = end + 1
                                    continue
                                }
                            }
                        }
                        i = i + 1
                    }
                    names
                }
            for (i in 0 until m.groups.size) {
                val name = if (i >= 1 && i - 1 < groupNames.size) groupNames[i - 1] else null
                if (name != null) {
                    d[name] = HString(m.groups[i]?.value ?: "")
                }
            }
            HDict(d)
        },

        // ── Crypto (v0.4.1) ────────────────────────────────────
        "crypto_sha256" to HNative("crypto_sha256", 1) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val md = java.security.MessageDigest.getInstance("SHA-256")
            val bytes = md.digest(s.toByteArray(Charsets.UTF_8))
            HString(bytes.joinToString("") { "%02x".format(it) })
        },
        "crypto_hmac_sha256" to HNative("crypto_hmac_sha256", 2) { args ->
            val key = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("hmac_sha256: key must be string")
            val msg = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("hmac_sha256: msg must be string")
            val mac = javax.crypto.Mac.getInstance("HmacSHA256")
            mac.init(javax.crypto.spec.SecretKeySpec(
                key.toByteArray(Charsets.UTF_8), "HmacSHA256"))
            val bytes = mac.doFinal(msg.toByteArray(Charsets.UTF_8))
            HString(bytes.joinToString("") { "%02x".format(it) })
        },
        "crypto_random_bytes" to HNative("crypto_random_bytes", 1) { args ->
            val n = HValueOps.toDouble(args[0]).toInt()
            val rng = java.security.SecureRandom()
            val bytes = ByteArray(n)
            rng.nextBytes(bytes)
            HString(bytes.joinToString("") { "%02x".format(it) })
        },
        "crypto_random_int" to HNative("crypto_random_int", 2) { args ->
            val lo = HValueOps.toDouble(args[0]).toLong()
            val hi = HValueOps.toDouble(args[1]).toLong()
            val rng = java.security.SecureRandom()
            val v = lo + (Math.abs(rng.nextLong()) % (hi - lo + 1))
            HNumber(v.toDouble())
        },
        "crypto_secure_eq" to HNative("crypto_secure_eq", 2) { args ->
            val a = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val b = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            // Constant-time comparison.  We pad the shorter
            // string to the length of the longer so the
            // length is not a side channel.
            val ab = a.toByteArray(Charsets.UTF_8)
            val bb = b.toByteArray(Charsets.UTF_8)
            if (ab.size != bb.size) {
                HBool(false)
            } else {
                var diff = 0
                for (i in ab.indices) {
                    diff = diff or (ab[i].toInt() xor bb[i].toInt())
                }
                HBool(diff == 0)
            }
        },
        "crypto_crc32" to HNative("crypto_crc32", 1) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            val crc = java.util.zip.CRC32()
            crc.update(s.toByteArray(Charsets.UTF_8))
            HNumber(crc.value.toDouble())
        },
        "crypto_base32_encode" to HNative("crypto_base32_encode", 1) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            HString(java.util.Base64.getEncoder().encodeToString(
                s.toByteArray(Charsets.UTF_8)))
        },
        "crypto_base32_decode" to HNative("crypto_base32_decode", 1) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            try { HString(String(java.util.Base64.getDecoder().decode(s), Charsets.UTF_8)) }
            catch (e: IllegalArgumentException) { throw HSharpRuntimeError("crypto_base32_decode: invalid base32 input") }
        },
        "crypto_pbkdf2" to HNative("crypto_pbkdf2", 4) { args ->
            val password = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("pbkdf2: password must be string")
            val salt = (args[1] as? HString)?.value
                ?: throw HSharpRuntimeError("pbkdf2: salt must be string")
            val iter = HValueOps.toDouble(args[2]).toInt()
            val keylen = HValueOps.toDouble(args[3]).toInt()
            val factory = javax.crypto.SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            val spec = javax.crypto.spec.PBEKeySpec(
                password.toCharArray(),
                salt.toByteArray(Charsets.UTF_8),
                iter, keylen * 8)
            val key = factory.generateSecret(spec).encoded
            HString(key.joinToString("") { "%02x".format(it) })
        },

        // ── IO ──
        "io_append_file" to HNative("io_append_file", 2) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("append_file: path must be string")
            val content = (args[1] as? HString)?.value ?: args[1].toDisplayString()
            File(path).appendText(content, Charsets.UTF_8)
            HNull
        },
        // `io_append_bytes(path, bytes)` — append raw bytes
        // (each element 0..255) to the file.  Used by the
        // raytracer pipeline to write a PPM image without going
        // through UTF-8.
        "io_append_bytes" to HNative("io_append_bytes", 2) { args ->
            val path = (args[0] as? HString)?.value ?: throw HSharpRuntimeError("append_bytes: path must be string")
            val list = args[1] as? HList ?: throw HSharpRuntimeError("append_bytes: bytes must be a list")
            val bytes = ByteArray(list.items.size)
            for (i in list.items.indices) {
                val v = HValueOps.toDouble(list.items[i]).toInt()
                bytes[i] = if (v < 0) 0.toByte() else if (v > 255) 255.toByte() else v.toByte()
            }
            File(path).appendBytes(bytes)
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
            HString(toJsonString(args[0]))
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
        "json_stringify" to HNative("json_stringify", 1) { args -> HString(toJsonString(args[0])) },
        "json_parse" to HNative("json_parse", 1) { args ->
            val s = (args[0] as? HString)?.value ?: args[0].toDisplayString()
            try {
                val parsed = com.hsharp.compiler.MiniJson(s).parseValue()
                HNativeBridge.jsonToHValue(parsed)
            } catch (e: Throwable) {
                throw HSharpRuntimeError("json_parse: ${e.message ?: "invalid JSON"}")
            }
        },

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
            fun hex2(i: Int): Int = if (hex.length >= i + 2) {
                try { hex.substring(i, i + 2).toInt(16) } catch (_: NumberFormatException) { 0 }
            } else 0
            HList(mutableListOf(HNumber(hex2(0).toDouble()), HNumber(hex2(2).toDouble()), HNumber(hex2(4).toDouble())))
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
        },
        // `gui_show_image(title, w, h, rgb_bytes)` — open a real
        // Swing JFrame on the event-dispatch thread and display
        // the rendered image.  The frame auto-scales the image
        // to fit (preserving aspect ratio) using nearest-neighbor
        // for crisp pixel art, bilinear for large upscales.  The
        // call blocks on a CountDownLatch until the user closes
        // the window.
        // `gui_render_to_png(path, w, h, rgb_bytes)` —
        // decodes the rgb_bytes exactly the same way
        // gui_show_image_fullscreen does and writes a PNG
        // to `path` (no display).  Useful for headless
        // debugging of "what does the JFrame actually see".
        "gui_render_to_png" to HNative("gui_render_to_png", 4) { args ->
            val path = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("gui_render_to_png: path must be a string")
            val w = HValueOps.toLong(args[1]).toInt().coerceAtLeast(1)
            val h = HValueOps.toLong(args[2]).toInt().coerceAtLeast(1)
            val list = args[3] as? HList
                ?: throw HSharpRuntimeError("gui_render_to_png: bytes must be a list")
            val expected = w * h * 3
            if (list.items.size < expected) {
                throw HSharpRuntimeError(
                    "gui_render_to_png: got ${list.items.size} bytes, need $expected"
                )
            }
            val img = java.awt.image.BufferedImage(w, h, java.awt.image.BufferedImage.TYPE_INT_RGB)
            var i = 0
            var p = 0
            while (i < w * h) {
                val r = HValueOps.toLong(list.items[p]).toInt() and 0xFF
                val g = HValueOps.toLong(list.items[p + 1]).toInt() and 0xFF
                val b = HValueOps.toLong(list.items[p + 2]).toInt() and 0xFF
                img.setRGB(i % w, i / w, (r shl 16) or (g shl 8) or b)
                i = i + 1
                p = p + 3
            }
            javax.imageio.ImageIO.write(img, "png", java.io.File(path))
            HString("ok:" + path)
        },
        "gui_show_image" to HNative("gui_show_image", 4) { args ->
            val title = (args[0] as? HString)?.value ?: "H# Image"
            val w = HValueOps.toLong(args[1]).toInt().coerceAtLeast(1)
            val h = HValueOps.toLong(args[2]).toInt().coerceAtLeast(1)
            val list = args[3] as? HList
                ?: throw HSharpRuntimeError("gui_show_image: bytes must be a list")
            val expected = w * h * 3
            if (list.items.size < expected) {
                throw HSharpRuntimeError(
                    "gui_show_image: got ${list.items.size} bytes, need $expected"
                )
            }
            val img = java.awt.image.BufferedImage(w, h, java.awt.image.BufferedImage.TYPE_INT_RGB)
            var i = 0
            var p = 0
            while (i < w * h) {
                val r = HValueOps.toLong(list.items[p]).toInt() and 0xFF
                val g = HValueOps.toLong(list.items[p + 1]).toInt() and 0xFF
                val b = HValueOps.toLong(list.items[p + 2]).toInt() and 0xFF
                img.setRGB(i % w, i / w, (r shl 16) or (g shl 8) or b)
                i = i + 1
                p = p + 3
            }
            val latch = java.util.concurrent.CountDownLatch(1)
            val frameRef = arrayOfNulls<javax.swing.JFrame>(1)
            javax.swing.SwingUtilities.invokeAndWait {
                val frame = javax.swing.JFrame(title)
                frame.defaultCloseOperation = javax.swing.JFrame.DISPOSE_ON_CLOSE
                val panel = object : javax.swing.JPanel() {
                    // Pre-scale the image to a known good size at
                    // construction time so paintComponent can
                    // never be called with a 0×0 panel or a
                    // half-laid-out panel.  This is the bug we
                    // were chasing: on some macOS / Java combos
                    // paintComponent runs with width/height that
                    // don't match the screen, and the centred
                    // drawImage call ends up painting a sliver
                    // — looking like a coloured bar.
                    private val scaled =
                        java.awt.image.BufferedImage(w * 4, h * 4,
                            java.awt.image.BufferedImage.TYPE_INT_RGB)
                    init {
                        val sg = scaled.createGraphics()
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_RENDERING,
                            java.awt.RenderingHints.VALUE_RENDER_QUALITY
                        )
                        sg.drawImage(img, 0, 0, w * 4, h * 4, null)
                        sg.dispose()
                    }
                    override fun getPreferredSize(): java.awt.Dimension =
                        java.awt.Dimension(w * 4, h * 4)
                    override fun paintComponent(g: java.awt.Graphics) {
                        super.paintComponent(g)
                        val g2 = g as java.awt.Graphics2D
                        g2.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        g2.setColor(java.awt.Color.BLACK)
                        g2.fillRect(0, 0, width, height)
                        // Always paint at the image's native
                        // 4× size, top-left aligned.  The
                        // JPanel's preferred size is w*4 × h*4,
                        // so frame.pack() will give us a window
                        // that's exactly the right size.  This
                        // avoids any layout/race-condition where
                        // the panel is drawn before it knows its
                        // own dimensions.
                        g2.drawImage(scaled, 0, 0, null)
                    }
                }
                panel.background = java.awt.Color(20, 20, 30)
                frame.contentPane.add(panel)
                frame.pack()
                frame.setLocationRelativeTo(null)
                frame.isVisible = true
                frameRef[0] = frame
                frame.addWindowListener(object : java.awt.event.WindowAdapter() {
                    override fun windowClosing(e: java.awt.event.WindowEvent) {
                        latch.countDown()
                    }
                    override fun windowClosed(e: java.awt.event.WindowEvent) {
                        latch.countDown()
                    }
                })
            }
            // Cap how long we block so a headless CI run doesn't hang forever.
            latch.await(180, java.util.concurrent.TimeUnit.SECONDS)
            frameRef[0]?.dispose()
            HNull
        },
        // `gui_show_image_fullscreen(title, w, h, rgb_bytes)` —
        // like gui_show_image, but goes into true exclusive
        // fullscreen using the default GraphicsDevice.  The
        // user can press Escape (or close the window via the
        // standard close affordance) to return.  The call
        // blocks on a CountDownLatch.
        "gui_show_image_fullscreen" to HNative("gui_show_image_fullscreen", 4) { args ->
            val title = (args[0] as? HString)?.value ?: "H# Image"
            val w = HValueOps.toLong(args[1]).toInt().coerceAtLeast(1)
            val h = HValueOps.toLong(args[2]).toInt().coerceAtLeast(1)
            val list = args[3] as? HList
                ?: throw HSharpRuntimeError("gui_show_image_fullscreen: bytes must be a list")
            val expected = w * h * 3
            if (list.items.size < expected) {
                throw HSharpRuntimeError(
                    "gui_show_image_fullscreen: got ${list.items.size} bytes, need $expected"
                )
            }
            val img = java.awt.image.BufferedImage(w, h, java.awt.image.BufferedImage.TYPE_INT_RGB)
            var i = 0
            var p = 0
            while (i < w * h) {
                val r = HValueOps.toLong(list.items[p]).toInt() and 0xFF
                val g = HValueOps.toLong(list.items[p + 1]).toInt() and 0xFF
                val b = HValueOps.toLong(list.items[p + 2]).toInt() and 0xFF
                img.setRGB(i % w, i / w, (r shl 16) or (g shl 8) or b)
                i = i + 1
                p = p + 3
            }
            val latch = java.util.concurrent.CountDownLatch(1)
            val frameRef = arrayOfNulls<javax.swing.JFrame>(1)
            val deviceRef = arrayOfNulls<java.awt.GraphicsDevice>(1)
            javax.swing.SwingUtilities.invokeAndWait {
                val gs = java.awt.GraphicsEnvironment.getLocalGraphicsEnvironment()
                val device = gs.defaultScreenDevice
                deviceRef[0] = device
                val frame = javax.swing.JFrame(title)
                frame.defaultCloseOperation = javax.swing.JFrame.DISPOSE_ON_CLOSE
                frame.isUndecorated = true
                val panel = object : javax.swing.JPanel() {
                    // Pre-scale to 4× at construction so paintComponent
                    // is never called with a not-yet-laid-out panel.
                    // Then in fullscreen, stretch the pre-scaled image
                    // to fill the screen while preserving aspect ratio.
                    private val scaled =
                        java.awt.image.BufferedImage(w * 4, h * 4,
                            java.awt.image.BufferedImage.TYPE_INT_RGB)
                    init {
                        val sg = scaled.createGraphics()
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_RENDERING,
                            java.awt.RenderingHints.VALUE_RENDER_QUALITY
                        )
                        sg.drawImage(img, 0, 0, w * 4, h * 4, null)
                        sg.dispose()
                    }
                    override fun paintComponent(g: java.awt.Graphics) {
                        super.paintComponent(g)
                        val panelW = width
                        val panelH = height
                        if (panelW <= 0 || panelH <= 0) return
                        val g2 = g as java.awt.Graphics2D
                        g2.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        g2.setColor(java.awt.Color(0, 0, 0))
                        g2.fillRect(0, 0, panelW, panelH)
                        val scale = kotlin.math.min(panelW / (w * 4), panelH / (h * 4)).coerceAtLeast(1)
                        val drawW = (w * 4) * scale
                        val drawH = (h * 4) * scale
                        val ox = (panelW - drawW) / 2
                        val oy = (panelH - drawH) / 2
                        g2.drawImage(scaled, ox, oy, drawW, drawH, null)
                        g2.color = java.awt.Color(180, 180, 200)
                        g2.font = java.awt.Font("SansSerif", java.awt.Font.PLAIN, 24)
                        g2.drawString(title, 32, 48)
                        g2.drawString(
                            "press Esc to exit  ·  " + w + "x" + h,
                            32, panelH - 32
                        )
                    }
                }
                panel.background = java.awt.Color(0, 0, 0)
                frame.contentPane.add(panel)
                frame.setFocusable(true)
                device.setFullScreenWindow(frame)
                frameRef[0] = frame
                frame.addKeyListener(object : java.awt.event.KeyAdapter() {
                    override fun keyPressed(e: java.awt.event.KeyEvent) {
                        if (e.keyCode == java.awt.event.KeyEvent.VK_ESCAPE) {
                            latch.countDown()
                        }
                    }
                })
                frame.addWindowListener(object : java.awt.event.WindowAdapter() {
                    override fun windowClosing(e: java.awt.event.WindowEvent) {
                        latch.countDown()
                    }
                    override fun windowClosed(e: java.awt.event.WindowEvent) {
                        latch.countDown()
                    }
                })
            }
            latch.await(180, java.util.concurrent.TimeUnit.SECONDS)
            javax.swing.SwingUtilities.invokeAndWait {
                deviceRef[0]?.setFullScreenWindow(null)
                frameRef[0]?.dispose()
            }
            HNull
        },
        // `gui_show_image_fullscreen_debug(title, w, h, rgb_bytes, out_png)`
        // — same as gui_show_image_fullscreen but exits 800ms
        // after painting, after saving a screen-capture of the
        // fullscreen frame to `out_png` via java.awt.Robot.  This
        // lets us verify what the JFrame actually rendered
        // without needing a human at the keyboard.
        "gui_show_image_fullscreen_debug" to HNative("gui_show_image_fullscreen_debug", 5) { args ->
            val title = (args[0] as? HString)?.value ?: "H# Image"
            val w = HValueOps.toLong(args[1]).toInt().coerceAtLeast(1)
            val h = HValueOps.toLong(args[2]).toInt().coerceAtLeast(1)
            val list = args[3] as? HList
                ?: throw HSharpRuntimeError("gui_show_image_fullscreen_debug: bytes must be a list")
            val outPng = (args[4] as? HString)?.value
                ?: throw HSharpRuntimeError("gui_show_image_fullscreen_debug: out_png must be a string")
            val expected = w * h * 3
            if (list.items.size < expected) {
                throw HSharpRuntimeError(
                    "gui_show_image_fullscreen_debug: got ${list.items.size} bytes, need $expected"
                )
            }
            val img = java.awt.image.BufferedImage(w, h, java.awt.image.BufferedImage.TYPE_INT_RGB)
            var i = 0
            var p = 0
            while (i < w * h) {
                val r = HValueOps.toLong(list.items[p]).toInt() and 0xFF
                val g = HValueOps.toLong(list.items[p + 1]).toInt() and 0xFF
                val b = HValueOps.toLong(list.items[p + 2]).toInt() and 0xFF
                img.setRGB(i % w, i / w, (r shl 16) or (g shl 8) or b)
                i = i + 1
                p = p + 3
            }
            val frameRef = arrayOfNulls<javax.swing.JFrame>(1)
            val deviceRef = arrayOfNulls<java.awt.GraphicsDevice>(1)
            javax.swing.SwingUtilities.invokeAndWait {
                val gs = java.awt.GraphicsEnvironment.getLocalGraphicsEnvironment()
                val device = gs.defaultScreenDevice
                deviceRef[0] = device
                val frame = javax.swing.JFrame(title)
                frame.defaultCloseOperation = javax.swing.JFrame.DISPOSE_ON_CLOSE
                frame.isUndecorated = true
                val panel = object : javax.swing.JPanel() {
                    private val scaled =
                        java.awt.image.BufferedImage(w * 4, h * 4,
                            java.awt.image.BufferedImage.TYPE_INT_RGB)
                    init {
                        val sg = scaled.createGraphics()
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_RENDERING,
                            java.awt.RenderingHints.VALUE_RENDER_QUALITY
                        )
                        sg.drawImage(img, 0, 0, w * 4, h * 4, null)
                        sg.dispose()
                    }
                    override fun paintComponent(g: java.awt.Graphics) {
                        super.paintComponent(g)
                        val panelW = width
                        val panelH = height
                        if (panelW <= 0 || panelH <= 0) return
                        val g2 = g as java.awt.Graphics2D
                        g2.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        g2.setColor(java.awt.Color(0, 0, 0))
                        g2.fillRect(0, 0, panelW, panelH)
                        val scale = kotlin.math.min(panelW / (w * 4), panelH / (h * 4)).coerceAtLeast(1)
                        val drawW = (w * 4) * scale
                        val drawH = (h * 4) * scale
                        val ox = (panelW - drawW) / 2
                        val oy = (panelH - drawH) / 2
                        g2.drawImage(scaled, ox, oy, drawW, drawH, null)
                        g2.color = java.awt.Color(180, 180, 200)
                        g2.font = java.awt.Font("SansSerif", java.awt.Font.PLAIN, 24)
                        g2.drawString(title, 32, 48)
                        g2.drawString(
                            "press Esc to exit  ·  " + w + "x" + h,
                            32, panelH - 32
                        )
                    }
                }
                panel.background = java.awt.Color(0, 0, 0)
                frame.contentPane.add(panel)
                frame.setFocusable(true)
                device.setFullScreenWindow(frame)
                frameRef[0] = frame
            }
            // Give the Swing repaint a moment, then screenshot the
            // entire screen via java.awt.Robot.  This is exactly
            // what the user is seeing on their display.
            Thread.sleep(800)
            try {
                val robot = java.awt.Robot()
                val screen = java.awt.Toolkit.getDefaultToolkit().screenSize
                val shot = robot.createScreenCapture(
                    java.awt.Rectangle(0, 0, screen.width, screen.height)
                )
                javax.imageio.ImageIO.write(shot, "png", java.io.File(outPng))
            } catch (e: Throwable) {
                System.err.println("fullscreen_debug: screenshot failed: " + e)
            }
            javax.swing.SwingUtilities.invokeAndWait {
                deviceRef[0]?.setFullScreenWindow(null)
                frameRef[0]?.dispose()
            }
            HNull
        },
        // `gui_start_recording(out_dir, fps)` — start a
        // background thread that uses java.awt.Robot to
        // capture the entire screen at `fps` frames per
        // second, writing `frame_NNNNNN.png` files to
        // `out_dir`.  The thread runs until
        // `gui_stop_recording` is called.  Returns the
        // directory the frames are being written to.
        "gui_start_recording" to HNative("gui_start_recording", 2) { args ->
            val outDir = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("gui_start_recording: out_dir must be a string")
            val fps = HValueOps.toLong(args[1]).toInt().coerceAtLeast(1)
            ScreenRecorder.start(outDir, fps)
            HString(outDir)
        },
        // `gui_stop_recording()` — stop the recording
        // thread started by gui_start_recording and
        // return the number of frames captured.  The
        // captured frames are still on disk and can be
        // post-processed (e.g. encoded to gif / mp4 by
        // an external tool).
        "gui_stop_recording" to HNative("gui_stop_recording", 0) { args ->
            HNumber(ScreenRecorder.stop().toDouble())
        },
        // `gui_capture_fullscreen(out_png)` — synchronous
        // full-screen capture (no display needed).  Useful
        // for grabbing a still frame for the README.
        "gui_capture_fullscreen" to HNative("gui_capture_fullscreen", 1) { args ->
            val outPng = (args[0] as? HString)?.value
                ?: throw HSharpRuntimeError("gui_capture_fullscreen: out_png must be a string")
            try {
                val robot = java.awt.Robot()
                val screen = java.awt.Toolkit.getDefaultToolkit().screenSize
                val shot = robot.createScreenCapture(
                    java.awt.Rectangle(0, 0, screen.width, screen.height)
                )
                javax.imageio.ImageIO.write(shot, "png", java.io.File(outPng))
                HString("ok:" + outPng)
            } catch (e: Throwable) {
                throw HSharpRuntimeError("gui_capture_fullscreen failed: " + e)
            }
        },
        // `gui_show_image_timed(title, w, h, bytes, timeout_ms)` —
        // like gui_show_image, but auto-closes after
        // `timeout_ms` milliseconds (or sooner if the user
        // closes manually).  Used by the recording demo so
        // we can run unattended.
        "gui_show_image_timed" to HNative("gui_show_image_timed", 5) { args ->
            val title = (args[0] as? HString)?.value ?: "H# Image"
            val w = HValueOps.toLong(args[1]).toInt().coerceAtLeast(1)
            val h = HValueOps.toLong(args[2]).toInt().coerceAtLeast(1)
            val list = args[3] as? HList
                ?: throw HSharpRuntimeError("gui_show_image_timed: bytes must be a list")
            val timeoutMs = HValueOps.toLong(args[4]).toLong().coerceAtLeast(0)
            val expected = w * h * 3
            if (list.items.size < expected) {
                throw HSharpRuntimeError(
                    "gui_show_image_timed: got ${list.items.size} bytes, need $expected"
                )
            }
            val img = java.awt.image.BufferedImage(w, h, java.awt.image.BufferedImage.TYPE_INT_RGB)
            var i = 0
            var p = 0
            while (i < w * h) {
                val r = HValueOps.toLong(list.items[p]).toInt() and 0xFF
                val g = HValueOps.toLong(list.items[p + 1]).toInt() and 0xFF
                val b = HValueOps.toLong(list.items[p + 2]).toInt() and 0xFF
                img.setRGB(i % w, i / w, (r shl 16) or (g shl 8) or b)
                i = i + 1
                p = p + 3
            }
            val latch = java.util.concurrent.CountDownLatch(1)
            val frameRef = arrayOfNulls<javax.swing.JFrame>(1)
            javax.swing.SwingUtilities.invokeAndWait {
                val frame = javax.swing.JFrame(title)
                frame.defaultCloseOperation = javax.swing.JFrame.DISPOSE_ON_CLOSE
                val panel = object : javax.swing.JPanel() {
                    private val scaled =
                        java.awt.image.BufferedImage(w * 4, h * 4,
                            java.awt.image.BufferedImage.TYPE_INT_RGB)
                    init {
                        val sg = scaled.createGraphics()
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        sg.setRenderingHint(
                            java.awt.RenderingHints.KEY_RENDERING,
                            java.awt.RenderingHints.VALUE_RENDER_QUALITY
                        )
                        sg.drawImage(img, 0, 0, w * 4, h * 4, null)
                        sg.dispose()
                    }
                    override fun getPreferredSize(): java.awt.Dimension =
                        java.awt.Dimension(w * 4, h * 4)
                    override fun paintComponent(g: java.awt.Graphics) {
                        super.paintComponent(g)
                        val g2 = g as java.awt.Graphics2D
                        g2.setRenderingHint(
                            java.awt.RenderingHints.KEY_INTERPOLATION,
                            java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR
                        )
                        g2.setColor(java.awt.Color.BLACK)
                        g2.fillRect(0, 0, width, height)
                        g2.drawImage(scaled, 0, 0, null)
                    }
                }
                panel.background = java.awt.Color(20, 20, 30)
                frame.contentPane.add(panel)
                frame.pack()
                frame.setLocationRelativeTo(null)
                frame.isVisible = true
                frameRef[0] = frame
                frame.addWindowListener(object : java.awt.event.WindowAdapter() {
                    override fun windowClosing(e: java.awt.event.WindowEvent) {
                        latch.countDown()
                    }
                    override fun windowClosed(e: java.awt.event.WindowEvent) {
                        latch.countDown()
                    }
                })
            }
            // Auto-close timer: fires after timeoutMs and counts down
            // the latch, which causes the await below to unblock and
            // us to dispose the frame.  This makes the recording
            // demo runnable unattended.
            val closer = java.util.Timer("hsharp-jframe-closer", true)
            closer.schedule(object : java.util.TimerTask() {
                override fun run() { latch.countDown() }
            }, timeoutMs)
            try {
                latch.await()
            } finally {
                closer.cancel()
                javax.swing.SwingUtilities.invokeAndWait {
                    frameRef[0]?.dispose()
                }
            }
            HNull
        }
    )

    // ── Screen recorder singleton ──
    //
    // Lives outside the HNative map because the recording
    // thread needs to capture state across multiple calls
    // (gui_start_recording starts, gui_stop_recording stops)
    // and the HNative closures don't have persistent state.
    private object ScreenRecorder {
        @Volatile private var thread: Thread? = null
        @Volatile private var frameCount: Int = 0
        @Volatile private var running: Boolean = false

        fun start(outDir: String, fps: Int) {
            if (thread != null) {
                // Idempotent: stop the previous run.
                stop()
            }
            val dir = java.io.File(outDir)
            dir.mkdirs()
            // NOTE: do NOT reset frameCount here — successive
            // start() calls (e.g. one per scene) should keep
            // counting so the PNG files in `outDir` are unique
            // and represent a continuous recording.
            running = true
            val periodMs = (1000L / fps).coerceAtLeast(1L)
            thread = Thread {
                val robot = java.awt.Robot()
                val screen = java.awt.Toolkit.getDefaultToolkit().screenSize
                val bounds = java.awt.Rectangle(0, 0, screen.width, screen.height)
                while (running) {
                    val t0 = System.currentTimeMillis()
                    try {
                        val shot = robot.createScreenCapture(bounds)
                        val idx = "%06d".format(frameCount)
                        val f = java.io.File(dir, "frame_$idx.png")
                        javax.imageio.ImageIO.write(shot, "png", f)
                        frameCount += 1
                    } catch (e: Throwable) {
                        System.err.println("recorder frame failed: " + e)
                    }
                    val elapsed = System.currentTimeMillis() - t0
                    val sleep = periodMs - elapsed
                    if (sleep > 0) {
                        try { Thread.sleep(sleep) } catch (_: InterruptedException) {}
                    }
                }
            }
            thread?.isDaemon = true
            thread?.name = "hsharp-screen-recorder"
            thread?.start()
        }

        fun stop(): Int {
            running = false
            val t = thread
            thread = null
            if (t != null) {
                t.interrupt()
                try { t.join(2000) } catch (_: InterruptedException) {}
            }
            return frameCount
        }
    }

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
        val absPath = f.absolutePath
        // Circular import detection
        if (absPath in loadingModules) {
            throw HSharpRuntimeError("Circular import detected: $path")
        }
        // Cache hit — return the previously loaded module directly
        loadedModules[absPath]?.let { cached ->
            vm.globals[f.nameWithoutExtension] = cached
            return
        }
        if (f.extension == "hbc" || f.path.endsWith(".hbc")) {
            loadingModules.add(absPath)
            try {
                val hbc = com.hsharp.compiler.HbcReader().read(f)
                for ((mname, mod) in hbc.modules) {
                    if (mname == hbc.mainModule().name) continue
                    val subVM = HVM(hbc, mname, hbcDir = vm.hbcDir)
                    subVM.globals.putAll(vm.globals)
                    subVM.run()
                    for ((k, v) in subVM.current.env) {
                        vm.globals[k] = v
                    }
                }
                val entryVM = HVM(hbc, hbc.mainModule().name, hbcDir = vm.hbcDir)
                entryVM.globals.putAll(vm.globals)
                entryVM.run()
                for ((k, v) in entryVM.current.env) {
                    vm.globals[k] = v
                }
                val module = HDict(vm.globals.toMutableMap())
                vm.globals[f.nameWithoutExtension] = module
                loadedModules[absPath] = module
                return
            } finally {
                loadingModules.remove(absPath)
            }
        }
        val textModule = HString(f.readText(Charsets.UTF_8))
        vm.globals[f.nameWithoutExtension] = textModule
        loadedModules[absPath] = textModule
    }

    private val EMPTY_FILE = com.hsharp.compiler.HbcFile(
        "v0.4", linkedMapOf("__empty__" to
            com.hsharp.compiler.HbcModule("__empty__", listOf("HALT" to null), emptyList())), 0L)
}