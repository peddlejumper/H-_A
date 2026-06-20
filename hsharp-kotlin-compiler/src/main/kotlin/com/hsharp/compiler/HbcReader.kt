/*
 * HBC JSON parser
 * ---------------
 * .hbc files are JSON, not a custom binary format. This parser turns the JSON
 * tree into a typed HbcFile model.
 *
 * Top level shape (see hsvm.c -> parse_file()):
 *   {
 *     "version": "v0.4",
 *     "modules": {
 *        "<module_name>": {
 *           "instructions": [ [op, arg], [op, arg], ... ],
 *           "consts":       [ <value>, <value>, ... ]
 *        }, ...
 *     },
 *     "built_at": <epoch_seconds>
 *   }
 *
 * Each instruction is encoded as a 2-element JSON array: [opname, argument].
 * The argument can be an int, a string, a 2-tuple ["name", argc], or null.
 *
 * The parser is intentionally written without any third-party JSON library so
 * the Kotlin compiler can be built and run with only the JDK available.
 */
package com.hsharp.compiler

import com.hsharp.runtime.*
import java.io.File
import java.io.InputStream

/** One module from an .hbc file. */
data class HbcModule(
    val name: String,
    val instructions: List<Pair<String, Any?>>,
    val consts: List<HValue>
)

/** Whole .hbc file model. */
data class HbcFile(
    val version: String,
    val modules: Map<String, HbcModule>,
    val builtAt: Long
) {
    /** Convenient: pick the 'main' module, fall back to the first one. */
    fun mainModule(): HbcModule =
        modules["main"] ?: modules.values.first()
}

/**
 * Reads an .hbc (JSON) file into a typed model. The implementation is in two
 * stages: first the text is parsed with a small permissive JSON parser, then
 * the untyped Map/List structure is converted into our HValue/HbcFile model.
 */
class HbcReader {

    fun read(file: File): HbcFile = file.inputStream().use { read(it, file.name) }

    fun read(stream: InputStream, sourceName: String = "<stream>"): HbcFile {
        val text = stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        val root = MiniJson(text).parseValue()
        if (root !is Map<*, *>) error("Invalid HBC: top-level must be a JSON object (in $sourceName)")
        val obj = root as Map<String, Any?>

        val version = (obj["version"] as? String) ?: "unknown"
        val builtAt = (obj["built_at"] as? Number)?.toLong() ?: 0L
        val modulesRaw = obj["modules"] as? Map<*, *>
            ?: error("Invalid HBC: missing 'modules' object (in $sourceName)")
        val modules = LinkedHashMap<String, HbcModule>()
        for ((mname, mval) in modulesRaw) {
            val m = mval as Map<*, *>
            val instrs = (m["instructions"] as? List<*>)
                ?: error("Module '$mname' missing 'instructions'")
            val constsRaw = (m["consts"] as? List<*>)
                ?: error("Module '$mname' missing 'consts'")
            val typedInstrs = instrs.map { parseInstruction(it) }
            val typedConsts = constsRaw.map { parseValue(it) }
            val fixedInstrs = fixForLoopJumps(typedInstrs)
            modules[mname.toString()] = HbcModule(mname.toString(), fixedInstrs, typedConsts)
        }
        return HbcFile(version, modules, builtAt)
    }

    /**
     * The Python compiler emits a for-loop body as:
     *   P:     FOR_ITER  end
     *   P+1:   <body>
     *   ...
     *   Q:     JUMP     P+1      <-- bug: jumps to body, not to FOR_ITER
     *   Q+1:   <end>
     * That makes the body run once with `i` stuck on the first element and
     * the JUMP loop forever.  Fix it to JUMP P (back to FOR_ITER) so the
     * iterator advances each iteration.
     */
    private fun fixForLoopJumps(instrs: List<Pair<String, Any?>>): List<Pair<String, Any?>> {
        val out = ArrayList<Pair<String, Any?>>(instrs.size)
        for (i in instrs.indices) {
            val (op, arg) = instrs[i]
            if (op == "JUMP" && arg is Number) {
                val target = arg.toInt()
                if (target in 1 until instrs.size && instrs[target - 1].first == "FOR_ITER") {
                    out.add(op to (target - 1))
                    continue
                }
            }
            out.add(op to arg)
        }
        return out
    }

    /* -------- value parsing -------- */

