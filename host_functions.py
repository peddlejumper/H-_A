"""
Additional host functions for H# bootstrap modules
These functions provide system-level capabilities needed by H# standard libraries
"""

import time
import os
import sys
import shutil
import tempfile
import calendar
from datetime import datetime

def builtin_time_now(args=None):
    """Return current time in milliseconds"""
    return int(time.time() * 1000)

def builtin_substring(args):
    """Extract substring: substring(string, start, length)"""
    if len(args) < 3:
        raise Exception("substring requires 3 arguments")
    s = str(args[0])
    start = int(args[1])
    length = int(args[2])
    return s[start:start + length]

def builtin_ord(args):
    """Get ASCII/Unicode code point of a character"""
    if len(args) < 1:
        raise Exception("ord requires 1 argument")
    ch = str(args[0])
    if len(ch) == 0:
        return 0
    return ord(ch[0])

def builtin_chr(args):
    """Get character from ASCII/Unicode code point"""
    if len(args) < 1:
        raise Exception("chr requires 1 argument")
    code = int(args[0])
    return chr(code)

def builtin_int(args):
    """Convert to integer"""
    if len(args) < 1:
        raise Exception("int requires 1 argument")
    return int(float(args[0]))

def builtin_str(args):
    """Convert to string"""
    if len(args) < 1:
        raise Exception("str requires 1 argument")
    return str(args[0])

