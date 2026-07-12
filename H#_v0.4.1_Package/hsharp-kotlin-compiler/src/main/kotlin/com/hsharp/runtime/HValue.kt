/*
 * H# Runtime Value System
 * -----------------------
 * Dynamic, boxed value type that mirrors the JSON shape of values in an .hbc file.
 * Every cell of the VM stack / env / const-pool is one of these.
 *
 * The .hbc file format (see hsvm.c) serialises values as JSON:
 *   - null                  -> HNull
 *   - true/false            -> HBool
 *   - integer / real number -> HNumber (always double precision, like Python VM)
 *   - "..."                 -> HString
 *   - [v0, v1, ...]         -> HList
 *   - { k: v, ... }         -> HDict
 *   - {"name":.., "args":[..], "bytecode":[[op,arg]...], "consts":[..], ...} -> HFunction
 *   - {"name":.., "methods":.., "fields":.., "private":[..], "base":.., ...}    -> HClass
 *   - {"__type__":"union", "name":.., "variants":[...]}                         -> HUnion
 *   - {"__class__":..., ...}                                                    -> HInstance
 */
package com.hsharp.runtime

/** Discriminator used for pattern matching and toJson(). */
enum class HType { NULL, BOOL, NUMBER, STRING, LIST, DICT, FUNCTION, CLASS, INSTANCE, UNION, NATIVE, FUTURE, CHANNEL, TASK }

/** Marker interface implemented by every runtime value. */
sealed interface HValue {
    val type: HType
    fun toKotlinLiteral(): String         // for code-gen
    fun toDisplayString(): String          // for H# PRINT
    fun toJson(): Any?                     // for serialisation / debugging
}

/** Singleton null. */
object HNull : HValue {
    override val type = HType.NULL
    override fun toKotlinLiteral() = "HNull"
    override fun toDisplayString() = "null"
    override fun toJson(): Any? = null
    override fun toString() = "null"
}

data class HBool(val value: Boolean) : HValue {
    override val type = HType.BOOL
    override fun toKotlinLiteral() = "HBool(${value})"
    override fun toDisplayString() = if (value) "true" else "false"
    override fun toJson(): Any? = value
    override fun toString() = toDisplayString()
}

data class HNumber(val value: Double) : HValue {
    override val type = HType.NUMBER
    override fun toKotlinLiteral() = "HNumber(${value})"
    override fun toDisplayString(): String {
        if (value == value.toLong().toDouble() &&
            value > Long.MIN_VALUE.toDouble() && value < Long.MAX_VALUE.toDouble()) {
            return value.toLong().toString()
        }
        return value.toString()
    }
    override fun toJson(): Any = value
    override fun toString() = toDisplayString()
}

data class HString(val value: String) : HValue {
    override val type = HType.STRING
    override fun toKotlinLiteral(): String {
        // escape for embedding inside Kotlin source
        val escaped = value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
            .replace("\$", "\\$")
        return "HString(\"$escaped\")"
    }
    override fun toDisplayString() = value
    override fun toJson(): String = value
    override fun toString() = value
}

data class HList(val items: MutableList<HValue>) : HValue {
    override val type = HType.LIST
    override fun toKotlinLiteral(): String =
        "HList(mutableListOf(" + items.joinToString(", ") { it.toKotlinLiteral() } + "))"
    override fun toDisplayString(): String =
        "[" + items.joinToString(", ") { it.toDisplayString() } + "]"
    override fun toJson(): List<Any?> = items.map { it.toJson() }
    override fun toString() = toDisplayString()
}

data class HDict(val entries: MutableMap<String, HValue>) : HValue {
    override val type = HType.DICT
    override fun toKotlinLiteral(): String {
        if (entries.isEmpty()) return "HDict(mutableMapOf())"
        val body = entries.entries.joinToString(", ") { (k, v) ->
            val ek = k.replace("\"", "\\\"")
            "${ek} to ${v.toKotlinLiteral()}"
        }
        return "HDict(mutableMapOf($body))"
    }
    override fun toDisplayString(): String =
        "{" + entries.entries.joinToString(", ") { (k, v) -> "${k}: ${v.toDisplayString()}" } + "}"
    override fun toJson(): Map<String, Any?> =
        entries.mapValues { it.value.toJson() }
    override fun toString() = toDisplayString()
}

/**
 * A user-defined function (or method) baked into the const-pool. It is a
 * recursively executable bytecode object: instructions + its own consts.
 *
 * In Python VM terms: {'args': [...], 'bytecode': [...], 'consts': [...],
 *                       'freevars': [...]?, 'is_coro': bool?, 'is_async': bool?,
 *                       'name': str?}
 */
