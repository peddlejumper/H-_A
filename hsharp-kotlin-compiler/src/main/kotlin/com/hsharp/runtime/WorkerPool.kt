/*
 * H# DZZW Worker Pool
 * --------------------
 * Multi-threaded runtime for `@parallel` annotated coroutines.
 *
 * Replaces the implicit single-threaded eager-resolve model of `async fn`
 * with a real worker pool that runs M H# tasks on N OS threads (N defaults
 * to Runtime.availableProcessors(), i.e. the available CPU cores).
 *
 * Work-stealing: each worker owns a double-ended deque.  When the local
 * deque is empty, the worker picks a random victim and tries to steal
 * from the victim's tail.  This is the standard load-balancing trick
 * that keeps all cores busy when the work is naturally divisible.
 *
 * Tasks are submitted with submit(...).  Each task returns an HValue
 * (or throws); the result is captured into the FutureCell of the
 * HFuture that the caller got back.  The submit() call returns the
 * HFuture immediately — it does NOT block.  `await` on that HFuture
 * blocks the calling thread until the worker finishes.
 *
 * Structured concurrency: a parent task can register child HFutures
 * with `WorkerPool.spawnScope { ... }`; the scope joins on all of them
 * and re-throws the first failure as a combined exception.  This is
 * the foundation for the H# `concurrent { ... }` block.
 *
 * Thread safety:
 *  - The local deques use LinkedBlockingDeque, which is itself thread-safe.
 *  - Globals in the HVM are still a MutableMap; we rely on the user
 *    not writing to them from inside a parallel task (parallel tasks
 *    are expected to be pure: read inputs from arguments, write to
 *    HChannel/return value/closure).  The VM marks globals reads
 *    as safe; any write is a programmer error under our model.
 *  - The WorkerPool's internal state is initialised once at construction
 *    and is read-only afterwards.
 */
package com.hsharp.runtime

import java.util.concurrent.LinkedBlockingDeque
import java.util.concurrent.ThreadLocalRandom
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong

/**
 * The state of a [FutureCell].  Only transitions PENDING -> RESOLVED or
 * PENDING -> FAILED are allowed; a complete/fail call on a non-pending
 * cell is a no-op (the cell can only be settled once).
 */
enum class FutureState { PENDING, RESOLVED, FAILED, CANCELLED }

/**
 * A mutable cell that backs an [HFuture].  Holds the result value or
 * the failure throwable and synchronises waiters.
 *
 * Designed to be both an await primitive (for the `await` opcode) and
 * the join point for a parent `concurrent { ... }` scope.
 */
class FutureCell {
    @Volatile private var state: FutureState = FutureState.PENDING
    @Volatile var value: HValue? = null
        private set
    @Volatile var error: Throwable? = null
        private set

    private val lock = Object()
    // Waiter list is built only when a thread is actually waiting; the
    // hot path (resolve without anyone waiting) takes the fast atomic
    // path and avoids the lock.
    private val waiters: MutableList<() -> Unit> = mutableListOf()

    fun isDone(): Boolean = state != FutureState.PENDING
    fun isResolved(): Boolean = state == FutureState.RESOLVED
    fun isFailed(): Boolean = state == FutureState.FAILED

    /** Settle the cell with a value.  No-op if already settled. */
    fun complete(v: HValue): Boolean {
        if (state != FutureState.PENDING) return false
        synchronized(lock) {
            if (state != FutureState.PENDING) return false
            value = v
            state = FutureState.RESOLVED
            for (w in waiters) w()
            waiters.clear()
        }
        return true
    }

    /** Settle the cell with a failure.  No-op if already settled. */
    fun fail(t: Throwable): Boolean {
        if (state != FutureState.PENDING) return false
        synchronized(lock) {
            if (state != FutureState.PENDING) return false
            error = t
            state = FutureState.FAILED
            for (w in waiters) w()
            waiters.clear()
        }
        return true
    }

    /** Cancel the cell.  Cancellation is treated as a failure with a
     *  HSharpCancelException, so that the structured-concurrency join
     *  code path can treat cancellations the same way as exceptions. */
    fun cancel(): Boolean {
        if (state != FutureState.PENDING) return false
        synchronized(lock) {
            if (state != FutureState.PENDING) return false
            error = HSharpCancelException()
            state = FutureState.CANCELLED
            for (w in waiters) w()
            waiters.clear()
        }
        return true
    }