# Date and Time functions
def builtin_date_now(args=None):
    """Return current date/time as formatted string"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def builtin_date_timestamp(args=None):
    """Return current timestamp (seconds since epoch)"""
    return time.time()

def builtin_date_format(args):
    """Format timestamp to date string: format(timestamp, format_string)"""
    if len(args) < 2:
        raise Exception("date_format requires 2 arguments")
    timestamp = float(args[0])
    fmt = str(args[1])
    
    # Convert H# style format to Python strftime format
    # H# uses: YYYY, MM, DD, HH, MM, SS
    # Python uses: %Y, %m, %d, %H, %M, %S
    fmt = fmt.replace("YYYY", "%Y")
    fmt = fmt.replace("MM", "%m")
    fmt = fmt.replace("DD", "%d")
    fmt = fmt.replace("HH", "%H")
    fmt = fmt.replace("mm", "%M")  # minutes (lowercase mm after HH)
    fmt = fmt.replace("SS", "%S")
    
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(fmt)

def builtin_date_parse(args):
    """Parse date string to components: parse(date_string)"""
    if len(args) < 1:
        raise Exception("date_parse requires 1 argument")
    date_str = str(args[0])
    try:
        # Try common formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return {
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "hour": dt.hour,
                    "minute": dt.minute,
                    "second": dt.second,
                    "timestamp": dt.timestamp()
                }
            except ValueError:
                continue
        raise Exception(f"Cannot parse date: {date_str}")
    except Exception as e:
        raise Exception(f"Date parse error: {e}")

# File system functions
def builtin_fs_exists(args):
    """Check if file/directory exists: exists(path)"""
    if len(args) < 1:
        raise Exception("exists requires 1 argument")
    path = str(args[0])
    return os.path.exists(path)

def builtin_fs_is_file(args):
    """Check if path is a file: is_file(path)"""
    if len(args) < 1:
        raise Exception("is_file requires 1 argument")
    path = str(args[0])
    return os.path.isfile(path)

def builtin_fs_is_dir(args):
    """Check if path is a directory: is_dir(path)"""
    if len(args) < 1:
        raise Exception("is_dir requires 1 argument")
    path = str(args[0])
    return os.path.isdir(path)

def builtin_fs_mkdir(args):
    """Create directory: mkdir(path)"""
    if len(args) < 1:
        raise Exception("mkdir requires 1 argument")
    path = str(args[0])
    try:
        os.makedirs(path, exist_ok=True)
        return None
    except Exception as e:
        raise Exception(f"Failed to create directory: {e}")

def builtin_fs_remove(args):
    """Remove file or empty directory: remove(path)"""
    if len(args) < 1:
        raise Exception("remove requires 1 argument")
    path = str(args[0])
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            os.rmdir(path)
        return None
    except Exception as e:
        raise Exception(f"Failed to remove: {e}")

def builtin_fs_list_dir(args):
    """List directory contents: list_dir(path)"""
    if len(args) < 1:
        raise Exception("list_dir requires 1 argument")
    path = str(args[0])
    try:
        return os.listdir(path)
    except Exception as e:
        raise Exception(f"Failed to list directory: {e}")

def builtin_fs_get_cwd(args=None):
    """Get current working directory"""
    return os.getcwd()

def builtin_fs_chdir(args):
    """Change current directory: chdir(path)"""
    if len(args) < 1:
        raise Exception("chdir requires 1 argument")
    path = str(args[0])
    try:
        os.chdir(path)
        return None
    except Exception as e:
        raise Exception(f"Failed to change directory: {e}")

def builtin_fs_join_path(args):
    """Join path components: join_path(path1, path2, ...)"""
    if len(args) < 1:
        raise Exception("join_path requires at least 1 argument")
    paths = [str(p) for p in args]
    return os.path.join(*paths)

def builtin_fs_get_ext(args):
    """Get file extension: get_ext(filename)"""
    if len(args) < 1:
        raise Exception("get_ext requires 1 argument")
    filename = str(args[0])
    _, ext = os.path.splitext(filename)
    return ext

def builtin_fs_get_basename(args):
    """Get base name (filename without path): get_basename(path)"""
    if len(args) < 1:
        raise Exception("get_basename requires 1 argument")
    path = str(args[0])
    return os.path.basename(path)

def builtin_fs_get_dirname(args):
    """Get directory name: get_dirname(path)"""
    if len(args) < 1:
        raise Exception("get_dirname requires 1 argument")
    path = str(args[0])
    return os.path.dirname(path)

# IO helper functions
def builtin_io_append_file(args):
    """Append content to file: append_file(path, content)"""
    if len(args) != 2:
        raise Exception("append_file(path, content) takes exactly 2 arguments")
    path, content = args
    if not isinstance(path, str) or not isinstance(content, str):
        raise Exception("Arguments must be strings")
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)
        return None
    except Exception as e:
        raise Exception(f"Failed to append file '{path}': {e}")

def builtin_io_read_lines(args):
    """Read file as array of lines: read_lines(path)"""
    if len(args) != 1:
        raise Exception("read_lines(path) takes exactly 1 argument")
    path = args[0]
    if not isinstance(path, str):
        raise Exception("File path must be a string")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.rstrip('\n') for line in f.readlines()]
    except Exception as e:
        raise Exception(f"Failed to read file '{path}': {e}")

def builtin_io_write_lines(args):
    """Write array of lines to file: write_lines(path, lines)"""
    if len(args) != 2:
        raise Exception("write_lines(path, lines) takes exactly 2 arguments")
    path, lines = args
    if not isinstance(path, str) or not isinstance(lines, list):
        raise Exception("Path must be string, lines must be array")
    try:
        with open(path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(str(line) + '\n')
        return None
    except Exception as e:
        raise Exception(f"Failed to write file '{path}': {e}")

# Network and HTTP functions
import urllib.request
import urllib.parse
import urllib.error
import socket
import json

def builtin_net_http_get(args):
    """HTTP GET request: http_get(url, headers_dict)"""
    if len(args) < 1:
        raise Exception("http_get requires at least 1 argument (url)")
    
    url = str(args[0])
    headers = {}
    
    # Parse optional headers (array of [key, value] pairs)
    if len(args) > 1 and args[1] is not None:
        headers_array = args[1]
        if isinstance(headers_array, list):
            for pair in headers_array:
                if isinstance(pair, list) and len(pair) >= 2:
                    headers[str(pair[0])] = str(pair[1])
    
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=30)
        status_code = response.getcode()
        response_headers = dict(response.headers)
        body = response.read().decode('utf-8', errors='ignore')
        
        return {
            "status": status_code,
            "headers": response_headers,
            "body": body,
            "success": True
        }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "headers": dict(e.headers),
            "body": str(e.reason),
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": 0,
            "headers": {},
            "body": "",
            "success": False,
            "error": str(e)
        }

def builtin_net_http_post(args):
    """HTTP POST request: http_post(url, data, headers_dict)"""
    if len(args) < 2:
        raise Exception("http_post requires at least 2 arguments (url, data)")
    
    url = str(args[0])
    data = args[1]
    headers = {"Content-Type": "application/json"}
    
    # Parse optional headers
    if len(args) > 2 and args[2] is not None:
        headers_array = args[2]
        if isinstance(headers_array, list):
            for pair in headers_array:
                if isinstance(pair, list) and len(pair) >= 2:
                    headers[str(pair[0])] = str(pair[1])
    
    try:
        # Convert data to JSON if it's a dict-like structure
        if isinstance(data, dict):
            data_bytes = json.dumps(data).encode('utf-8')
        elif isinstance(data, list):
            # H# dicts are represented as arrays of [key, value] pairs
            py_dict = {}
            for pair in data:
                if isinstance(pair, list) and len(pair) >= 2:
                    py_dict[str(pair[0])] = pair[1]
            data_bytes = json.dumps(py_dict).encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        response = urllib.request.urlopen(req, timeout=30)
        status_code = response.getcode()
        response_headers = dict(response.headers)
        body = response.read().decode('utf-8', errors='ignore')
        
        return {
            "status": status_code,
            "headers": response_headers,
            "body": body,
            "success": True
        }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "headers": dict(e.headers),
            "body": str(e.reason),
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": 0,
            "headers": {},
            "body": "",
            "success": False,
            "error": str(e)
        }

def builtin_net_url_parse(args):
    """Parse URL: url_parse(url)"""
    if len(args) < 1:
        raise Exception("url_parse requires 1 argument")
    
    url = str(args[0])
    try:
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        # Convert query params to H# format (array of [key, value] pairs)
        params_array = []
        for key, values in query_params.items():
            for value in values:
                params_array.append([key, value])
        
        # Return as H# compatible dict (array of [key, value] pairs)
        return [
            ["scheme", parsed.scheme],
            ["netloc", parsed.netloc],
            ["path", parsed.path],
            ["query", parsed.query],
            ["fragment", parsed.fragment],
            ["params", params_array]
        ]
    except Exception as e:
        return [
            ["scheme", ""],
            ["netloc", ""],
            ["path", ""],
            ["query", ""],
            ["fragment", ""],
            ["params", []],
            ["error", str(e)]
        ]

def builtin_net_url_build(args):
    """Build URL from components: url_build(scheme, host, path, params)"""
    if len(args) < 2:
        raise Exception("url_build requires at least 2 arguments")
    
    scheme = str(args[0])
    host = str(args[1])
    path = str(args[2]) if len(args) > 2 and args[2] is not None else ""
    
    # Build query string from params array
    query = ""
    if len(args) > 3 and args[3] is not None:
        params = args[3]
        if isinstance(params, list):
            query_parts = []
            for pair in params:
                if isinstance(pair, list) and len(pair) >= 2:
                    query_parts.append(f"{urllib.parse.quote(str(pair[0]))}={urllib.parse.quote(str(pair[1]))}")
            query = "&".join(query_parts)
    
    url = f"{scheme}://{host}{path}"
    if query:
        url += f"?{query}"
    
    return url

def builtin_net_tcp_connect(args):
    """Create TCP socket connection: tcp_connect(host, port)"""
    if len(args) < 2:
        raise Exception("tcp_connect requires 2 arguments (host, port)")
    
    host = str(args[0])
    port = int(args[1])
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        return {
            "connected": True,
            "socket_id": id(sock),
            "socket": sock  # Store socket object for later use
        }
    except Exception as e:
        return {
            "connected": False,
            "socket_id": 0,
            "error": str(e)
        }

def builtin_net_tcp_send(args):
    """Send data over TCP: tcp_send(socket_obj, data)"""
    if len(args) < 2:
        raise Exception("tcp_send requires 2 arguments")
    
    sock = args[0]
    data = str(args[1])
    
    try:
        if hasattr(sock, 'send'):
            sent = sock.send(data.encode('utf-8'))
            return {"sent": sent, "success": True}
        else:
            return {"sent": 0, "success": False, "error": "Invalid socket"}
    except Exception as e:
        return {"sent": 0, "success": False, "error": str(e)}

def builtin_net_tcp_recv(args):
    """Receive data from TCP: tcp_recv(socket_obj, buffer_size)"""
    if len(args) < 1:
        raise Exception("tcp_recv requires at least 1 argument")
    
    sock = args[0]
    buffer_size = int(args[1]) if len(args) > 1 else 4096
    
    try:
        if hasattr(sock, 'recv'):
            data = sock.recv(buffer_size).decode('utf-8', errors='ignore')
            return {"data": data, "success": True}
        else:
            return {"data": "", "success": False, "error": "Invalid socket"}
    except Exception as e:
        return {"data": "", "success": False, "error": str(e)}

def builtin_net_tcp_close(args):
    """Close TCP socket: tcp_close(socket_obj)"""
    if len(args) < 1:
        raise Exception("tcp_close requires 1 argument")
    
    sock = args[0]
    try:
        if hasattr(sock, 'close'):
            sock.close()
            return {"success": True}
        else:
            return {"success": False, "error": "Invalid socket"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def builtin_net_udp_create(args):
    """Create UDP socket: udp_create()"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        return {
            "created": True,
            "socket_id": id(sock),
            "socket": sock
        }
    except Exception as e:
        return {
            "created": False,
            "socket_id": 0,
            "error": str(e)
        }

