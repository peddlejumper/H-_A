"""
dzzw.py — DZZW Parallel Multi-Tasking Runtime for H# (Python implementation)

Mirrors the dzzw.h v2.0 C API but uses Python threading:
  - concurrent.futures.ThreadPoolExecutor for the work-stealing pool
  - queue.Queue for channels
  - threading.Lock for mutexes
  - A module-level handle registry to expose them as int handles to H# code

Every Interpreter instance gets its own DzzwRuntime so handles stay scoped
to a single program run.
"""

from __future__ import annotations
import queue
import threading
from concurrent.futures import Future as PyFuture
from typing import Any, Callable, List, Optional

# Top-level import of ReturnException so the worker's exception handler
# can use it without triggering Python's "local variable not associated"
# error that occurs when an exception class is referenced inside a
# nested except block.
def _get_return_exception():
    from interpreter import ReturnException
    return ReturnException

_RETURN_EXC = _get_return_exception()


class DzzwRuntime:
    """DZZW runtime bound to a single Interpreter.

    All public methods follow the C API: they take/return H# values
    (plain Python objects) and use integer handles for Futures/Channels/Mutexes
    that cross thread boundaries.
    """

    def __init__(self, interpreter):
        self.interpreter = interpreter
        self._lock = threading.Lock()
        self._next_handle = 1
        self._registry: dict[int, Any] = {}

        # Stats (mirror C API counters)
        self._total_submitted = 0
        self._total_completed = 0
        self._stats_lock = threading.Lock()

        # Thread pool — daemon=True so worker threads die with the main process
        self._executor = _DzzwExecutor(max_workers=_default_worker_count())

    # ── handle helpers ───────────────────────────────────────────

    def _alloc(self, obj) -> int:
        with self._lock:
            h = self._next_handle
            self._next_handle += 1
            self._registry[h] = obj
            return h

    def _get(self, h: int):
        if not isinstance(h, int) or h <= 0:
            return None
        with self._lock:
            return self._registry.get(h)

    def _take(self, h: int):
        if not isinstance(h, int) or h <= 0:
            return None
        with self._lock:
            return self._registry.pop(h, None)

    def _bump_submitted(self):
        with self._stats_lock:
            self._total_submitted += 1

    def _bump_completed(self):
        with self._stats_lock:
            self._total_completed += 1

    # ── future ──────────────────────────────────────────────────

    def _future_new(self) -> int:
        pyfut: PyFuture = PyFuture()
        # Count completion whenever the future finishes (success or fail)
        def _on_done(_):
            with self._stats_lock:
                self._total_completed += 1
        pyfut.add_done_callback(_on_done)
        h = self._alloc(pyfut)
        return h

    def _future_done_cb(self, h: int):
        def _cb(_):
            with self._stats_lock:
                self._total_completed += 1
        pyfut = self._get(h)
        if pyfut is not None:
            pyfut.add_done_callback(_cb)

    def _future_set_error(self, h: int, err):
        pyfut = self._get(h)
        if pyfut is None:
            return
        if not pyfut.done():
            pyfut.set_exception(err if isinstance(err, BaseException)
                                 else Exception(str(err)))

    # ── H# invocation ───────────────────────────────────────────

    def _invoke_hs_function(self, fn, args: list):
        """Invoke an H# callable from any thread.

        `fn` may be:
          - a Function AST node (with .name/.params/.body)
          - a dict with 'params'/'body' keys (interpreter closure style)
          - a real Python callable
        """
        try:
            # Function AST node path
            if hasattr(fn, 'body') and hasattr(fn, 'params') and not isinstance(fn, dict):
                from interpreter import Environment
                params = fn.params or []
                if len(args) != len(params):
                    raise Exception(
                        f"Function '{getattr(fn, 'name', '?')}' expects {len(params)} args, got {len(args)}"
                    )
                call_env = Environment(parent=self.interpreter.global_env)
                for p, a in zip(params, args):
                    call_env.define(p, a)
                try:
                    self.interpreter.visit_BlockStatement(fn.body, call_env)
                    return None
                except _RETURN_EXC as rs:
                    return rs.value
            elif isinstance(fn, dict) and 'body' in fn:
                from interpreter import Environment
                closure = fn.get('closure_env', self.interpreter.global_env)
                call_env = Environment(parent=closure)
                params = fn.get('params', [])
                if len(args) != len(params):
                    raise Exception(
                        f"Function expects {len(params)} arguments, got {len(args)}"
                    )
                for p, a in zip(params, args):
                    call_env.define(p, a)
                try:
                    self.interpreter.visit_BlockStatement(fn['body'], call_env)
                    return None
                except _RETURN_EXC as rs:
                    return rs.value
            elif isinstance(fn, dict) and 'bytecode' in fn:
                from bytecode import VM
                vm = VM({'instructions': fn['bytecode'], 'consts': fn.get('consts', [])})
                vm.run()
                return None
            elif callable(fn):
                return fn(*args)
            else:
                raise Exception(f'Unsupported callable passed to dzzw_spawn: {type(fn).__name__}')
        except _RETURN_EXC as rs:
            return rs.value

    # ── public API (C-compatible names) ─────────────────────────

    def dzzw_spawn(self, fn, args):
        """Spawn a task. Returns an int future handle."""
        if not isinstance(args, list):
            args = [args]
        fut_h = self._future_new()
        pyfut = self._get(fut_h)
        self._bump_submitted()

        def _task():
            try:
                result = self._invoke_hs_function(fn, args)
                if not pyfut.done():
                    pyfut.set_result(result)
            except Exception as e:
                if not pyfut.done():
                    pyfut.set_exception(e)

        self._executor.submit(_task)
        return fut_h

    def dzzw_await(self, h):
        """Block on a future and return its result. Frees the future."""
        if not isinstance(h, int):
            return None
        pyfut = self._take(h)
        if pyfut is None:
            raise Exception(f"dzzw_await: invalid future handle {h}")
        try:
            return pyfut.result()
        except Exception as e:
            raise Exception(f"dzzw_await task failed: {e}")

    def dzzw_try_await(self, h):
        """Non-blocking: return result if done, otherwise None. Keeps future."""
        pyfut = self._get(h)
        if pyfut is None:
            return None
        if pyfut.done():
            try:
                return pyfut.result()
            except Exception as e:
                return None
        return None

    def dzzw_await_any(self, handles: list):
        """Wait for any future. Returns its index."""
        if not isinstance(handles, list) or len(handles) == 0:
            raise Exception("dzzw_await_any: expected non-empty list of handles")
        py_futures = []
        for h in handles:
            pyfut = self._get(h) if isinstance(h, int) else None
            py_futures.append(pyfut)
        # Use a done-event approach: poll
        import time
        deadline = time.monotonic() + 3600.0  # 1h hard cap
        while time.monotonic() < deadline:
            for i, f in enumerate(py_futures):
                if f is not None and f.done():
                    return i
            time.sleep(0.001)
        raise Exception("dzzw_await_any: timeout")

    def dzzw_await_all(self, handles: list):
        """Wait for all futures to complete."""
        if not isinstance(handles, list):
            return
        for h in handles:
            pyfut = self._get(h) if isinstance(h, int) else None
            if pyfut is not None:
                try:
                    pyfut.result()
                except Exception:
                    pass

    def dzzw_parallel_map(self, fn, items: list):
        """Spawn one task per item, wait for all, return list of results."""
        if not isinstance(items, list):
            raise Exception("dzzw_parallel_map: items must be a list")
        handles = [self.dzzw_spawn(fn, [item]) for item in items]
        self.dzzw_await_all(handles)
        results = []
        for h in handles:
            pyfut = self._take(h)
            if pyfut is not None:
                try:
                    results.append(pyfut.result())
                except Exception as e:
                    results.append(None)
        return results

    def dzzw_worker_count(self) -> int:
        return self._executor.max_workers

    def dzzw_pending_count(self) -> int:
        return len(self._executor._work_queue) if hasattr(self._executor, '_work_queue') else 0

    def dzzw_total_submitted(self) -> int:
        with self._stats_lock:
            return self._total_submitted

    def dzzw_total_completed(self) -> int:
        with self._stats_lock:
            return self._total_completed

    def dzzw_dump_stats(self):
        print(
            f"[dzzw] workers={self.dzzw_worker_count()} "
            f"submitted={self.dzzw_total_submitted()} "
            f"completed={self.dzzw_total_completed()}"
        )

    # ── channel ─────────────────────────────────────────────────

    def dzzw_channel_create(self, capacity=0):
        if isinstance(capacity, list) and len(capacity) >= 1:
            capacity = capacity[0]
        capacity = int(capacity) if capacity else 0
        ch = queue.Queue(maxsize=capacity) if capacity > 0 else queue.Queue()
        return self._alloc(ch)

    def dzzw_channel_send(self, h, value):
        ch = self._get(h)
        if ch is None:
            raise Exception(f"dzzw_channel_send: invalid channel handle {h}")
        ch.put(value)

    def dzzw_channel_recv(self, h):
        ch = self._get(h)
        if ch is None:
            raise Exception(f"dzzw_channel_recv: invalid channel handle {h}")
        return ch.get()

    def dzzw_channel_try_send(self, h, value):
        ch = self._get(h)
        if ch is None or ch.full():
            return False
        try:
            ch.put_nowait(value)
            return True
        except queue.Full:
            return False

    def dzzw_channel_try_recv(self, h):
        ch = self._get(h)
        if ch is None:
            return None
        try:
            return ch.get_nowait()
        except queue.Empty:
            return None

    def dzzw_channel_close(self, h):
        ch = self._get(h)
        if ch is None:
            return
        # Python queue.Queue has no close; emulate by sending a sentinel via shutdown
        try:
            ch.put_nowait(_CHANNEL_CLOSED)
        except Exception:
            pass

    def dzzw_channel_free(self, h):
        ch = self._take(h)
        if ch is None:
            return
        # Drain any pending items
        try:
            while True:
                ch.get_nowait()
        except queue.Empty:
            pass

    def dzzw_channel_size(self, h):
        ch = self._get(h)
        if ch is None:
            return 0
        return ch.qsize()

    # ── mutex ───────────────────────────────────────────────────

    def dzzw_mutex_create(self):
        m = threading.Lock()
        return self._alloc(m)

    def dzzw_mutex_lock(self, h):
        m = self._get(h)
        if m is None:
            raise Exception(f"dzzw_mutex_lock: invalid mutex handle {h}")
        m.acquire()

    def dzzw_mutex_unlock(self, h):
        m = self._get(h)
        if m is None:
            raise Exception(f"dzzw_mutex_unlock: invalid mutex handle {h}")
        m.release()

    def dzzw_mutex_try_lock(self, h):
        m = self._get(h)
        if m is None:
            return False
        return m.acquire(blocking=False)

    def dzzw_mutex_free(self, h):
        self._take(h)

    # ── shutdown ────────────────────────────────────────────────

    def shutdown(self, wait=True):
        self._executor.shutdown(wait=wait)


# Sentinel signaling channel closure
_CHANNEL_CLOSED = object()


def _default_worker_count() -> int:
    import os
    try:
        return max(1, min(32, (os.cpu_count() or 4)))
    except Exception:
        return 4


class _DzzwExecutor:
    """Tiny wrapper around ThreadPoolExecutor to expose queue length
    and to allow future extension to work-stealing semantics."""
    def __init__(self, max_workers: int):
        from concurrent.futures import ThreadPoolExecutor
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dzzw")
        self.max_workers = max_workers
        try:
            self._work_queue = self._pool._work_queue
        except Exception:
            self._work_queue = None

    def submit(self, fn, *args, **kwargs):
        return self._pool.submit(fn, *args, **kwargs)

    def shutdown(self, wait=True):
        self._pool.shutdown(wait=wait)