    /** Block the calling thread until the cell is settled, then return
     *  the value (or re-throw the failure). */
    fun await(): HValue {
        if (state != FutureState.PENDING) {
            return throwOrValue()
        }
        synchronized(lock) {
            while (state == FutureState.PENDING) {
                val done = java.util.concurrent.atomic.AtomicBoolean(false)
                val cb: () -> Unit = { done.set(true); synchronized(lock) { lock.notifyAll() } }
                waiters.add(cb)
                // Re-check state in case it was settled between the
                // first check and the synchronized block.
                if (state != FutureState.PENDING) {
                    waiters.remove(cb)
                    break
                }
                try { lock.wait() } catch (_: InterruptedException) { Thread.currentThread().interrupt() }
            }
        }
        return throwOrValue()
    }

    private fun throwOrValue(): HValue = when (state) {
        FutureState.RESOLVED -> value ?: HNull
        FutureState.FAILED -> {
            // Re-throw the original error rather than the message string.
            // If the worker raised an HSharpException (i.e. the H# user
            // code did `throw "boom"`), unwrap to its inner value so the
            // `catch (e)` clause in user code sees the original payload
            // (`"boom"`), not a re-wrapped `"H# exception: boom"`.  This
            // mirrors how the H# Python VM propagates throw values: the
            // runtime re-raises the original payload, not the message.
            val t = error
            when (t) {
                is HSharpException -> throw HSharpException(t.value)
                is HSharpCancelException -> throw HSharpException(HString("cancelled"))
                else -> throw HSharpException(HString(t?.message ?: "future failed"))
            }
        }
        FutureState.CANCELLED -> throw HSharpException(HString("future cancelled"))
        else -> throw HSharpRuntimeError("FutureCell in unexpected state: $state")
    }
}

/** Marker exception raised when a structured-concurrency scope is cancelled. */
class HSharpCancelException : RuntimeException("cancelled")

/**
 * A single worker thread.  Owns a [LinkedBlockingDeque] of tasks; when
 * the local deque is empty, picks a random other worker and tries to
 * steal from its tail (FIFO from the thief's perspective gives better
 * load balancing when work is bursty).
 */
internal class Worker(
    val id: Int,
    val pool: WorkerPool
) : Thread("hsharp-worker-$id") {
    val deque: LinkedBlockingDeque<Runnable> = LinkedBlockingDeque()
    private val running = AtomicBoolean(true)

    init { isDaemon = true }

    override fun run() {
        val rand = ThreadLocalRandom.current()
        while (running.get()) {
            val task: Runnable? = tryGetLocal() ?: trySteal(rand)
            if (task == null) {
                // Nothing to do — sleep briefly to avoid spinning.
                try { Thread.sleep(0, 100_000) } catch (_: InterruptedException) {}
                continue
            }
            try {
                task.run()
            } catch (t: Throwable) {
                // We never want a single bad task to kill the worker.
                // The future has its own cell; if a task throws before
                // reaching the cell.fail call, the cell will be left
                // PENDING and the awaiter will time out — that's still
                // better than crashing the VM.  The H#-level error
                // reporting goes through the structured-concurrency
                // path in spawnScope, so this catch is a final safety
                // net.
                System.err.println("[hsharp-worker-$id] task threw: ${t.message}")
            }
        }
    }

    private fun tryGetLocal(): Runnable? = try { deque.takeFirst() } catch (_: InterruptedException) { null }

    private fun trySteal(rand: ThreadLocalRandom): Runnable? {
        val victims = pool.workers
        if (victims.size <= 1) return null
        // Try a handful of random victims; bounded to avoid pathological
        // spinning on heavily contended pools.
        val n = victims.size
        for (i in 0 until 4) {
            val v = victims[rand.nextInt(n)]
            if (v === this) continue
            val stolen = v.deque.pollLast()
            if (stolen != null) return stolen
        }
        return null
    }

    fun shutdown() { running.set(false); interrupt() }
}

/**
 * A structured-concurrency scope.  Created by `concurrent { ... }` and
 * tracks all child tasks spawned within.  The scope's join blocks until
 * every child has settled; the scope's cancel cancels every child
 * (the cancel-propagation requirement).
 *
 * Scopes are NOT user-visible H# values — they are an internal handle
 * that the HVM holds while running a `concurrent { ... }` body.  The
 * user sees the result of the block (or the re-thrown exception) and
 * any tasks they explicitly held onto.
 */