def builtin_net_udp_send(args):
    """Send UDP data: udp_send(socket_obj, data, host, port)"""
    if len(args) < 4:
        raise Exception("udp_send requires 4 arguments")
    
    sock = args[0]
    data = str(args[1])
    host = str(args[2])
    port = int(args[3])
    
    try:
        if hasattr(sock, 'sendto'):
            sent = sock.sendto(data.encode('utf-8'), (host, port))
            return {"sent": sent, "success": True}
        else:
            return {"sent": 0, "success": False, "error": "Invalid socket"}
    except Exception as e:
        return {"sent": 0, "success": False, "error": str(e)}

def builtin_net_udp_recv(args):
    """Receive UDP data: udp_recv(socket_obj, buffer_size)"""
    if len(args) < 1:
        raise Exception("udp_recv requires at least 1 argument")
    
    sock = args[0]
    buffer_size = int(args[1]) if len(args) > 1 else 4096
    
    try:
        if hasattr(sock, 'recvfrom'):
            data, addr = sock.recvfrom(buffer_size)
            return {
                "data": data.decode('utf-8', errors='ignore'),
                "from_host": addr[0],
                "from_port": addr[1],
                "success": True
            }
        else:
            return {"data": "", "success": False, "error": "Invalid socket"}
    except Exception as e:
        return {"data": "", "success": False, "error": str(e)}

def builtin_net_base64_encode(args):
    """Base64 encode: base64_encode(data)"""
    import base64
    if len(args) < 1:
        raise Exception("base64_encode requires 1 argument")
    
    data = str(args[0])
    try:
        encoded = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        return encoded
    except Exception as e:
        return ""

def builtin_net_base64_decode(args):
    """Base64 decode: base64_decode(encoded_data)"""
    import base64
    if len(args) < 1:
        raise Exception("base64_decode requires 1 argument")
    
    data = str(args[0])
    try:
        decoded = base64.b64decode(data.encode('utf-8')).decode('utf-8')
        return decoded
    except Exception as e:
        return ""

def builtin_net_json_stringify(args):
    """Convert H# data to JSON string: json_stringify(data)"""
    if len(args) < 1:
        raise Exception("json_stringify requires 1 argument")

    data = args[0]
    try:
        # Convert H# data to Python: handle real dicts, list-of-pairs, and lists
        def convert_hsharp_to_python(obj):
            if isinstance(obj, dict):
                return {str(k): convert_hsharp_to_python(v) for k, v in obj.items()}
            if isinstance(obj, list):
                # Check if it's a dict-like structure (list of [key, value] pairs)
                if len(obj) > 0 and all(isinstance(item, list) and len(item) >= 2 for item in obj):
                    return {str(item[0]): convert_hsharp_to_python(item[1]) for item in obj}
                return [convert_hsharp_to_python(item) for item in obj]
            return obj

        python_data = convert_hsharp_to_python(data)
        return json.dumps(python_data, ensure_ascii=False)
    except Exception as e:
        return ""

def builtin_net_json_parse(args):
    """Parse JSON string: json_parse(json_string)"""
    if len(args) < 1:
        raise Exception("json_parse requires 1 argument")

    json_str = str(args[0])
    try:
        python_data = json.loads(json_str)

        # Convert Python dict/list to H# format
        # H# supports obj["key"] on Python dicts, so keep dicts as dicts
        def convert_python_to_hsharp(obj):
            if isinstance(obj, dict):
                d = {}
                for k, v in obj.items():
                    d[k] = convert_python_to_hsharp(v)
                return d
            elif isinstance(obj, list):
                return [convert_python_to_hsharp(item) for item in obj]
            else:
                return obj

        return convert_python_to_hsharp(python_data)
    except Exception as e:
        return []

# Database functions (SQLite)
import sqlite3

# Global database connections registry
_db_connections = {}
_db_counter = 0