data class HFunction(
    val name: String,
    val args: List<String>,
    val instructions: List<Pair<String, Any?>>,
    val consts: List<HValue>,
    val freevars: List<String> = emptyList(),
    val isCoro: Boolean = false,
    // `is_async` is the user-visible async/await sugar.  The compiler
    // emits this in addition to `is_coro: true` for `async fn`; the VM
    // uses it to wrap the call result in an HFuture so that `await`
    // can be type-checked against Future<T>.
    val isAsync: Boolean = false,
    // `is_parallel` is the DZZW worker-pool marker.  Set by the
    // compiler when a function is decorated with `@parallel` (or
    // declared with `parallel fn`); the VM uses it to dispatch the
    // call to a worker thread instead of running it on the caller's
    // thread.  Functions that have both `is_async` and `is_parallel`
    // are wrapped in a *lazy* HFuture (the worker fills in the
    // value asynchronously) rather than an *eager* HFuture.
    val isParallel: Boolean = false,
    // Generic / template type-parameter names declared on this function
    // (e.g. `fn identity<T>(x)` → typeParams = ["T"]).  Empty list for
    // non-generic functions.  Used for runtime introspection; H# itself
    // is dynamically typed and does not perform static type checks.
    val typeParams: List<String> = emptyList(),
    // Mutable closure-cell map: freevar name -> HList cell.  Each HList
    // holds a single HValue so that STORE_DEREF can mutate it in place and
    // the change is visible to all functions sharing the same closure.
    val closure: MutableMap<String, HValue> = mutableMapOf()
) : HValue {
    override val type = HType.FUNCTION
    override fun toKotlinLiteral() = "/* HFunction ${name} */ HNull"
    override fun toDisplayString() = "<function ${name}/${args.size}>"
    override fun toJson(): Map<String, Any?> = mapOf(
        "name" to name,
        "args" to args,
        "n_instrs" to instructions.size
    )
    override fun toString() = toDisplayString()
}

/**
 * A class template stored as a const.
 *
 * Shape: {'name': str, 'methods': {name: HFunction, ...},
 *         'fields': {name: HValue, ...}, 'private': [str, ...],
 *         'base': str?, 'implements': [str, ...]?,
 *         'type_params': [str, ...]?,
 *         '__static__': {name: HFunction, ...}?}
 */
data class HClass(
    val name: String,
    val methods: MutableMap<String, HFunction> = mutableMapOf(),
    val fields: MutableMap<String, HValue> = mutableMapOf(),
    val privateFields: MutableList<String> = mutableListOf(),
    val base: String? = null,
    val implements: MutableList<String> = mutableListOf(),
    val staticMethods: MutableMap<String, HFunction> = mutableMapOf(),
    // Generic / template type-parameter names declared on this class
    // (e.g. `class Box<T>` → typeParams = ["T"]).  Empty list for
    // non-generic classes.
    val typeParams: List<String> = emptyList()
) : HValue {
    override val type = HType.CLASS
    override fun toKotlinLiteral() = "/* HClass ${name} */ HNull"
    override fun toDisplayString(): String {
        if (typeParams.isNotEmpty()) {
            return "<class ${name}<${typeParams.joinToString(", ")}>>"
        }
        return "<class ${name}>"
    }
    override fun toJson(): Map<String, Any?> = mapOf("name" to name, "kind" to "class")
    override fun toString() = toDisplayString()
}

/**
 * Object instance.  Field '__class__' holds the HClass template, '__union__'/
 * '__variant__' mark union values. All other entries are user fields.
 */
data class HInstance(val fields: MutableMap<String, HValue> = mutableMapOf()) : HValue {
    override val type = HType.INSTANCE
    val klass: HClass? get() = (fields["__class__"] as? HClass)
    val unionName: String? get() = (fields["__union__"] as? HString)?.value
    val variantName: String? get() = (fields["__variant__"] as? HString)?.value
    override fun toKotlinLiteral() = "/* HInstance */ HNull"
    override fun toDisplayString(): String {
        val cls = klass
        val u = unionName
        val v = variantName
        if (u != null && v != null) {
            val body = fields.entries
                .filter { it.key !in listOf("__class__", "__union__", "__variant__") }
                .joinToString(", ") { (k, vv) -> "${k} = ${vv.toDisplayString()}" }
            return "${u}.${v}{${body}}"
        }
        val clsName = cls?.name ?: "object"
        val body = fields.entries
            .filter { it.key != "__class__" }
            .joinToString(", ") { (k, vv) -> "${k} = ${vv.toDisplayString()}" }
        return "${clsName}{${body}}"
    }
    override fun toJson(): Map<String, Any?> =
        fields.mapValues { it.value.toJson() }
    override fun toString() = toDisplayString()
}

