"""
Additional host functions for H# bootstrap modules
These functions provide system-level capabilities needed by H# standard libraries
"""

import time
import os
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
        # Convert H# dict format (array of [key,value] pairs) to Python dict
        def convert_hsharp_to_python(obj):
            if isinstance(obj, list):
                # Check if it's a dict-like structure
                if len(obj) > 0 and all(isinstance(item, list) and len(item) >= 2 for item in obj):
                    return {str(item[0]): convert_hsharp_to_python(item[1]) for item in obj}
                else:
                    return [convert_hsharp_to_python(item) for item in obj]
            else:
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
        def convert_python_to_hsharp(obj):
            if isinstance(obj, dict):
                return [[k, convert_python_to_hsharp(v)] for k, v in obj.items()]
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