def builtin_db_connect(args):
    """Connect to SQLite database: db_connect(path)"""
    global _db_counter
    if len(args) < 1:
        raise Exception("db_connect requires 1 argument (database path)")
    
    db_path = str(args[0])
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn_id = f"db_{_db_counter}"
        _db_counter += 1
        _db_connections[conn_id] = conn
        
        return [
            ["connected", True],
            ["connection_id", conn_id],
            ["path", db_path]
        ]
    except Exception as e:
        return [
            ["connected", False],
            ["connection_id", ""],
            ["error", str(e)]
        ]

def builtin_db_close(args):
    """Close database connection: db_close(connection_id)"""
    if len(args) < 1:
        raise Exception("db_close requires 1 argument")
    
    conn_id = str(args[0])
    
    try:
        if conn_id in _db_connections:
            _db_connections[conn_id].close()
            del _db_connections[conn_id]
            return [["success", True]]
        else:
            return [["success", False], ["error", "Connection not found"]]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_execute(args):
    """Execute SQL statement: db_execute(connection_id, sql, params)"""
    if len(args) < 2:
        raise Exception("db_execute requires at least 2 arguments")
    
    conn_id = str(args[0])
    sql = str(args[1])
    params = []
    
    # Parse optional parameters
    if len(args) > 2 and args[2] is not None:
        params_array = args[2]
        if isinstance(params_array, list):
            params = [p[1] if isinstance(p, list) and len(p) >= 2 else p for p in params_array]
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"]]
        
        conn = _db_connections[conn_id]
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        
        # Get last insert id
        last_id = cursor.lastrowid
        
        return [
            ["success", True],
            ["rows_affected", cursor.rowcount],
            ["last_insert_id", last_id if last_id else 0]
        ]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_query(args):
    """Execute SQL query and return results: db_query(connection_id, sql, params)"""
    if len(args) < 2:
        raise Exception("db_query requires at least 2 arguments")
    
    conn_id = str(args[0])
    sql = str(args[1])
    params = []
    
    # Parse optional parameters
    if len(args) > 2 and args[2] is not None:
        params_array = args[2]
        if isinstance(params_array, list):
            params = [p[1] if isinstance(p, list) and len(p) >= 2 else p for p in params_array]
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"], ["rows", []]]
        
        conn = _db_connections[conn_id]
        cursor = conn.cursor()
        cursor.execute(sql, params)
        
        # Fetch all rows and convert to H# format
        columns = [description[0] for description in cursor.description] if cursor.description else []
        rows = []
        
        for row in cursor.fetchall():
            row_dict = []
            for i, value in enumerate(row):
                row_dict.append([columns[i] if i < len(columns) else f"col_{i}", value])
            rows.append(row_dict)
        
        return [
            ["success", True],
            ["rows", rows],
            ["columns", columns],
            ["row_count", len(rows)]
        ]
    except Exception as e:
        return [
            ["success", False],
            ["error", str(e)],
            ["rows", []],
            ["columns", []],
            ["row_count", 0]
        ]

def builtin_db_query_one(args):
    """Execute SQL query and return single row: db_query_one(connection_id, sql, params)"""
    if len(args) < 2:
        raise Exception("db_query_one requires at least 2 arguments")
    
    conn_id = str(args[0])
    sql = str(args[1])
    params = []
    
    if len(args) > 2 and args[2] is not None:
        params_array = args[2]
        if isinstance(params_array, list):
            params = [p[1] if isinstance(p, list) and len(p) >= 2 else p for p in params_array]
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"], ["row", []]]
        
        conn = _db_connections[conn_id]
        cursor = conn.cursor()
        cursor.execute(sql, params)
        
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description] if cursor.description else []
            row_dict = []
            for i, value in enumerate(row):
                row_dict.append([columns[i] if i < len(columns) else f"col_{i}", value])
            return [["success", True], ["row", row_dict]]
        else:
            return [["success", True], ["row", []]]
    except Exception as e:
        return [["success", False], ["error", str(e)], ["row", []]]

def builtin_db_begin_transaction(args):
    """Begin transaction: db_begin_transaction(connection_id)"""
    if len(args) < 1:
        raise Exception("db_begin_transaction requires 1 argument")
    
    conn_id = str(args[0])
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"]]
        
        conn = _db_connections[conn_id]
        conn.execute("BEGIN TRANSACTION")
        return [["success", True]]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_commit(args):
    """Commit transaction: db_commit(connection_id)"""
    if len(args) < 1:
        raise Exception("db_commit requires 1 argument")
    
    conn_id = str(args[0])
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"]]
        
        conn = _db_connections[conn_id]
        conn.commit()
        return [["success", True]]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_rollback(args):
    """Rollback transaction: db_rollback(connection_id)"""
    if len(args) < 1:
        raise Exception("db_rollback requires 1 argument")
    
    conn_id = str(args[0])
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"]]
        
        conn = _db_connections[conn_id]
        conn.rollback()
        return [["success", True]]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_create_table(args):
    """Create table: db_create_table(connection_id, table_name, columns)"""
    if len(args) < 3:
        raise Exception("db_create_table requires 3 arguments")
    
    conn_id = str(args[0])
    table_name = str(args[1])
    columns = args[2]  # Array of [name, type] pairs
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"]]
        
        # Build CREATE TABLE SQL
        col_defs = []
        for col in columns:
            if isinstance(col, list) and len(col) >= 2:
                col_defs.append(f"{col[0]} {col[1]}")
        
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
        
        conn = _db_connections[conn_id]
        conn.execute(sql)
        conn.commit()
        
        return [["success", True]]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_drop_table(args):
    """Drop table: db_drop_table(connection_id, table_name)"""
    if len(args) < 2:
        raise Exception("db_drop_table requires 2 arguments")
    
    conn_id = str(args[0])
    table_name = str(args[1])
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"]]
        
        conn = _db_connections[conn_id]
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        
        return [["success", True]]
    except Exception as e:
        return [["success", False], ["error", str(e)]]

