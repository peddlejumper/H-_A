/*
 * H# Runtime VM (Kotlin implementation)
 * --------------------------------------
 * Re-implements the semantics of the Python `bytecode.py` VM and the C
 * `hsvm` binary, but in pure Kotlin so the compiled app needs no Python or
 * C toolchain to run.
 *
 * Semantics source-of-truth: hsvm.c (enum Opcode + execute()).
 */
package com.hsharp.runtime

import com.hsharp.compiler.HbcFile
import com.hsharp.compiler.HbcModule
import java.io.File
import java.util.concurrent.atomic.AtomicReference

class HSharpRuntimeError(message: String) : RuntimeException(message)

/**
 * One stack frame. Functions get a fresh frame on entry; the top-level program
 * is a synthetic frame with a null function.
 */
class HFrame(
    val func: HFunction?,            // null for top-level
    val consts: List<HValue>,
    val instrs: List<Pair<String, Any?>>,
    val env: MutableMap<String, HValue> = mutableMapOf(),
    val parent: HFrame? = null
) {
    var pc: Int = 0
    val stack: ArrayDeque<HValue> = ArrayDeque()
    val handlers: ArrayDeque<Triple<Int, Int, String>> = ArrayDeque()  // (target_pc, saved_sp, exc_name)
    var retVal: HValue = HNull
    var halted: Boolean = false
}

/**
 * The VM. Only one is needed: all call frames live on a shared stack.
 *
 * @param file  the .hbc file (used for the default entry module)
 * @param entry optional override for the entry module name (defaults to
 *              "main" then to the first module)
 */
class HVM(private val file: HbcFile, val entryName: String? = null, val hbcDir: File? = null) {

    /** Shared global symbol table.  ConcurrentHashMap makes reads from
     *  parallel worker threads safe; writes are still expected to come
     *  from the main thread (parallel tasks are pure: they read args,
     *  produce results, and use channels for I/O). */
    val globals: java.util.concurrent.ConcurrentHashMap<String, HValue> = java.util.concurrent.ConcurrentHashMap()

    /** Per-thread current frame.  Workers running on the DZZW pool each
     *  have their own slot, so they don't trample on the main thread's
     *  `current`.  The HVM is still logically a single interpreter;
     *  the only "parallel" part is that several of these interpreters
     *  can be in flight at the same time, each on its own thread. */
    private val threadCurrent: ThreadLocal<HFrame?> = ThreadLocal.withInitial { null }

    private val frames: ArrayDeque<HFrame> = ArrayDeque()
    /** Per-thread current frame.  The HVM is logically a single
     *  interpreter, but several interpreters can be in flight at the
     *  same time (one per worker thread), so `current` reads from a
     *  thread-local slot.  The main thread's slot is initialised by
     *  [resetEntry] before [run] is called. */
    var current: HFrame
        get() = threadCurrent.get() ?: error("no current frame on this thread; call resetEntry first")
        private set(value) { threadCurrent.set(value) }

    /** The active structured-concurrency scope for this thread, or
     *  null if we're outside any `concurrent { ... }` block.  Set by
     *  the [CONCURRENT_ENTER] / [CONCURRENT_EXIT] opcodes; read by
     *  [invokeHFunction] when it dispatches a parallel task so the
     *  new task can be registered as a child of the surrounding scope
     *  (this is what enables cancel propagation and parent-wins
     *  join semantics).
     *
     *  ThreadLocal: a worker thread running a nested `concurrent {}`
     *  block must not race with the main thread's scope.  Each thread
     *  gets its own slot. */
    private val _currentScope: ThreadLocal<ConcurrentScope?> = ThreadLocal.withInitial { null }
    var currentScope: ConcurrentScope?
        get() = _currentScope.get()
        set(value) { _currentScope.set(value) }

    /** Per-thread stack of scopes.  [CONCURRENT_ENTER] pushes the
     *  current scope, [CONCURRENT_EXIT] pops it.  This lets nested
     *  `concurrent { concurrent { ... } }` blocks work. */
    private val scopeStack: ThreadLocal<ArrayDeque<ConcurrentScope?>> = ThreadLocal.withInitial { ArrayDeque() }

    private fun makeEntryFrame(): HFrame {
        val mod = entryName?.let { file.modules[it] } ?: file.mainModule()
        return HFrame(null, mod.consts, mod.instructions)
    }

    /** Re-seat the entry frame (used by HbcRunner to inject pre-loaded globals). */
    internal fun resetEntry(frame: HFrame) {
        current = frame
        frames.clear()
    }

    /** Initialise the main thread's frame slot from the default entry. */
    private fun ensureEntryOnCurrentThread() {
        if (threadCurrent.get() == null) {
            threadCurrent.set(makeEntryFrame())
        }
    }

    fun run(): HValue {
        ensureEntryOnCurrentThread()
        frames.addLast(current)
        try {
            loop@ while (true) {
                val f = current
                if (f.halted) break
                if (f.pc >= f.instrs.size) break
                val (op, arg) = f.instrs[f.pc]
                f.pc++
                try {
                    if (!step(op, arg)) break@loop
                } catch (ex: HSharpException) {
                    dispatchException(ex)
                } catch (ex: HSharpRuntimeError) {
                    // turn runtime errors into catchable H# exceptions
                    dispatchException(HSharpException(HString(ex.message ?: "H# error")))
                } catch (ex: RuntimeException) {
                    // Catch JVM-level errors (IndexOutOfBounds, ClassCast,
                    // IllegalArgument, NumberFormat, Arithmetic, etc.) that
                    // escape from native bridges / collection ops and surface
                    // them to H# `try/catch` as catchable exceptions.  Without
                    // this, any Kotlin RuntimeException kills the VM.
                    dispatchException(HSharpException(HString(ex.message ?: ex::class.simpleName ?: "runtime error")))
                }
            }
        } finally {
            frames.removeLast()
        }
        return current.retVal
    }