    private fun parseValue(v: Any?): HValue = when (v) {
        null -> HNull
        is Boolean -> HBool(v)
        is Number -> HNumber(v.toDouble())
        is String -> HString(v)
        is List<*> -> HList(v.map { parseValue(it) }.toMutableList())
        is Map<*, *> -> parseDict(v)
        else -> error("Unsupported const value: $v (${v?.javaClass})")
    }

    private fun parseDict(m: Map<*, *>): HValue {
        val out = LinkedHashMap<String, HValue>()
        // First detect special shapes
        val typeTag = m["__type__"]
        if (typeTag == "union") {
            val name = (m["name"] as? String) ?: error("union missing 'name'")
            val variants = (m["variants"] as? List<*>)
                ?: error("union '$name' missing 'variants'")
            val typedVariants = variants.map { vi ->
                val vmap = vi as Map<*, *>
                val vname = vmap["name"] as String
                val fields = (vmap["fields"] as? List<*>)
                    ?.map { it.toString() } ?: emptyList()
                vname to fields
            }
            return HUnion(name, typedVariants)
        }
        if ("bytecode" in m && "args" in m) {
            return parseFunction(m)
        }
        if ("methods" in m && "fields" in m) {
            return parseClass(m)
        }
        for ((k, v) in m) {
            out[k.toString()] = parseValue(v)
        }
        return HDict(out.toMutableMap())
    }

    private fun parseFunction(m: Map<*, *>): HFunction {
        val name = (m["name"] as? String) ?: "<lambda>"
        val args = (m["args"] as? List<*> )?.map { it.toString() } ?: emptyList()
        val bc = (m["bytecode"] as? List<*>)
            ?: error("function '$name' missing 'bytecode'")
        val consts = (m["consts"] as? List<*> )?.map { parseValue(it) } ?: emptyList()
        val freevars = (m["freevars"] as? List<*>)
            ?.map { it.toString() } ?: emptyList()
        val isCoro = (m["is_coro"] as? Boolean) ?: false
        val isAsync = (m["is_async"] as? Boolean) ?: false
        val isParallel = (m["is_parallel"] as? Boolean) ?: false
        val typeParams = (m["type_params"] as? List<*>)
            ?.map { it.toString() } ?: emptyList()
        // The same Python-compiler JUMP bug exists inside nested functions
        // too, so apply the fix here as well.
        val typedBc = bc.map { parseInstruction(it) }
        return HFunction(
            name = name,
            args = args,
            instructions = fixForLoopJumps(typedBc),
            consts = consts,
            freevars = freevars,
            isCoro = isCoro,
            isAsync = isAsync,
            isParallel = isParallel,
            typeParams = typeParams
        )
    }

    private fun parseClass(m: Map<*, *>): HClass {
        val name = (m["name"] as? String) ?: error("class missing 'name'")
        val methods = LinkedHashMap<String, HFunction>()
        val fields = LinkedHashMap<String, HValue>()
        val priv = mutableListOf<String>()
        val statics = LinkedHashMap<String, HFunction>()
        val base = m["base"] as? String
        val impls = (m["implements"] as? List<*>)?.map { it.toString() }?.toMutableList()
            ?: mutableListOf()
        @Suppress("UNCHECKED_CAST")
        val methodMap = (m["methods"] as? Map<*, *>) ?: emptyMap<Any, Any>()
        for ((mk, mv) in methodMap) {
            val mname = mk.toString()
            // Older Python compiler versions nested __static__ inside
            // `methods`; current versions put it at the top level.  Accept both.
            if (mname == "__static__") {
                @Suppress("UNCHECKED_CAST")
                val staticMap = mv as? Map<*, *> ?: continue
                for ((sk, sv) in staticMap) {
                    val sval = parseValue(sv) as? HFunction
                        ?: error("static method '$sk' is not a function")
                    statics[sk.toString()] = sval
                }
                continue
            }
            val mfunc = parseValue(mv) as? HFunction
                ?: error("method '$mname' is not a function")
            methods[mname] = mfunc
        }
        // Top-level __static__ (current Python compiler layout).
        @Suppress("UNCHECKED_CAST")
        val topStatic = m["__static__"] as? Map<*, *>
        if (topStatic != null) {
            for ((sk, sv) in topStatic) {
                val sval = parseValue(sv) as? HFunction
                    ?: error("static method '$sk' is not a function")
                statics[sk.toString()] = sval
            }
        }
        @Suppress("UNCHECKED_CAST")
        val fieldsMap = (m["fields"] as? Map<*, *>) ?: emptyMap<Any, Any>()
        for ((fk, fv) in fieldsMap) {
            fields[fk.toString()] = parseValue(fv)
        }
        @Suppress("UNCHECKED_CAST")
        val privList = (m["private"] as? List<*>) ?: emptyList<Any>()
        for (p in privList) priv.add(p.toString())
        @Suppress("UNCHECKED_CAST")
        val typeParams = (m["type_params"] as? List<*>)
            ?.map { it.toString() } ?: emptyList()
        return HClass(name, methods, fields, priv, base, impls, statics, typeParams)
    }