def builtin_db_get_tables(args):
    """Get list of tables: db_get_tables(connection_id)"""
    if len(args) < 1:
        raise Exception("db_get_tables requires 1 argument")
    
    conn_id = str(args[0])
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"], ["tables", []]]
        
        conn = _db_connections[conn_id]
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        return [["success", True], ["tables", tables]]
    except Exception as e:
        return [["success", False], ["error", str(e)], ["tables", []]]

def builtin_db_get_table_info(args):
    """Get table schema: db_get_table_info(connection_id, table_name)"""
    if len(args) < 2:
        raise Exception("db_get_table_info requires 2 arguments")
    
    conn_id = str(args[0])
    table_name = str(args[1])
    
    try:
        if conn_id not in _db_connections:
            return [["success", False], ["error", "Connection not found"], ["columns", []]]
        
        conn = _db_connections[conn_id]
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = []
        
        for row in cursor.fetchall():
            columns.append([
                ["name", row[1]],
                ["type", row[2]],
                ["not_null", bool(row[3])],
                ["default_value", row[4]],
                ["primary_key", bool(row[5])]
            ])
        
        return [["success", True], ["columns", columns]]
    except Exception as e:
        return [["success", False], ["error", str(e)], ["columns", []]]

# ═══════════════════════════════════════════════════════════════
#  HASH TABLE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def builtin_htable_create(args=None):
    """Create a new hash table (Python dict): htable_create()"""
    return {}

def builtin_htable_set(args):
    """Set a key-value pair: htable_set(table, key, value)"""
    if len(args) < 3:
        raise Exception("htable_set requires 3 arguments (table, key, value)")
    table = args[0]
    key = args[1]
    value = args[2]
    if not isinstance(table, dict):
        raise Exception("htable_set: first argument must be a hash table")
    table[key] = value
    return table

def builtin_htable_get(args):
    """Get a value by key: htable_get(table, key)"""
    if len(args) < 2:
        raise Exception("htable_get requires 2 arguments (table, key)")
    table = args[0]
    key = args[1]
    if not isinstance(table, dict):
        raise Exception("htable_get: first argument must be a hash table")
    return table.get(key, None)

def builtin_htable_has(args):
    """Check if key exists: htable_has(table, key) → true/false"""
    if len(args) < 2:
        raise Exception("htable_has requires 2 arguments (table, key)")
    table = args[0]
    key = args[1]
    if not isinstance(table, dict):
        raise Exception("htable_has: first argument must be a hash table")
    return key in table

def builtin_htable_delete(args):
    """Remove a key: htable_delete(table, key)"""
    if len(args) < 2:
        raise Exception("htable_delete requires 2 arguments (table, key)")
    table = args[0]
    key = args[1]
    if not isinstance(table, dict):
        raise Exception("htable_delete: first argument must be a hash table")
    if key in table:
        del table[key]
        return True
    return False

def builtin_htable_size(args):
    """Get number of entries: htable_size(table) → int"""
    if len(args) < 1:
        raise Exception("htable_size requires 1 argument (table)")
    table = args[0]
    if not isinstance(table, dict):
        raise Exception("htable_size: argument must be a hash table")
    return len(table)

def builtin_htable_keys(args):
    """Get all keys: htable_keys(table) → array"""
    if len(args) < 1:
        raise Exception("htable_keys requires 1 argument (table)")
    table = args[0]
    if not isinstance(table, dict):
        raise Exception("htable_keys: argument must be a hash table")
    return list(table.keys())

def builtin_htable_values(args):
    """Get all values: htable_values(table) → array"""
    if len(args) < 1:
        raise Exception("htable_values requires 1 argument (table)")
    table = args[0]
    if not isinstance(table, dict):
        raise Exception("htable_values: argument must be a hash table")
    return list(table.values())


# ============= System process execution =============

import subprocess as _subprocess
import signal as _signal