    /* =============================================================
     * Main dispatch
     * ============================================================= */
    private fun step(op: String, arg: Any?): Boolean {
        val f = current
        when (op) {
            "HALT" -> { f.halted = true; return false }
            "LOAD_CONST" -> f.stack.addLast(f.consts[(arg as Number).toInt()])
            "LOAD_NAME" -> f.stack.addLast(lookup(arg as String))
            "STORE_NAME" -> {
                val name = arg as String
                val v = f.stack.removeLast()
                // If we're inside a method and the name is a class field,
                // route to self.fields[name] so it persists across methods.
                val self = f.env["self"] as? HInstance
                if (self != null) {
                    val cls = self.klass
                    if (cls != null && (name in cls.fields || name in cls.privateFields)) {
                        self.fields[name] = v
                        return@step true
                    }
                }
                f.env[name] = v
            }
            "PRINT" -> {
                val v = f.stack.removeLast()
                println(v.toDisplayString())
            }
            "POP_TOP" -> f.stack.removeLast()

            "MAKE_LIST" -> {
                val n = (arg as Number).toInt()
                val items = ArrayList<HValue>(n)
                repeat(n) { items.add(0, f.stack.removeLast()) }
                f.stack.addLast(HList(items))
            }
            "MAKE_DICT" -> {
                val n = (arg as Number).toInt()
                // Stack has [k0, v0, k1, v1, ...] with the LAST pair on
                // top.  Pop all pairs first, then insert in source order
                // so the dict's iteration order matches the literal.
                val pairs = ArrayList<Pair<String, HValue>>(n)
                repeat(n) {
                    val v = f.stack.removeLast()
                    val k = f.stack.removeLast()
                    pairs.add(coerceKey(k) to v)
                }
                val d = LinkedHashMap<String, HValue>()
                for ((k, v) in pairs.asReversed()) d[k] = v
                f.stack.addLast(HDict(d))
            }
            "GET_ITEM" -> {
                val idx = f.stack.removeLast()
                val left = f.stack.removeLast()
                f.stack.addLast(getItem(left, idx))
            }
            "SET_ITEM" -> {
                val v = f.stack.removeLast()
                val idx = f.stack.removeLast()
                val left = f.stack.removeLast()
                setItem(left, idx, v)
                // NOTE: do NOT push v back — assignment is a statement, not an
                // expression.  The compiler emits POP_TOP only when it actually
                // needs the result, which is never for plain `d[k] = v`.
            }
            "DELETE_ITEM" -> {
                // `del a[i]` — pop-and-discard the item at `i`.  Stack
                // layout (compiler emits in this order): [..., target, idx].
                // For lists, `i` is an index (negative counts from the end,
                // out-of-range raises).  For dicts, `i` is a key (coerced to
                // string) and the entry is removed silently if absent.  This
                // gives `del a[i]` the correct pop-by-index semantics for
                // lists, instead of the previous `a.remove(i)` lowering which
                // removed the first element *equal to* i (Bug 3).
                val idx = f.stack.removeLast()
                val target = f.stack.removeLast()
                when (target) {
                    is HList -> {
                        val i = HValueOps.toLong(idx).toInt()
                        val real = if (i < 0) target.items.size + i else i
                        if (real < 0 || real >= target.items.size)
                            throw HSharpRuntimeError("list index out of range: $i (size ${target.items.size})")
                        target.items.removeAt(real)
                    }
                    is HDict -> {
                        target.entries.remove(coerceKey(idx))
                    }
                    else -> throw HSharpRuntimeError("Cannot delete item from ${target.type}")
                }
            }
            "LOAD_ATTR" -> {
                val name = arg as String
                val obj = f.stack.removeLast()
                f.stack.addLast(loadAttr(obj, name))
            }
            "STORE_ATTR" -> {
                val name = arg as String
                val v = f.stack.removeLast()
                val obj = f.stack.removeLast()
                storeAttr(obj, name, v)
                f.stack.addLast(v)
            }

            "BINARY_ADD" -> {
                val b = f.stack.removeLast()
                val a = f.stack.removeLast()
                f.stack.addLast(binAdd(a, b))
            }
            "BINARY_SUB" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(binSub(a, b)) }
            "BINARY_MUL" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(binMul(a, b)) }
            "BINARY_DIV" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast();
                val db = HValueOps.toDouble(b)
                if (db == 0.0) throw HSharpRuntimeError("division by zero")
                val da = HValueOps.toDouble(a)
                // HNumber is internally a Double and cannot distinguish int from
                // float at runtime.  When both operands are integer-valued (no
                // fractional part), use floor (integer) division so `7/2 == 3` —
                // this matches H#'s integer-arithmetic expectations and the
                // existing test suite.  Otherwise use true division.  The
                // `1.0/3.0 == 0` consequence is acceptable given HNumber=Double.
                val bothInt = da == da.toLong().toDouble() && db == db.toLong().toDouble()
                val r = if (bothInt) Math.floorDiv(da.toLong(), db.toLong()).toDouble() else da / db
                f.stack.addLast(HNumber(r)) }
            "BINARY_MOD" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast();
                if (HValueOps.toDouble(b) == 0.0) throw HSharpRuntimeError("modulo by zero")
                // Python uses floored modulo (result takes sign of divisor),
                // not Java's truncated %.  e.g. -7 % 3 == 2 (not -1).
                val da = HValueOps.toDouble(a); val db = HValueOps.toDouble(b)
                val r = da - db * Math.floor(da / db)
                f.stack.addLast(HNumber(r)) }
            "BINARY_BITAND" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) and HValueOps.toLong(b)).toDouble())) }
            "BINARY_BITOR"  -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) or  HValueOps.toLong(b)).toDouble())) }
            "BINARY_BITXOR" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) xor HValueOps.toLong(b)).toDouble())) }
            "BINARY_LSHIFT" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) shl HValueOps.toLong(b).toInt()).toDouble())) }
            "BINARY_RSHIFT" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) shr HValueOps.toLong(b).toInt()).toDouble())) }

            "UNARY_NOT" -> {
                val v = f.stack.removeLast()
                // `not x` returns `!truthiness(x)`.  Previously any non-bool/
                // non-null value collapsed to false, so `not 0` returned false
                // instead of true.  Truthiness: 0/""/[]/{} -> false, else true.
                f.stack.addLast(HBool(!HValueOps.truthy(v)))
            }
            "UNARY_TILDE" -> f.stack.addLast(HNumber((HValueOps.toLong(f.stack.removeLast()).inv()).toDouble()))

            "COMPARE_OP" -> {
                val b = f.stack.removeLast()
                val a = f.stack.removeLast()
                val r = compareOp(arg as String, a, b)
                f.stack.addLast(HBool(r))
            }

            "JUMP" -> f.pc = (arg as Number).toInt()
            "JUMP_IF_FALSE" -> {
                val v = f.stack.removeLast()
                if (!HValueOps.truthy(v)) f.pc = (arg as Number).toInt()
            }

            "SETUP_EXCEPT" -> f.handlers.addLast(Triple((arg as Number).toInt(), f.stack.size, "__except__"))
            "POP_EXCEPT" -> if (f.handlers.isNotEmpty()) f.handlers.removeLast()
            "RAISE" -> throw HSharpException(f.stack.removeLast())

            "DUP" -> {
                // Duplicate the top-of-stack value.  Used by
                // `match` so each arm can DUP the scrutinee, run
                // MATCH_CASE which pops both, and leave the
                // scrutinee on the stack for the next arm.
                if (f.stack.isNotEmpty()) f.stack.addLast(f.stack.last())
            }
            "POP" -> if (f.stack.isNotEmpty()) f.stack.removeLast()
            "SWAP" -> {
                // Swap the top two stack slots.  Used by `match`
                // to discard the leftover scrutinee after a
                // successful arm pushed the body's result.
                if (f.stack.size >= 2) {
                    val top = f.stack.removeLast()
                    val below = f.stack.removeLast()
                    f.stack.addLast(top)
                    f.stack.addLast(below)
                }
            }

            "MATCH_CASE" -> {
                // Pop the pattern const and the (duplicated)
                // scrutinee, run matchPattern, push a bool.  Stack
                // layout entering this opcode:
                //   [..., scrutinee, scrutinee, pattern_dict]
                // The pattern sits on top (pushed by the most
                // recent LOAD_CONST), and the duplicate scrutinee
                // is right below it.  We pop both, leaving the
                // *original* scrutinee on the stack for the body's
                // JUMP end to consume or for the next case to DUP.
                // See the `matchPattern` helper below.
                val patIdx = (arg as Number).toInt()
                val pat = f.consts[patIdx] as HDict
                f.stack.removeLast()  // discard the pattern (was on top)
                val scrutinee = f.stack.removeLast()  // duplicated scrutinee
                val matched = matchPattern(f, pat, scrutinee)
                f.stack.addLast(if (matched) HBool(true) else HBool(false))
            }

            "SETUP_PROPAGATE" -> f.handlers.addLast(
                Triple((arg as Number).toInt(), f.stack.size, "__propagate__"))
            "POP_PROPAGATE" -> {
                if (f.handlers.isNotEmpty() &&
                    f.handlers.last().third == "__propagate__") {
                    f.handlers.removeLast()
                }
            }

            "RETURN_VALUE" -> {
                f.retVal = if (f.stack.isNotEmpty()) f.stack.removeLast() else HNull
                f.halted = true
                return false
            }

            "CALL_METHOD" -> {
                @Suppress("UNCHECKED_CAST")
                val pair = arg as List<Any>
                val name = pair[0] as String
                val argc = (pair[1] as Number).toInt()
                callMethod(name, argc)
            }
            "CALL_SUPER" -> {
                @Suppress("UNCHECKED_CAST")
                val pair = arg as List<Any>
                val name = pair[0] as String
                val argc = (pair[1] as Number).toInt()
                callSuper(name, argc)
            }
            "CALL_FUNCTION" -> {
                @Suppress("UNCHECKED_CAST")
                val pair = arg as List<Any>
                val name = pair[0] as String
                val argc = (pair[1] as Number).toInt()
                callFunction(name, argc, hasTypeArgs = false)
            }
            "CALL_FUNCTION_T" -> {
                // Generic function call with explicit type arguments.
                // Stack layout: [..., arg1, ..., argN, type_args]
                // (the function itself is looked up by name, not on the stack).
                // The `type_args` are exposed to the called body through the
                // call frame's `__type_args__` env entry.
                @Suppress("UNCHECKED_CAST")
                val pair = arg as List<Any>
                val name = pair[0] as String
                val argc = (pair[1] as Number).toInt()
                callFunction(name, argc, hasTypeArgs = true)
            }
            "CALL_VALUE_T" -> {
                val argc = (arg as Number).toInt()
                callValue(argc, hasTypeArgs = true)
            }
            "CALL_METHOD_T" -> {
                @Suppress("UNCHECKED_CAST")
                val pair = arg as List<Any>
                val name = pair[0] as String
                val argc = (pair[1] as Number).toInt()
                callMethod(name, argc, hasTypeArgs = true)
            }
            "LOAD_DEREF" -> {
                val name = arg as String
                val cell = f.env[name]
                    ?: throw HSharpRuntimeError("LOAD_DEREF: free var '$name' has no cell")
                val lst = cell as? HList
                    ?: throw HSharpRuntimeError("LOAD_DEREF: cell for '$name' is not a list")
                if (lst.items.isEmpty())
                    throw HSharpRuntimeError("LOAD_DEREF: empty cell for '$name'")
                val v = lst.items[0]
                f.stack.addLast(v)
            }
            "STORE_DEREF" -> {
                val name = arg as String
                val v = f.stack.removeLast()
                val cell = f.env[name]
                    ?: throw HSharpRuntimeError("STORE_DEREF: free var '$name' has no cell")
                val lst = cell as? HList
                    ?: throw HSharpRuntimeError("STORE_DEREF: cell for '$name' is not a list")
                if (lst.items.isEmpty()) lst.items.add(v)
                else lst.items[0] = v
            }
            "MAKE_CLOSURE" -> {
                // Pops the function template, then pops n values that will
                // become the closure cells (one per free var, in order).
                val n = (arg as Number).toInt()
                val tmpl = f.stack.removeLast() as? HFunction
                    ?: throw HSharpRuntimeError("MAKE_CLOSURE: top of stack is not a function")
                if (n != tmpl.freevars.size)
                    throw HSharpRuntimeError("MAKE_CLOSURE: arity $n != freevars ${tmpl.freevars.size}")
                val captured = ArrayList<HValue>(n)
                repeat(n) { captured.add(0, f.stack.removeLast()) }  // reverse so [0] is freevars[0]
                // IMPORTANT: build a brand-new HFunction so the const-pool
                // template is not mutated.  Each call to MAKE_CLOSURE must
                // produce a fresh closure object; otherwise two separate
                // calls (e.g. `makeAdder(5)` and `makeAdder(10)`) would
                // overwrite each other's captured cells.  Kotlin's
                // data-class `copy()` would share the closure map, so we
                // construct the new HFunction by hand.
                val func = HFunction(
                    name = tmpl.name,
                    args = tmpl.args,
                    instructions = tmpl.instructions,
                    consts = tmpl.consts,
                    freevars = tmpl.freevars,
                    isCoro = tmpl.isCoro,
                    isAsync = tmpl.isAsync,
                    isParallel = tmpl.isParallel,
                    typeParams = tmpl.typeParams,
                    closure = mutableMapOf(),
                    // FIX (Bug 1): copy default-arg and variadic flags from
                    // the template so closures preserve the original call
                    // signature.  Without these, a closure over a variadic
                    // or defaulted function lost both behaviours.
                    defaultArgs = tmpl.defaultArgs,
                    isVariadic = tmpl.isVariadic
                )
                for ((i, name) in tmpl.freevars.withIndex()) {
                    func.closure[name] = HList(mutableListOf(captured[i]))
                }
                f.stack.addLast(func)
            }
            "SLICE" -> {
                // Stack (top -> bottom): step, end, start, collection
                val step = f.stack.removeLast()
                val end = f.stack.removeLast()
                val start = f.stack.removeLast()
                val target = f.stack.removeLast()
                f.stack.addLast(sliceValue(target, start, end, step))
            }
            "CALL_VALUE" -> {
                val argc = (arg as Number).toInt()
                callValue(argc, hasTypeArgs = false)
            }
            "CALL_NEW" -> {
                val argc = (arg as Number).toInt()
                callNew(argc, hasTypeArgs = false)
            }
            "CALL_NEW_T" -> {
                val argc = (arg as Number).toInt()
                callNew(argc, hasTypeArgs = true)
            }

            "INSTANCEOF" -> {
                val typeName = arg as String
                val obj = f.stack.removeLast()
                f.stack.addLast(HBool(isInstance(obj, typeName)))
            }

            "UNION_MAKE" -> {
                val argc = (arg as Number).toInt()
                val values = ArrayList<HValue>(argc)
                repeat(argc) { values.add(0, f.stack.removeLast()) }
                val variant = (f.stack.removeLast() as HString).value
                val utype = f.stack.removeLast()
                if (utype !is HUnion) throw HSharpRuntimeError("UNION_MAKE on non-union type")
                val v = utype.variants.firstOrNull { it.first == variant }
                    ?: throw HSharpRuntimeError("Unknown variant $variant for union ${utype.name}")
                if (values.size != v.second.size)
                    throw HSharpRuntimeError("Variant $variant expects ${v.second.size} fields, got ${values.size}")
                val inst = HInstance(mutableMapOf(
                    "__class__" to utype,    // store union desc as class for repr purposes
                    "__union__" to HString(utype.name),
                    "__variant__" to HString(variant)
                ))
                for ((i, fname) in v.second.withIndex()) inst.fields[fname] = values[i]
                f.stack.addLast(inst)
            }

            "FOR_ITER" -> forIter((arg as Number).toInt())
            "AWAIT" -> {
                // `await` is the runtime half of the `async fn` / `await expr`
                // sugar: it pops a value off the stack and, if that value is
                // an HFuture, blocks on the underlying FutureCell and pushes
                // the resolved value.  Anything else is a type error — H#
                // refuses to silently coerce.
                //
                // The Python compiler is expected to have already rejected
                // `await` outside an `async fn` body at compile time, so by
                // the time we get here the static check has passed.  This
                // runtime check is the second line of defence and also
                // catches the case where the awaited expression is not a
                // future (e.g. `await 42`).
                //
                // For an eager-resolve HFuture (the one `async fn` produces
                // when the body has already finished), the cell is already
                // RESOLVED and the call returns immediately.  For a
                // multi-threaded HFuture (the one `@parallel` produces), the
                // cell is PENDING and the call blocks the calling thread
                // until a worker completes it.
                val v = f.stack.removeLast()
                if (v is HFuture) {
                    f.stack.addLast(v.cell.await())
                } else {
                    throw HSharpRuntimeError(
                        "AWAIT: expected Future<T>, got ${v::class.simpleName} (${v.toDisplayString()})"
                    )
                }
            }
            "CHAN_NEW" -> {
                // `chan_new(capacity)` — the runtime half of the
                // `chan T` / `chan_new(N)` syntax.  Pops the capacity
                // (must be a number) and pushes a fresh HChannel.
                // Capacity 0 means unbounded.
                val cap = HValueOps.toLong(f.stack.removeLast()).toInt()
                f.stack.addLast(HChannel(cap))
            }
            "CHAN_SEND" -> {
                // `chan_send(ch, v)` — push the channel under the
                // value (or just check the channel and then pop the
                // value off).  We pop the value last, then the
                // channel, but the compiler emits them in (channel,
                // value) order, so the stack has [..., channel,
                // value].  The send() call blocks if the channel is
                // at capacity (bounded channel) — the worker thread
                // parks on the queue until space is available.
                val v = f.stack.removeLast()
                val ch = f.stack.removeLast()
                if (ch !is HChannel) {
                    throw HSharpRuntimeError("CHAN_SEND: expected HChannel, got ${ch.type}")
                }
                ch.send(v)
            }
            "CHAN_RECV" -> {
                // `chan_recv(ch)` — pops the channel and pushes the
                // next value.  Blocks until a sender produces one
                // (or the channel is closed and drained, in which case
                // it raises an H# exception).
                val ch = f.stack.removeLast()
                if (ch !is HChannel) {
                    throw HSharpRuntimeError("CHAN_RECV: expected HChannel, got ${ch.type}")
                }
                f.stack.addLast(ch.recv())
            }
            "CHAN_CLOSE" -> {
                val ch = f.stack.removeLast()
                if (ch !is HChannel) {
                    throw HSharpRuntimeError("CHAN_CLOSE: expected HChannel, got ${ch.type}")
                }
                ch.close()
            }
            "CONCURRENT_ENTER" -> {
                // `concurrent { ... }` open: allocate a fresh
                // ConcurrentScope and push the previous scope onto
                // the thread-local scope stack.  All parallel tasks
                // spawned inside the block are registered as
                // children of this scope.
                val scope = ConcurrentScope()
                scopeStack.get().addLast(currentScope)
                currentScope = scope
            }
            "CONCURRENT_EXIT" -> {
                // `concurrent { ... }` close: join the scope (wait
                // for every child, propagate the first failure) and
                // then pop back to the parent scope.
                //
                // Idempotent: if there is no active scope (either
                // because CONCURRENT_EXIT was never paired with a
                // CONCURRENT_ENTER, or — the common case — because
                // cleanup already ran via the exception handler that
                // the compiler emits around the body), this is a
                // no-op.  This makes it safe for the compiler to
                // place CONCURRENT_EXIT in both the normal-exit path
                // and the SETUP_EXCEPT handler without risking a
                // double-join or a spurious "without CONCURRENT_ENTER"
                // error on the second visit.
                val scope = currentScope
                if (scope != null) {
                    val stack = scopeStack.get()
                    val parent = if (stack.isEmpty()) null else stack.removeLast()
                    try {
                        // joinPendingOnly waits for still-PENDING children
                        // and skips already-settled ones, so an exception
                        // already caught by a try/catch inside the block
                        // is NOT re-thrown here (Bug 1 fix).  A child whose
                        // failure was never observed (still PENDING when
                        // the block exits) still propagates its failure.
                        scope.joinPendingOnly()
                    } finally {
                        currentScope = parent
                    }
                }
            }
            "CLEANUP_FOR" -> {
                // Pop the for-loop iterator dict that the current `for`
                // pushed onto the stack.  This is only meaningful on the
                // `break` path (where forIter's normal end-of-iteration
                // pop was skipped).  On the normal end-of-iteration
                // path, forIter has already set f.pc past this
                // instruction, so we never get here.
                if (f.stack.isNotEmpty()) {
                    val top = f.stack.last()
                    if (top is HDict && top.entries["__is_iter"] == HBool(true)) {
                        f.stack.removeLast()
                    }
                }
            }
            "CONTINUE" -> { /* no-op: continue targets are baked in by compiler */ }
            "BREAK" -> {
                // C VM behaviour: scan forward past the next backward JUMP
                // (the loop-end marker). This handles bytecode that wasn't
                // backpatched by the Python compiler.
                var i = f.pc
                while (i < f.instrs.size) {
                    val (op2, arg2) = f.instrs[i]
                    if (op2 == "JUMP" && arg2 is Number && (arg2 as Number).toInt() < i) {
                        f.pc = i + 1
                        return@step true
                    }
                    i++
                }
                f.pc = f.instrs.size
            }
            "MAKE_MODULE" -> {
                val name = (f.consts[(arg as Number).toInt()] as HString).value
                val proxy = HDict(LinkedHashMap(f.env).toMutableMap())
                f.env[name] = proxy
            }
            "ASM" -> { /* ASH block — handled inside const pool */ }
            "CAST" -> {
                // `expr as Type` — runtime half of CastExpression.
                // The compiler emits `CAST type_name` with the value on
                // top of the stack (the type name is in `arg`, NOT on
                // the stack).  Previously this was a no-op, so `x as T`
                // silently returned x unchanged even on a mismatch.
                // Now: primitive type names perform a coercive
                // conversion; class/interface names perform a runtime
                // membership check and throw on mismatch.
                val v = f.stack.removeLast()
                val tn = arg as String
                if (tn == "int") {
                    f.stack.addLast(HNumber(HValueOps.toDouble(v).toLong().toDouble()))
                    return@step true
                }
                if (tn == "float") {
                    f.stack.addLast(HNumber(HValueOps.toDouble(v)))
                    return@step true
                }
                if (tn == "str" || tn == "string") {
                    f.stack.addLast(HString(v.toDisplayString()))
                    return@step true
                }
                if (tn == "bool") {
                    f.stack.addLast(HBool(HValueOps.truthy(v)))
                    return@step true
                }
                // Class / interface / other: checked assertion — no
                // coercion.  isInstance handles HInstance class/iface
                // matching and primitive type names too, so a bad cast
                // like `5 as Point` raises instead of silently passing.
                if (!isInstance(v, tn)) {
                    throw HSharpRuntimeError("Cannot cast ${v.type} to $tn")
                }
                f.stack.addLast(v)
            }
            "DEREF" -> { /* pointer ref — no-op in this runtime */ }

            "IMPORT_NAME" -> {
                val modname = arg as String
                val proxy = HNativeBridge.importPython(modname)
                f.env[modname] = proxy
            }
            "IMPORT_FILE" -> {
                val path = arg as String
                HNativeBridge.importHFile(path, this)
            }

            else -> throw HSharpRuntimeError("Unknown opcode: $op (arg=$arg)")
        }
        return true
    }

    /* =============================================================
     * Builtins / call conventions
     *
     * Stack layout convention (set by the Python compiler):
     *
     *   CALL_FUNCTION:    [..., arg1, ..., argN]                 (name is looked up, not on stack)
     *   CALL_FUNCTION_T:  [..., arg1, ..., argN, type_args]
     *   CALL_VALUE:       [..., arg1, ..., argN, function]        (function is on stack)
     *   CALL_VALUE_T:     [..., arg1, ..., argN, type_args, function]
     *   CALL_METHOD:      [..., arg1, ..., argN, self]            (self is on stack)
     *   CALL_METHOD_T:    [..., arg1, ..., argN, type_args, self]
     *   CALL_NEW:         [..., arg1, ..., argN, class]           (class is on stack)
     *   CALL_NEW_T:       [..., arg1, ..., argN, type_args, class]
     *
     * In all cases the value args are on TOP of the stack (pushed last),
     * with the function/self/class (and, when present, the type-args list)
     * below them.  The call helpers pop args first, then the type-args
     * list (if `hasTypeArgs`), then the callee object.
     * ============================================================= */
    private fun callFunction(name: String, argc: Int, hasTypeArgs: Boolean) {
        val f = current
        val args = popArgs(argc)
        val targs: HList? = if (hasTypeArgs) f.stack.removeLast() as? HList else null
        // Python VM checks builtins FIRST, then falls back to env lookup.
        // This ensures builtins like len() aren't shadowed by user variables.
        val builtin = HNativeBridge.builtins[name]
        if (builtin != null) {
            f.stack.addLast(builtin.call(args))
            return
        }
        val v = lookup(name)
        val res = invokeCallable(v, args, instance = null, nameForError = name, typeArgs = targs)
        f.stack.addLast(res)
    }

    private fun callMethod(name: String, argc: Int, hasTypeArgs: Boolean = false) {
        val f = current
        val args = popArgs(argc)
        val inst = f.stack.removeLast()
        val targs: HList? = if (hasTypeArgs) f.stack.removeLast() as? HList else null
        // Built-in string methods.  Strings in the Kotlin VM are HString
        // (not a class with a method table), so we dispatch the common
        // methods by hand.  This mirrors the surface that the Python
        // VM gets for free from CPython's str.
        if (inst is HString) {
            val res = callStringMethod(inst, name, args)
            f.stack.addLast(res)
            return
        }
        // Built-in list methods (a few, just enough for common idioms).
        if (inst is HList) {
            val res = callListMethod(inst, name, args)
            f.stack.addLast(res)
            return
        }
        // Module-like dict: direct call or static map
        if (inst is HDict && "__class__" !in inst.entries) {
            // Built-in dict methods (get / has_key / contains / size /
            // keys / values / items).  These take precedence over any
            // user-defined entry of the same name, mirroring how
            // callStringMethod / callListMethod work.
            val builtin = callDictMethod(inst, name, args)
            if (builtin != null) {
                f.stack.addLast(builtin)
                return
            }
            // Direct attribute on module dict
            val entry = inst.entries[name]
            if (entry != null) {
                val res = invokeCallable(entry, args, instance = inst, nameForError = name)
                f.stack.addLast(res)
                return
            }
            // Static methods stored under __static__ container (Python VM pattern)
            val staticMap = inst.entries["__static__"]
            if (staticMap is HDict) {
                val staticMethod = staticMap.entries[name]
                if (staticMethod is HFunction) {
                    val res = invokeHFunction(staticMethod, args, instance = null, parent = current)
                    f.stack.addLast(res)
                    return
                }
            }
            throw HSharpRuntimeError("Attribute '$name' not found on module")
        }
        // Class: `ClassName.staticMethod(...)` — invoke without an instance.
        if (inst is HClass) {
            // FIX: walk the base-class chain so a static method
            // inherited from a parent is reachable via the subclass
            // (`Sub.helper()` where `helper` is defined on Base).
            // The HClass stored in globals is the unresolved template
            // (resolveClass only runs at `new` time), so we must walk
            // `base` links ourselves, resolving each ancestor by name.
            var cls: HClass? = inst
            while (cls != null) {
                val sm = cls.staticMethods[name]
                if (sm != null) {
                    val res = invokeHFunction(sm, args, instance = null, parent = current, staticClass = cls)
                    f.stack.addLast(res)
                    return
                }
                cls = cls.base?.let { lookup(it) as? HClass }
            }
            throw HSharpRuntimeError("Static method '$name' not found on class ${inst.name}")
        }
        if (inst !is HInstance) throw HSharpRuntimeError("CALL_METHOD on non-instance ($name)")
        val cls = inst.klass ?: throw HSharpRuntimeError("Instance has no __class__")
        // FIX (Bug 4): check the instance field FIRST, before class
        // methods, so `obj.field()` and `obj.field` agree — both
        // resolve to the instance field when one exists.  This matches
        // LOAD_ATTR's field-first lookup order.  Only callable field
        // values (HFunction / HNative) shadow the method here; a
        // non-callable field falls through to the class method so that
        // existing code where a non-function field shares a name with
        // a method is not broken.
        val fieldVal = inst.fields[name]
        if (fieldVal is HFunction || fieldVal is HNative) {
            val res = invokeCallable(fieldVal, args, instance = null, nameForError = name, typeArgs = targs)
            f.stack.addLast(res)
            return
        }
        val mfunc = cls.methods[name]
        if (mfunc != null) {
            val res = invokeHFunction(mfunc, args, instance = inst, parent = current, typeArgs = targs)
            f.stack.addLast(res)
            return
        }
        // FIX: fallback to static methods on the instance's class (and
        // its parent classes) so `instance.staticMethod()` works.
        // Mirrors the `HClass` branch above: invoked without an instance
        // (static methods don't receive `self`).
        var walkCls: HClass? = cls
        while (walkCls != null) {
            val sm = walkCls.staticMethods[name]
            if (sm != null) {
                val res = invokeHFunction(
                    sm, args, instance = null, parent = current,
                    staticClass = walkCls, typeArgs = targs
                )
                f.stack.addLast(res)
                return
            }
            walkCls = walkCls.base?.let { lookup(it) as? HClass }
        }
        throw HSharpRuntimeError("Method '$name' not found on ${cls.name}")
    }

    private fun callStringMethod(self: HString, name: String, args: List<HValue>): HValue {
        return when (name) {
            "strip" -> {
                require(args.isEmpty()) { "strip() takes no arguments" }
                HString(self.value.trim())
            }
            "lstrip" -> {
                require(args.isEmpty()) { "lstrip() takes no arguments" }
                HString(self.value.trimStart())
            }
            "rstrip" -> {
                require(args.isEmpty()) { "rstrip() takes no arguments" }
                HString(self.value.trimEnd())
            }
            "lower" -> {
                require(args.isEmpty()) { "lower() takes no arguments" }
                HString(self.value.lowercase())
            }
            "upper" -> {
                require(args.isEmpty()) { "upper() takes no arguments" }
                HString(self.value.uppercase())
            }
            "is_empty" -> {
                require(args.isEmpty()) { "is_empty() takes no arguments" }
                HBool(self.value.isEmpty())
            }
            "len", "length" -> {
                require(args.isEmpty()) { "len() takes no arguments" }
                HNumber(self.value.codePointCount(0, self.value.length).toDouble())
            }
            "starts_with" -> {
                require(args.size == 1) { "starts_with() takes exactly 1 argument" }
                val p = (args[0] as? HString)?.value
                    ?: throw HSharpRuntimeError("starts_with() expects a string")
                HBool(self.value.startsWith(p))
            }
            "ends_with" -> {
                require(args.size == 1) { "ends_with() takes exactly 1 argument" }
                val p = (args[0] as? HString)?.value
                    ?: throw HSharpRuntimeError("ends_with() expects a string")
                HBool(self.value.endsWith(p))
            }
            "contains" -> {
                require(args.size == 1) { "contains() takes exactly 1 argument" }
                val p = (args[0] as? HString)?.value
                    ?: throw HSharpRuntimeError("contains() expects a string")
                HBool(p in self.value)
            }
            "find" -> {
                require(args.size in 1..2) { "find() takes 1 or 2 arguments" }
                val p = (args[0] as? HString)?.value
                    ?: throw HSharpRuntimeError("find() expects a string")
                // FIX: the start argument and the returned position are
                // code-point indices at the H# level, but String.indexOf
                // works on UTF-16 offsets.  Bridge the two so emoji and
                // other supplementary characters don't skew the result.
                val startCp = if (args.size >= 2) HValueOps.toLong(args[1]).toInt().coerceAtLeast(0) else 0
                val s = self.value
                val cpLen = codePointLength(s)
                val startCpClamped = startCp.coerceAtMost(cpLen)
                val startUtf = codePointToCharIndex(s, startCpClamped)
                val posUtf = s.indexOf(p, startUtf)
                HNumber(if (posUtf < 0) -1.0 else s.codePointCount(0, posUtf).toDouble())
            }
            "replace" -> {
                require(args.size == 2) { "replace() takes exactly 2 arguments" }
                val oldS = (args[0] as? HString)?.value
                    ?: throw HSharpRuntimeError("replace() expects a string")
                val newS = (args[1] as? HString)?.value
                    ?: throw HSharpRuntimeError("replace() expects a string")
                HString(self.value.replace(oldS, newS))
            }
            "split" -> {
                require(args.size == 1) { "split() takes exactly 1 argument" }
                val sep = (args[0] as? HString)?.value
                    ?: throw HSharpRuntimeError("split() expects a string")
                if (sep.isEmpty()) {
                    throw HSharpRuntimeError("split() empty separator")
                }
                HList(self.value.split(sep).map { HString(it) }.toMutableList())
            }
            "join" -> {
                require(args.size == 1) { "join() takes exactly 1 argument" }
                val lst = args[0] as? HList
                    ?: throw HSharpRuntimeError("join() expects a list")
                // Convert each element to its display string so non-string
                // items (numbers, bools, etc.) don't trigger a ClassCastException.
                HString(lst.items.joinToString(self.value) { it.toDisplayString() })
            }
            else -> throw HSharpRuntimeError("Unknown string method '$name'")
        }
    }

    private fun callListMethod(self: HList, name: String, args: List<HValue>): HValue {
        return when (name) {
            "len", "length" -> {
                require(args.isEmpty()) { "len() takes no arguments" }
                HNumber(self.items.size.toDouble())
            }
            "is_empty" -> {
                require(args.isEmpty()) { "is_empty() takes no arguments" }
                HBool(self.items.isEmpty())
            }
            "append" -> {
                require(args.size == 1) { "append() takes exactly 1 argument" }
                self.items.add(args[0])
                HNull
            }
            "push" -> {
                require(args.size == 1) { "push() takes exactly 1 argument" }
                self.items.add(args[0])
                HNull
            }
            "pop" -> {
                // pop() -> remove and return last element
                // pop(i) -> remove and return element at position i
                // (negative i counts from the end, like Python)
                if (args.isEmpty()) {
                    if (self.items.isEmpty()) throw HSharpRuntimeError("pop from empty list")
                    self.items.removeAt(self.items.size - 1)
                } else {
                    require(args.size == 1) { "pop() takes 0 or 1 arguments" }
                    val i = HValueOps.toLong(args[0]).toInt()
                    val idx = if (i < 0) self.items.size + i else i
                    if (idx < 0 || idx >= self.items.size)
                        throw HSharpRuntimeError("pop index out of range: $i (size ${self.items.size})")
                    self.items.removeAt(idx)
                }
            }
            "insert" -> {
                // insert(i, x): insert x before position i.
                // Negative i counts from the end; out-of-range i is
                // clamped to 0 / size (Python semantics).
                require(args.size == 2) { "insert() requires 2 arguments" }
                val i = HValueOps.toLong(args[0]).toInt()
                val idx = if (i < 0) (self.items.size + i).coerceAtLeast(0)
                          else i.coerceAtMost(self.items.size)
                self.items.add(idx, args[1])
                HNull
            }
            "remove" -> {
                // remove(x): remove the first occurrence of x.
                require(args.size == 1) { "remove() requires 1 argument" }
                val target = args[0]
                val idx = self.items.indexOfFirst { HValueOps.equals(it, target) }
                if (idx < 0) throw HSharpRuntimeError("remove(): element not found")
                self.items.removeAt(idx)
                HNull
            }
            "sort" -> {
                // General in-place sort.  Previously used `sortBy { toDouble(it) }`
                // which only worked for numbers and threw on string lists.
                // Now: HNumber compared by value, HString by lexicographic
                // order, HBool by false<true; mixed types compare by type
                // name then value so the sort is total (no ClassCast / NaN).
                require(args.isEmpty() || args.size == 1) { "sort() takes 0 or 1 arguments" }
                self.items.sortWith { x, y -> hValueCompare(x, y) }
                HNull
            }
            "reverse" -> {
                require(args.isEmpty()) { "reverse() takes no arguments" }
                self.items.reverse()
                HNull
            }
            "index" -> {
                // index(x): position of first occurrence, or -1 if absent.
                require(args.size == 1) { "index() requires 1 argument" }
                val target = args[0]
                val idx = self.items.indexOfFirst { HValueOps.equals(it, target) }
                HNumber(idx.toDouble())
            }
            "clear" -> {
                require(args.isEmpty()) { "clear() takes no arguments" }
                self.items.clear()
                HNull
            }
            "contains" -> {
                require(args.size == 1) { "contains() takes exactly 1 argument" }
                HBool(self.items.contains(args[0]))
            }
            else -> throw HSharpRuntimeError("Unknown list method '$name'")
        }
    }

    /** Built-in methods on plain dicts (`{}`).  Returns null if `name`
     *  is not a recognised dict method, so [callMethod] can fall
     *  through to the module-attribute / static-method path for
     *  non-builtin names. */
    private fun callDictMethod(self: HDict, name: String, args: List<HValue>): HValue? {
        return when (name) {
            "get" -> {
                // d.get(key)         -> value or null
                // d.get(key, default) -> value or default
                require(args.size == 1 || args.size == 2) { "get() takes 1 or 2 arguments" }
                val key = dictKeyOf(args[0])
                val v = self.entries[key]
                v ?: (if (args.size == 2) args[1] else HNull)
            }
            "has_key" -> {
                require(args.size == 1) { "has_key() takes exactly 1 argument" }
                val key = dictKeyOf(args[0])
                HBool(key in self.entries)
            }
            "contains" -> {
                require(args.size == 1) { "contains() takes exactly 1 argument" }
                val key = dictKeyOf(args[0])
                HBool(key in self.entries)
            }
            "len", "length", "size" -> {
                require(args.isEmpty()) { "$name() takes no arguments" }
                HNumber(self.entries.size.toDouble())
            }
            "is_empty" -> {
                require(args.isEmpty()) { "is_empty() takes no arguments" }
                HBool(self.entries.isEmpty())
            }
            "keys" -> {
                require(args.isEmpty()) { "keys() takes no arguments" }
                HList(self.entries.keys.map { HString(it) }.toMutableList())
            }
            "values" -> {
                require(args.isEmpty()) { "values() takes no arguments" }
                HList(self.entries.values.toMutableList())
            }
            "items" -> {
                require(args.isEmpty()) { "items() takes no arguments" }
                HList(self.entries.entries.map { (k, v) ->
                    HList(mutableListOf(HString(k), v))
                }.toMutableList())
            }
            "clear" -> {
                require(args.isEmpty()) { "clear() takes no arguments" }
                self.entries.clear()
                HNull
            }
            "remove" -> {
                require(args.size == 1) { "remove() takes exactly 1 argument" }
                val key = dictKeyOf(args[0])
                self.entries.remove(key)
                HNull
            }
            "copy" -> {
                require(args.isEmpty()) { "copy() takes no arguments" }
                HDict(self.entries.toMutableMap())
            }
            else -> null
        }
    }

    /** Coerce an HValue to a dict key string (HDict keys are always
     *  String in the Kotlin VM). */
    private fun dictKeyOf(v: HValue): String = when (v) {
        is HString -> v.value
        // FIX: was v.value.toString() which produced "1.0" for whole
        // numbers (HNumber stores Double). Use toDisplayString() so an
        // integer key produces "1" — matching coerceKey() used by
        // dict assignment. This keeps lookup and assignment consistent.
        is HNumber -> v.toDisplayString()
        is HBool -> if (v.value) "true" else "false"
        else -> v.toDisplayString()
    }

    private fun callSuper(name: String, argc: Int) {
        val f = current
        val args = popArgs(argc)
        val inst = f.env["self"] as? HInstance
            ?: throw HSharpRuntimeError("super() can only be called within a method")
        val cls = inst.klass ?: throw HSharpRuntimeError("self has no __class__")
        // FIX (super-chain): start the search from the parent of the
        // class that DEFINED the currently-executing method, not from
        // the instance's actual class. `inst.klass` never changes
        // across super calls, so without `__current_class__` a chain
        // C→B→A would restart at B on every level and recurse forever.
        // `__current_class__` is stamped onto the frame by invokeHFunction
        // when it is invoked with a `definingClass` (see callSuper below).
        val startCls = (f.env["__current_class__"] as? HClass) ?: cls
        // Walk up the base class chain to find the method
        var baseName = startCls.base
        while (baseName != null) {
            val base = (lookup(baseName) as? HClass)
                ?: throw HSharpRuntimeError("Base class $baseName not found")
            val mfunc = base.methods[name]
            if (mfunc != null) {
                // Pass `definingClass = base` so a further nested
                // super.method() resumes the search from base.base.
                val res = invokeHFunction(
                    mfunc, args, instance = inst, parent = current,
                    definingClass = base
                )
                f.stack.addLast(res)
                return
            }
            baseName = base.base
        }
        throw HSharpRuntimeError("Method '$name' not found in any base class of ${cls.name}")
    }

    private fun callValue(argc: Int, hasTypeArgs: Boolean = false) {
        val f = current
        // Stack layout for CALL_VALUE:    [..., arg1, ..., argN, function]
        // Stack layout for CALL_VALUE_T:  [..., arg1, ..., argN, type_args, function]
        // The function (or type-args list, then function) is at the TOP of
        // the stack — pushed LAST by the compiler — so we pop it first.
        val fn = f.stack.removeLast()
        val targs: HList? = if (hasTypeArgs) f.stack.removeLast() as? HList else null
        val args = popArgs(argc)
        val res = invokeCallable(fn, args, instance = null, nameForError = "<lambda>", typeArgs = targs)
        f.stack.addLast(res)
    }

    private fun callNew(argc: Int, hasTypeArgs: Boolean = false) {
        val f = current
        // Stack layout for CALL_NEW:    [..., arg1, ..., argN, class]
        // Stack layout for CALL_NEW_T:  [..., arg1, ..., argN, type_args, class]
        // The class was pushed FIRST, then (optionally) the type-args list,
        // then the value args on top.  So we pop the value args first,
        // then the type-args list, then the class.
        val args = popArgs(argc)
        val targsList: HList? = if (hasTypeArgs) f.stack.removeLast() as? HList else null
        val cls = f.stack.removeLast()
        if (cls !is HClass) throw HSharpRuntimeError("CALL_NEW on non-class object (got ${cls.type})")
        val resolved = resolveClass(cls)
        val inst = HInstance(mutableMapOf("__class__" to resolved))
        if (targsList != null) {
            // Generics: the call site supplied explicit type arguments
            // (`new Box<int>(42)`).  Stash them on the instance as
            // `__type_args__` so method bodies can introspect them.
            inst.fields["__type_args__"] = targsList
        }
        for ((k, v) in resolved.fields) inst.fields[k] = deepCopy(v)
        val init = resolved.methods["__init__"] ?: resolved.methods["init"]
        if (init != null) {
            // Only auto-call the constructor when the supplied arg count
            // matches the constructor's effective parameter count
            // (excluding `self`).  This preserves backward compatibility
            // with the old convention
            //   `let p = new Point(); p.init(3, 4);`
            // where `new Point()` is expected to NOT invoke the
            // constructor, while still supporting the new
            //   `let p = new Point(3, 4);`
            // convention.  Both `fn init(...)` and `fn __init__(...)`
            // are recognised as constructors.
            val initParams = if (init.args.isNotEmpty() && init.args[0] == "self") init.args.drop(1) else init.args
            if (initParams.size == args.size) {
                invokeHFunction(init, args, instance = inst, parent = current)
            }
        }
        f.stack.addLast(inst)
    }

    private fun invokeCallable(v: HValue, args: List<HValue>, instance: HValue?, nameForError: String, typeArgs: HValue? = null): HValue {
        // Built-in?
        if (v is HNative) return v.call(args)
        // H# user function?
        if (v is HFunction) {
            return invokeHFunction(v, args, instance = instance, parent = current, typeArgs = typeArgs)
        }
        // Bound-method proxy produced by LOAD_ATTR on an HInstance:
        //   HDict({"__method__": HFunction, "__self__": HInstance})
        // This lets `obj.field(args)` and `obj?.method(args)` work when
        // the method was obtained as a value (LOAD_ATTR) rather than
        // dispatched directly (CALL_METHOD).
        if (v is HDict && "__method__" in v.entries && "__self__" in v.entries) {
            val m = v.entries["__method__"] as? HFunction
                ?: throw HSharpRuntimeError("Bound method proxy has non-function __method__")
            val self = v.entries["__self__"]
            return invokeHFunction(m, args, instance = self, parent = current, typeArgs = typeArgs)
        }
        throw HSharpRuntimeError("Cannot call value of type ${v.type} ($nameForError)")
    }

    private fun invokeHFunction(
        func: HFunction,
        args: List<HValue>,
        instance: HValue?,
        parent: HFrame,
        staticClass: HClass? = null,
        typeArgs: HValue? = null,
        // FIX (super-chain): the class in which this method was defined.
        // Stored on the new frame as `__current_class__` so that a
        // nested `super.method()` call knows to resume the search from
        // THIS class's parent (not from the instance's actual class,
        // which never changes). Without this, C→B→A super chains loop
        // forever on B.
        definingClass: HClass? = null
    ): HValue {
        // When called as a bound method (instance != null) the function's
        // first parameter is conventionally `self` and is supplied by the
        // VM (not the caller).  Drop it from the arity check and from the
        // positional binding so `new Point(1,2)` correctly maps to
        // `fn init(self, x, y)` with self=inst, x=1, y=2.
        val methodSelf = instance != null && func.args.isNotEmpty() && func.args[0] == "self"
        val params = if (methodSelf) func.args.drop(1) else func.args
        // Variadic parameters: `fn f(...args)` or `fn f(a, b, ...rest)`.
        // The last parameter collects all trailing positional args into
        // an HList.  A variadic function may ALSO have default values on
        // the fixed parameters preceding the variadic one (e.g.
        // `fn f(a, b=1, ...rest)`); the parser allows defaults before
        // `...rest`.  Order of operations: bind positional args to the
        // fixed params, fill defaults for any fixed params the caller
        // omitted, then collect the remaining args into the variadic
        // list.  None of the three steps may short-circuit the others
        // (Bug 2: previously the variadic path returned early and
        // skipped default-arg filling entirely).
        if (func.isVariadic) {
            val nfixed = params.size - 1
            val nDefaults = func.defaultArgs.size
            val minArgs = nfixed - nDefaults
            if (args.size < minArgs) {
                throw HSharpRuntimeError(
                    "Function ${func.name} expects at least $minArgs args, got ${args.size}")
            }
            val frame = HFrame(func, func.consts, func.instructions, mutableMapOf(), parent)
            // 1. Bind fixed positional params, falling back to defaults
            //    for trailing fixed params the caller did not supply.
            //    Defaults are aligned with the tail of the fixed params
            //    (excluding the variadic capture name), so fixed param
            //    index `i` maps to default index `i - minArgs`.
            for (i in 0 until nfixed) {
                frame.env[params[i]] = if (i < args.size) args[i] else {
                    val di = i - minArgs
                    if (di in func.defaultArgs.indices) func.defaultArgs[di]
                    else throw HSharpRuntimeError(
                        "Function ${func.name} missing argument for ${params[i]}")
                }
            }
            // 2. Collect remaining positional args into the variadic
            //    list.  args.drop(nfixed) is empty when the caller
            //    supplied fewer than nfixed args (the missing fixed
            //    slots were filled from defaults above).
            frame.env[params.last()] = HList(args.drop(nfixed).toMutableList())
            if (instance != null) frame.env["self"] = instance
            if (typeArgs != null) frame.env["__type_args__"] = typeArgs
            if (staticClass != null) frame.env["__static_class__"] = staticClass
            // FIX (super-chain): record the defining class so nested
            // super calls resume the search from the right ancestor.
            if (definingClass != null) frame.env["__current_class__"] = definingClass
            for (fv in func.freevars) {
                val cell = func.closure[fv]
                if (cell != null) frame.env[fv] = cell
                else frame.env[fv] = try { lookup(fv) } catch (_: HSharpRuntimeError) {
                    throw HSharpRuntimeError("Function '${func.name}' references free variable '$fv' which is not in scope")
                }
            }
            val raw = runFrame(frame)
            return if (func.isAsync) HFuture(raw, resolved = true) else raw
        }
        // Default arguments: the trailing parameters may have default
        // values attached to the function object.  Fill in any that the
        // caller omitted.  E.g. `fn f(a, b, c=1, d=2)` called as
        // `f(10, 20)` → effective args = [10, 20, 1, 2].  We allow
        // trailing-omission only (no middle skips, like Python).
        val nDefaults = func.defaultArgs.size
        val minArgs = params.size - nDefaults
        val effectiveArgs = when {
            args.size == params.size -> args
            args.size in minArgs until params.size -> {
                // Append the missing trailing defaults.  The defaults
                // list is aligned with the *tail* of params, so the
                // first missing slot at index `args.size` corresponds
                // to default index `args.size - minArgs`.
                val filled = ArrayList<HValue>(args)
                val skipCount = args.size - minArgs
                for (i in skipCount until nDefaults) {
                    filled.add(func.defaultArgs[i])
                }
                filled
            }
            else -> throw HSharpRuntimeError(
                "Function ${func.name} expects ${params.size} args (min $minArgs), got ${args.size}")
        }

        // Multi-threaded dispatch: a `@parallel` (or `parallel fn`)
        // coroutine is submitted to the DZZW worker pool instead of
        // running on the caller's thread.  The function still
        // produces an HFuture so that `await` works uniformly: the
        // difference is only whether the HFuture's cell is already
        // resolved at the time `invokeHFunction` returns.
        if (func.isParallel) {
            val cell = FutureCell()
            val fut = HFuture(cell)
            // Register with the active structured-concurrency scope, if
            // any.  This is what makes parent cancellation propagate to
            // children: a scope that has been cancelled will call
            // `cell.cancel()` on every child future it knows about.
            currentScope?.add(fut)
            // Capture the caller's frame as the parent so that free
            // variable lookups (e.g. module-level `let W = 80`) inside
            // the worker fall through to the main module's env.  The
            // worker runs on a different thread, but `HFrame` is a
            // passive data structure, so sharing it across threads is
            // safe (the worker only reads it; the main thread isn't
            // mutating it after submission).
            val callerFrame = current
            WorkerPool.defaultPool().submit {
                try {
                    val raw = runOnWorker(func, args, instance, staticClass, typeArgs, parent = callerFrame)
                    cell.complete(raw)
                } catch (t: Throwable) {
                    cell.fail(t)
                }
                // The HFuture is the user-visible result; the lambda's
                // return value is just a sentinel.
                HNull
            }
            return fut
        }

        val frame = HFrame(func, func.consts, func.instructions, mutableMapOf(), parent)
        for ((p, v) in params.zip(effectiveArgs)) frame.env[p] = v
        if (instance != null) frame.env["self"] = instance
        if (typeArgs != null) frame.env["__type_args__"] = typeArgs
        if (staticClass != null) frame.env["__static_class__"] = staticClass
        // FIX (super-chain): record the defining class so nested super
        // calls resume the search from the right ancestor.
        if (definingClass != null) frame.env["__current_class__"] = definingClass
        // Free variables are looked up first in the function's own closure
        // (attached at MAKE_CLOSURE time).  Fall back to the caller's frame
        // for module-level helpers, which don't have a closure.  If neither
        // has the binding, raise rather than silently binding null (a
        // captured variable that resolves to null is a real bug in the
        // user's program and should be surfaced).
        for (fv in func.freevars) {
            val cell = func.closure[fv]
            if (cell != null) {
                frame.env[fv] = cell
            } else {
                frame.env[fv] = try { lookup(fv) } catch (_: HSharpRuntimeError) {
                    throw HSharpRuntimeError("Function '${func.name}' references free variable '$fv' which is not in scope")
                }
            }
        }
        val raw = runFrame(frame)
        // async/await sugar: when the call site invokes an `async fn`,
        // wrap the return value in a Future<T> so that `await` can
        // type-check and unwrap it.  Plain `coro fn` (isCoro without
        // isAsync) keeps its raw coroutine semantics — it stays the
        // low-level API, async/await is the user-facing sugar layer.
        return if (func.isAsync) HFuture(raw, resolved = true) else raw
    }

    /**
     * Worker-thread variant of `runFrame` for `@parallel` functions.
     * Identical semantics, but called from a WorkerPool thread.
     * The frame's `pc` and `env` are local to the worker; the only
     * shared state touched is `globals` (which is a ConcurrentHashMap).
     */
    private fun runOnWorker(
        func: HFunction,
        args: List<HValue>,
        instance: HValue?,
        staticClass: HClass?,
        typeArgs: HValue?,
        parent: HFrame? = null
    ): HValue {
        val methodSelf = instance != null && func.args.isNotEmpty() && func.args[0] == "self"
        val params = if (methodSelf) func.args.drop(1) else func.args
        // Variadic parameters (worker-thread variant — same logic as
        // invokeHFunction, kept inline so the worker doesn't dispatch
        // back through the caller's frame).  Bug 2 fix: also fill
        // default args for fixed params preceding the variadic one.
        if (func.isVariadic) {
            val nfixed = params.size - 1
            val nDefaults = func.defaultArgs.size
            val minArgs = nfixed - nDefaults
            if (args.size < minArgs) {
                throw HSharpRuntimeError(
                    "Function ${func.name} expects at least $minArgs args, got ${args.size}")
            }
            val frame = HFrame(func, func.consts, func.instructions, mutableMapOf(), parent)
            for (i in 0 until nfixed) {
                frame.env[params[i]] = if (i < args.size) args[i] else {
                    val di = i - minArgs
                    if (di in func.defaultArgs.indices) func.defaultArgs[di]
                    else throw HSharpRuntimeError(
                        "Function ${func.name} missing argument for ${params[i]}")
                }
            }
            frame.env[params.last()] = HList(args.drop(nfixed).toMutableList())
            if (instance != null) frame.env["self"] = instance
            if (typeArgs != null) frame.env["__type_args__"] = typeArgs
            if (staticClass != null) frame.env["__static_class__"] = staticClass
            for (fv in func.freevars) {
                val cell = func.closure[fv]
                if (cell != null) frame.env[fv] = cell
                else frame.env[fv] = try { lookup(fv) } catch (_: HSharpRuntimeError) {
                    throw HSharpRuntimeError("Function '${func.name}' references free variable '$fv' which is not in scope")
                }
            }
            return runFrame(frame)
        }
        // Apply default arguments for trailing parameters (same logic
        // as invokeHFunction — kept inline so the worker doesn't need
        // an extra dispatch through the caller's frame).
        val nDefaults = func.defaultArgs.size
        val minArgs = params.size - nDefaults
        val effectiveArgs = when {
            args.size == params.size -> args
            args.size in minArgs until params.size -> {
                val filled = ArrayList<HValue>(args)
                val skipCount = args.size - minArgs
                for (i in skipCount until nDefaults) filled.add(func.defaultArgs[i])
                filled
            }
            else -> args  // let runFrame surface the arity error
        }
        val frame = HFrame(func, func.consts, func.instructions, mutableMapOf(), parent)
        for ((p, v) in params.zip(effectiveArgs)) frame.env[p] = v
        if (instance != null) frame.env["self"] = instance
        if (typeArgs != null) frame.env["__type_args__"] = typeArgs
        if (staticClass != null) frame.env["__static_class__"] = staticClass
        for (fv in func.freevars) {
            val cell = func.closure[fv]
            if (cell != null) {
                frame.env[fv] = cell
            } else {
                frame.env[fv] = try { lookup(fv) } catch (_: HSharpRuntimeError) {
                    throw HSharpRuntimeError("Function '${func.name}' references free variable '$fv' which is not in scope")
                }
            }
        }
        return runFrame(frame)
    }

    private fun sliceValue(target: HValue, start: HValue, end: HValue, step: HValue): HValue {
        fun asInt(v: HValue, default: Int?): Int? = when (v) {
            is HNull -> default
            is HNumber -> v.value.toInt()
            else -> throw HSharpRuntimeError("SLICE indices must be numbers, got ${v::class.simpleName}")
        }
        val stepN = asInt(step, null)
        if (stepN == 0) throw HSharpRuntimeError("SLICE step cannot be zero")
        val useStep = stepN ?: 1
        return when (target) {
            is HString -> {
                val s = target.value
                // FIX: operate on code points, not UTF-16 chars, so
                // supplementary code points (emoji etc.) aren't split.
                val n = codePointLength(s)
                if (useStep < 0) {
                    val indices = negSliceIndices(asInt(start, null), asInt(end, null), n, useStep)
                    HString(indices.joinToString("") { codePointAt(s, it) })
                } else {
                    val (lo, hi) = sliceBounds(asInt(start, 0) ?: 0, asInt(end, n) ?: n, n)
                    if (useStep == 1) HString(codePointSubstring(s, lo, hi))
                    else HString((lo until hi step useStep).joinToString("") { codePointAt(s, it) })
                }
            }
            is HList -> {
                val arr = target.items
                val n = arr.size
                // FIX: handle negative step (reverse slicing) e.g. list[4:0:-1].
                if (useStep < 0) {
                    val indices = negSliceIndices(asInt(start, null), asInt(end, null), n, useStep)
                    HList(indices.map { arr[it] }.toMutableList())
                } else {
                    val (lo, hi) = sliceBounds(asInt(start, 0) ?: 0, asInt(end, n) ?: n, n)
                    if (useStep == 1) HList(arr.subList(lo, hi).toMutableList())
                    else HList((lo until hi step useStep).map { arr[it] }.toMutableList())
                }
            }
            else -> throw HSharpRuntimeError("SLICE on non-indexable ${target::class.simpleName}")
        }
    }

    /**
     * FIX: compute slice indices for a negative step.
     *
     * Python semantics: with step < 0, the slice walks from `start`
     * DOWN to `end` (exclusive), stepping by `step` (a negative number).
     * Default `start` is the last element (n-1); default `end` is "past
     * the beginning" so index 0 is included. Negative bounds wrap by n.
     * Out-of-range indices are clamped to the valid range; only indices
     * inside [0, n) are emitted.
     */
    private fun negSliceIndices(rawStart: Int?, rawEnd: Int?, n: Int, step: Int): List<Int> {
        val start = when {
            rawStart == null -> n - 1
            rawStart < 0 -> rawStart + n
            else -> minOf(rawStart, n - 1)
        }
        val rawEndResolved = when {
            rawEnd == null -> -1
            rawEnd < 0 -> rawEnd + n
            else -> rawEnd
        }
        // Clamp the exclusive lower bound so we never iterate below -1
        // (indices < 0 are never valid, this just avoids wasted loops).
        val end = maxOf(rawEndResolved, -1)
        val result = ArrayList<Int>()
        var i = start
        while (i > end) {
            if (i in 0 until n) result.add(i)
            i += step // step is negative
        }
        return result
    }

    private fun sliceBounds(rawStart: Int, rawEnd: Int, n: Int): Pair<Int, Int> {
        var s = rawStart
        var e = rawEnd
        if (s < 0) s += n
        if (e < 0) e += n
        if (s < 0) s = 0
        if (e < 0) e = 0
        if (e > n) e = n
        if (s > e) s = e
        return s to e
    }

    private fun runFrame(frame: HFrame): HValue {
        current = frame
        try {
            while (true) {
                if (frame.halted || frame.pc >= frame.instrs.size) break
                val (op, arg) = frame.instrs[frame.pc]
                frame.pc++
                try {
                    if (!step(op, arg)) break
                } catch (ex: HSharpException) {
                    dispatchException(ex)
                } catch (ex: HSharpRuntimeError) {
                    dispatchException(HSharpException(HString(ex.message ?: "H# error")))
                } catch (ex: RuntimeException) {
                    // Catch JVM-level errors (IndexOutOfBounds, ClassCast,
                    // IllegalArgument, NumberFormat, Arithmetic, etc.) that
                    // escape from builtins / collection ops and surface them
                    // to H# `try/catch` as catchable exceptions.  Without
                    // this, any Kotlin RuntimeException propagating through
                    // nested lambda calls would kill the VM (mirrors `run()`).
                    dispatchException(HSharpException(HString(ex.message ?: ex::class.simpleName ?: "runtime error")))
                }
            }
        } finally {
            current = frame.parent ?: current
        }
        return frame.retVal
    }

    private fun popArgs(n: Int): List<HValue> {
        val out = ArrayList<HValue>(n)
        repeat(n) { out.add(0, current.stack.removeLast()) }
        return out
    }

    /* =============================================================
     * Exception dispatch (mirrors hsvm's while handlers loop)
     * ============================================================= */
    private fun dispatchException(ex: HSharpException) {
        val f = current
        while (f.handlers.isNotEmpty()) {
            val (target, savedSp, excName) = f.handlers.removeLast()
            while (f.stack.size > savedSp) f.stack.removeLast()
            if (excName == "__propagate__") {
                // `expr?` postfix.  The catch path is the success
                // continuation of the postfix: push the unwrapped
                // exception value as the postfix's result and jump
                // to the target.  This is the runtime half of the
                // `?` operator: the value of `expr?` is the
                // exception payload if `expr` raised, otherwise the
                // normal return value of `expr`.
                f.stack.addLast(ex.value)
                f.pc = target
                return
            }
            f.stack.addLast(ex.value)
            if (excName != "__except__") f.env[excName] = ex.value
            f.pc = target
            return
        }
        // No local handler: rethrow to caller frame
        val parent = f.parent
        if (parent != null) {
            current = parent
            throw ex
        }
        throw HSharpException(ex.value)
    }

    /* =============================================================
     * Attribute / item access (mirrors LOAD_ATTR/STORE_ATTR semantics)
     * ============================================================= */
    private fun loadAttr(obj: HValue, name: String): HValue {
        when (obj) {
            is HDict -> {
                obj.entries[name]?.let { return it }
                throw HSharpRuntimeError("Attribute '$name' not found on dict")
            }
            is HClass -> {
                // Generics-related introspection: `ClassName.__type_params__`
                // returns the list of type-parameter names declared on the
                // class (empty list for non-generic classes).  This mirrors
                // the Python VM's behaviour for class-level metadata.
                if (name == "__type_params__") {
                    return HList(obj.typeParams.map { HString(it) }.toMutableList())
                }
                throw HSharpRuntimeError("Attribute '$name' not found on class")
            }
            is HFunction -> {
                // A handful of read-only attributes are exposed on function
                // values for introspection (e.g. `fn.is_async`,
                // `fn.is_coro`, `fn.is_parallel`, `fn.name`, `fn.args`).
                // These mirror the data-class fields on HFunction; we don't
                // expose the full bytecode/consts/closure surface because
                // that's an implementation detail.
                return when (name) {
                    "name"        -> HString(obj.name)
                    "args"        -> HList(obj.args.map { HString(it) }.toMutableList())
                    "is_coro"     -> HBool(obj.isCoro)
                    "is_async"    -> HBool(obj.isAsync)
                    "is_parallel" -> HBool(obj.isParallel)
                    else -> throw HSharpRuntimeError("Attribute '$name' not found on function")
                }
            }
            is HInstance -> {
                // Private check
                val cls = obj.klass
                if (cls != null && name in cls.privateFields) {
                    val callerSelf = current.env["self"]
                    if (callerSelf !== obj) {
                        // Also allow reads from a static method of the same class
                        val staticCls = current.env["__static_class__"]
                        if (staticCls !== cls) {
                            throw HSharpRuntimeError("Private attribute '$name' access denied")
                        }
                    }
                }
                // Direct field
                obj.fields[name]?.let { return it }
                // Class default field
                cls?.fields?.get(name)?.let { return it }
                // Bound method
                val m = cls?.methods?.get(name)
                if (m != null) {
                    // Return a synthetic bound-method as an HDict-of-{'__method__','__self__'}
                    val proxy = HDict(mutableMapOf("__method__" to m, "__self__" to obj))
                    return proxy
                }
                // Generics-related fallbacks.  Reading `__type_args__` on an
                // instance of a non-generic class (or before the call site
                // provided explicit type arguments) should yield nullptr
                // rather than raise an Attribute-not-found error, matching
                // Python's behaviour.
                if (name == "__type_args__") return HNull
                throw HSharpRuntimeError("Attribute '$name' not found on object")
            }
            else -> throw HSharpRuntimeError("Cannot load attribute on ${obj.type}")
        }
    }

    private fun storeAttr(obj: HValue, name: String, v: HValue) {
        when (obj) {
            is HDict -> obj.entries[name] = v
            is HInstance -> {
                val cls = obj.klass
                if (cls != null && name in cls.privateFields) {
                    val callerSelf = current.env["self"]
                    if (callerSelf !== obj) {
                        // Also allow writes from a static method of the same class
                        val staticCls = current.env["__static_class__"]
                        if (staticCls !== cls) {
                            throw HSharpRuntimeError("Private attribute '$name' write denied")
                        }
                    }
                }
                obj.fields[name] = v
            }
            else -> throw HSharpRuntimeError("STORE_ATTR target is not an object")
        }
    }

    /* =============================================================
     * Code-point-based string helpers.
     *
     * H# strings are sequences of Unicode code points, but Kotlin's
     * String is UTF-16: supplementary code points (e.g. emoji) occupy
     * two chars.  Indexing/slicing/iterating by `s.length` or
     * `s.substring(lo, hi)` would split surrogate pairs and produce
     * garbage.  These helpers operate on code-point indices instead.
     * ============================================================= */
    private fun codePointLength(s: String): Int = s.codePointCount(0, s.length)

    /** The code point at code-point index `cpIndex` as a 1-or-2-char
     *  String; empty string if out of range. */
    private fun codePointAt(s: String, cpIndex: Int): String {
        var idx = 0
        var cp = 0
        while (cp < cpIndex && idx < s.length) {
            idx += Character.charCount(s.codePointAt(idx))
            cp++
        }
        return if (idx < s.length) String(Character.toChars(s.codePointAt(idx))) else ""
    }

    /** Substring by code-point range [start, end).  Out-of-range
     *  bounds are clamped; returns "" if start >= end. */
    private fun codePointSubstring(s: String, start: Int, end: Int): String {
        val len = codePointLength(s)
        val s2 = start.coerceIn(0, len)
        val e2 = end.coerceIn(0, len)
        if (s2 >= e2) return ""
        var idx = 0
        var cp = 0
        while (cp < s2 && idx < s.length) {
            idx += Character.charCount(s.codePointAt(idx))
            cp++
        }
        val startIdx = idx
        while (cp < e2 && idx < s.length) {
            idx += Character.charCount(s.codePointAt(idx))
            cp++
        }
        return s.substring(startIdx, idx)
    }

    /** Convert a code-point index to a UTF-16 char index, clamped to
     *  [0, s.length].  Used to bridge code-point offsets (H# level)
     *  with String.indexOf (UTF-16 level) in find(). */
    private fun codePointToCharIndex(s: String, cpIndex: Int): Int {
        var idx = 0
        var cp = 0
        while (cp < cpIndex && idx < s.length) {
            idx += Character.charCount(s.codePointAt(idx))
            cp++
        }
        return idx
    }

    private fun getItem(left: HValue, idx: HValue): HValue = when (left) {
        is HList -> {
            val i = HValueOps.toLong(idx).toInt()
            val n = left.items.size
            val real = if (i < 0) i + n else i
            if (real < 0 || real >= n) throw HSharpRuntimeError("list index out of range: $i (size $n)")
            left.items[real]
        }
        is HDict -> left.entries[coerceKey(idx)]
            ?: throw HSharpRuntimeError("Key '${coerceKey(idx)}' not in dict")
        is HString -> {
            val i = HValueOps.toLong(idx).toInt()
            val n = codePointLength(left.value)
            val real = if (i < 0) i + n else i
            if (real < 0 || real >= n) throw HSharpRuntimeError("string index out of range: $i (length $n)")
            HString(codePointAt(left.value, real))
        }
        else -> throw HSharpRuntimeError("Cannot index ${left.type}")
    }

    private fun setItem(left: HValue, idx: HValue, v: HValue) {
        when (left) {
            is HList -> {
                val i = HValueOps.toLong(idx).toInt()
                val n = left.items.size
                val real = if (i < 0) i + n else i
                if (real < 0 || real >= n) throw HSharpRuntimeError("list index out of range: $i (size $n)")
                left.items[real] = v
            }
            is HDict -> left.entries[coerceKey(idx)] = v
            else -> throw HSharpRuntimeError("Cannot SET_ITEM on ${left.type}")
        }
    }

    private fun coerceKey(v: HValue): String = when (v) {
        is HString -> v.value
        is HNumber -> v.toDisplayString()
        is HBool -> if (v.value) "true" else "false"
        is HNull -> "null"
        else -> v.toDisplayString()
    }

    private fun binAdd(a: HValue, b: HValue): HValue {
        // FIX: a list/dict on the LEFT of `+` used to fall through to
        // the string-coercion branches and produce nonsense like
        // "[1, 2]hello" (Bug 9: `list + string` type confusion).  Now
        // a list/dict only concatenates with its own kind; any other
        // right operand is a type error.  `string + list` (string on
        // the left) is unchanged — string is the dominant type there
        // and the coercion is the documented "string + anything" path.
        if (a is HList && b is HList) return HList((a.items + b.items).toMutableList())
        if (a is HList) throw HSharpRuntimeError("cannot add list and ${b.type}")
        if (a is HDict && b is HDict) {
            val merged = LinkedHashMap(a.entries)
            merged.putAll(b.entries)
            return HDict(merged)
        }
        if (a is HDict) throw HSharpRuntimeError("cannot add dict and ${b.type}")
        return when {
            a is HString && b !is HString -> HString(a.value + b.toDisplayString())
            b is HString && a !is HString -> HString(a.toDisplayString() + b.value)
            a is HString && b is HString -> HString(a.value + b.value)
            // C VM: preserve int when both operands are exact integers
            a is HNumber && b is HNumber && a.value == a.value.toLong().toDouble() &&
                b.value == b.value.toLong().toDouble() && a.value > Long.MIN_VALUE.toDouble() &&
                a.value < Long.MAX_VALUE.toDouble() && b.value > Long.MIN_VALUE.toDouble() &&
                b.value < Long.MAX_VALUE.toDouble() ->
                HNumber((a.value.toLong() + b.value.toLong()).toDouble())
            else -> HNumber(HValueOps.toDouble(a) + HValueOps.toDouble(b))
        }
    }

    private fun binSub(a: HValue, b: HValue): HValue {
        return when {
            a is HList -> {
                val rm = HValueOps.toDouble(b).toInt()
                HList(a.items.drop(rm).toMutableList())
            }
            // C VM: preserve int when both operands are exact integers
            a is HNumber && b is HNumber && a.value == a.value.toLong().toDouble() &&
                b.value == b.value.toLong().toDouble() && a.value > Long.MIN_VALUE.toDouble() &&
                a.value < Long.MAX_VALUE.toDouble() && b.value > Long.MIN_VALUE.toDouble() &&
                b.value < Long.MAX_VALUE.toDouble() ->
                HNumber((a.value.toLong() - b.value.toLong()).toDouble())
            else -> HNumber(HValueOps.toDouble(a) - HValueOps.toDouble(b))
        }
    }

    private fun binMul(a: HValue, b: HValue): HValue {
        return when (a) {
            is HString -> HString(a.value.repeat(HValueOps.toLong(b).toInt()))
            is HList -> {
                val n = HValueOps.toLong(b).toInt()
                HList((0 until n).flatMap { a.items }.toMutableList())
            }
            // C VM: preserve int when both operands are exact integers
            is HNumber -> {
                if (b is HString) {
                    // FIX: support `int * str` symmetrically with `str * int`
                    // (previously only `"ab" * 3` worked; `3 * "ab"` threw).
                    val m = a.value.toLong().toInt()
                    if (m < 0) throw HSharpRuntimeError("cannot multiply string by negative number")
                    HString(b.value.repeat(m))
                } else if (b is HList) {
                    // FIX: support `int * list` symmetrically with `list * int`
                    // (previously only `[1,2] * 3` worked; `3 * [1,2]` threw
                    // because the HNumber branch only checked for HString).
                    val m = a.value.toLong().toInt()
                    if (m < 0) throw HSharpRuntimeError("cannot multiply list by negative number")
                    HList((0 until m).flatMap { b.items }.toMutableList())
                } else if (a.value == a.value.toLong().toDouble() && a.value > Long.MIN_VALUE.toDouble() &&
                    a.value < Long.MAX_VALUE.toDouble() && b is HNumber &&
                    b.value == b.value.toLong().toDouble() && b.value > Long.MIN_VALUE.toDouble() &&
                    b.value < Long.MAX_VALUE.toDouble()) {
                    HNumber((a.value.toLong() * b.value.toLong()).toDouble())
                } else {
                    // FIX: use full double for both operands (was
                    // `* n` which silently truncated the fractional
                    // part of the second operand).
                    HNumber(HValueOps.toDouble(a) * HValueOps.toDouble(b))
                }
            }
            else -> HNumber(HValueOps.toDouble(a) * HValueOps.toDouble(b))
        }
    }

    /** Total-order comparator for HValues, used by `sort()` and by list
     *  lexicographic comparison in [compareOp].  Returns negative / zero /
     *  positive like Kotlin's `compareTo`.
     *
     *  - Same-type pairs compare by value (numbers by magnitude, strings
     *    lexicographically, bools false<true, lists element-by-element
     *    lexicographically with the shorter list ordered first when it is a
     *    prefix, dicts by size then by entry-wise comparison).
     *  - Different-type pairs compare by type name, so the order is total
     *    (no ClassCast / NaN surprises) and stable.
     *  - HList comparison recurses through this function so nested lists
     *    (`[[1,2],[1,3]]`) compare correctly. */
    private fun hValueCompare(a: HValue, b: HValue): Int {
        // Same-type fast paths
        when {
            a is HNumber && b is HNumber -> return a.value.compareTo(b.value)
            a is HString && b is HString -> return a.value.compareTo(b.value)
            a is HBool && b is HBool -> return a.value.compareTo(b.value)
            a is HNull && b is HNull -> return 0
            a is HList && b is HList -> {
                val n = minOf(a.items.size, b.items.size)
                for (i in 0 until n) {
                    val c = hValueCompare(a.items[i], b.items[i])
                    if (c != 0) return c
                }
                return a.items.size - b.items.size
            }
            a is HDict && b is HDict -> {
                val c = a.entries.size - b.entries.size
                if (c != 0) return c
                val ae = a.entries.entries.iterator()
                val be = b.entries.entries.iterator()
                while (ae.hasNext() && be.hasNext()) {
                    val ea = ae.next(); val eb = be.next()
                    val kc = ea.key.compareTo(eb.key)
                    if (kc != 0) return kc
                    val vc = hValueCompare(ea.value, eb.value)
                    if (vc != 0) return vc
                }
                return 0
            }
        }
        // Different types: order by type name so the sort is total.
        return a.type.name.compareTo(b.type.name)
    }

    private fun compareOp(op: String, a: HValue, b: HValue): Boolean {
        if (op == "EQEQ") return HValueOps.equals(a, b)
        if (op == "BANGEQ") return !HValueOps.equals(a, b)
        // Membership: `x in y` / `x not in y`.  Supports list, dict
        // (key membership), and string (substring membership).
        if (op == "IN" || op == "NOTIN") {
            val contains = when (b) {
                is HList -> b.items.any { HValueOps.equals(it, a) }
                is HDict -> {
                    // FIX: route through coerceKey() so integer keys
                    // produce "1" (not "1.0"), matching dict assignment
                    // and lookup. Previously this used a.value.toString()
                    // for HNumber, which broke `1 in dict` after
                    // `dict[1] = ...`.
                    // NOTE: use containsKey(key), NOT `key in b.entries`
                    // — b.entries is a Set<Entry>, so `key in entries`
                    // would check for Entry equality, always false.
                    val key = coerceKey(a)
                    b.entries.containsKey(key)
                }
                is HString -> {
                    val needle = when (a) {
                        is HString -> a.value
                        else -> a.toDisplayString()
                    }
                    needle in b.value
                }
                else -> throw HSharpRuntimeError("'in' expects list/dict/string, got ${b.type}")
            }
            return if (op == "IN") contains else !contains
        }
        if (a is HString && b is HString) {
            val c = a.value.compareTo(b.value)
            return when (op) { "GT" -> c > 0; "LT" -> c < 0; "GTE" -> c >= 0; "LTE" -> c <= 0; else -> error("bad cmp $op") }
        }
        // FIX: list/dict lexicographic comparison.  Previously two lists
        // fell through to `toDouble`, which threw for non-empty lists.
        // Now `[1,2] < [1,3]` and `[1] < [1,2]` work like Python's
        // element-wise ordering.  HDict compares by size then entries.
        if ((a is HList && b is HList) || (a is HDict && b is HDict)) {
            val c = hValueCompare(a, b)
            return when (op) { "GT" -> c > 0; "LT" -> c < 0; "GTE" -> c >= 0; "LTE" -> c <= 0; else -> error("bad cmp $op") }
        }
        val x = HValueOps.toDouble(a)
        val y = HValueOps.toDouble(b)
        return when (op) { "GT" -> x > y; "LT" -> x < y; "GTE" -> x >= y; "LTE" -> x <= y; else -> error("bad cmp $op") }
    }

    /* =============================================================
     * Class / inheritance / instance-of
     * ============================================================= */
    private fun resolveClass(c: HClass): HClass {
        if (c.base == null) return c
        val base = (lookup(c.base) as? HClass) ?: throw HSharpRuntimeError("Base class ${c.base} not found")
        val resolvedBase = resolveClass(base)
        val merged = HClass(
            name = c.name,
            methods = LinkedHashMap(resolvedBase.methods).apply { putAll(c.methods) },
            fields = LinkedHashMap(resolvedBase.fields).apply { putAll(c.fields) },
            privateFields = (resolvedBase.privateFields + c.privateFields).toMutableList(),
            base = c.base,
            implements = (resolvedBase.implements + c.implements).toMutableList(),
            staticMethods = LinkedHashMap(resolvedBase.staticMethods).apply { putAll(c.staticMethods) }
        )
        return merged
    }

    private fun isInstance(obj: HValue, typeName: String): Boolean {
        // FIX: primitive type checks (aligned with typeMatch).  Previously
        // `x is int` / `x is str` / etc. returned false for every non-
        // instance value, which made `is` useless on built-in types.
        when (obj) {
            is HNumber -> {
                if (typeName == "int") {
                    val v = obj.value
                    return v == v.toLong().toDouble() &&
                        v >= Long.MIN_VALUE.toDouble() && v <= Long.MAX_VALUE.toDouble()
                }
                return typeName == "float" || typeName == "number"
            }
            is HString -> return typeName == "str" || typeName == "string"
            is HBool -> return typeName == "bool"
            is HList -> return typeName == "list"
            is HDict -> return typeName == "dict"
            is HNull -> return typeName == "null"
            is HChannel -> return typeName == "chan" || typeName == "channel"
            is HFunction -> return typeName == "function" || typeName == "fn"
            else -> { /* HInstance / HClass / HUnion / HNative / HFuture / HTask: fall through to the class check below. */ }
        }
        if (obj !is HInstance) return false
        val cls = obj.klass ?: return false
        return isInstanceOfClass(cls, typeName)
    }

    /** Recursively check if a class (or any of its bases) matches typeName. */
    private fun isInstanceOfClass(cls: HClass, typeName: String): Boolean {
        if (cls.name == typeName) return true
        // Check interfaces, recursing into each interface's parent
        // interfaces (interface extends interface).  A class that
        // implements A, where A extends B, is also an instance of B.
        val visited = mutableSetOf<String>()
        for (iface in cls.implements) {
            if (interfaceMatches(iface, typeName, visited)) return true
        }
        // Walk up the base class chain
        var baseName = cls.base
        while (baseName != null) {
            val base = try { lookup(baseName) as? HClass } catch (_: Throwable) { null }
            if (base != null) {
                if (base.name == typeName) return true
                for (iface in base.implements) {
                    if (interfaceMatches(iface, typeName, visited)) return true
                }
                baseName = base.base
            } else {
                break
            }
        }
        return false
    }

    /** Recursively check whether interface `ifaceName` (or any of its
     *  parent interfaces, reached via the interface's `extends` chain)
     *  matches `typeName`.  Interfaces may be registered at runtime as
     *  HClass objects whose `implements` field holds the parent
     *  interface names; if the interface is a pure compile-time
     *  construct and is not present at runtime, this returns false
     *  (no match, but no crash either).  `visited` guards against
     *  cycles in the interface hierarchy. */
    private fun interfaceMatches(ifaceName: String, typeName: String, visited: MutableSet<String>): Boolean {
        if (ifaceName == typeName) return true
        if (!visited.add(ifaceName)) return false  // cycle guard
        val iface = globals[ifaceName] as? HClass ?: return false
        for (parent in iface.implements) {
            if (interfaceMatches(parent, typeName, visited)) return true
        }
        return false
    }

    /* =============================================================
     * Pattern matching helper
     *
     * Implements the seven pattern kinds the compiler emits in
     * `_pattern_to_const`:
     *   wildcard  : `_`                — always matches
     *   binding   : `x`                — always matches, binds x = scrutinee
     *   literal   : `42` / `"s"` / …  — H# structural equality
     *   type      : `is T [as x]`     — class/union membership + optional bind
     *   variant   : `Variant(x,y,..)` — union variant + payload bindings
     *   chan_send : `chan send(v)`    — channel can accept a send
     *   chan_recv : `chan recv(v)`    — channel has a pending value
     *   chan_close: `chan close`      — channel is closed
     *
     * Bindings are written into the current frame's `env` so the body
     * of the arm (on the right-hand side of `=>`) can read them.
     * ============================================================= */
    private fun matchPattern(f: HFrame, pat: HDict, scrutinee: HValue): Boolean {
        val kind = (pat.entries["kind"] as? HString)?.value ?: return false
        return when (kind) {
            "wildcard" -> true
            "binding" -> {
                val name = (pat.entries["name"] as? HString)?.value ?: return false
                f.env[name] = scrutinee
                true
            }
            "literal" -> literalEq(pat.entries["literal"], scrutinee)
            "type" -> {
                val typeName = (pat.entries["type_name"] as? HString)?.value ?: return false
                val binding = (pat.entries["binding"] as? HString)?.value
                if (!typeMatch(scrutinee, typeName)) return false
                if (binding != null) f.env[binding] = scrutinee
                true
            }
            "variant" -> {
                val variant = (pat.entries["variant"] as? HString)?.value ?: return false
                val ui = scrutinee as? HInstance ?: return false
                if ((ui.fields["__variant__"] as? HString)?.value != variant) return false
                val names = (pat.entries["names"] as? HList)?.items ?: emptyList()
                // Bind payload fields by POSITION, not by the binding name.
                // A `Some(v)` pattern's `v` should bind to the first payload
                // field of the Some variant, regardless of what that field
                // is called in the union definition.  We collect the union's
                // declared field order from the variant descriptor, then map
                // pattern binding names to those positions in order.
                val unionName = (ui.fields["__union__"] as? HString)?.value
                val fieldOrder: List<String> = if (unionName != null) {
                    val union = globals[unionName] as? HUnion
                    union?.variants?.firstOrNull { it.first == variant }?.second ?: emptyList()
                } else emptyList()
                for ((i, n) in names.withIndex()) {
                    val name = (n as? HString)?.value ?: continue
                    // Position 0 is the first declared payload field; if we
                    // can't resolve the descriptor, fall back to a positional
                    // scan of non-meta fields.
                    val key = fieldOrder.getOrNull(i)
                        ?: ui.fields.entries.filter { it.key !in listOf("__class__", "__union__", "__variant__") }.getOrNull(i)?.key
                        ?: name
                    f.env[name] = ui.fields[key] ?: HNull
                }
                true
            }
            "chan_send" -> {
                val ch = scrutinee as? HChannel ?: return false
                if (ch.closed) return false
                // For an unbuffered channel (capacity == 0) the queue
                // can hold at most one item: a sender parks until a
                // receiver takes the value.  So `chan send(_)` should
                // only match when there's room to send — for
                // unbuffered that's size < 1, for bounded it's
                // size < capacity.  Using `(capacity == 0 ||
                // size < capacity)` would match an unbuffered channel
                // even when it already holds a pending item, which is
                // wrong: a second send would block.
                val sendsOk = ch.size() <
                    (if (ch.capacity == 0) 1 else ch.capacity)
                if (!sendsOk) return false
                // The optional binding name in `chan send(v)` is
                // bound to `true` — a placeholder that says "the
                // send would have been possible".  This keeps the
                // arm body able to refer to `v` without crashing
                // on undefined-name.
                (pat.entries["name"] as? HString)?.value?.let {
                    f.env[it] = HBool(true)
                }
                true
            }
            "chan_recv" -> {
                val ch = scrutinee as? HChannel ?: return false
                if (ch.size() <= 0) return false
                // `chan recv(v)` binds v to the first queued
                // value (peek).  The body then sees `v` as the
                // value that *would* be received.  We don't
                // actually pop the value — matching is a pure
                // observation, the arm body decides whether to
                // call `chan_recv` to actually consume it.
                (pat.entries["name"] as? HString)?.value?.let { name ->
                    val peeked = ch.peek()
                    if (peeked != null) f.env[name] = peeked
                }
                true
            }
            "chan_close" -> {
                val ch = scrutinee as? HChannel ?: return false
                ch.closed
            }
            else -> false
        }
    }

    /** H# structural equality used by the `literal` pattern kind. */
    private fun literalEq(lit: HValue?, scrutinee: HValue): Boolean {
        if (lit == null) return scrutinee is HNull
        return HValueOps.equals(lit, scrutinee)
    }

    /** H# type-membership test for the `is T` pattern kind.
     *
     * Accepts both class instances and union values.  The string
     * `"int"` / `"float"` / `"str"` / `"bool"` / `"list"` / `"dict"`
     * / `"chan"` map onto the corresponding built-in HValue subtypes;
     * any other name is treated as a class / union name resolved via
     * the current `env` / globals.  */
    private fun typeMatch(scrutinee: HValue, typeName: String): Boolean {
        when (typeName) {
            "int", "float" -> {
                if (scrutinee !is HNumber) return false
                if (typeName == "int") {
                    val v = scrutinee.value
                    return v == v.toLong().toDouble() &&
                        v >= Long.MIN_VALUE.toDouble() && v <= Long.MAX_VALUE.toDouble()
                }
                return true
            }
            "str"  -> return scrutinee is HString
            "bool" -> return scrutinee is HBool
            "list" -> return scrutinee is HList
            "dict" -> return scrutinee is HDict
            "chan" -> return scrutinee is HChannel
            "null" -> return scrutinee is HNull
        }
        // Class / union name: use the existing isInstance helper.
        return isInstance(scrutinee, typeName)
    }

    /* =============================================================
     * For-loop iteration
     *
     * The Python VM keeps the iterator state on the VM stack itself
     * (a special dict {"__is_iter": True, "__iterable": [...], ...}).
     * First call: stack top is the ('__ITER__', var1, var2) tuple
     *             (parsed as an HList of [string, string, null]).
     *             Below it is the iterable.  We pop the tuple, pop the
     *             iterable, prime the loop, and push the iterator dict.
     * Subsequent: stack top is the iterator dict.  Advance the counter;
     *             if exhausted, pop the iterator and jump to the end.
     * ============================================================= */
    private fun forIter(jumpTarget: Int) {
        val f = current
        if (f.stack.isEmpty()) {
            f.pc = jumpTarget
            return
        }
        val top = f.stack.last()
        // Case 1: existing iterator on top
        if (top is HDict && top.entries["__is_iter"] == HBool(true)) {
            val it = top
            val iterList = (it.entries["__iterable"] as? HList)?.items
            val iterStr = (it.entries["__iterable"] as? HString)?.value
            var idx = HValueOps.toLong(it.entries["__iter_idx"] ?: HNumber(0.0)).toInt()
            val v1 = (it.entries["__var1"] as? HString)?.value ?: "i"
            val v2 = (it.entries["__var2"] as? HString)?.value
            val dict = it.entries["__dict"] as? HDict
            if (iterStr != null) {
                // String iteration: each char is a single code point
                // (FIX: was UTF-16 char, which split surrogate pairs).
                val cpLen = codePointLength(iterStr)
                if (idx < cpLen) {
                    val ch = codePointAt(iterStr, idx)
                    // FIX: two-var string iteration (`for i, c in "abc"`)
                    // sets v1 = index, v2 = char (matching list two-var
                    // semantics).  Previously the `v2 != null && dict`
                    // branch was dead code for strings (__dict was never
                    // set in forIterFirst), so v2 kept a stale value.
                    if (v2 != null) {
                        f.env[v1] = HNumber(idx.toDouble())
                        f.env[v2] = HString(ch)
                    } else {
                        f.env[v1] = HString(ch)
                    }
                    it.entries["__iter_idx"] = HNumber((idx + 1).toDouble())
                } else {
                    f.stack.removeLast()
                    f.pc = jumpTarget
                }
            } else if (iterList != null) {
                if (idx < iterList.size) {
                    if (v2 != null && dict != null) {
                        val key = (iterList[idx] as? HString)?.value ?: iterList[idx].toDisplayString()
                        f.env[v1] = HString(key)
                        f.env[v2] = dict.entries[key] ?: HNull
                    } else if (v2 != null) {
                        // FIX: list iteration with two vars (`for k, v in list`):
                        // v1 = current index, v2 = element at that index.
                        // Previously this branch was unreachable because it
                        // was gated on `dict != null` (only set for dicts),
                        // so v2 kept a stale value.
                        f.env[v1] = HNumber(idx.toDouble())
                        f.env[v2] = iterList[idx]
                    } else {
                        f.env[v1] = iterList[idx]
                    }
                    it.entries["__iter_idx"] = HNumber((idx + 1).toDouble())
                } else {
                    f.stack.removeLast()
                    f.pc = jumpTarget
                }
            } else {
                f.stack.removeLast()
                f.pc = jumpTarget
            }
            return
        }
        // Case 2: new-pattern config tuple ('__ITER__', var1, var2)
        if (top is HList && top.items.size == 3 &&
            (top.items[0] as? HString)?.value == "__ITER__") {
            f.stack.removeLast()            // pop the tuple
            val var1 = (top.items[1] as? HString)?.value ?: "i"
            val var2 = (top.items[2] as? HString)?.value
            if (f.stack.isEmpty()) { f.pc = jumpTarget; return }
            val iterable = f.stack.removeLast()
            forIterFirst(iterable, var1, var2, jumpTarget)
            return
        }
        // Case 3: legacy pattern (iterable already on top, no config)
        val iterable = f.stack.removeLast()
        forIterFirst(iterable, "i", null, jumpTarget)
    }

    private fun forIterFirst(iterable: HValue, var1: String, var2: String?, jumpTarget: Int) {
        val f = current
        when (iterable) {
            is HList -> {
                if (iterable.items.isEmpty()) { f.pc = jumpTarget; return }
                // FIX: when iterating a list with two loop vars
                // (`for k, v in someList`), var1 must be the INDEX and
                // var2 the element. Previously var1 got the element and
                // var2 was never set (stale), because the two-var
                // handling only existed for the dict path.
                if (var2 != null) {
                    f.env[var1] = HNumber(0.0)
                    f.env[var2] = iterable.items[0]
                } else {
                    f.env[var1] = iterable.items[0]
                }
                val it = HDict(LinkedHashMap<String, HValue>().apply {
                    put("__is_iter", HBool(true))
                    put("__iterable", HList(iterable.items.toMutableList()))
                    put("__iter_idx", HNumber(1.0))
                    put("__var1", HString(var1))
                    if (var2 != null) put("__var2", HString(var2))
                })
                f.stack.addLast(it)
            }
            is HString -> {
                if (iterable.value.isEmpty()) { f.pc = jumpTarget; return }
                // FIX: iterate by code point so a supplementary char
                // (e.g. emoji) is yielded as one element, not two
                // surrogate halves.
                // FIX: two-var string iteration (`for i, c in "abc"`)
                // now sets var1 = index, var2 = char (matching the
                // list two-var semantics).  Previously var2 was never
                // set because the HString branch neither set __dict
                // nor handled v2 directly.
                if (var2 != null) {
                    f.env[var1] = HNumber(0.0)
                    f.env[var2] = HString(codePointAt(iterable.value, 0))
                } else {
                    f.env[var1] = HString(codePointAt(iterable.value, 0))
                }
                val it = HDict(LinkedHashMap<String, HValue>().apply {
                    put("__is_iter", HBool(true))
                    put("__iterable", HString(iterable.value))
                    put("__iter_idx", HNumber(1.0))
                    put("__var1", HString(var1))
                    if (var2 != null) put("__var2", HString(var2))
                })
                f.stack.addLast(it)
            }
            is HDict -> {
                val keys = iterable.entries.keys.toList()
                if (keys.isEmpty()) { f.pc = jumpTarget; return }
                f.env[var1] = HString(keys[0])
                if (var2 != null) f.env[var2] = iterable.entries[keys[0]] ?: HNull
                val it = HDict(LinkedHashMap<String, HValue>().apply {
                    put("__is_iter", HBool(true))
                    put("__iterable", HList(keys.map { HString(it) }.toMutableList()))
                    put("__dict", iterable)
                    put("__iter_idx", HNumber(1.0))
                    put("__var1", HString(var1))
                    if (var2 != null) put("__var2", HString(var2))
                })
                f.stack.addLast(it)
            }
            else -> throw HSharpRuntimeError("FOR_ITER: unsupported iterable ${iterable.type.name.lowercase()}")
        }
    }

    /* =============================================================
     * Scope/name lookup (current env → parents → globals → builtins)
     * ============================================================= */
    fun lookup(name: String): HValue {
        val f = current
        // 1. Current frame env: locals, params, captured freevars, `self`.
        f.env[name]?.let { return it }
        // 2. self fields & class methods — checked BEFORE globals so a
        //    same-named global no longer shadows a field when reading a
        //    bare name inside a method.  This mirrors STORE_NAME, which
        //    routes field writes to self.fields[name]; reads must be
        //    consistent or methods would see globals instead of their
        //    own fields.  The bound-method proxy shape matches what
        //    LOAD_ATTR produces for `obj.method` (understood by
        //    invokeCallable()).
        val self = f.env["self"] as? HInstance
        if (self != null) {
            self.fields[name]?.let { return it }
            val cls = self.klass
            cls?.fields?.get(name)?.let { return it }
            cls?.let { c ->
                c.methods[name]?.let { m ->
                    return HDict(mutableMapOf("__method__" to m, "__self__" to self))
                }
            }
        }
        // 3. Caller frame chain (parent frames — the dynamic call chain).
        var p = f.parent
        while (p != null) {
            p.env[name]?.let { return it }
            p = p.parent
        }
        // 4. Globals
        globals[name]?.let { return it }
        // 5. Builtins
        HNativeBridge.builtins[name]?.let { return it }
        throw HSharpRuntimeError("Undefined name: $name")
    }

    private fun deepCopy(v: HValue): HValue = when (v) {
        is HList -> HList(v.items.map(::deepCopy).toMutableList())
        is HDict -> HDict(v.entries.mapValues { deepCopy(it.value) }.toMutableMap())
        is HInstance -> HInstance(v.fields.mapValues { deepCopy(it.value) }.toMutableMap())
        else -> v
    }
}
