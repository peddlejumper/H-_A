#!/usr/bin/env python3
# python_host/server_runner.py
# ZZW Code Teacher — HTTP ↔ H# dispatch 桥接层
#
# 协议:
#   Python HTTP server 收到 HTTP 请求 →
#   序列化为 JSON 写入 H# 子进程 stdin →
#   H# 处理后从 stdout 读 RESP <json> →
#   反序列化为 HTTP 响应发回客户端
#
# 用法:
#   python3 python_host/server_runner.py [PORT]
#   默认 PORT=8765

import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import queue
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HSHARP = os.path.join(os.path.dirname(ROOT), "hsharp.py")
DISPATCH = os.path.join(ROOT, "main_server_dispatch.hto")
DEFAULT_PORT = 8765


class HSharpDispatchProcess:
    """Manages a single H# dispatch process.

    Communication is line-based JSON over stdin/stdout:
      - Input:  {"id": 1, "method": "GET", "path": "/api/health",
                 "headers": {...}, "body": "..."}
      - Output: RESP {"id": 1, "status": 200, "body": "...", "content_type": "..."}
    """

    def __init__(self, cwd=None):
        self.cwd = cwd or ROOT
        self.proc = None
        self.lock = threading.Lock()
        self.pending = {}  # id -> Queue
        self.reader_thread = None
        self._next_id = 1
        self._ready_event = threading.Event()
        self.start()

    def start(self):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        # Use binary mode for stdout to avoid line-buffering surprises
        self.proc = subprocess.Popen(
            [sys.executable, "-u", HSHARP, DISPATCH],
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            env=env,
            bufsize=0,
        )
        # Spawn reader thread that owns stdout parsing
        self.reader_thread = threading.Thread(
            target=self._reader_loop, args=(True,), daemon=True)
        self.reader_thread.start()
        # Wait until reader thread signals READY
        self._ready_event.wait(timeout=20)
        if not self._ready_event.is_set():
            raise RuntimeError("H# dispatch did not emit READY in time")
        print(f"[H# dispatch] started (pid={self.proc.pid})", file=sys.stderr)

    def _reader_loop(self, signal_ready=False):
        """Reads RESP lines and dispatches to waiting queues.

        If signal_ready is True, sets _ready_event when "READY" is seen.
        """
        import os as _os
        try:
            stream = self.proc.stdout
            fd = stream.fileno()
            buf = b""
            while True:
                if not buf:
                    chunk = _os.read(fd, 4096)
                    if not chunk:
                        break
                    buf = chunk
                nl = buf.find(b"\n")
                if nl < 0:
                    more = _os.read(fd, 4096)
                    if not more:
                        buf = b""
                        break
                    buf += more
                    continue
                line_bytes = buf[:nl]
                buf = buf[nl + 1:]
                try:
                    line = line_bytes.decode("utf-8", errors="replace")
                except Exception:
                    line = ""
                line = line.rstrip("\r")
                if not line:
                    continue
                if signal_ready and line == "READY":
                    self._ready_event.set()
                    signal_ready = False
                    continue
                if line.startswith("RESP "):
                    payload = line[5:]
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    rid = obj.get("id")
                    if rid in self.pending:
                        self.pending[rid].put(obj)
                else:
                    # Non-RESP output is treated as a stderr-style log line.
                    sys.stderr.write(f"[H#] {line}\n")
                    sys.stderr.flush()
        except Exception as exc:
            print(f"[H# dispatch] reader error: {exc}", file=sys.stderr)

    def call(self, method, path, headers=None, body=""):
        """Send a request to the H# dispatch and wait for the response."""
        with self.lock:
            rid = self._next_id
            self._next_id += 1
            q = queue.Queue()
            self.pending[rid] = q
        req = {
            "id": rid,
            "method": method,
            "path": path,
            "headers": headers or {},
            "body": body or "",
        }
        try:
            payload = (json.dumps(req) + "\n").encode("utf-8")
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            return {"status": 500, "body": '{"error": "dispatch down"}', "content_type": "application/json"}
        try:
            r = q.get(timeout=10)
            return r
        except queue.Empty:
            return {"status": 504, "body": '{"error": "dispatch timeout"}', "content_type": "application/json"}
        finally:
            with self.lock:
                self.pending.pop(rid, None)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.write("EXIT\n")
                self.proc.stdin.flush()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()