def builtin_sys_run(args):
    """Run a shell command and return its exit code.

    sys_run(command_string, timeout_ms) → exit_code
    - command_string: a shell command line
    - timeout_ms: max time in milliseconds (0 or absent = no timeout)

    Uses bash -c to support shell redirects (< > 2>). Signals SIGKILL on timeout.
    """
    if len(args) < 1:
        raise Exception("sys_run requires at least 1 argument (command)")
    cmd = str(args[0])
    timeout_ms = 0
    if len(args) > 1 and args[1] is not None:
        try:
            timeout_ms = int(args[1])
        except (TypeError, ValueError):
            timeout_ms = 0
    timeout_sec = (timeout_ms / 1000.0) if timeout_ms > 0 else None
    try:
        proc = _subprocess.Popen(
            cmd,
            shell=True,
            executable="/bin/bash",
            stdin=_subprocess.DEVNULL,
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        try:
            rc = proc.wait(timeout=timeout_sec)
            return int(rc)
        except _subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, _signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                proc.wait(timeout=1)
            except Exception:
                pass
            return 124  # 124 = timeout
    except FileNotFoundError:
        return 127
    except Exception:
        return 1


def builtin_read_line(args):
    """Read a single line from stdin. read_line() → string"""
    try:
        line = sys.stdin.readline()
        if not line:
            return ""  # EOF — return empty string, not raise
        return line.rstrip("\n").rstrip("\r")
    except Exception:
        return ""


def builtin_rand_int(args):
    """Random integer in [lo, hi]. rand_int(lo, hi) → int"""
    import random as _random
    if len(args) < 2:
        raise Exception("rand_int requires 2 arguments (lo, hi)")
    try:
        lo = int(args[0])
        hi = int(args[1])
    except (TypeError, ValueError):
        raise Exception("rand_int: arguments must be integers")
    if hi < lo:
        lo, hi = hi, lo
    return _random.randint(lo, hi)


# ============= Extended HTTP helpers (used by ZZW Code Teacher) =============

def builtin_net_http_get_with_headers(args):
    """HTTP GET with custom headers: http_get_with_headers(url, headers_array)"""
    if len(args) < 2:
        return builtin_net_http_get(args)
    return builtin_net_http_get(args)

def builtin_net_http_post_json(args):
    """HTTP POST with JSON body: http_post_json(url, body_string, headers_array)"""
    if len(args) < 2:
        raise Exception("http_post_json requires at least 2 arguments (url, body)")
    return builtin_net_http_post(args)

def builtin_net_http_post_with_headers(args):
    """HTTP POST with custom headers: http_post_with_headers(url, body, headers)"""
    if len(args) < 3:
        return builtin_net_http_post(args)
    return builtin_net_http_post(args)

def builtin_net_http_put_json(args):
    """HTTP PUT with JSON body: http_put_json(url, body, headers_array)"""
    if len(args) < 2:
        raise Exception("http_put_json requires at least 2 arguments (url, body)")
    url = str(args[0])
    data = args[1]
    headers = {"Content-Type": "application/json"}
    if len(args) > 2 and args[2] is not None:
        headers_array = args[2]
        if isinstance(headers_array, list):
            for pair in headers_array:
                if isinstance(pair, list) and len(pair) >= 2:
                    headers[str(pair[0])] = str(pair[1])
    try:
        if isinstance(data, dict):
            data_bytes = json.dumps(data).encode('utf-8')
        elif isinstance(data, list):
            py_dict = {}
            for pair in data:
                if isinstance(pair, list) and len(pair) >= 2:
                    py_dict[str(pair[0])] = pair[1]
            data_bytes = json.dumps(py_dict).encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='PUT')
        response = urllib.request.urlopen(req, timeout=30)
        return {
            "status": response.getcode(),
            "headers": dict(response.headers),
            "body": response.read().decode('utf-8', errors='ignore'),
            "success": True
        }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": dict(e.headers), "body": str(e.reason), "success": False, "error": str(e)}
    except Exception as e:
        return {"status": 0, "headers": {}, "body": "", "success": False, "error": str(e)}

def builtin_net_http_delete(args):
    """HTTP DELETE: http_delete(url, headers_array)"""
    if len(args) < 1:
        raise Exception("http_delete requires at least 1 argument (url)")
    url = str(args[0])
    headers = {}
    if len(args) > 1 and args[1] is not None:
        headers_array = args[1]
        if isinstance(headers_array, list):
            for pair in headers_array:
                if isinstance(pair, list) and len(pair) >= 2:
                    headers[str(pair[0])] = str(pair[1])
    try:
        req = urllib.request.Request(url, headers=headers, method='DELETE')
        response = urllib.request.urlopen(req, timeout=30)
        return {
            "status": response.getcode(),
            "headers": dict(response.headers),
            "body": response.read().decode('utf-8', errors='ignore'),
            "success": True
        }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": dict(e.headers), "body": str(e.reason), "success": False, "error": str(e)}
    except Exception as e:
        return {"status": 0, "headers": {}, "body": "", "success": False, "error": str(e)}

def builtin_get_http_body(args):
    """Extract body from HTTP response dict: http_get_body(response)"""
    if len(args) < 1:
        return ""
    resp = args[0]
    if isinstance(resp, dict):
        return resp.get("body", "")
    return str(resp)

def builtin_get_http_status(args):
    """Extract status from HTTP response dict: http_get_status(response)"""
    if len(args) < 1:
        return 0
    resp = args[0]
    if isinstance(resp, dict):
        return int(resp.get("status", 0))
    return 0

def builtin_float(args):
    """Convert to float: float(value)"""
    if len(args) < 1:
        raise Exception("float requires 1 argument")
    try:
        return float(args[0])
    except (ValueError, TypeError):
        return 0.0

def builtin_notify_warning(args):
    """Show warning notification: notify_warning(title, message)"""
    if len(args) < 2:
        raise Exception("notify_warning requires 2 arguments (title, message)")
    _get_hwd_ui().notify_warning(args[0], args[1])
    return None

# Alias for json_utils.hto which calls net_json_stringify / net_json_parse
# Both point to the same underlying implementations
builtin_net_json_stringify_alias = builtin_net_json_stringify
builtin_net_json_parse_alias = builtin_net_json_parse

# ============= HwdUI host functions =============
# These let H# code drive a Tk-backed GUI via a `new WidgetName()` DSL.
# Implementation lives in python_host/hwd_ui.py (loaded lazily so the
# interpreter doesn't require Tk on hosts that only run servers).

_hwd_ui_mod = None

# Module-level dict that the Interpreter can use to publish its "current"
# instance to host functions. The Interpreter sets "current" on entry of
# its main visit() loop. We use a dict (not a bare module global) so the
# indirection is explicit and threadsafe-by-construction for the single
# interpreter model that H# uses.
_interp_ref = {"current": None}


def _get_hwd_ui():
    global _hwd_ui_mod
    if _hwd_ui_mod is None:
        # The host_functions module is imported by interpreter.py; the
        # python_host/ directory is a sibling of the project root, so we
        # add it to sys.path dynamically.
        import os as _os
        here = _os.path.dirname(_os.path.abspath(__file__))
        # host_functions.py is at the H# v0.4 root; the project (with
        # python_host/) is one level up under zzw-code-teacher.
        project_root = _os.path.normpath(_os.path.join(here, "zzw-code-teacher"))
        py_dir = _os.path.join(project_root, "python_host")
        if py_dir not in sys.path:
            sys.path.insert(0, py_dir)
        import hwd_ui as _hwd
        _hwd_ui_mod = _hwd
    return _hwd_ui_mod