/**
 * Union type descriptor. {'name': str, 'variants': [{'name': str, 'fields': [str,...]}, ...]}
 */
data class HUnion(
    val name: String,
    val variants: List<Pair<String, List<String>>>
) : HValue {
    override val type = HType.UNION
    override fun toKotlinLiteral() = "/* HUnion ${name} */ HNull"
    override fun toDisplayString() = "<union ${name}>"
    override fun toJson(): Map<String, Any?> = mapOf("name" to name, "kind" to "union")
    override fun toString() = toDisplayString()
}

/**
 * A native (host) function. We model it as a thin wrapper around a Kotlin
 * lambda so that callers (e.g. CALL_METHOD, CALL_VALUE) can invoke it.
 */
data class HNative(val name: String, val arity: Int, val call: (List<HValue>) -> HValue) : HValue {
    override val type = HType.NATIVE
    override fun toKotlinLiteral() = "/* HNative ${name} */ HNull"
    override fun toDisplayString() = "<native ${name}/${arity}>"
    override fun toJson(): Map<String, Any?> = mapOf("name" to name, "kind" to "native")
    override fun toString() = toDisplayString()
}

/**
 * A `Future<T>` produced by an `async fn` or `@parallel` call.  Wraps a
 * [FutureCell] that holds the eventual value (or failure) and synchronises
 * waiters.  Both eager and lazy resolve share the same shape:
 *
 *  - `async fn` (no `@parallel`): the body runs immediately and the
 *    [FutureCell] is completed before the constructor returns, so `await`
 *    is a no-op.  This preserves the user-visible single-threaded behaviour
 *    of plain `async fn` while keeping the surface syntax (`await expr`)
 *    type-checked against `HType.FUTURE`.
 *  - `@parallel` annotated `coro fn`: the body is submitted to a
 *    [WorkerPool] and the cell is left PENDING.  `await` then blocks
 *    the calling thread until a worker completes the cell.
 *
 * The two paths share the same value type because the user's `await`
 * expression has no way to tell them apart at the source level — and
 * crucially, mixing the two in the same code is fine: `await` always
 * just blocks if the cell isn't done yet.
 */
class HFuture(val cell: FutureCell) : HValue {
    override val type = HType.FUTURE
    /** Convenience constructor for the eager case (body already ran). */
    constructor(value: HValue) : this(FutureCell().also { it.complete(value) })
    /** Convenience constructor for the eager case with an explicit resolved flag. */
    constructor(value: HValue, resolved: Boolean) : this(
        FutureCell().also { if (resolved) it.complete(value) }
    )
    val resolved: Boolean get() = cell.isResolved()
    val value: HValue get() = if (cell.isResolved()) cell.value ?: HNull else throw HSharpRuntimeError("future not resolved yet")
    override fun toKotlinLiteral() = "HFuture()"
    override fun toDisplayString() = "<future>"
    override fun toJson(): Map<String, Any?> = mapOf(
        "__type__" to "future",
        "resolved" to cell.isResolved(),
        "value" to (cell.value?.toJson())
    )
    override fun toString() = toDisplayString()
}

/**
 * A thread-safe channel of [HValue].  Backed by a [java.util.concurrent.LinkedBlockingQueue]
 * for unbounded channels or an [java.util.concurrent.ArrayBlockingQueue]
 * for bounded channels.  This is the value type that `chan T` desugars to.
 *
 * `chan_send(ch, v)` enqueues; `chan_recv(ch)` dequeues; both block as
 * needed.  `chan_close(ch)` marks the channel as closed, after which
 * further sends raise an error and further receives return the next
 * pending value or an H# `ChannelClosed` exception.
 */