    private fun parseInstruction(raw: Any?): Pair<String, Any?> {
        if (raw !is List<*>) error("Instruction must be a 2-element array, got: $raw")
        if (raw.isEmpty()) error("Instruction array is empty: $raw")
        val op = raw[0].toString()
        val arg: Any? = if (raw.size >= 2) raw[1] else null
        return op to arg
    }
}

/* ============================================================================
 * Minimal JSON parser (no external deps). Permissive: accepts integers,
 * floats, booleans, null, strings (with \uXXXX escapes), arrays and objects.
 * ========================================================================= */
internal class MiniJson(private val src: String) {
    private var pos = 0
    fun parseValue(): Any? {
        skipWs()
        if (pos >= src.length) error("Unexpected end of JSON")
        return when (val c = src[pos]) {
            '{' -> parseObject()
            '[' -> parseArray()
            '"' -> parseString()
            't', 'f' -> parseBool()
            'n' -> parseNull()
            else -> if (c == '-' || c.isDigit()) parseNumber()
            else error("Unexpected '$c' at $pos")
        }
    }

    private fun parseObject(): Map<String, Any?> {
        expect('{')
        val out = LinkedHashMap<String, Any?>()
        skipWs()
        if (peek() == '}') { pos++; return out }
        while (true) {
            skipWs()
            val key = parseString()
            skipWs(); expect(':'); skipWs()
            out[key] = parseValue()
            skipWs()
            if (peek() == ',') { pos++; continue }
            expect('}')
            return out
        }
    }

    private fun parseArray(): List<Any?> {
        expect('[')
        val out = ArrayList<Any?>()
        skipWs()
        if (peek() == ']') { pos++; return out }
        while (true) {
            out.add(parseValue())
            skipWs()
            if (peek() == ',') { pos++; continue }
            expect(']')
            return out
        }
    }

    private fun parseString(): String {
        expect('"')
        val sb = StringBuilder()
        while (pos < src.length) {
            val c = src[pos++]
            if (c == '"') return sb.toString()
            if (c == '\\') {
                val e = src[pos++]
                sb.append(when (e) {
                    '"' -> '"'
                    '\\' -> '\\'
                    '/' -> '/'
                    'n' -> '\n'
                    'r' -> '\r'
                    't' -> '\t'
                    'b' -> '\b'
                    'f' -> '\u000C'
                    'u' -> {
                        val hex = src.substring(pos, pos + 4); pos += 4
                        hex.toInt(16).toChar()
                    }
                    else -> e
                })
            } else sb.append(c)
        }
        error("Unterminated string")
    }

    private fun parseBool(): Boolean = when {
        src.startsWith("true", pos) -> { pos += 4; true }
        src.startsWith("false", pos) -> { pos += 5; false }
        else -> error("Invalid literal at $pos")
    }

    private fun parseNull(): Any? {
        if (src.startsWith("null", pos)) { pos += 4; return null }
        error("Invalid literal at $pos")
    }

    private fun parseNumber(): Number {
        val start = pos
        if (peek() == '-') pos++
        while (pos < src.length && (src[pos].isDigit() || src[pos] in ".eE+-")) pos++
        val s = src.substring(start, pos)
        return if ('.' in s || 'e' in s || 'E' in s) s.toDouble()
        else s.toLong()
    }

    private fun peek(): Char = if (pos < src.length) src[pos] else '\u0000'
    private fun expect(c: Char) {
        if (peek() != c) error("Expected '$c' at $pos, got '${peek()}'")
        pos++
    }
    private fun skipWs() {
        while (pos < src.length && src[pos].isWhitespace()) pos++
    }
}
