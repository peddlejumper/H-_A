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
     *  join semantics). */
    var currentScope: ConcurrentScope? = null

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
                val d = LinkedHashMap<String, HValue>()
                repeat(n) {
                    val v = f.stack.removeLast()
                    val k = f.stack.removeLast()
                    d[coerceKey(k)] = v
                }
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
                // Python VM uses floor division (//)
                val da = HValueOps.toDouble(a)
                val result = Math.floor(da / db)
                f.stack.addLast(HNumber(result)) }
            "BINARY_MOD" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast();
                if (HValueOps.toDouble(b) == 0.0) throw HSharpRuntimeError("modulo by zero")
                f.stack.addLast(HNumber(HValueOps.toDouble(a) % HValueOps.toDouble(b))) }
            "BINARY_BITAND" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) and HValueOps.toLong(b)).toDouble())) }
            "BINARY_BITOR"  -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) or  HValueOps.toLong(b)).toDouble())) }
            "BINARY_BITXOR" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) xor HValueOps.toLong(b)).toDouble())) }
            "BINARY_LSHIFT" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) shl HValueOps.toLong(b).toInt()).toDouble())) }
            "BINARY_RSHIFT" -> { val b = f.stack.removeLast(); val a = f.stack.removeLast(); f.stack.addLast(HNumber((HValueOps.toLong(a) shr HValueOps.toLong(b).toInt()).toDouble())) }

            "UNARY_NOT" -> {
                val v = f.stack.removeLast()
                // C VM behaviour: nil → true, bool → !bool, everything else → false
                f.stack.addLast(HBool(
                    when (v) {
                        is HBool -> !v.value
                        is HNull -> true
                        else -> false
                    }
                ))
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
                    closure = mutableMapOf()
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
                val scope = currentScope ?: throw HSharpRuntimeError("CONCURRENT_EXIT without CONCURRENT_ENTER")
                val stack = scopeStack.get()
                val parent = if (stack.isEmpty()) null else stack.removeLast()
                try {
                    scope.join()
                } finally {
                    currentScope = parent
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
            "CAST" -> { /* type hints only */ }
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
            val sm = inst.staticMethods[name]
                ?: throw HSharpRuntimeError("Static method '$name' not found on class ${inst.name}")
            val res = invokeHFunction(sm, args, instance = null, parent = current, staticClass = inst)
            f.stack.addLast(res)
            return
        }
        if (inst !is HInstance) throw HSharpRuntimeError("CALL_METHOD on non-instance ($name)")
        val cls = inst.klass ?: throw HSharpRuntimeError("Instance has no __class__")
        val mfunc = cls.methods[name] ?: throw HSharpRuntimeError("Method '$name' not found on ${cls.name}")
        val res = invokeHFunction(mfunc, args, instance = inst, parent = current, typeArgs = targs)
        f.stack.addLast(res)
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
                HNumber(self.value.length.toDouble())
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
                HNumber(self.value.indexOf(p).toDouble())
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
                HList(self.value.split(sep).map { HString(it) }.toMutableList())
            }
            "join" -> {
                require(args.size == 1) { "join() takes exactly 1 argument" }
                val lst = args[0] as? HList
                    ?: throw HSharpRuntimeError("join() expects a list")
                HString(lst.items.joinToString(self.value) { (it as HString).value })
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
                require(args.isEmpty()) { "pop() takes no arguments" }
                if (self.items.isEmpty())
                    throw HSharpRuntimeError("pop from empty list")
                self.items.removeAt(self.items.size - 1)
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

    private fun callSuper(name: String, argc: Int) {
        val f = current
        val args = popArgs(argc)
        val inst = f.env["self"] as? HInstance
            ?: throw HSharpRuntimeError("super() can only be called within a method")
        val cls = inst.klass ?: throw HSharpRuntimeError("self has no __class__")
        // Walk up the base class chain to find the method
        var baseName = cls.base
        while (baseName != null) {
            val base = (lookup(baseName) as? HClass)
                ?: throw HSharpRuntimeError("Base class $baseName not found")
            val mfunc = base.methods[name]
            if (mfunc != null) {
                val res = invokeHFunction(mfunc, args, instance = inst, parent = current)
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
        val init = resolved.methods["__init__"]
        if (init != null) {
            invokeHFunction(init, args, instance = inst, parent = current)
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
        throw HSharpRuntimeError("Cannot call value of type ${v.type} ($nameForError)")
    }

    private fun invokeHFunction(
        func: HFunction,
        args: List<HValue>,
        instance: HValue?,
        parent: HFrame,
        staticClass: HClass? = null,
        typeArgs: HValue? = null
    ): HValue {
        if (func.args.size != args.size)
            throw HSharpRuntimeError("Function ${func.name} expects ${func.args.size} args, got ${args.size}")

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
        for ((p, v) in func.args.zip(args)) frame.env[p] = v
        if (instance != null) frame.env["self"] = instance
        // Generics: when the call site supplied explicit type arguments,
        // make them available to the body as `__type_args__` so generic
        // code can introspect them at runtime.  We don't perform static
        // type checks because H# is dynamically typed.
        if (typeArgs != null) frame.env["__type_args__"] = typeArgs
        if (staticClass != null) frame.env["__static_class__"] = staticClass
        // Free variables are looked up first in the function's own closure
        // (attached at MAKE_CLOSURE time).  Fall back to the caller's frame
        // for module-level helpers, which don't have a closure.
        for (fv in func.freevars) {
            val cell = func.closure[fv]
            if (cell != null) {
                frame.env[fv] = cell
            } else {
                frame.env[fv] = try { lookup(fv) } catch (_: Throwable) { HNull }
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
        val frame = HFrame(func, func.consts, func.instructions, mutableMapOf(), parent)
        for ((p, v) in func.args.zip(args)) frame.env[p] = v
        if (instance != null) frame.env["self"] = instance
        if (typeArgs != null) frame.env["__type_args__"] = typeArgs
        if (staticClass != null) frame.env["__static_class__"] = staticClass
        for (fv in func.freevars) {
            val cell = func.closure[fv]
            if (cell != null) {
                frame.env[fv] = cell
            } else {
                frame.env[fv] = try { lookup(fv) } catch (_: Throwable) { HNull }
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
                val n = s.length
                val (lo, hi) = sliceBounds(asInt(start, 0) ?: 0, asInt(end, n) ?: n, n)
                if (useStep == 1) HString(s.substring(lo, hi))
                else HString((lo until hi step useStep).map { s[it] }.joinToString(""))
            }
            is HList -> {
                val arr = target.items
                val n = arr.size
                val (lo, hi) = sliceBounds(asInt(start, 0) ?: 0, asInt(end, n) ?: n, n)
                if (useStep == 1) HList(arr.subList(lo, hi).toMutableList())
                else HList((lo until hi step useStep).map { arr[it] }.toMutableList())
            }
            else -> throw HSharpRuntimeError("SLICE on non-indexable ${target::class.simpleName}")
        }
    }

    private fun sliceBounds(rawStart: Int, rawEnd: Int, n: Int): Pair<Int, Int> {
        var s = rawStart
        var e = rawEnd
        if (s < 0) s += n
        if (e < 0) e += n
        if (s < 0) s = 0
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

    private fun getItem(left: HValue, idx: HValue): HValue = when (left) {
        is HList -> left.items[HValueOps.toLong(idx).toInt()]
        is HDict -> left.entries[coerceKey(idx)]
            ?: throw HSharpRuntimeError("Key '${coerceKey(idx)}' not in dict")
        is HString -> {
            val i = HValueOps.toLong(idx).toInt()
            HString(left.value.substring(i, i + 1))
        }
        else -> throw HSharpRuntimeError("Cannot index ${left.type}")
    }

    private fun setItem(left: HValue, idx: HValue, v: HValue) {
        when (left) {
            is HList -> left.items[HValueOps.toLong(idx).toInt()] = v
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
        return when {
            a is HList && b is HList -> HList((a.items + b.items).toMutableList())
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
        val n = HValueOps.toLong(b).toInt()
        return when (a) {
            is HString -> HString(a.value.repeat(n))
            is HList -> HList((0 until n).flatMap { a.items }.toMutableList())
            // C VM: preserve int when both operands are exact integers
            is HNumber -> {
                if (a.value == a.value.toLong().toDouble() && a.value > Long.MIN_VALUE.toDouble() &&
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

    private fun compareOp(op: String, a: HValue, b: HValue): Boolean {
        if (op == "EQEQ") return HValueOps.equals(a, b)
        if (op == "BANGEQ") return !HValueOps.equals(a, b)
        if (a is HString && b is HString) {
            val c = a.value.compareTo(b.value)
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
        if (obj !is HInstance) return false
        val cls = obj.klass ?: return false
        return isInstanceOfClass(cls, typeName)
    }

    /** Recursively check if a class (or any of its bases) matches typeName. */
    private fun isInstanceOfClass(cls: HClass, typeName: String): Boolean {
        if (cls.name == typeName) return true
        // Check interfaces
        if (typeName in cls.implements) return true
        // Walk up the base class chain
        var baseName = cls.base
        while (baseName != null) {
            val base = try { lookup(baseName) as? HClass } catch (_: Throwable) { null }
            if (base != null) {
                if (base.name == typeName) return true
                if (typeName in base.implements) return true
                baseName = base.base
            } else {
                break
            }
        }
        return false
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
                // String iteration: each char is a single-character string
                if (idx < iterStr.length) {
                    f.env[v1] = HString(iterStr.substring(idx, idx + 1))
                    if (v2 != null && dict != null) {
                        f.env[v2] = dict.entries[iterStr.substring(idx, idx + 1)] ?: HNull
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
                f.env[var1] = iterable.items[0]
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
                f.env[var1] = HString(iterable.value.substring(0, 1))
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
            else -> throw HSharpRuntimeError("FOR_ITER: unsupported iterable ${iterable.type}")
        }
    }

    /* =============================================================
     * Scope/name lookup (current env → parents → globals → builtins)
     * ============================================================= */
    fun lookup(name: String): HValue {
        var node: HFrame? = current
        while (node != null) {
            node.env[name]?.let { return it }
            node = node.parent
        }
        globals[name]?.let { return it }
        HNativeBridge.builtins[name]?.let { return it }
        // If we're inside a method with self, try self.fields
        val self = current.env["self"] as? HInstance
        if (self != null) {
            self.fields[name]?.let { return it }
            val cls = self.klass
            cls?.fields?.get(name)?.let { return it }
        }
        throw HSharpRuntimeError("Undefined name: $name")
    }

    private fun deepCopy(v: HValue): HValue = when (v) {
        is HList -> HList(v.items.map(::deepCopy).toMutableList())
        is HDict -> HDict(v.entries.mapValues { deepCopy(it.value) }.toMutableMap())
        is HInstance -> HInstance(v.fields.mapValues { deepCopy(it.value) }.toMutableMap())
        else -> v
    }
}