def builtin_hwdui_init(args):
    _get_hwd_ui().hwdui_init()
    # Populate the host widget registry the first time the H# program calls
    # hwdui_init, so the program only pays the import cost when needed.
    interp = _interp_ref.get("current")
    if interp is not None and not interp._hwdui_loaded:
        mod = _get_hwd_ui()
        for name, factory in mod.WIDGET_FACTORIES.items():
            interp._host_widgets[name] = lambda args, f=factory: f(*args)
        interp._hwdui_loaded = True
    return True


def builtin_hwdui_theme_dark(args):
    _get_hwd_ui().hwdui_theme_dark()
    return True


def builtin_hwdui_create_window(args):
    if len(args) < 3:
        raise Exception("hwdui_create_window requires 3 arguments (title, w, h)")
    title = args[0]
    w = args[1]
    h = args[2]
    return _get_hwd_ui().hwdui_create_window(title, w, h)


def builtin_ui_run(args):
    _get_hwd_ui().ui_run()
    return None


def builtin_ui_quit(args):
    _get_hwd_ui().ui_quit()
    return None


def builtin_notify_info(args):
    if len(args) < 2:
        raise Exception("notify_info requires 2 arguments (title, message)")
    _get_hwd_ui().notify_info(args[0], args[1])
    return None


def builtin_notify_error(args):
    if len(args) < 2:
        raise Exception("notify_error requires 2 arguments (title, message)")
    _get_hwd_ui().notify_error(args[0], args[1])
    return None


def builtin_new_widget(args):
    """Generic `new ClassName(args...)` dispatch used by the interpreter when
    a class isn't defined in H# but is registered as a host widget."""
    if len(args) < 1:
        raise Exception("new requires at least 1 argument (class name)")
    cname = args[0]
    remaining = list(args[1:])
    return _get_hwd_ui().make_widget(cname, remaining)


# ============================================================================
# Standard-library functions expected by test_standard_libs.hto
# (datetime_*, fs_*, io_* and str_contains). These mirror the richer API of
# the Kotlin/.NET backends so the documented stdlib works on the Python VM too.
# ============================================================================

# ---- Date / Time ----------------------------------------------------------

def builtin_datetime_now(args=None):
    """Current local date/time as 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def builtin_datetime_timestamp(args=None):
    """Current Unix timestamp in seconds."""
    return int(time.time())


def builtin_datetime_format(args):
    """Format a timestamp (seconds) with a strftime format string."""
    if len(args) < 2:
        raise Exception("datetime_format requires 2 arguments (timestamp, format)")
    ts = float(args[0])
    fmt = str(args[1])
    return datetime.fromtimestamp(ts).strftime(fmt)


def builtin_datetime_parse(args):
    """Parse a date string into an internal timestamp (seconds) or nullptr on failure."""
    if len(args) < 1:
        raise Exception("datetime_parse requires 1 argument (date_string)")
    s = str(args[0]).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d", "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S", "%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return int(time.mktime(datetime.strptime(s, fmt).timetuple()))
        except Exception:
            continue
    return None


def builtin_datetime_get_year(args):
    """Year component of a parsed timestamp."""
    if len(args) < 1:
        raise Exception("datetime_get_year requires 1 argument")
    ts = float(args[0])
    return datetime.fromtimestamp(ts).year


def builtin_datetime_is_leap_year(args):
    """True if the given year is a leap year."""
    if len(args) < 1:
        raise Exception("datetime_is_leap_year requires 1 argument (year)")
    year = int(args[0])
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def builtin_datetime_days_in_month(args):
    """Number of days in the given month of the given year."""
    if len(args) < 2:
        raise Exception("datetime_days_in_month requires 2 arguments (year, month)")
    year = int(args[0])
    month = int(args[1])
    return calendar.monthrange(year, month)[1]


def builtin_datetime_format_duration(args):
    """Format a duration in seconds as 'Nh Nm Ns'."""
    if len(args) < 1:
        raise Exception("datetime_format_duration requires 1 argument (seconds)")
    secs = int(float(args[0]))
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def builtin_datetime_today(args=None):
    """Today's date as 'YYYY-MM-DD'."""
    return datetime.now().strftime("%Y-%m-%d")


def builtin_datetime_timer_start(args=None):
    """Return a timer handle (perf_counter)."""
    return time.perf_counter()


def builtin_datetime_timer_elapsed(args):
    """Elapsed seconds since a timer handle was started."""
    if len(args) < 1:
        raise Exception("datetime_timer_elapsed requires 1 argument (timer)")
    return time.perf_counter() - float(args[0])


# ---- File System ----------------------------------------------------------

def builtin_fs_dir_current(args=None):
    """Current working directory."""
    return os.getcwd()


def builtin_fs_path_join(args):
    """Join path components."""
    if len(args) < 2:
        raise Exception("fs_path_join requires at least 2 arguments")
    return os.path.join(str(args[0]), str(args[1]))


def builtin_fs_path_filename(args):
    """Basename of a path."""
    if len(args) < 1:
        raise Exception("fs_path_filename requires 1 argument")
    return os.path.basename(str(args[0]))


def builtin_fs_path_extension(args):
    """Extension of a path (includes the leading dot)."""
    if len(args) < 1:
        raise Exception("fs_path_extension requires 1 argument")
    return os.path.splitext(str(args[0]))[1]


def builtin_fs_path_is_absolute(args):
    """True if the path is absolute."""
    if len(args) < 1:
        raise Exception("fs_path_is_absolute requires 1 argument")
    return os.path.isabs(str(args[0]))


def builtin_fs_temp_dir(args):
    """Create a temp directory with the given prefix; return its path."""
    prefix = str(args[0]) if args else "hsharp"
    return tempfile.mkdtemp(prefix=prefix + "_")


def builtin_fs_cleanup_temp(args):
    """Remove a temporary directory created by fs_temp_dir."""
    if len(args) < 1:
        raise Exception("fs_cleanup_temp requires 1 argument")
    p = str(args[0])
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
    return None