class ConcurrentScope {
    private val children: MutableList<HFuture> = mutableListOf()
    private val childLock = Any()
    @Volatile var cancelled: Boolean = false

    /** Register a child future with this scope.  Used by the VM to
     *  record every parallel coroutine spawned inside the body. */
    fun add(future: HFuture) {
        synchronized(childLock) { children.add(future) }
        if (cancelled) future.cell.cancel()
    }

    /** Wait for every child to settle.  If the scope was cancelled,
     *  cancel any still-pending children first.  Re-throws the first
     *  failure (parent wins: a single bad child makes the whole
     *  concurrent block fail). */
    fun join(): List<HValue> {
        if (cancelled) {
            synchronized(childLock) { for (c in children) c.cell.cancel() }
        }
        val out = ArrayList<HValue>(children.size)
        var firstError: Throwable? = null
        for (c in children) {
            try {
                out.add(c.cell.await())
            } catch (t: Throwable) {
                if (firstError == null) firstError = t
            }
        }
        if (firstError != null) throw firstError
        return out
    }

    /** Cancel every pending child without waiting.  Called when the
     *  parent itself is being cancelled (so the children should be
     *  torn down too — the cancel-propagation rule). */
    fun cancel() {
        cancelled = true
        synchronized(childLock) { for (c in children) c.cell.cancel() }
    }
}

/**
 * A pool of worker threads that execute H# parallel tasks.
 *
 * Usage:
 * ```
 *   val pool = WorkerPool()                    // default size = #cores
 *   val fut = pool.submit { invokeHFunction(...) }   // returns HFuture
 *   val v   = fut.cell.await()                       // blocks
 * ```
 *
 * The pool is a process-wide singleton — created lazily on first
 * reference and shut down when the JVM exits (workers are daemon
 * threads).
 */
class WorkerPool(val parallelism: Int = java.lang.Runtime.getRuntime().availableProcessors()) {

    internal val workers: List<Worker> = List(parallelism) { Worker(it, this) }
    private val rr = AtomicLong(0)
    @Volatile private var started = false

    init {
        workers.forEach { it.start() }
        started = true
    }

    /** Submit a task that produces an [HValue] result.  Returns an
     *  HFuture that the caller can `await`.  Never blocks. */
    fun submit(task: () -> HValue): HFuture {
        val cell = FutureCell()
        val fut = HFuture(cell)
        // Round-robin distribute new tasks across workers; this gives
        // a balanced starting point.  Once a worker drains its local
        // deque, the stealing protocol takes over and keeps things
        // balanced even under bursty workloads.
        val target = workers[(rr.getAndIncrement() % workers.size).toInt()]
        target.deque.addFirst(Runnable {
            try {
                val v = task()
                cell.complete(v)
            } catch (t: Throwable) {
                cell.fail(t)
            }
        })
        return fut
    }

    /** Convenience: run a list of futures to completion and collect
     *  the results.  Re-throws the first failure (cancellations
     *  included).  Used as the join primitive for `concurrent { }`
     *  blocks. */
    fun joinAll(futures: List<HFuture>): List<HValue> {
        val out = ArrayList<HValue>(futures.size)
        var firstError: Throwable? = null
        for (f in futures) {
            try {
                out.add(f.cell.await())
            } catch (t: Throwable) {
                if (firstError == null) firstError = t
            }
        }
        if (firstError != null) throw firstError
        return out
    }

    /** Cancel every future in the list that is still pending.  This
     *  is the cancel-propagation half of structured concurrency. */
    fun cancelAll(futures: List<HFuture>) {
        for (f in futures) f.cell.cancel()
    }

    /** Process-wide default pool.  H# code refers to this singleton
     *  when it sees an `@parallel` function call. */
    companion object {
        @Volatile private var defaultRef: WorkerPool? = null
        fun defaultPool(): WorkerPool {
            var d = defaultRef
            if (d == null) {
                synchronized(this) {
                    d = defaultRef
                    if (d == null) {
                        d = WorkerPool()
                        defaultRef = d
                    }
                }
            }
            return d!!
        }
    }
}