DISPATCH_SINGLETON = None
DISPATCH_LOCK = threading.Lock()


def get_dispatch():
    global DISPATCH_SINGLETON
    with DISPATCH_LOCK:
        if DISPATCH_SINGLETON is None or DISPATCH_SINGLETON.proc.poll() is not None:
            DISPATCH_SINGLETON = HSharpDispatchProcess()
        return DISPATCH_SINGLETON


# ============= HTTP server =============

STATUS_REASONS = {
    200: "OK", 201: "Created", 204: "No Content",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 409: "Conflict",
    500: "Internal Server Error", 504: "Gateway Timeout",
}


def build_http_response(dispatch_resp):
    status = int(dispatch_resp.get("status", 500))
    body = dispatch_resp.get("body", "")
    if isinstance(body, dict):
        body = json.dumps(body, ensure_ascii=False)
    elif body is None:
        body = ""
    ct = dispatch_resp.get("content_type") or "application/json; charset=utf-8"
    reason = STATUS_REASONS.get(status, "OK")
    head = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Type: {ct}\r\n"
        f"Content-Length: {len(body.encode('utf-8'))}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
        f"Access-Control-Allow-Headers: Content-Type, Authorization\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    return head.encode("utf-8") + body.encode("utf-8")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class HTTPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            data = self._recv_request()
        except Exception as exc:
            print(f"[HTTP] recv error: {exc}", file=sys.stderr)
            return
        if not data:
            return
        try:
            method, path, headers, body = self._parse_http(data)
        except Exception as exc:
            self._send_raw(build_http_response({
                "status": 400, "body": f"Bad Request: {exc}",
                "content_type": "text/plain",
            }))
            return
        try:
            dispatch = get_dispatch()
            resp = dispatch.call(method, path, headers, body)
        except Exception as exc:
            print(f"[HTTP] dispatch error: {exc}", file=sys.stderr)
            resp = {"status": 500, "body": '{"error":"dispatch error"}', "content_type": "application/json"}
        try:
            self._send_raw(build_http_response(resp))
        except Exception as exc:
            print(f"[HTTP] send error: {exc}", file=sys.stderr)

    def _recv_request(self):
        """Receive HTTP request with a Content-Length-aware body read."""
        buf = b""
        # Read headers
        while b"\r\n\r\n" not in buf:
            chunk = self.request.recv(4096)
            if not chunk:
                return buf
            buf += chunk
            if len(buf) > 64 * 1024:
                break
        head_end = buf.find(b"\r\n\r\n")
        if head_end < 0:
            return buf
        headers_blob = buf[:head_end].decode("iso-8859-1", errors="replace")
        body = buf[head_end + 4:]
        # Parse Content-Length
        content_length = 0
        for line in headers_blob.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_length = 0
                break
        # Read remaining body if needed
        while len(body) < content_length:
            chunk = self.request.recv(4096)
            if not chunk:
                break
            body += chunk
        return headers_blob.encode("iso-8859-1") + b"\r\n\r\n" + body

    def _parse_http(self, raw):
        head_end = raw.find(b"\r\n\r\n")
        head = raw[:head_end].decode("iso-8859-1", errors="replace")
        body = raw[head_end + 4:].decode("utf-8", errors="replace")
        lines = head.split("\r\n")
        if not lines:
            raise ValueError("empty request")
        start = lines[0]
        parts = start.split(" ")
        if len(parts) < 2:
            raise ValueError(f"bad request line: {start!r}")
        method, path = parts[0], parts[1]
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
        return method, path, headers, body

    def _send_raw(self, payload: bytes):
        try:
            self.request.sendall(payload)
        finally:
            try:
                self.request.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.request.close()
            except Exception:
                pass


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"bad port: {sys.argv[1]}", file=sys.stderr)
            sys.exit(2)
    print(f"[ZZW bridge] http://127.0.0.1:{port} → H# dispatch", file=sys.stderr)
    # Pre-warm dispatch
    try:
        get_dispatch()
    except Exception as exc:
        print(f"[ZZW bridge] failed to start H# dispatch: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        with ThreadedHTTPServer(("127.0.0.1", port), HTTPHandler) as srv:
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[ZZW bridge] shutting down", file=sys.stderr)
    finally:
        if DISPATCH_SINGLETON:
            DISPATCH_SINGLETON.stop()


if __name__ == "__main__":
    main()