def builtin_fs_format_size(args):
    """Human-readable file size from a byte count."""
    if len(args) < 1:
        raise Exception("fs_format_size requires 1 argument (bytes)")
    size = float(args[0])
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024.0 or unit == "PB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.1f} PB"


def builtin_fs_validate_path(args):
    """Validate a path string (reject control/invalid filename chars)."""
    if len(args) < 1:
        raise Exception("fs_validate_path requires 1 argument")
    p = str(args[0])
    invalid = set('<>"|?*')
    if any(c in invalid for c in p):
        return False
    if "\x00" in p:
        return False
    return True


def builtin_fs_change_extension(args):
    """Replace a path's extension. ext may include or omit the leading dot."""
    if len(args) < 2:
        raise Exception("fs_change_extension requires 2 arguments (path, ext)")
    p = str(args[0])
    ext = str(args[1])
    if not ext.startswith("."):
        ext = "." + ext
    base, _ = os.path.splitext(p)
    return base + ext


def builtin_fs_path_parent(args):
    """Parent directory of a path."""
    if len(args) < 1:
        raise Exception("fs_path_parent requires 1 argument")
    return os.path.dirname(str(args[0]))


def builtin_fs_file_delete(args):
    """Delete a file."""
    if len(args) < 1:
        raise Exception("fs_file_delete requires 1 argument")
    p = str(args[0])
    if os.path.exists(p):
        os.remove(p)
    return None


def builtin_fs_file_exists(args):
    """True if the path exists."""
    if len(args) < 1:
        raise Exception("fs_file_exists requires 1 argument")
    return os.path.exists(str(args[0]))


def builtin_fs_dir_exists(args):
    """True if the path exists and is a directory."""
    if len(args) < 1:
        raise Exception("fs_dir_exists requires 1 argument")
    return os.path.isdir(str(args[0]))


# ---- I/O helpers ----------------------------------------------------------

def builtin_io_pad_right(args):
    """Right-pad a string to a given width."""
    if len(args) < 2:
        raise Exception("io_pad_right requires 2 arguments (string, width)")
    return str(args[0]).ljust(int(args[1]))


def builtin_io_csv_parse_line(args):
    """Split a CSV line by a separator into a list of fields."""
    if len(args) < 2:
        raise Exception("io_csv_parse_line requires 2 arguments (line, sep)")
    return str(args[0]).split(str(args[1]))


def builtin_io_progress_bar(args):
    """Print a simple progress bar. No return value."""
    if len(args) < 3:
        raise Exception("io_progress_bar requires 3 arguments (current, total, width)")
    cur = int(args[0])
    total = max(int(args[1]), 1)
    width = int(args[2])
    frac = cur / total
    filled = int(width * frac)
    bar = "#" * filled + "-" * (width - filled)
    print(f"[{bar}] {cur}/{total} ({int(frac * 100)}%)")
    return None


def builtin_io_display_table(args):
    """Print a simple ASCII table. No return value."""
    if len(args) < 2:
        raise Exception("io_display_table requires at least 2 arguments (headers, rows)")
    headers = args[0]
    rows = args[1]
    cols = list(headers)
    widths = [len(str(c)) for c in cols]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "-+-".join("-" * (w + 2) for w in widths)
    print("  " + "  |  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)))
    print(line)
    for row in rows:
        print("  " + "  |  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
    return None


def builtin_io_file_write(args):
    """Write content to a file (overwrite)."""
    if len(args) < 2:
        raise Exception("io_file_write requires 2 arguments (path, content)")
    with open(str(args[0]), "w", encoding="utf-8") as f:
        f.write(str(args[1]))
    return None


def builtin_io_file_read(args):
    """Read a file's full content as a string."""
    if len(args) < 1:
        raise Exception("io_file_read requires 1 argument (path)")
    with open(str(args[0]), "r", encoding="utf-8") as f:
        return f.read()


def builtin_io_file_append(args):
    """Append content to a file."""
    if len(args) < 2:
        raise Exception("io_file_append requires 2 arguments (path, content)")
    with open(str(args[0]), "a", encoding="utf-8") as f:
        f.write(str(args[1]))
    return None


def builtin_io_file_write_lines(args):
    """Write a list of lines to a file (one per line)."""
    if len(args) < 2:
        raise Exception("io_file_write_lines requires 2 arguments (path, lines)")
    with open(str(args[0]), "w", encoding="utf-8") as f:
        for line in args[1]:
            f.write(str(line) + "\n")
    return None


def builtin_io_file_read_lines(args):
    """Read a file into a list of lines (newlines stripped)."""
    if len(args) < 1:
        raise Exception("io_file_read_lines requires 1 argument (path)")
    with open(str(args[0]), "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def builtin_io_kv_write(args):
    """Write key/value pairs to a file as `key=value` lines."""
    if len(args) < 3:
        raise Exception("io_kv_write requires 3 arguments (path, keys, values)")
    keys = args[1]
    values = args[2]
    with open(str(args[0]), "w", encoding="utf-8") as f:
        for k, v in zip(keys, values):
            f.write(f"{k}={v}\n")
    return None


def builtin_io_kv_read(args):
    """Read a `key=value` file; returns [keys_list, values_list]."""
    if len(args) < 1:
        raise Exception("io_kv_read requires 1 argument (path)")
    keys = []
    values = []
    if os.path.exists(str(args[0])):
        with open(str(args[0]), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                keys.append(k)
                values.append(v)
    return [keys, values]


def builtin_io_log_info(args):
    """Append a timestamped INFO log entry to a file."""
    if len(args) < 2:
        raise Exception("io_log_info requires 2 arguments (path, message)")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(str(args[0]), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] INFO {args[1]}\n")
    return None


def builtin_str_contains(args):
    """True if `haystack` contains `needle`."""
    if len(args) < 2:
        raise Exception("str_contains requires 2 arguments (haystack, needle)")
    return str(args[0]) != "" and str(args[1]) in str(args[0])