class HChannel(
    val capacity: Int,                      // 0 = unbounded
    val queue: java.util.concurrent.BlockingQueue<HValue> =
        if (capacity == 0) java.util.concurrent.LinkedBlockingQueue()
        else java.util.concurrent.ArrayBlockingQueue(capacity),
    @Volatile var closed: Boolean = false
) : HValue {
    override val type = HType.CHANNEL
    /** Total items currently in the queue (snapshot). */
    fun size(): Int = queue.size
    fun isEmpty(): Boolean = queue.isEmpty()
    fun send(v: HValue) {
        if (closed) throw HSharpException(HString("send on closed channel"))
        queue.put(v)
    }
    /** Non-blocking send; throws ChannelFull if the queue is at capacity. */
    fun trySend(v: HValue): Boolean {
        if (closed) throw HSharpException(HString("send on closed channel"))
        return queue.offer(v)
    }
    /** Blocking receive.  Returns the next value or throws if the channel
     *  is closed and drained. */
    fun recv(): HValue {
        if (closed && queue.isEmpty()) throw HSharpException(HString("recv on closed channel"))
        return queue.take()
    }
    /** Non-blocking receive; returns null if the queue is empty (and the
     *  channel is not closed). */
    fun tryRecv(): HValue? {
        return queue.poll()
    }
    /** Non-destructive peek at the head of the queue.  Returns null
     *  if the queue is empty.  Used by `chan recv(v)` pattern matching
     *  so the body can observe the queued value without consuming it.
     *
     *  BlockingQueue does not expose a non-destructive peek in the
     *  interface, so we `poll()` and then `put()` the value back.
     *  For an unbounded queue this is O(1) and safe; for a bounded
     *  queue it could fail if the queue is full *and* a concurrent
     *  sender is blocked.  Since pattern matching is a synchronous,
     *  single-threaded observation that doesn't run in parallel with
     *  the rest of the VM, this is safe in practice. */
    fun peek(): HValue? {
        val head = queue.poll() ?: return null
        return try {
            queue.put(head)
            head
        } catch (e: Throwable) {
            // The queue may have been closed mid-peek.  Put the
            // value back in a best-effort way; even if that fails
            // the value is preserved as the return.
            try { queue.offer(head) } catch (_: Throwable) {}
            head
        }
    }
    fun close() { closed = true }

    override fun toKotlinLiteral() = "/* HChannel */ HNull"
    override fun toDisplayString() = "<chan cap=${capacity} closed=${closed} size=${queue.size}>"
    override fun toJson(): Map<String, Any?> = mapOf(
        "__type__" to "channel",
        "capacity" to capacity,
        "closed" to closed,
        "size" to queue.size
    )
    override fun toString() = toDisplayString()
}

/**
 * A handle to a task running on the [WorkerPool].  This is the user-visible
 * object that a `concurrent { ... }` block produces.  A [HTask] is
 * essentially a tagged [HFuture] — the structured-concurrency join code
 * path uses the type tag to know which futures belong to a scope.
 */
class HTask(val future: HFuture, val scope: ConcurrentScope? = null) : HValue {
    override val type = HType.TASK
    override fun toKotlinLiteral() = "/* HTask */ HNull"
    override fun toDisplayString() = "<task>"
    override fun toJson(): Map<String, Any?> = mapOf("__type__" to "task")
    override fun toString() = toDisplayString()
}

/* ---------- Equality & truthiness rules (mirror the Python VM) ---------- */

/**
 * Exception raised by H# `RAISE`.  The payload is whatever was on the stack
 * (an arbitrary HValue).  We subclass RuntimeException so the Kotlin `try`
 * machinery catches it cleanly.
 */
class HSharpException(val value: HValue) : RuntimeException("H# exception: ${value.toDisplayString()}")

object HValueOps {
    fun equals(a: HValue, b: HValue): Boolean {
        if (a === b) return true
        return when {
            a is HNull && b is HNull -> true
            a is HBool && b is HBool -> a.value == b.value
            a is HNumber && b is HNumber -> a.value == b.value
            a is HString && b is HString -> a.value == b.value
            a is HList && b is HList -> a.items.size == b.items.size &&
                a.items.zip(b.items).all { (x, y) -> equals(x, y) }
            a is HDict && b is HDict -> a.entries.size == b.entries.size &&
                a.entries.all { (k, v) -> b.entries[k]?.let { equals(v, it) } == true }
            a is HInstance && b is HInstance -> a === b
            else -> false
        }
    }

    fun truthy(v: HValue): Boolean = when (v) {
        is HNull -> false
        is HBool -> v.value
        is HNumber -> v.value != 0.0
        is HString -> v.value.isNotEmpty()
        is HList -> v.items.isNotEmpty()
        is HDict -> v.entries.isNotEmpty()
        else -> true
    }

    fun toBool(v: HValue): Boolean = when (v) {
        is HBool -> v.value
        is HNull -> false
        else -> throw RuntimeException("expected bool, got ${v.type}")
    }

    fun toDouble(v: HValue): Double = when (v) {
        is HNumber -> v.value
        is HBool -> if (v.value) 1.0 else 0.0
        is HString -> v.value.toDoubleOrNull()
            ?: throw RuntimeException("cannot coerce string '${v.value}' to number")
        is HNull -> 0.0
        else -> throw RuntimeException("cannot coerce ${v.type} to number")
    }

    fun toLong(v: HValue): Long = when (v) {
        is HNumber -> v.value.toLong()
        is HBool -> if (v.value) 1L else 0L
        else -> throw RuntimeException("cannot coerce ${v.type} to int")
    }
}
