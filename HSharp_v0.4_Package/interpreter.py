import os
import sys
import math as _math
from h_ast import *
from tokens import TokenType
from bytecode import VM
from host_functions import (
    builtin_time_now,
    builtin_substring,
    builtin_ord,
    builtin_chr,
    builtin_int,
    builtin_str,
    builtin_date_now,
    builtin_date_timestamp,
    builtin_date_format,
    builtin_date_parse,
    builtin_fs_exists,
    builtin_fs_is_file,
    builtin_fs_is_dir,
    builtin_fs_mkdir,
    builtin_fs_remove,
    builtin_fs_list_dir,
    builtin_fs_get_cwd,
    builtin_fs_chdir,
    builtin_fs_join_path,
    builtin_fs_get_ext,
    builtin_fs_get_basename,
    builtin_fs_get_dirname,
    builtin_io_append_file,
    builtin_io_read_lines,
    builtin_io_write_lines,
    # Network functions
    builtin_net_http_get,
    builtin_net_http_post,
    builtin_net_url_parse,
    builtin_net_url_build,
    builtin_net_tcp_connect,
    builtin_net_tcp_send,
    builtin_net_tcp_recv,
    builtin_net_tcp_close,
    builtin_net_udp_create,
    builtin_net_udp_send,
    builtin_net_udp_recv,
    builtin_net_base64_encode,
    builtin_net_base64_decode,
    builtin_net_json_stringify,
    builtin_net_json_parse,
    # Database functions
    builtin_db_connect,
    builtin_db_close,
    builtin_db_execute,
    builtin_db_query,
    builtin_db_query_one,
    builtin_db_begin_transaction,
    builtin_db_commit,
    builtin_db_rollback,
    builtin_db_create_table,
    builtin_db_drop_table,
    builtin_db_get_tables,
    builtin_db_get_table_info,
    # Hash table functions
    builtin_htable_create,
    builtin_htable_set,
    builtin_htable_get,
    builtin_htable_has,
    builtin_htable_delete,
    builtin_htable_size,
    builtin_htable_keys,
    builtin_htable_values,
)
import time


# Bridge: wrap a list of tokens produced by an H# tokenizer into an object
# compatible with the Python Parser (provides get_next_token()).
class HSharpTokenStream:
    def __init__(self, tokens_list):
        # tokens_list: list of dicts {"type": str, "value": val}
        self.tokens = tokens_list or []
        self.pos = 0

    def _convert_value(self, ttype, val):
        if val is None:
            return None
        if ttype == 'NUMBER':
            try:
                if isinstance(val, (int, float)):
                    return val
                s = str(val)
                if '.' in s:
                    return float(s)
                return int(s)
            except Exception:
                return val
        if ttype == 'BOOL':
            return bool(val)
        # keep strings and other values as-is
        return val

    def get_next_token(self):
        if self.pos >= len(self.tokens):
            return (TokenType.EOF, None)
        tk = self.tokens[self.pos]
        self.pos += 1
        tname = tk.get('type')
        val = tk.get('value')
        # map token name to TokenType enum; if missing, raise
        try:
            ttype = getattr(TokenType, tname)
        except Exception:
            raise HSharpError(f"Unknown token type from H# tokenizer: {tname}")
        return (ttype, self._convert_value(tname, val))

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class ContinueException(Exception):
    pass

class BreakException(Exception):
    pass

class HSharpError(Exception):
    pass

# Add polymorphism-related AST nodes
class SuperExpression(AST):
    def __init__(self, method_name, args):
        self.method_name = method_name
        self.args = args

class InstanceOfExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

class CastExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

# Add polymorphism-related AST nodes
class SuperExpression(AST):
    def __init__(self, method_name, args):
        self.method_name = method_name
        self.args = args

class InstanceOfExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

class CastExpression(AST):
    def __init__(self, expr, type_name):
        self.expr = expr
        self.type_name = type_name

class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def define(self, name, value):
        self.vars[name] = value

    def assign(self, name, value):
        if name in self.vars:
            self.vars[name] = value
        elif self.parent:
            self.parent.assign(name, value)
        else:
            raise HSharpError(f"Undefined variable: '{name}'")

    def lookup(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        raise HSharpError(f"Undefined variable: '{name}'")


class CoroYield(Exception):
    pass


class Coroutine:
    def __init__(self, func_node, interpreter, args):
        self.func = func_node
        self.interpreter = interpreter
        # prepare env with params
        self.env = Environment(parent=interpreter.global_env)
        for pname, arg in zip(func_node.params, args):
            self.env.define(pname, arg)
        self.done = False
        self.retval = None
        self.pc = 0
        # stack of frames: each is dict {'stmts': list, 'pc': int, 'env': Environment}
        self.stack = []
        self.waiting = None  # None or ('sleep', until) or ('event', name)
        self.priority = 0

    def resume(self):
        if self.done:
            return self.retval
        prev = self.interpreter._current_coroutine
        self.interpreter._current_coroutine = self
        try:
            # initialize stack with function body if empty
            if not self.stack:
                self.stack.append({'stmts': list(self.func.body.statements), 'pc': 0, 'env': self.env})

            while self.stack:
                frame = self.stack[-1]
                # generator frame
                if 'gen' in frame:
                    gen = frame['gen']
                    try:
                        yielded = next(gen)
                        # if generator yields a suspend tuple, suspend coroutine
                        if isinstance(yielded, tuple) and yielded[0] == 'suspend':
                            return None
                        # otherwise continue running
                        continue
                    except StopIteration as e:
                        # generator finished with value
                            self.stack.pop()
                            # advance parent frame pc so the statement that spawned the gen is not re-run
                            if self.stack:
                                parent = self.stack[-1]
                                if 'pc' in parent:
                                    parent['pc'] = parent.get('pc', 0) + 1
                            continue
                else:
                    stmts = frame['stmts']
                    pc = frame['pc']
                    if pc >= len(stmts):
                        # pop finished frame
                        self.stack.pop()
                        continue
                    stmt = stmts[pc]
                    try:
                        # execute a single statement in coroutine-aware mode
                        finished = self.interpreter.execute_stmt_for_coro(stmt, frame['env'], self)
                        if finished is True:
                            # statement completed normally
                            frame['pc'] += 1
                            continue
                        # if finished is False, it means control transferred (e.g., pushed new frame)
                        # in that case do not advance pc here
                        continue
                    except CoroYield:
                        # suspend: advance pc so resume continues after this statement
                        frame['pc'] += 1
                        return None
            # no frames left: finished
            self.done = True
            return self.retval
        except ReturnException as e:
            self.retval = e.value
            self.done = True
            return self.retval
        finally:
            self.interpreter._current_coroutine = prev
        # finished without explicit return
        self.done = True
        return None

# --- Built-in Functions ---

def builtin_len(args):
    if len(args) != 1:
        raise HSharpError("len() takes exactly 1 argument")
    obj = args[0]
    if isinstance(obj, list):
        return len(obj)
    elif isinstance(obj, str):
        return len(obj)
    elif isinstance(obj, dict):
        return len(obj)
    else:
        raise HSharpError("len() argument must be array, dict, or string")

def builtin_tag(args):
    if len(args) != 1:
        raise HSharpError("_tag(obj) takes exactly 1 argument")
    obj = args[0]
    try:
        return obj[0]
    except (TypeError, IndexError, KeyError):
        return None

def builtin_push(args):
    if len(args) != 2:
        raise HSharpError("push(arr, x) takes exactly 2 arguments")
    arr, x = args
    if not isinstance(arr, list):
        raise HSharpError("First argument to push must be an array")
    arr.append(x)
    return None

def builtin_pop(args):
    if len(args) != 1:
        raise HSharpError("pop(arr) takes exactly 1 argument")
    arr = args[0]
    if not isinstance(arr, list):
        raise HSharpError("Argument to pop must be an array")
    if not arr:
        raise HSharpError("Cannot pop from empty array")
    return arr.pop()

def builtin_read_file(args):
    if len(args) != 1:
        raise HSharpError("read_file(path) takes exactly 1 argument")
    path = args[0]
    if not isinstance(path, str):
        raise HSharpError("File path must be a string")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise HSharpError(f"Failed to read file '{path}': {e}")

def builtin_write_file(args):
    if len(args) != 2:
        raise HSharpError("write_file(path, content) takes exactly 2 arguments")
    path, content = args
    if not isinstance(path, str) or not isinstance(content, str):
        raise HSharpError("Arguments must be strings")
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return None
    except Exception as e:
        raise HSharpError(f"Failed to write file '{path}': {e}")

def builtin_input(args):
    if len(args) > 1:
        raise HSharpError("input() takes at most 1 argument")
    if args:
        prompt = args[0]
        if not isinstance(prompt, str):
            raise HSharpError("input() argument must be a string")
        return input(prompt)
    else:
        return input()

def builtin_input(args):
    if len(args) > 1:
        raise HSharpError("input() takes at most 1 argument")
    if args:
        prompt = args[0]
        if not isinstance(prompt, str):
            raise HSharpError("input() argument must be a string")
        return input(prompt)
    else:
        return input()

# ── Math Builtins ──
def _math_arg1(args, fn, name):
    if len(args) != 1:
        raise HSharpError(f"{name}() takes exactly 1 argument")
    return fn(float(args[0]))

def _math_arg2(args, fn, name):
    if len(args) != 2:
        raise HSharpError(f"{name}() takes exactly 2 arguments")
    return fn(float(args[0]), float(args[1]))

def builtin_math_sin(args): return _math_arg1(args, _math.sin, "math_sin")
def builtin_math_cos(args): return _math_arg1(args, _math.cos, "math_cos")
def builtin_math_tan(args): return _math_arg1(args, _math.tan, "math_tan")
def builtin_math_asin(args):
    if len(args) != 1: raise HSharpError("math_asin() takes exactly 1 argument")
    x = float(args[0])
    if x < -1 or x > 1: return None
    return _math.asin(x)
def builtin_math_acos(args):
    if len(args) != 1: raise HSharpError("math_acos() takes exactly 1 argument")
    x = float(args[0])
    if x < -1 or x > 1: return None
    return _math.acos(x)
def builtin_math_atan(args): return _math_arg1(args, _math.atan, "math_atan")
def builtin_math_atan2(args): return _math_arg2(args, _math.atan2, "math_atan2")
def builtin_math_sinh(args): return _math_arg1(args, _math.sinh, "math_sinh")
def builtin_math_cosh(args): return _math_arg1(args, _math.cosh, "math_cosh")
def builtin_math_tanh(args): return _math_arg1(args, _math.tanh, "math_tanh")
def builtin_math_exp(args): return _math_arg1(args, _math.exp, "math_exp")
def builtin_math_log(args):
    if len(args) != 1: raise HSharpError("math_log() takes exactly 1 argument")
    x = float(args[0])
    if x <= 0: return None
    return _math.log(x)
def builtin_math_log10(args):
    if len(args) != 1: raise HSharpError("math_log10() takes exactly 1 argument")
    x = float(args[0])
    if x <= 0: return None
    return _math.log10(x)
def builtin_math_log2(args):
    if len(args) != 1: raise HSharpError("math_log2() takes exactly 1 argument")
    x = float(args[0])
    if x <= 0: return None
    return _math.log2(x)
def builtin_math_sqrt(args):
    if len(args) != 1: raise HSharpError("math_sqrt() takes exactly 1 argument")
    x = float(args[0])
    if x < 0: return None
    return _math.sqrt(x)
def builtin_math_pow(args): return _math_arg2(args, _math.pow, "math_pow")
def builtin_math_floor(args): return _math_arg1(args, _math.floor, "math_floor")
def builtin_math_ceil(args): return _math_arg1(args, _math.ceil, "math_ceil")
def builtin_math_fabs(args): return _math_arg1(args, _math.fabs, "math_fabs")
def builtin_math_fmod(args):
    if len(args) != 2: raise HSharpError("math_fmod() takes exactly 2 arguments")
    y = float(args[1])
    if y == 0: return None
    return _math.fmod(float(args[0]), y)
def builtin_math_cbrt(args):
    x = float(args[0])
    return x ** (1.0/3.0) if x >= 0 else -((-x) ** (1.0/3.0))
def builtin_math_hypot(args): return _math_arg2(args, _math.hypot, "math_hypot")
def builtin_math_erf(args): return _math_arg1(args, _math.erf, "math_erf")
def builtin_math_erfc(args): return _math_arg1(args, _math.erfc, "math_erfc")
def builtin_math_tgamma(args): return _math_arg1(args, _math.gamma, "math_tgamma")
def builtin_math_lgamma(args): return _math_arg1(args, _math.lgamma, "math_lgamma")

# ── Dictionary Builtins ──
def builtin_dict_keys(args):
    if len(args) != 1:
        raise HSharpError("dict_keys() takes exactly 1 argument")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("dict_keys() argument must be a dictionary")
    return list(d.keys())

def builtin_dict_values(args):
    if len(args) != 1:
        raise HSharpError("dict_values() takes exactly 1 argument")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("dict_values() argument must be a dictionary")
    return list(d.values())

def builtin_dict_items(args):
    if len(args) != 1:
        raise HSharpError("dict_items() takes exactly 1 argument")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("dict_items() argument must be a dictionary")
    return [[k, v] for k, v in d.items()]

def builtin_dict_get(args):
    if len(args) < 2:
        raise HSharpError("dict_get(dict, key[, default]) requires at least 2 arguments")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("First argument must be a dictionary")
    key = args[1]
    if key in d:
        return d[key]
    if len(args) >= 3:
        return args[2]
    return None

def builtin_dict_has(args):
    if len(args) != 2:
        raise HSharpError("dict_has(dict, key) takes exactly 2 arguments")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("First argument must be a dictionary")
    key = args[1]
    return key in d

def builtin_dict_pop(args):
    if len(args) < 2:
        raise HSharpError("dict_pop(dict, key[, default]) requires at least 2 arguments")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("First argument must be a dictionary")
    key = args[1]
    if key in d:
        val = d[key]
        del d[key]
        return val
    if len(args) >= 3:
        return args[2]
    raise HSharpError(f"Key '{key}' not found in dictionary")

def builtin_dict_clear(args):
    if len(args) != 1:
        raise HSharpError("dict_clear() takes exactly 1 argument")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("First argument must be a dictionary")
    d.clear()
    return None

def builtin_dict_merge(args):
    if len(args) != 2:
        raise HSharpError("dict_merge(target, source) takes exactly 2 arguments")
    target = args[0]
    source = args[1]
    if not isinstance(target, dict) or not isinstance(source, dict):
        raise HSharpError("Both arguments must be dictionaries")
    for k, v in source.items():
        target[k] = v
    return target

def builtin_dict_copy(args):
    if len(args) != 1:
        raise HSharpError("dict_copy() takes exactly 1 argument")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("First argument must be a dictionary")
    return dict(d)

def builtin_dict_len(args):
    if len(args) != 1:
        raise HSharpError("dict_len() takes exactly 1 argument")
    d = args[0]
    if not isinstance(d, dict):
        raise HSharpError("First argument must be a dictionary")
    return len(d)

# ── List Builtins ──
def builtin_list_append(args):
    if len(args) != 2:
        raise HSharpError("list_append(list, item) takes exactly 2 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    lst.append(args[1])
    return None

def builtin_list_push(args):
    if len(args) != 2:
        raise HSharpError("list_push(list, item) takes exactly 2 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    lst.append(args[1])
    return None

def builtin_list_pop(args):
    if len(args) == 0 or len(args) > 2:
        raise HSharpError("list_pop(list[, index]) takes 1 or 2 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    if len(lst) == 0:
        raise HSharpError("Cannot pop from empty list")
    if len(args) == 2:
        idx = int(args[1])
        if idx < 0 or idx >= len(lst):
            raise HSharpError("List index out of bounds")
        val = lst[idx]
        del lst[idx]
        return val
    return lst.pop()

def builtin_list_insert(args):
    if len(args) != 3:
        raise HSharpError("list_insert(list, index, item) takes exactly 3 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    idx = int(args[1])
    if idx < 0:
        idx = len(lst) + idx
    if idx < 0:
        idx = 0
    if idx > len(lst):
        idx = len(lst)
    lst.insert(idx, args[2])
    return None

def builtin_list_remove(args):
    if len(args) != 2:
        raise HSharpError("list_remove(list, value) takes exactly 2 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    val = args[1]
    i = 0
    while i < len(lst):
        if lst[i] == val:
            del lst[i]
            return None
        i = i + 1
    raise HSharpError("Value not found in list")

def builtin_list_index(args):
    if len(args) < 2:
        raise HSharpError("list_index(list, value[, start[, end]]) takes at least 2 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    val = args[1]
    start = 0
    end = len(lst)
    if len(args) >= 3:
        start = int(args[2])
    if len(args) >= 4:
        end = int(args[3])
    i = start
    while i < end:
        if lst[i] == val:
            return i
        i = i + 1
    raise HSharpError("Value not found in list")

def builtin_list_extend(args):
    if len(args) != 2:
        raise HSharpError("list_extend(target, items) takes exactly 2 arguments")
    lst = args[0]
    items = args[1]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    if not isinstance(items, list):
        raise HSharpError("Second argument must be a list")
    lst.extend(items)
    return None

def builtin_list_reverse(args):
    if len(args) != 1:
        raise HSharpError("list_reverse(list) takes exactly 1 argument")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    lst.reverse()
    return None

def builtin_list_sort(args):
    if len(args) != 1:
        raise HSharpError("list_sort(list) takes exactly 1 argument")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    lst.sort()
    return None

def builtin_list_slice(args):
    if len(args) == 2:
        lst = args[0]
        if not isinstance(lst, list):
            raise HSharpError("First argument must be a list")
        start = int(args[1])
        return lst[start:]
    elif len(args) == 3:
        lst = args[0]
        start = int(args[1])
        end = int(args[2])
        return lst[start:end]
    elif len(args) == 4:
        lst = args[0]
        start = int(args[1])
        end = int(args[2])
        step = int(args[3])
        return lst[start:end:step]
    else:
        raise HSharpError("list_slice(list[, start[, end[, step]]]) takes 1-4 arguments")

def builtin_list_count(args):
    if len(args) != 2:
        raise HSharpError("list_count(list, value) takes exactly 2 arguments")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    val = args[1]
    count = 0
    for item in lst:
        if item == val:
            count = count + 1
    return count

def builtin_list_clear(args):
    if len(args) != 1:
        raise HSharpError("list_clear(list) takes exactly 1 argument")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    lst.clear()
    return None

def builtin_list_copy(args):
    if len(args) != 1:
        raise HSharpError("list_copy(list) takes exactly 1 argument")
    lst = args[0]
    if not isinstance(lst, list):
        raise HSharpError("First argument must be a list")
    return list(lst)

def builtin_list_fill(args):
    if len(args) != 3:
        raise HSharpError("list_fill(list, length, value) takes exactly 3 arguments")
    length = int(args[1])
    if length < 0:
        raise HSharpError("Length must be non-negative")
    return [args[2] for _ in range(length)]

def builtin_list_reserve(args):
    if len(args) != 2:
        raise HSharpError("list_reserve(list, capacity) takes exactly 2 arguments")
    # In Python list doesn't have reserve, this is a no-op that does nothing
    return None

class Interpreter:
    def __init__(self, global_env=None, functions=None):
        self.global_env = global_env or Environment()
        self.functions = functions or {}
        self.interfaces = {}
        self.builtins = {
            'len': builtin_len,
            '_tag': builtin_tag,
            'push': builtin_push,
            'pop': builtin_pop,
            'read_file': builtin_read_file,
            'write_file': builtin_write_file,
            'input': builtin_input,
            'thread_spawn': self._builtin_thread_spawn,
            'thread_join': self._builtin_thread_join,
            'coro_yield': self._builtin_coro_yield,
            'coro_resume': self._builtin_coro_resume,
            'coro_sleep': self._builtin_coro_sleep,
            'coro_wait': self._builtin_coro_wait,
            'coro_signal': self._builtin_coro_signal,
            'coro_signal_io': self._builtin_coro_signal_io,
            'scheduler_run': self._builtin_scheduler_run,
            # New host functions for bootstrap modules
            'time_now': builtin_time_now,
            'substring': builtin_substring,
            'ord': builtin_ord,
            'chr': builtin_chr,
            'int': builtin_int,
            'str': builtin_str,
            # Date and Time functions
            'date_now': builtin_date_now,
            'date_timestamp': builtin_date_timestamp,
            'date_format': builtin_date_format,
            'date_parse': builtin_date_parse,
            # File system functions
            'fs_exists': builtin_fs_exists,
            'fs_is_file': builtin_fs_is_file,
            'fs_is_dir': builtin_fs_is_dir,
            'fs_mkdir': builtin_fs_mkdir,
            'fs_remove': builtin_fs_remove,
            'fs_list_dir': builtin_fs_list_dir,
            'fs_get_cwd': builtin_fs_get_cwd,
            'fs_chdir': builtin_fs_chdir,
            'fs_join_path': builtin_fs_join_path,
            'fs_get_ext': builtin_fs_get_ext,
            'fs_get_basename': builtin_fs_get_basename,
            'fs_get_dirname': builtin_fs_get_dirname,
            # IO helper functions
            'io_append_file': builtin_io_append_file,
            'io_read_lines': builtin_io_read_lines,
            'io_write_lines': builtin_io_write_lines,
            # Network functions
            'http_get': builtin_net_http_get,
            'http_post': builtin_net_http_post,
            'url_parse': builtin_net_url_parse,
            'url_build': builtin_net_url_build,
            'tcp_connect': builtin_net_tcp_connect,
            'tcp_send': builtin_net_tcp_send,
            'tcp_recv': builtin_net_tcp_recv,
            'tcp_close': builtin_net_tcp_close,
            'udp_create': builtin_net_udp_create,
            'udp_send': builtin_net_udp_send,
            'udp_recv': builtin_net_udp_recv,
            'base64_encode': builtin_net_base64_encode,
            'base64_decode': builtin_net_base64_decode,
            'json_stringify': builtin_net_json_stringify,
            'json_parse': builtin_net_json_parse,
            # Database functions
            'db_connect': builtin_db_connect,
            'db_close': builtin_db_close,
            'db_execute': builtin_db_execute,
            'db_query': builtin_db_query,
            'db_query_one': builtin_db_query_one,
            'db_begin_transaction': builtin_db_begin_transaction,
            'db_commit': builtin_db_commit,
            'db_rollback': builtin_db_rollback,
            'db_create_table': builtin_db_create_table,
            'db_drop_table': builtin_db_drop_table,
            'db_get_tables': builtin_db_get_tables,
            'db_get_table_info': builtin_db_get_table_info,
            # Hash table functions
            'htable_create': builtin_htable_create,
            'htable_set': builtin_htable_set,
            'htable_get': builtin_htable_get,
            'htable_has': builtin_htable_has,
            'htable_delete': builtin_htable_delete,
            'htable_size': builtin_htable_size,
            'htable_keys': builtin_htable_keys,
            'htable_values': builtin_htable_values,
            # DZZW concurrency primitives
            'dzzw_spawn': self._dzzw_spawn,
            'dzzw_await': self._dzzw_await,
            'dzzw_try_await': self._dzzw_try_await,
            'dzzw_await_any': self._dzzw_await_any,
            'dzzw_await_all': self._dzzw_await_all,
            'dzzw_parallel_map': self._dzzw_parallel_map,
            'dzzw_worker_count': self._dzzw_worker_count,
            'dzzw_pending_count': self._dzzw_pending_count,
            'dzzw_total_submitted': self._dzzw_total_submitted,
            'dzzw_total_completed': self._dzzw_total_completed,
            'dzzw_dump_stats': self._dzzw_dump_stats,
            'dzzw_channel_create': self._dzzw_channel_create,
            'dzzw_channel_send': self._dzzw_channel_send,
            'dzzw_channel_recv': self._dzzw_channel_recv,
            'dzzw_channel_try_send': self._dzzw_channel_try_send,
            'dzzw_channel_try_recv': self._dzzw_channel_try_recv,
            'dzzw_channel_close': self._dzzw_channel_close,
            'dzzw_channel_free': self._dzzw_channel_free,
            'dzzw_channel_size': self._dzzw_channel_size,
            'dzzw_mutex_create': self._dzzw_mutex_create,
            'dzzw_mutex_lock': self._dzzw_mutex_lock,
            'dzzw_mutex_unlock': self._dzzw_mutex_unlock,
            'dzzw_mutex_try_lock': self._dzzw_mutex_try_lock,
            'dzzw_mutex_free': self._dzzw_mutex_free,
            # Math functions
            'math_sin': builtin_math_sin,
            'math_cos': builtin_math_cos,
            'math_tan': builtin_math_tan,
            'math_asin': builtin_math_asin,
            'math_acos': builtin_math_acos,
            'math_atan': builtin_math_atan,
            'math_atan2': builtin_math_atan2,
            'math_sinh': builtin_math_sinh,
            'math_cosh': builtin_math_cosh,
            'math_tanh': builtin_math_tanh,
            'math_exp': builtin_math_exp,
            'math_log': builtin_math_log,
            'math_log10': builtin_math_log10,
            'math_log2': builtin_math_log2,
            'math_sqrt': builtin_math_sqrt,
            'math_pow': builtin_math_pow,
            'math_floor': builtin_math_floor,
            'math_ceil': builtin_math_ceil,
            'math_fabs': builtin_math_fabs,
            'math_fmod': builtin_math_fmod,
            'math_cbrt': builtin_math_cbrt,
            'math_hypot': builtin_math_hypot,
            'math_erf': builtin_math_erf,
            'math_erfc': builtin_math_erfc,
            'math_tgamma': builtin_math_tgamma,
            'math_lgamma': builtin_math_lgamma,
            # Dictionary operations
            'dict_keys': builtin_dict_keys,
            'dict_values': builtin_dict_values,
            'dict_items': builtin_dict_items,
            'dict_get': builtin_dict_get,
            'dict_has': builtin_dict_has,
            'dict_pop': builtin_dict_pop,
            'dict_clear': builtin_dict_clear,
            'dict_merge': builtin_dict_merge,
            'dict_copy': builtin_dict_copy,
            'dict_len': builtin_dict_len,
            # List operations
            'list_append': builtin_list_append,
            'list_push': builtin_list_push,
            'list_pop': builtin_list_pop,
            'list_insert': builtin_list_insert,
            'list_remove': builtin_list_remove,
            'list_index': builtin_list_index,
            'list_extend': builtin_list_extend,
            'list_reverse': builtin_list_reverse,
            'list_sort': builtin_list_sort,
            'list_slice': builtin_list_slice,
            'list_count': builtin_list_count,
            'list_clear': builtin_list_clear,
            'list_copy': builtin_list_copy,
            'list_fill': builtin_list_fill,
            'list_reserve': builtin_list_reserve,
        }

        self._current_coroutine = None
        self._event_waiters = {}
        self._io_waiters = {}

        # DZZW parallel runtime — spawned tasks run in real OS threads
        from dzzw import DzzwRuntime
        self.dzzw = DzzwRuntime(self)

    # ── DZZW builtin wrappers (thin adapters to self.dzzw) ─────
    def _dzzw_spawn(self, args):
        if len(args) < 1:
            raise HSharpError('dzzw_spawn(fn, args_list) needs at least fn')
        fn = args[0]
        call_args = args[1] if len(args) > 1 else []
        if not isinstance(call_args, list):
            call_args = [call_args]
        return self.dzzw.dzzw_spawn(fn, call_args)

    def _dzzw_await(self, args):
        if len(args) < 1:
            raise HSharpError('dzzw_await(handle) requires a handle')
        return self.dzzw.dzzw_await(args[0])

    def _dzzw_try_await(self, args):
        if len(args) < 1:
            return None
        return self.dzzw.dzzw_try_await(args[0])

    def _dzzw_await_any(self, args):
        if len(args) < 1:
            raise HSharpError('dzzw_await_any(handles_list) requires a list')
        handles = args[0]
        if not isinstance(handles, list):
            raise HSharpError('dzzw_await_any expects a list of handles')
        return self.dzzw.dzzw_await_any(handles)

    def _dzzw_await_all(self, args):
        if len(args) < 1:
            return
        handles = args[0]
        if not isinstance(handles, list):
            return
        self.dzzw.dzzw_await_all(handles)
        return None

    def _dzzw_parallel_map(self, args):
        if len(args) < 2:
            raise HSharpError('dzzw_parallel_map(fn, items) requires 2 arguments')
        return self.dzzw.dzzw_parallel_map(args[0], args[1])

    def _dzzw_worker_count(self, args):
        return self.dzzw.dzzw_worker_count()

    def _dzzw_pending_count(self, args):
        return self.dzzw.dzzw_pending_count()

    def _dzzw_total_submitted(self, args):
        return self.dzzw.dzzw_total_submitted()

    def _dzzw_total_completed(self, args):
        return self.dzzw.dzzw_total_completed()

    def _dzzw_dump_stats(self, args):
        self.dzzw.dzzw_dump_stats()
        return None

    def _dzzw_channel_create(self, args):
        cap = args[0] if len(args) >= 1 else 0
        return self.dzzw.dzzw_channel_create(cap)

    def _dzzw_channel_send(self, args):
        if len(args) < 2:
            raise HSharpError('dzzw_channel_send(handle, value) requires 2 args')
        self.dzzw.dzzw_channel_send(args[0], args[1])
        return None

    def _dzzw_channel_recv(self, args):
        if len(args) < 1:
            raise HSharpError('dzzw_channel_recv(handle) requires 1 arg')
        return self.dzzw.dzzw_channel_recv(args[0])

    def _dzzw_channel_try_send(self, args):
        if len(args) < 2:
            return False
        return self.dzzw.dzzw_channel_try_send(args[0], args[1])

    def _dzzw_channel_try_recv(self, args):
        if len(args) < 1:
            return None
        return self.dzzw.dzzw_channel_try_recv(args[0])

    def _dzzw_channel_close(self, args):
        if len(args) < 1:
            return None
        self.dzzw.dzzw_channel_close(args[0])
        return None

    def _dzzw_channel_free(self, args):
        if len(args) < 1:
            return None
        self.dzzw.dzzw_channel_free(args[0])
        return None

    def _dzzw_channel_size(self, args):
        if len(args) < 1:
            return 0
        return self.dzzw.dzzw_channel_size(args[0])

    def _dzzw_mutex_create(self, args):
        return self.dzzw.dzzw_mutex_create()

    def _dzzw_mutex_lock(self, args):
        if len(args) < 1:
            raise HSharpError('dzzw_mutex_lock(handle) requires 1 arg')
        self.dzzw.dzzw_mutex_lock(args[0])
        return None

    def _dzzw_mutex_unlock(self, args):
        if len(args) < 1:
            raise HSharpError('dzzw_mutex_unlock(handle) requires 1 arg')
        self.dzzw.dzzw_mutex_unlock(args[0])
        return None

    def _dzzw_mutex_try_lock(self, args):
        if len(args) < 1:
            return False
        return self.dzzw.dzzw_mutex_try_lock(args[0])

    def _dzzw_mutex_free(self, args):
        if len(args) < 1:
            return None
        self.dzzw.dzzw_mutex_free(args[0])
        return None

    def _dict_to_ast(self, node):
        """Convert a serialized AST (from H# parser) into Python h_ast objects.
        Expected node format (examples):
        {"type": "Program", "statements": [...]}
        {"type": "LetStatement", "name": "x", "value": {...}}
        Expressions similarly: {"type":"Identifier","name":"x"},
        {"type":"NumberLiteral","value": 1}
        This is a conservative converter for common node types used in bootstrap.
        """
        if node is None:
            return None
        # Accept two serialized forms from the H# parser: dict-based or list-based positional.
        if isinstance(node, list):
            t = node[0]
            if t == 'Program':
                stmts = [self._dict_to_ast(s) for s in node[1]]
                return Program(stmts)
            if t == 'LetStatement':
                name = node[1]
                val = self._dict_to_ast(node[2])
                return LetStatement(name, val)
            if t == 'PrintStatement':
                expr = self._dict_to_ast(node[1])
                return PrintStatement(expr)
            if t == 'ReturnStatement':
                expr = self._dict_to_ast(node[1])
                return ReturnStatement(expr)
            if t == 'Function':
                name = node[1]
                params = node[2] or []
                body = self._dict_to_ast(node[3])
                return Function(name, params, body)
            if t == 'BlockStatement':
                stm = [self._dict_to_ast(s) for s in node[1]]
                return BlockStatement(stm)
            if t == 'WhileStatement':
                cond = self._dict_to_ast(node[1])
                body = self._dict_to_ast(node[2])
                return WhileStatement(cond, body)
            if t == 'IfStatement':
                cond = self._dict_to_ast(node[1])
                cons = self._dict_to_ast(node[2])
                alt = self._dict_to_ast(node[3]) if node[3] else None
                return IfStatement(cond, cons, alt)
            # expressions
            if t == 'Identifier':
                return Identifier(node[1])
            if t == 'NumberLiteral':
                return NumberLiteral(node[1])
            if t == 'StringLiteral':
                return StringLiteral(node[1])
            if t == 'BooleanLiteral':
                return BooleanLiteral(node[1])
            if t == 'NullLiteral':
                return NullLiteral()
            if t == 'CallExpression':
                func = self._dict_to_ast(node[1])
                args = [self._dict_to_ast(a) for a in node[2]]
                return CallExpression(func, args)
            if t == 'BinaryOp':
                left = self._dict_to_ast(node[1])
                op = node[2]
                right = self._dict_to_ast(node[3])
                # map op name to TokenType if possible
                if isinstance(op, str):
                    try:
                        op_token = getattr(TokenType, op)
                    except Exception:
                        symmap = {'+':'PLUS','-':'MINUS','*':'STAR','/':'SLASH','==':'EQEQ','!=':'BANGEQ','>':'GT','<':'LT','>=':'GTE','<=':'LTE','&':'BITAND','|':'BITOR','^':'BITXOR','<<':'LSHIFT','>>':'RSHIFT'}
                        opname = symmap.get(op, None)
                        op_token = getattr(TokenType, opname) if opname else op
                else:
                    op_token = op
                return BinaryOp(left, op_token, right)
            if t == 'UnaryOp':
                op = node[1]
                operand = self._dict_to_ast(node[2])
                try:
                    op_token = getattr(TokenType, op)
                except Exception:
                    op_token = op
                return UnaryOp(op_token, operand)
            # array / dict / index / member
            if t == 'ArrayLiteral':
                elems = [self._dict_to_ast(e) for e in node[1]]
                return ArrayLiteral(elems)
            if t == 'DictLiteral':
                pairs = []
                for k, v in node[1]:
                    pairs.append((self._dict_to_ast(k), self._dict_to_ast(v)))
                return DictLiteral(pairs)
            if t == 'IndexExpression':
                left = self._dict_to_ast(node[1])
                index = self._dict_to_ast(node[2])
                return IndexExpression(left, index)
            if t == 'MemberExpression':
                left = self._dict_to_ast(node[1])
                name = node[2]
                return MemberExpression(left, name)
            # assignments
            if t == 'AssignmentIndex':
                arr = self._dict_to_ast(node[1])
                index = self._dict_to_ast(node[2])
                val = self._dict_to_ast(node[3])
                return AssignmentIndex(arr, index, val)
            if t == 'AssignmentMember':
                left = self._dict_to_ast(node[1])
                name = node[2]
                val = self._dict_to_ast(node[3])
                return AssignmentMember(left, name, val)
            if t == 'AssignmentIdentifier':
                name = node[1]
                val = self._dict_to_ast(node[2])
                return AssignmentIdentifier(name, val)
            # for / lambda / new / super / instanceof / cast
            if t == 'ForStatement':
                var1 = node[1]
                var2 = node[2]
                iterable = self._dict_to_ast(node[3])
                body = self._dict_to_ast(node[4])
                return ForStatement(var1, var2, iterable, body)
            if t == 'Lambda':
                params = node[1] or []
                body = self._dict_to_ast(node[2])
                return Lambda(params, body)
            if t == 'NewExpression':
                cname = node[1]
                args = [self._dict_to_ast(a) for a in node[2]]
                return NewExpression(cname, args)
            if t == 'SuperExpression':
                mname = node[1]
                args = [self._dict_to_ast(a) for a in node[2]]
                return SuperExpression(mname, args)
            if t == 'InstanceOfExpression':
                expr = self._dict_to_ast(node[1])
                type_name = node[2]
                return InstanceOfExpression(expr, type_name)
            if t == 'CastExpression':
                expr = self._dict_to_ast(node[1])
                type_name = node[2]
                return CastExpression(expr, type_name)
            # declarations / module / concept / asm / pointer
            if t == 'ModuleDeclaration':
                name = node[1]
                body = self._dict_to_ast(node[2])
                return ModuleDeclaration(name, body)
            if t == 'ConceptDeclaration':
                name = node[1]
                body = self._dict_to_ast(node[2]) if node[2] else None
                return ConceptDeclaration(name, body)
            if t == 'AsmBlock':
                return AsmBlock(node[1])
            if t == 'PointerDereference':
                target = self._dict_to_ast(node[1])
                return PointerDereference(target)
            if t == 'ContinueStatement':
                return ContinueStatement()
            if t == 'BreakStatement':
                return BreakStatement()
            if t == 'CoroFunction':
                return CoroFunction(node[1], node[2] or [], self._dict_to_ast(node[3]))
            if t == 'D3SizePowerDeclaration':
                name = node[1]
                props = [self._dict_to_ast(p) for p in node[2]]
                body = self._dict_to_ast(node[3])
                return D3SizePowerDeclaration(name, props, body)
            if t == 'D3Em3dDeclaration':
                name = node[1]
                parent = node[2]
                props = [self._dict_to_ast(p) for p in node[3]]
                body = self._dict_to_ast(node[4])
                return D3Em3dDeclaration(name, parent, props, body)
            if t == 'D3Property':
                name = node[1]
                params = node[2]
                is_pub = node[3] if len(node) > 3 else False
                return D3Property(name, params, is_pub)
            if t == 'D3RegionDeclaration':
                name = node[1]
                coords = node[2]
                body = self._dict_to_ast(node[3])
                impls = node[4] if len(node) > 4 else []
                return D3RegionDeclaration(name, coords, body, impls)
            if t == 'D3RegionInterfaceDeclaration':
                name = node[1]
                methods = [self._dict_to_ast(m) for m in node[2]]
                bases = node[3] if len(node) > 3 else []
                return D3RegionInterfaceDeclaration(name, methods, bases)
            if t == 'D3CoordinateExpr':
                return D3CoordinateExpr(node[1])
        if not isinstance(node, dict):
            raise HSharpError("Invalid AST node from H# parser")
        t = node.get('type')
        if t == 'Program':
            stmts = [self._dict_to_ast(s) for s in node.get('statements', [])]
            return Program(stmts)
        if t == 'LetStatement':
            name = node.get('name')
            val = self._dict_to_ast(node.get('value'))
            return LetStatement(name, val)
        if t == 'PrintStatement':
            expr = self._dict_to_ast(node.get('expr'))
            return PrintStatement(expr)
        if t == 'ReturnStatement':
            expr = self._dict_to_ast(node.get('expr'))
            return ReturnStatement(expr)
        if t == 'Function':
            name = node.get('name')
            params = node.get('params', []) or []
            body = self._dict_to_ast(node.get('body'))
            return Function(name, params, body)
        if t == 'BlockStatement':
            stm = [self._dict_to_ast(s) for s in node.get('statements', [])]
            return BlockStatement(stm)
        if t == 'WhileStatement':
            cond = self._dict_to_ast(node.get('condition'))
            body = self._dict_to_ast(node.get('body'))
            return WhileStatement(cond, body)
        if t == 'IfStatement':
            cond = self._dict_to_ast(node.get('condition'))
            cons = self._dict_to_ast(node.get('consequence'))
            alt = self._dict_to_ast(node.get('alternative')) if node.get('alternative') else None
            return IfStatement(cond, cons, alt)
        if t == 'ForStatement':
            var1 = node.get('var1')
            var2 = node.get('var2')
            iterable = self._dict_to_ast(node.get('iterable'))
            body = self._dict_to_ast(node.get('body'))
            return ForStatement(var1, var2, iterable, body)
        # Expressions
        if t == 'Identifier':
            return Identifier(node.get('name'))
        if t == 'NumberLiteral':
            return NumberLiteral(node.get('value'))
        if t == 'StringLiteral':
            return StringLiteral(node.get('value'))
        if t == 'BooleanLiteral':
            return BooleanLiteral(node.get('value'))
        if t == 'NullLiteral':
            return NullLiteral()
        if t == 'ArrayLiteral':
            elems = [self._dict_to_ast(e) for e in node.get('elements', [])]
            return ArrayLiteral(elems)
        if t == 'DictLiteral':
            pairs = []
            for k, v in node.get('pairs', []):
                pairs.append((self._dict_to_ast(k), self._dict_to_ast(v)))
            return DictLiteral(pairs)
        if t == 'IndexExpression':
            left = self._dict_to_ast(node.get('left'))
            index = self._dict_to_ast(node.get('index'))
            return IndexExpression(left, index)
        if t == 'MemberExpression':
            left = self._dict_to_ast(node.get('left'))
            name = node.get('name')
            return MemberExpression(left, name)
        if t == 'CallExpression':
            func = self._dict_to_ast(node.get('func'))
            args = [self._dict_to_ast(a) for a in node.get('args', [])]
            return CallExpression(func, args)
        if t == 'BinaryOp':
            left = self._dict_to_ast(node.get('left'))
            right = self._dict_to_ast(node.get('right'))
            op = node.get('op')
            # map op name to TokenType if possible
            if isinstance(op, str):
                try:
                    op_token = getattr(TokenType, op)
                except Exception:
                    # map symbols
                    symmap = {'+':'PLUS','-':'MINUS','*':'STAR','/':'SLASH','==':'EQEQ','!=':'BANGEQ','>':'GT','<':'LT','>=':'GTE','<=':'LTE','&':'BITAND','|':'BITOR','^':'BITXOR','<<':'LSHIFT','>>':'RSHIFT'}
                    opname = symmap.get(op, None)
                    op_token = getattr(TokenType, opname) if opname else op
            else:
                op_token = op
            return BinaryOp(left, op_token, right)
        if t == 'UnaryOp':
            op = node.get('op')
            operand = self._dict_to_ast(node.get('operand'))
            # map op string to TokenType
            try:
                op_token = getattr(TokenType, op)
            except Exception:
                op_token = op
            return UnaryOp(op_token, operand)
        # assignments
        if t == 'AssignmentIndex':
            arr = self._dict_to_ast(node.get('array'))
            index = self._dict_to_ast(node.get('index'))
            val = self._dict_to_ast(node.get('value'))
            return AssignmentIndex(arr, index, val)
        if t == 'AssignmentMember':
            left = self._dict_to_ast(node.get('left'))
            name = node.get('name')
            val = self._dict_to_ast(node.get('value'))
            return AssignmentMember(left, name, val)
        if t == 'AssignmentIdentifier':
            name = node.get('name')
            val = self._dict_to_ast(node.get('value'))
            return AssignmentIdentifier(name, val)
        if t == 'CoroFunction':
            name = node.get('name')
            params = node.get('params', []) or []
            body = self._dict_to_ast(node.get('body'))
            return CoroFunction(name, params, body)
        if t == 'D3SizePowerDeclaration':
            name = node.get('name')
            props = [self._dict_to_ast(p) for p in node.get('properties', [])]
            body = self._dict_to_ast(node.get('body'))
            return D3SizePowerDeclaration(name, props, body)
        if t == 'D3Em3dDeclaration':
            name = node.get('name')
            parent = node.get('parent_d3')
            props = [self._dict_to_ast(p) for p in node.get('properties', [])]
            body = self._dict_to_ast(node.get('body'))
            return D3Em3dDeclaration(name, parent, props, body)
        if t == 'D3Property':
            name = node.get('name')
            params = node.get('params', [])
            is_pub = node.get('is_public', False)
            return D3Property(name, params, is_pub)
        if t == 'D3RegionDeclaration':
            name = node.get('name')
            coords = node.get('coords', [])
            body = self._dict_to_ast(node.get('body'))
            impls = node.get('implements', [])
            return D3RegionDeclaration(name, coords, body, impls)
        if t == 'D3RegionInterfaceDeclaration':
            name = node.get('name')
            methods = [self._dict_to_ast(m) for m in node.get('methods', [])]
            bases = node.get('bases', [])
            return D3RegionInterfaceDeclaration(name, methods, bases)
        if t == 'D3CoordinateExpr':
            return D3CoordinateExpr(node.get('params', {}))
        # fallback
        raise HSharpError(f"Unsupported AST node type from H# parser: {t}")

    def interpret(self, program, env=None):
        env = env or self.global_env
        try:
            for stmt in program.statements:
                result = self.execute(stmt, env)
                if isinstance(result, ReturnException):
                    return result.value
        except HSharpError as e:
            print(f"Runtime Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def execute(self, stmt, env):
        method_name = f'visit_{type(stmt).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(stmt, env)

    def generic_visit(self, node, env):
        raise Exception(f'No visit_{type(node).__name__} method')

    def visit_LetStatement(self, stmt, env):
        value = self.eval_expr(stmt.value, env)
        env.define(stmt.name, value)

    def visit_PrintStatement(self, stmt, env):
        value = self.eval_expr(stmt.expr, env)
        print(value)

    def visit_ImportStatement(self, stmt, env):
        # stmt.path may be a string ("file.hto") or an Identifier (module name)
        path = stmt.path
        # import a local H# file when given a string literal
        if isinstance(path, str):
            if not path.endswith('.hto'):
                path += '.hto'
            if not os.path.exists(path):
                raise HSharpError(f"Module not found: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            # If an H# tokenizer `tokenize` is available in this interpreter (self.functions),
            # prefer to use it to produce tokens. If an H# `parse` is also available,
            # call it and convert the returned dict-structured AST into Python AST objects.
            program = None
            try:
                if 'tokenize' in self.functions:
                    call_tok = CallExpression(Identifier('tokenize'), [StringLiteral(code)])
                    tokens_list = self.visit_CallExpression(call_tok, env)
                    # if an H# parser is available, call it with tokens_list
                    if 'parse' in self.functions:
                        call_parse = CallExpression(Identifier('parse'), [Identifier('TOK_PLACEHOLDER')])
                        # direct call into H# parse: bypassing evaluation, so use visit_CallExpression but
                        # we need parse to accept raw Python list; our visit_CallExpression expects expressions,
                        # so instead call parse by invoking the callable directly if present in self.functions
                        parse_fn = self.functions.get('parse')
                        try:
                            ast_dict = None
                            # If parse_fn is a Python-callable (unlikely), call directly
                            if callable(parse_fn):
                                ast_dict = parse_fn(tokens_list)
                            else:
                                # otherwise, call via interpreter by creating a temporary callable wrapper
                                ast_dict = self.visit_CallExpression(CallExpression(Identifier('parse'), []), env)
                        except Exception:
                            ast_dict = None
                        if ast_dict is not None:
                            # convert serialized AST (dict) to h_ast objects
                            program = self._dict_to_ast(ast_dict)
                            if program is None:
                                # fallback to building parser stream
                                stream = HSharpTokenStream(tokens_list)
                                from parser import Parser
                                parser = Parser(stream)
                                program = parser.parse()
                            # else we have a Program
                    else:
                        # no H# parser: feed tokens into Python Parser via wrapper stream
                        stream = HSharpTokenStream(tokens_list)
                        from parser import Parser
                        parser = Parser(stream)
                        program = parser.parse()
            except Exception:
                program = None
            if program is None:
                from lexer import Lexer
                from parser import Parser
                lexer = Lexer(code)
                parser = Parser(lexer)
                program = parser.parse()
            # run in the current env (imported names populate current env)
            sub_interpreter = Interpreter(global_env=env, functions=self.functions)
            sub_interpreter.interpret(program, env)
            # ensure any functions registered by the imported module are available
            try:
                self.functions.update(sub_interpreter.functions)
            except Exception:
                pass
            # merge interfaces from imported module
            if hasattr(sub_interpreter, 'interfaces'):
                self.interfaces.update(sub_interpreter.interfaces)
        else:
            # assume Identifier: try to import a Python module of that name
            if isinstance(path, Identifier):
                modname = path.name
            else:
                raise HSharpError('Unsupported import path')
            try:
                import importlib
                mod = importlib.import_module(modname)
            except Exception as e:
                raise HSharpError(f"Failed to import Python module '{modname}': {e}")
            # wrap module into a simple H#-friendly dict exposing attributes
            proxy = {}
            for attr in dir(mod):
                if attr.startswith('_'):
                    continue
                try:
                    val = getattr(mod, attr)
                except Exception:
                    continue
                # allow functions and simple objects; leave as-is
                proxy[attr] = val
            env.define(modname, proxy)

    def _builtin_thread_spawn(self, args):
        if len(args) != 1:
            raise HSharpError('thread_spawn(func) takes exactly 1 argument')
        fn = args[0]
        import threading

        def target_callable():
            try:
                if isinstance(fn, dict) and 'body' in fn:
                    # interpreter-style function/closure
                    call_env = Environment(parent=self.global_env)
                    for pname in fn.get('params', []):
                        # no args supported for now
                        call_env.define(pname, None)
                    self.visit_BlockStatement(fn['body'], call_env)
                elif isinstance(fn, dict) and 'bytecode' in fn:
                    # compiled function-like object for interpreter: run via VM
                    vm = VM({'instructions': fn['bytecode'], 'consts': fn.get('consts', [])})
                    vm.run()
                elif callable(fn):
                    fn()
                else:
                    raise HSharpError('Unsupported callable passed to thread_spawn')
            except Exception as e:
                print(f"Thread error: {e}")

        t = threading.Thread(target=target_callable)
        t.start()
        return t

    def _builtin_thread_join(self, args):
        if len(args) != 1:
            raise HSharpError('thread_join(t) takes exactly 1 argument')
        t = args[0]
        try:
            t.join()
            return None
        except Exception as e:
            raise HSharpError(f'Error joining thread: {e}')

    # --- Coroutine support (cooperative generator-style) ---
    def _builtin_coro_yield(self, args):
        # coro_yield(): plain yield
        # coro_yield(event_name:str): wait for event
        # coro_yield(seconds: number): sleep for seconds
        coro = self._current_coroutine
        if coro is None:
            raise HSharpError('coro_yield must be called inside a coroutine')
        if len(args) == 0:
            raise CoroYield()
        if len(args) == 1:
            a = args[0]
            if isinstance(a, (int, float)):
                coro.waiting = ('sleep', time.time() + float(a))
                raise CoroYield()
            if isinstance(a, str):
                coro.waiting = ('event', a)
                self._event_waiters.setdefault(a, []).append(coro)
                raise CoroYield()
        raise HSharpError('coro_yield takes 0 or 1 argument')

    def _builtin_coro_resume(self, args):
        if len(args) != 1:
            raise HSharpError('coro_resume(coro) takes exactly 1 argument')
        coro = args[0]
        if not isinstance(coro, Coroutine):
            raise HSharpError('Argument to coro_resume must be a coroutine')
        # debug: indicate resume called
        # print(f"DEBUG: coro_resume called on {coro}")
        return coro.resume()

    def _builtin_coro_sleep(self, args):
        if len(args) != 1:
            raise HSharpError('coro_sleep(seconds) takes exactly 1 argument')
        coro = self._current_coroutine
        if coro is None:
            raise HSharpError('coro_sleep must be called inside a coroutine')
        seconds = args[0]
        if not isinstance(seconds, (int, float)):
            raise HSharpError('coro_sleep requires numeric seconds')
        coro.waiting = ('sleep', time.time() + float(seconds))
        raise CoroYield()

    def _builtin_coro_wait(self, args):
        if len(args) != 1:
            raise HSharpError('coro_wait(event) takes exactly 1 argument')
        coro = self._current_coroutine
        if coro is None:
            raise HSharpError('coro_wait must be called inside a coroutine')
        ev = args[0]
        if not isinstance(ev, str):
            raise HSharpError('coro_wait requires an event name string')
        coro.waiting = ('event', ev)
        self._event_waiters.setdefault(ev, []).append(coro)
        raise CoroYield()

    def _builtin_coro_signal(self, args):
        if len(args) != 1:
            raise HSharpError('coro_signal(event) takes exactly 1 argument')
        ev = args[0]
        if not isinstance(ev, str):
            raise HSharpError('coro_signal requires an event name string')
        waiters = self._event_waiters.pop(ev, [])
        for c in waiters:
            if c.waiting and c.waiting[0] == 'event' and c.waiting[1] == ev:
                c.waiting = None
        return None

    def _builtin_coro_signal_io(self, args):
        # signal that an io handle is ready: coro_signal_io(handle)
        if len(args) != 1:
            raise HSharpError('coro_signal_io(handle) takes exactly 1 argument')
        handle = args[0]
        waiters = self._io_waiters.pop(handle, [])
        for c in waiters:
            if c.waiting and c.waiting[0] == 'io' and c.waiting[1] == handle:
                c.waiting = None
        return None

    def _builtin_scheduler_run(self, args):
        # scheduler_run(tasks) - tasks is a list of Coroutine or (Coroutine, priority)
        if len(args) != 1:
            raise HSharpError('scheduler_run(list) takes exactly 1 argument')
        lst = args[0]
        if not isinstance(lst, list):
            raise HSharpError('Argument to scheduler_run must be a list')
        # normalize to dicts with coro and priority
        tasks = []
        for item in lst:
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], Coroutine) and isinstance(item[1], (int, float)):
                c = item[0]
                c.priority = int(item[1])
                tasks.append(c)
            elif isinstance(item, Coroutine):
                tasks.append(item)
            else:
                # ignore non-coroutine entries
                continue

        # round-robin with priority: higher priority scheduled earlier each cycle
        while True:
            # filter out finished
            tasks = [c for c in tasks if not c.done]
            if not tasks:
                break
            # sort by priority desc
            tasks.sort(key=lambda c: getattr(c, 'priority', 0), reverse=True)
            progressed = False
            for c in list(tasks):
                # skip if waiting on event/sleep
                if c.waiting:
                    w = c.waiting
                    if w[0] == 'sleep':
                        if time.time() >= w[1]:
                            c.waiting = None
                        else:
                            continue
                    elif w[0] == 'event':
                        # still waiting until someone signals
                        continue
                    elif w[0] == 'io':
                        handle = w[1]
                        # determine readiness: handle can be callable or object with ready()
                        ready = False
                        try:
                            if callable(handle):
                                ready = bool(handle())
                            elif hasattr(handle, 'ready') and callable(getattr(handle, 'ready')):
                                ready = bool(handle.ready())
                            elif hasattr(handle, 'fileno'):
                                # try select on file/socket-like objects
                                try:
                                    import select
                                    r, w, x = select.select([handle], [], [], 0)
                                    ready = bool(r)
                                except Exception:
                                    try:
                                        fd = handle.fileno()
                                        import select
                                        r, w, x = select.select([fd], [], [], 0)
                                        ready = bool(r)
                                    except Exception:
                                        ready = False
                            else:
                                # not a callable/ready-able object; rely on external signal via coro_signal_io
                                ready = False
                        except Exception:
                            ready = False
                        # check timeout
                        until = w[2]
                        if not ready and until is not None and time.time() >= until:
                            # timeout reached; remove from io waiters and optionally call a timeout callback by setting waiting=None
                            c.waiting = None
                            # remove from mapping
                            lst = self._io_waiters.get(handle, [])
                            if c in lst:
                                lst.remove(c)
                            continue
                        if not ready:
                            continue
                        # ready
                        c.waiting = None
                        lst = self._io_waiters.get(handle, [])
                        if c in lst:
                            lst.remove(c)
                res = c.resume()
                progressed = True
            if not progressed:
                # deadlock or all waiting: sleep a short while to wait for timeouts/events
                time.sleep(0.001)
                # re-evaluate waiters; if still nothing progresses after sleep, break to avoid infinite loop
                still = any(not c.done and (c.waiting is None or (c.waiting[0] == 'sleep' and time.time() >= c.waiting[1])) for c in tasks)
                if not still:
                    break
        return None

    def visit_WhileStatement(self, stmt, env):
        while True:
            cond = self.eval_expr(stmt.condition, env)
            if not isinstance(cond, bool):
                raise HSharpError("While condition must be boolean")
            if not cond:
                break
            try:
                result = self.execute_block(stmt.body, env)
            except ContinueException:
                continue
            except BreakException:
                break
            if isinstance(result, ReturnException):
                return result

    def visit_IfStatement(self, stmt, env):
        cond = self.eval_expr(stmt.condition, env)
        if not isinstance(cond, bool):
            raise HSharpError("If condition must be boolean")
        if cond:
            return self.execute_block(stmt.consequence, env)
        elif stmt.alternative:
            if isinstance(stmt.alternative, IfStatement):
                return self.visit_IfStatement(stmt.alternative, env)
            return self.execute_block(stmt.alternative, env)

    def visit_AssignmentIdentifier(self, stmt, env):
        value = self.eval_expr(stmt.value, env)
        env.assign(stmt.name, value)
        return None

    def visit_ContinueStatement(self, stmt, env):
        raise ContinueException()

    def visit_BreakStatement(self, stmt, env):
        raise BreakException()

    def visit_ForStatement(self, stmt, env):
        iterable = self.eval_expr(stmt.iterable, env)
        loop_env = Environment(parent=env)
        if isinstance(iterable, list):
            for item in iterable:
                loop_env.define(stmt.var1, item)
                try:
                    result = self.execute_block(stmt.body, loop_env)
                except ContinueException:
                    continue
                except BreakException:
                    break
                if isinstance(result, ReturnException):
                    return result
        elif isinstance(iterable, dict):
            for k, v in iterable.items():
                loop_env.define(stmt.var1, k)
                if stmt.var2:
                    loop_env.define(stmt.var2, v)
                result = self.execute_block(stmt.body, loop_env)
                if isinstance(result, ReturnException):
                    return result
        elif isinstance(iterable, str):
            for char in iterable:
                loop_env.define(stmt.var1, char)
                try:
                    result = self.execute_block(stmt.body, loop_env)
                except ContinueException:
                    continue
                except BreakException:
                    break
                if isinstance(result, ReturnException):
                    return result
        else:
            raise HSharpError("Can only iterate over array, dict, or string")

    def execute_block(self, block, env):
        block_env = Environment(parent=env)
        for s in block.statements:
            result = self.execute(s, block_env)
            if isinstance(result, ReturnException):
                return result

    def visit_BlockStatement(self, stmt, env):
        # For normal (non-coroutine) execution, execute entire block.
        # For coroutine-driven execution, block stepping is handled by `execute_stmt_for_coro`.
        if self._current_coroutine is None:
            return self.execute_block(stmt, env)
        # if in coroutine, signal caller to push frame
        return None

    def execute_stmt_for_coro(self, stmt, env, coro):
        # Execute a single top-level statement in coroutine mode.
        # Return True if statement completed, False if control transferred (pushed new frame).
        # Handle common statement types directly to maintain frame/pc.
        if isinstance(stmt, BlockStatement):
            # push block's statements as a new frame
            coro.stack.append({'stmts': list(stmt.statements), 'pc': 0, 'env': Environment(parent=env)})
            return False
        if isinstance(stmt, LetStatement):
            self.visit_LetStatement(stmt, env)
            return True
        if isinstance(stmt, DeleteStatement):
            self.visit_DeleteStatement(stmt, env)
            return True
        if isinstance(stmt, PrintStatement):
            self.visit_PrintStatement(stmt, env)
            return True
        if isinstance(stmt, ImportStatement):
            self.visit_ImportStatement(stmt, env)
            return True
        if isinstance(stmt, ReturnStatement):
            # execute return expression and raise to unwind
            val = self.eval_expr(stmt.expr, env)
            raise ReturnException(val)
        if isinstance(stmt, Function):
            self.visit_Function(stmt, env)
            return True
        if isinstance(stmt, ClassDeclaration):
            self.visit_ClassDeclaration(stmt, env)
            return True
        if isinstance(stmt, InterfaceDeclaration):
            self.visit_InterfaceDeclaration(stmt, env)
            return True
        if isinstance(stmt, UnionDeclaration):
            self.visit_UnionDeclaration(stmt, env)
            return True
        if isinstance(stmt, D3SizePowerDeclaration):
            self.visit_D3SizePowerDeclaration(stmt, env)
            return True
        if isinstance(stmt, D3Em3dDeclaration):
            self.visit_D3Em3dDeclaration(stmt, env)
            return True
        if isinstance(stmt, D3RegionDeclaration):
            return True
        if isinstance(stmt, D3RegionInterfaceDeclaration):
            return True
        if isinstance(stmt, IfStatement):
            cond = self.eval_expr(stmt.condition, env)
            if not isinstance(cond, bool):
                raise HSharpError("If condition must be boolean")
            if cond:
                coro.stack.append({'stmts': list(stmt.consequence.statements), 'pc': 0, 'env': Environment(parent=env)})
            elif stmt.alternative:
                if isinstance(stmt.alternative, IfStatement):
                    coro.stack.append({'stmts': [stmt.alternative], 'pc': 0, 'env': Environment(parent=env)})
                else:
                    coro.stack.append({'stmts': list(stmt.alternative.statements), 'pc': 0, 'env': Environment(parent=env)})
            return False
        if isinstance(stmt, WhileStatement):
            cond = self.eval_expr(stmt.condition, env)
            if not isinstance(cond, bool):
                raise HSharpError("While condition must be boolean")
            if cond:
                # push a frame that will re-evaluate the condition after body finishes
                coro.stack.append({'stmts': list(stmt.body.statements), 'pc': 0, 'env': Environment(parent=env)})
                # push a sentinel frame to re-check the while (we'll re-push the while stmt)
                coro.stack.append({'stmts': [stmt], 'pc': 0, 'env': env})
            return False
        if isinstance(stmt, ForStatement):
            iterable = self.eval_expr(stmt.iterable, env)
            if isinstance(iterable, list):
                # create a sequence of let assignments + body frames
                combined = []
                for item in iterable:
                    # let var1 = item; then body
                    combined.append(LetStatement(stmt.var1, NumberLiteral(item) if isinstance(item, int) else Identifier(item) if isinstance(item, str) else NumberLiteral(0)))
                    combined.extend(stmt.body.statements)
                coro.stack.append({'stmts': combined, 'pc': 0, 'env': Environment(parent=env)})
                return False
            else:
                raise HSharpError("Can only iterate over array, dict, or string in coroutine for-statement simplified support")
        # Expression statements (call, assignment, member assignment, index assignment)
        # Evaluate expression for side-effects using generator-based evaluator
        if isinstance(stmt, (CallExpression, BinaryOp, UnaryOp, MemberExpression, IndexExpression, AssignmentIndex, AssignmentMember)):
            gen = self.gen_eval_expr(stmt, env)
            coro.stack.append({'gen': gen, 'env': env})
            return False
        # fall back to normal evaluation for other kinds
        try:
            self.eval_expr(stmt, env)
        except CoroYield:
            raise
        return True

    def gen_eval_expr(self, expr, env):
        # Generator-based evaluator for expressions. Yields ('suspend', info) when coroutine should suspend.
        # Always defined as generator.
        if False:
            yield None
        # Literals
        if isinstance(expr, NumberLiteral):
            return expr.value
        if isinstance(expr, StringLiteral):
            return expr.value
        if isinstance(expr, BooleanLiteral):
            return expr.value
        if isinstance(expr, NullLiteral):
            return None
        if isinstance(expr, Identifier):
            try:
                return env.lookup(expr.name)
            except HSharpError:
                if expr.name in self.functions:
                    return self.functions[expr.name]
                raise
        # Array
        if isinstance(expr, ArrayLiteral):
            res = []
            for e in expr.elements:
                v = yield from self.gen_eval_expr(e, env)
                res.append(v)
            return res
        # Dict
        if isinstance(expr, DictLiteral):
            d = {}
            for kexpr, vexpr in expr.pairs:
                k = yield from self.gen_eval_expr(kexpr, env)
                val = yield from self.gen_eval_expr(vexpr, env)
                d[k] = val
            return d
        # Index
        if isinstance(expr, IndexExpression):
            left = yield from self.gen_eval_expr(expr.left, env)
            index = yield from self.gen_eval_expr(expr.index, env)
            if isinstance(left, list):
                if not isinstance(index, int):
                    raise HSharpError("Array index must be integer")
                if index < 0:
                    index = len(left) + index
                if index < 0 or index >= len(left):
                    raise HSharpError("Array index out of bounds")
                return left[index]
            elif isinstance(left, str):
                if not isinstance(index, int):
                    raise HSharpError("String index must be integer")
                if index < 0:
                    index = len(left) + index
                if index < 0 or index >= len(left):
                    raise HSharpError("String index out of bounds")
                return left[index]
            elif isinstance(left, dict):
                if index not in left:
                    return None  # Return nullptr for missing keys
                return left[index]
            else:
                raise HSharpError("Can only index arrays, strings, or dictionaries")
        # Member
        if isinstance(expr, MemberExpression):
            left = yield from self.gen_eval_expr(expr.left, env)
            if isinstance(left, dict) and '__class__' in left:
                if expr.name in left:
                    return left[expr.name]
                class_obj = left['__class__']
                fields = class_obj.get('fields', {})
                if expr.name in fields:
                    return fields[expr.name]
                raise HSharpError(f"Attribute '{expr.name}' not found on instance")
            if isinstance(left, dict):
                if expr.name in left:
                    return left[expr.name]
            raise HSharpError(f"Cannot access attribute '{expr.name}' on non-object")
        # Lambda
        if isinstance(expr, Lambda):
            return {'params': expr.params, 'body': expr.body, 'closure_env': env}
        # New expression
        if isinstance(expr, NewExpression):
            cname = expr.class_name.name if isinstance(expr.class_name, Identifier) else None
            args = []
            for a in expr.args:
                args.append((yield from self.gen_eval_expr(a, env)))
            if cname in self.functions:
                cls = self.functions[cname]
                # naive instantiation
                inst = {'__class__': cls}
                # initialize fields
                for k, v in cls.get('fields', {}).items():
                    inst[k] = v
                return inst
            raise HSharpError(f"Class '{cname}' not found")
        # Union construction
        if isinstance(expr, UnionConstructExpression):
            type_name = expr.type_name.name if isinstance(expr.type_name, Identifier) else None
            variant_name = expr.variant_name
            values = []
            for v in expr.values:
                values.append((yield from self.gen_eval_expr(v, env)))
            if type_name in self.functions:
                union_type = self.functions[type_name]
                if not isinstance(union_type, dict) or union_type.get('__type__') != 'union':
                    raise HSharpError(f"'{type_name}' is not a union type")
                variant = None
                for vv in union_type.get('variants', []):
                    if vv['name'] == variant_name:
                        variant = vv
                        break
                if variant is None:
                    raise HSharpError(f"Unknown variant '{variant_name}' for union '{type_name}'")
                if len(values) != len(variant['fields']):
                    raise HSharpError(f"Variant '{variant_name}' expects {len(variant['fields'])} fields, got {len(values)}")
                inst = {}
                inst['__union__'] = type_name
                inst['__variant__'] = variant_name
                for i, fname in enumerate(variant['fields']):
                    inst[fname] = values[i]
                return inst
            raise HSharpError(f"Union type '{type_name}' not found")
        # Call expression
        if isinstance(expr, CallExpression):
            func_node = expr.func
            # evaluate callee
            if isinstance(func_node, Identifier):
                name = func_node.name
                # handle coroutine builtins specially
                if name in ('coro_yield', 'coro_sleep', 'coro_wait'):
                    # evaluate arg if present
                    if expr.args:
                        av = yield from self.gen_eval_expr(expr.args[0], env)
                    else:
                        av = None
                    coro = self._current_coroutine
                    if coro is None:
                        raise HSharpError(f"{name} must be called inside a coroutine")
                    if name == 'coro_yield':
                        if av is None:
                            # plain yield
                            yield ('suspend', None)
                            return None
                        if isinstance(av, (int, float)):
                            coro.waiting = ('sleep', time.time() + float(av))
                            yield ('suspend', ('sleep', coro.waiting[1]))
                            return None
                        if isinstance(av, str):
                            coro.waiting = ('event', av)
                            self._event_waiters.setdefault(av, []).append(coro)
                            yield ('suspend', ('event', av))
                            return None
                    if name == 'coro_sleep':
                        seconds = av
                        if not isinstance(seconds, (int, float)):
                            raise HSharpError('coro_sleep requires numeric seconds')
                        coro.waiting = ('sleep', time.time() + float(seconds))
                        yield ('suspend', ('sleep', coro.waiting[1]))
                        return None
                    if name == 'coro_wait':
                        ev = av
                        if not isinstance(ev, str):
                            raise HSharpError('coro_wait requires event name string')
                        coro.waiting = ('event', ev)
                        self._event_waiters.setdefault(ev, []).append(coro)
                        yield ('suspend', ('event', ev))
                        return None
                    if name == 'coro_wait_io':
                        # coro_wait_io(handle, timeout_seconds=None)
                        handle = av
                        timeout = None
                        if len(expr.args) > 1:
                            timeout = yield from self.gen_eval_expr(expr.args[1], env)
                        if handle is None:
                            raise HSharpError('coro_wait_io requires a handle')
                        until = None
                        if timeout is not None:
                            if not isinstance(timeout, (int, float)):
                                raise HSharpError('timeout must be numeric')
                            until = time.time() + float(timeout)
                        coro.waiting = ('io', handle, until)
                        self._io_waiters.setdefault(handle, []).append(coro)
                        yield ('suspend', ('io', handle, until))
                        return None
                if name == 'coro_signal':
                    ev = None
                    if expr.args:
                        ev = yield from self.gen_eval_expr(expr.args[0], env)
                    if not isinstance(ev, str):
                        raise HSharpError('coro_signal requires event name string')
                    waiters = self._event_waiters.pop(ev, [])
                    for c in waiters:
                        if c.waiting and c.waiting[0] == 'event' and c.waiting[1] == ev:
                            c.waiting = None
                    return None
                # normal function lookup
                # first check builtins
                if name in self.builtins:
                    # evaluate args
                    args = []
                    for a in expr.args:
                        args.append((yield from self.gen_eval_expr(a, env)))
                    # call builtin synchronously
                    return self.builtins[name](args)
                # lookup variable/function
                val = env.lookup(name)
                if callable(val):
                    args = []
                    for a in expr.args:
                        args.append((yield from self.gen_eval_expr(a, env)))
                    return val(*args)
                if isinstance(val, dict) and 'body' in val:
                    # interpreter closure
                    args = []
                    for a in expr.args:
                        args.append((yield from self.gen_eval_expr(a, env)))
                    call_env = Environment(parent=val.get('closure_env', self.global_env))
                    for pname, argval in zip(val.get('params', []), args):
                        call_env.define(pname, argval)
                    # push function body as new frame
                    gen = self.gen_eval_stmt_block(val['body'], call_env)
                    result = yield from gen
                    return result
                # otherwise it might be a named function in self.functions
                if name in self.functions:
                    func = self.functions[name]
                    # evaluate args first
                    args = []
                    for a in expr.args:
                        args.append((yield from self.gen_eval_expr(a, env)))
                    # coroutine function: return Coroutine object
                    if isinstance(func, Function) and getattr(func, 'is_coro', False):
                        coro = Coroutine(func, self, args)
                        return coro
                    if isinstance(func, Function):
                        # create new environment and execute function body as generator
                        call_env = Environment(parent=self.global_env)
                        for pname, argval in zip(func.params, args):
                            call_env.define(pname, argval)
                        gen = self.gen_eval_stmt_block(func.body, call_env)
                        result = yield from gen
                        return result
                    elif isinstance(func, dict) and 'methods' in func:
                        raise HSharpError(f"'{name}' is a class, cannot call directly")
            else:
                # callee is an expression
                callee = yield from self.gen_eval_expr(func_node, env)
                args = []
                for a in expr.args:
                    args.append((yield from self.gen_eval_expr(a, env)))
                if callable(callee):
                    return callee(*args)
                if isinstance(callee, dict) and 'body' in callee:
                    call_env = Environment(parent=callee.get('closure_env', self.global_env))
                    for pname, argval in zip(callee.get('params', []), args):
                        call_env.define(pname, argval)
                    gen = self.gen_eval_stmt_block(callee['body'], call_env)
                    result = yield from gen
                    return result
                raise HSharpError('Unsupported call expression')
        # BinaryOp
        if isinstance(expr, BinaryOp):
            op = expr.op
            if op == TokenType.AND:
                left = yield from self.gen_eval_expr(expr.left, env)
                if not left:
                    return left
                return (yield from self.gen_eval_expr(expr.right, env))
            if op == TokenType.OR:
                left = yield from self.gen_eval_expr(expr.left, env)
                if left:
                    return left
                return (yield from self.gen_eval_expr(expr.right, env))
            left = yield from self.gen_eval_expr(expr.left, env)
            right = yield from self.gen_eval_expr(expr.right, env)
            if op == TokenType.PLUS:
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                if isinstance(left, list) and isinstance(right, list):
                    return left + right
                self._ensure_number(left, right)
                return left + right
            elif op == TokenType.MINUS:
                self._ensure_number(left, right)
                return left - right
            elif op == TokenType.STAR:
                self._ensure_number(left, right)
                return left * right
            elif op == TokenType.SLASH:
                self._ensure_number(left, right)
                if right == 0:
                    raise HSharpError("Division by zero")
                if isinstance(left, float) or isinstance(right, float):
                    return left / right
                return left // right
            elif op == TokenType.EQEQ:
                return left == right
            elif op == TokenType.MOD:
                self._ensure_number(left, right)
                if right == 0:
                    raise HSharpError("Modulo by zero")
                return left % right
            elif op == TokenType.BANGEQ:
                return left != right
            elif op == TokenType.GT:
                self._ensure_comparable(left, right)
                return left > right
            elif op == TokenType.LT:
                self._ensure_comparable(left, right)
                return left < right
            elif op == TokenType.GTE:
                self._ensure_comparable(left, right)
                return left >= right
            elif op == TokenType.LTE:
                self._ensure_comparable(left, right)
                return left <= right
            elif op == TokenType.IN:
                if isinstance(right, list):
                    return left in right
                if isinstance(right, dict):
                    return left in right
                if isinstance(right, str):
                    if not isinstance(left, str):
                        raise HSharpError("'in' operator with string requires string left operand")
                    return left in right
                raise HSharpError("'in' operator requires list, dict, or string on right side")
            elif op == TokenType.BITAND:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Bitwise operations require integer operands')
                return left & right
            elif op == TokenType.BITOR:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Bitwise operations require integer operands')
                return left | right
            elif op == TokenType.BITXOR:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Bitwise operations require integer operands')
                return left ^ right
            elif op == TokenType.LSHIFT:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Shift operations require integer operands')
                return left << right
            elif op == TokenType.RSHIFT:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Shift operations require integer operands')
                return left >> right
            else:
                raise HSharpError(f"Unknown operator: {op}")
        # AssignmentIndex
        if isinstance(expr, AssignmentIndex):
            arr = yield from self.gen_eval_expr(expr.array, env)
            index = yield from self.gen_eval_expr(expr.index, env)
            value = yield from self.gen_eval_expr(expr.value, env)
            if isinstance(arr, list):
                if not isinstance(index, int):
                    raise HSharpError("Array index must be integer")
                if index < 0:
                    index = len(arr) + index
                if index < 0 or index >= len(arr):
                    raise HSharpError("Array index out of bounds")
                arr[index] = value
            elif isinstance(arr, dict):
                arr[index] = value
            else:
                raise HSharpError("Can only assign to array or dictionary elements")
            return value
        # AssignmentMember
        if isinstance(expr, AssignmentMember):
            obj = yield from self.gen_eval_expr(expr.left, env)
            if not isinstance(obj, dict) or '__class__' not in obj:
                raise HSharpError('Left side of member assignment is not an object')
            value = yield from self.gen_eval_expr(expr.value, env)
            obj[expr.name] = value
            return value
        # UnaryOp
        if isinstance(expr, UnaryOp):
            if expr.op == TokenType.NOT:
                val = yield from self.gen_eval_expr(expr.operand, env)
                if not isinstance(val, bool):
                    raise HSharpError("'not' operand must be boolean")
                return not val
            elif expr.op == TokenType.TILDE:
                val = yield from self.gen_eval_expr(expr.operand, env)
                if not isinstance(val, int):
                    raise HSharpError("'~' operand must be integer")
                return ~val
            else:
                raise HSharpError(f"Unknown unary operator: {expr.op}")
        raise HSharpError(f"Unknown expression: {expr}")

    def gen_eval_stmt_block(self, block, env):
        # generator that evaluates all statements in a block sequentially
        for s in block.statements:
            # for each statement, if it's an expression-type, yield from its generator
            if isinstance(s, (CallExpression, BinaryOp, UnaryOp, MemberExpression, IndexExpression, AssignmentIndex, AssignmentMember)):
                yield from self.gen_eval_expr(s, env)
            else:
                # reuse existing visit_ methods for side-effects
                self.execute(s, env)
        return None

    def visit_ReturnStatement(self, stmt, env):
        value = self.eval_expr(stmt.expr, env)
        raise ReturnException(value)

    def visit_Function(self, stmt, env):
        self.functions[stmt.name] = stmt

    def visit_CoroFunction(self, stmt, env):
        # register coroutine function; mark as coroutine for runtime
        try:
            setattr(stmt, 'is_coro', True)
        except Exception:
            pass
        self.functions[stmt.name] = stmt

    def visit_ModuleDeclaration(self, stmt, env):
        # execute module body in isolated env and expose as dict
        mod_env = Environment()
        # run statements in module body
        for s in stmt.body.statements:
            self.execute(s, mod_env)
        # export names
        proxy = {}
        for k, v in mod_env.vars.items():
            proxy[k] = v
        try:
            env.define(stmt.name, proxy)
        except Exception:
            self.global_env.define(stmt.name, proxy)

    def visit_ConceptDeclaration(self, stmt, env):
        # store concept as interface-like entry
        methods = {}
        if stmt.body:
            for s in stmt.body.statements:
                if isinstance(s, Function):
                    methods[s.name] = s
        iface = {'name': stmt.name, 'methods': methods, 'body': stmt.body}
        self.interfaces[stmt.name] = iface

    def visit_AsmBlock(self, stmt, env):
        # Inline asm placeholder - store raw code under a special name or ignore
        # For now we simply attach asm text to env as `_last_asm` and return None
        env.define('_last_asm', stmt.code)
        return None

    def visit_ClassDeclaration(self, stmt, env):
        # collect methods and fields, support inheritance and private fields
        methods = {}
        fields = {}
        private = []
        for s in stmt.body.statements:
            if isinstance(s, Function):
                if getattr(s, 'is_static', False):
                    methods.setdefault('__static__', {})[s.name] = s
                else:
                    methods[s.name] = s
            elif isinstance(s, FieldDeclaration):
                # evaluate default in global env (only simple literals expected)
                fields[s.name] = self.eval_expr(s.value, self.global_env)
                if s.is_private:
                    private.append(s.name)
        class_obj = {'name': stmt.name, 'methods': methods, 'fields': fields, 'private': private}
        # handle inheritance by merging base if present
        if getattr(stmt, 'base', None):
            base_name = stmt.base
            base = None
            try:
                base = self.functions.get(base_name) or self.global_env.lookup(base_name)
            except HSharpError:
                base = None
            if not base:
                raise HSharpError(f"Base class not found: {base_name}")
            # merge base methods/fields/private
            merged_methods = {}
            merged_fields = {}
            merged_private = []
            if isinstance(base, dict):
                merged_methods.update(base.get('methods', {}))
                merged_fields.update(base.get('fields', {}))
                merged_private.extend(base.get('private', []))
            merged_methods.update(methods)
            merged_fields.update(fields)
            merged_private.extend(private)
            class_obj['methods'] = merged_methods
            class_obj['fields'] = merged_fields
            class_obj['private'] = merged_private

        # expose static methods at top-level for easier lookup
        if '__static__' in class_obj.get('methods', {}):
            class_obj['__static__'] = class_obj['methods'].pop('__static__')

        self.functions[stmt.name] = class_obj
        # also expose class name in the current environment for lookup (e.g. A.hello())
        try:
            env.define(stmt.name, class_obj)
        except Exception:
            # if env doesn't support define, fallback to global env
            self.global_env.define(stmt.name, class_obj)
        # verify interface implementations
        for iface_name in getattr(stmt, 'implements', []) or []:
            iface = self.interfaces.get(iface_name)
            if iface is None:
                raise HSharpError(f"Interface '{iface_name}' not found for class '{stmt.name}'")
            # iface.methods contains merged methods from bases; entries may be Function nodes (with body for defaults)
            for mname, sig in iface.get('methods', {}).items():
                found = class_obj['methods'].get(mname)
                if not found:
                    # if interface provides a default implementation (Function with body), copy it into class
                    if isinstance(sig, Function) and sig.body is not None:
                        class_obj['methods'][mname] = sig
                        continue
                    raise HSharpError(f"Class '{stmt.name}' does not implement interface method '{mname}' from '{iface_name}'")
                # check arity
                if len(found.params) != len(sig.params):
                    raise HSharpError(f"Method '{mname}' in class '{stmt.name}' has wrong arity for interface '{iface_name}'")

    def visit_CallExpression(self, expr, env):
        args = [self.eval_expr(arg, env) for arg in expr.args]
        # function can be Identifier or MemberExpression or other
        if isinstance(expr.func, Identifier):
            name = expr.func.name
            if name in self.builtins:
                return self.builtins[name](args)
            # first check local/global variables (let-bound functions or values)
            try:
                val = env.lookup(name)
            except HSharpError:
                val = None
            if val is not None:
                # variable may be a callable value (closure or Python callable)
                if callable(val):
                    try:
                        return val(*args)
                    except Exception as e:
                        raise HSharpError(f'Error calling external function: {e}')
                if isinstance(val, dict):
                    # interpreter lambda/closure representation
                    if 'body' in val:
                        closure = val.get('closure_env', self.global_env)
                        call_env = Environment(parent=closure)
                        if len(args) != len(val.get('params', [])):
                            raise HSharpError(f"Function expects {len(val.get('params', []))} arguments, got {len(args)}")
                        for param, arg in zip(val.get('params', []), args):
                            call_env.define(param, arg)
                        try:
                            self.visit_BlockStatement(val['body'], call_env)
                        except ReturnException as e:
                            return e.value
                        return None
                # H# Function object stored as variable
                if isinstance(val, Function):
                    if getattr(val, 'is_coro', False):
                        coro = Coroutine(val, self, args)
                        return coro
                    if len(args) != len(val.params):
                        raise HSharpError(f"Function '{name}' expects {len(val.params)} arguments, got {len(args)}")
                    call_env = Environment(parent=self.global_env)
                    for param, arg in zip(val.params, args):
                        call_env.define(param, arg)
                    try:
                        self.visit_BlockStatement(val.body, call_env)
                    except ReturnException as e:
                        return e.value
                    return None
                # fallthrough to error if not callable
                raise HSharpError(f"Variable '{name}' is not a function")
            if name not in self.functions:
                raise HSharpError(f"Function '{name}' not defined")
            func = self.functions[name]
            if isinstance(func, dict) and 'methods' in func:
                raise HSharpError(f"'{name}' is a class, cannot call directly")
            # coroutine function: return a Coroutine object (cooperative)
            if (isinstance(func, Function) or isinstance(func, CoroFunction)) and getattr(func, 'is_coro', False):
                coro = Coroutine(func, self, args)
                return coro
            if len(args) != len(func.params):
                raise HSharpError(f"Function '{name}' expects {len(func.params)} arguments, got {len(args)}")
            call_env = Environment(parent=self.global_env)
            for param, arg in zip(func.params, args):
                call_env.define(param, arg)
            try:
                self.visit_BlockStatement(func.body, call_env)
            except ReturnException as e:
                return e.value
            return None
        elif isinstance(expr.func, MemberExpression):
            # method call: evaluate left to get instance
                left = self.eval_expr(expr.func.left, env)
                attr = expr.func.name
                # If left is a Python module proxy (dict), allow calling its callable attributes
                if isinstance(left, dict) and attr in left:
                    val = left.get(attr)
                    if callable(val):
                        try:
                            return val(*args)
                        except Exception as e:
                            raise HSharpError(f"Error calling external function '{attr}': {e}")
                    if isinstance(val, Function):
                        call_env = Environment(parent=self.global_env)
                        if len(args) != len(val.params):
                            raise HSharpError(f"Method '{attr}' expects {len(val.params)} arguments, got {len(args)}")
                        for param, arg in zip(val.params, args):
                            call_env.define(param, arg)
                        try:
                            self.visit_BlockStatement(val.body, call_env)
                        except ReturnException as e:
                            return e.value
                        return None
                    if isinstance(val, dict) and 'params' in val and 'body' in val:
                        # Lambda closure call
                        closure = val.get('closure_env', env)
                        call_env = Environment(parent=closure)
                        if len(args) != len(val['params']):
                            raise HSharpError(f"Lambda expects {len(val['params'])} arguments, got {len(args)}")
                        for param, arg in zip(val['params'], args):
                            call_env.define(param, arg)
                        try:
                            self.visit_BlockStatement(val['body'], call_env)
                        except ReturnException as e:
                            return e.value
                        return None
                    else:
                        raise HSharpError(f"Attribute '{attr}' on module is not callable")
                # If left is a class object (dict without '__class__'), support static methods
                if isinstance(left, dict) and '__class__' not in left:
                    static_map = left.get('__static__', {})
                    if attr in static_map:
                        method = static_map[attr]
                        if len(args) != len(method.params):
                            raise HSharpError(f"Method '{attr}' expects {len(method.params)} arguments, got {len(args)}")
                        call_env = Environment(parent=self.global_env)
                        for param, arg in zip(method.params, args):
                            call_env.define(param, arg)
                        try:
                            self.visit_BlockStatement(method.body, call_env)
                        except ReturnException as e:
                            return e.value
                        return None
                # If left is a real Python object (module or other), try getattr
                try:
                    if not isinstance(left, dict) and hasattr(left, attr):
                        val = getattr(left, attr)
                        if callable(val):
                            try:
                                return val(*args)
                            except Exception as e:
                                raise HSharpError(f"Error calling external function '{attr}': {e}")
                        else:
                            raise HSharpError(f"Attribute '{attr}' on object is not callable")
                except Exception:
                    # fallthrough to existing H# object method handling
                    pass
                # method call on H# object instances
                if not isinstance(left, dict) or '__class__' not in left:
                    raise HSharpError('Left side of member call is not an object')
                class_obj = left['__class__']
                methods = class_obj.get('methods', {})
                if attr not in methods:
                    # may be callable field
                    val = left.get(attr)
                    if callable(val):
                        return val(*args)
                    raise HSharpError(f"Attribute '{attr}' not found on instance")
                method = methods[attr]
                call_env = Environment(parent=self.global_env)
                call_env.define('self', left)
                if len(args) != len(method.params):
                    raise HSharpError(f"Method '{attr}' expects {len(method.params)} arguments, got {len(args)}")
                for param, arg in zip(method.params, args):
                    call_env.define(param, arg)
                try:
                    self.visit_BlockStatement(method.body, call_env)
                except ReturnException as e:
                    return e.value
                return None
        else:
            # general callable value: evaluate function value then call
            func_val = self.eval_expr(expr.func, env)
            # Python callable
            if callable(func_val):
                try:
                    return func_val(*args)
                except Exception as e:
                    raise HSharpError(f'Error calling external function: {e}')
            # interpreter lambda/closure representation
            if isinstance(func_val, dict) and 'body' in func_val:
                closure = func_val.get('closure_env', self.global_env)
                call_env = Environment(parent=closure)
                if len(args) != len(func_val.get('params', [])):
                    raise HSharpError(f'Function expects {len(func_val.get("params", []))} arguments, got {len(args)}')
                for param, arg in zip(func_val.get('params', []), args):
                    call_env.define(param, arg)
                try:
                    self.visit_BlockStatement(func_val['body'], call_env)
                except ReturnException as e:
                    return e.value
                return None
            # H# Function object (from self.functions)
            if isinstance(func_val, Function):
                call_env = Environment(parent=self.global_env)
                if len(args) != len(func_val.params):
                    raise HSharpError(f'Function expects {len(func_val.params)} arguments, got {len(args)}')
                for param, arg in zip(func_val.params, args):
                    call_env.define(param, arg)
                try:
                    self.visit_BlockStatement(func_val.body, call_env)
                except ReturnException as e:
                    return e.value
                return None
            raise HSharpError('Unsupported call expression')
    def visit_SuperExpression(self, expr, env):
        # Get self from current environment
        if 'self' not in env.vars:
            raise HSharpError("super() can only be called within a method")
        
        self_obj = env.lookup('self')
        if not isinstance(self_obj, dict) or '__class__' not in self_obj:
            raise HSharpError("super() can only be called within a class method")
        
        class_obj = self_obj['__class__']
        base_name = class_obj.get('base')
        if not base_name:
            raise HSharpError(f"Class '{class_obj.get('name', 'Unknown')}' has no parent class")
        
        # Get base class
        try:
            base = self.functions.get(base_name)
            if not base:
                base = self.global_env.lookup(base_name)
        except HSharpError:
            raise HSharpError(f"Base class '{base_name}' not found")
        
        if not isinstance(base, dict) or 'methods' not in base:
            raise HSharpError(f"'{base_name}' is not a valid class")
        
        # Get method from base class
        methods = base.get('methods', {})
        method_name = expr.method_name
        if method_name not in methods:
            raise HSharpError(f"Method '{method_name}' not found in base class '{base_name}'")
        
        method = methods[method_name]
        args = [self.eval_expr(arg, env) for arg in expr.args]
        
        # Create new environment for method call
        call_env = Environment(parent=self.global_env)
        call_env.define('self', self_obj)
        if len(args) != len(method.params):
            raise HSharpError(f"Method '{method_name}' expects {len(method.params)} arguments, got {len(args)}")
        
        for param, arg in zip(method.params, args):
            call_env.define(param, arg)
        
        try:
            self.visit_BlockStatement(method.body, call_env)
        except ReturnException as e:
            return e.value
        return None

    def visit_InstanceOfExpression(self, expr, env):
        obj = self.eval_expr(expr.expr, env)
        if not isinstance(obj, dict) or '__class__' not in obj:
            return False
        
        class_obj = obj['__class__']
        type_name = expr.type_name
        
        # Check if object is instance of type_name or its subclass
        def is_instance(class_obj, type_name):
            if class_obj.get('name') == type_name:
                return True
            # Check base class
            base_name = class_obj.get('base')
            if base_name:
                try:
                    base = self.functions.get(base_name)
                    if not base:
                        base = self.global_env.lookup(base_name)
                    if is_instance(base, type_name):
                        return True
                except HSharpError:
                    pass
            # Check interfaces
            interfaces = class_obj.get('implements', [])
            if type_name in interfaces:
                return True
            return False
        
        return is_instance(class_obj, type_name)

    def visit_SuperExpression(self, expr, env):
        # Get self from current environment
        if 'self' not in env.vars:
            raise HSharpError("super() can only be called within a method")
        
        self_obj = env.lookup('self')
        if not isinstance(self_obj, dict) or '__class__' not in self_obj:
            raise HSharpError("super() can only be called within a class method")
        
        class_obj = self_obj['__class__']
        base_name = class_obj.get('base')
        if not base_name:
            raise HSharpError(f"Class '{class_obj.get('name', 'Unknown')}' has no parent class")
        
        # Get base class
        try:
            base = self.functions.get(base_name)
            if not base:
                base = self.global_env.lookup(base_name)
        except HSharpError:
            raise HSharpError(f"Base class '{base_name}' not found")
        
        if not isinstance(base, dict) or 'methods' not in base:
            raise HSharpError(f"'{base_name}' is not a valid class")
        
        # Get method from base class
        methods = base.get('methods', {})
        method_name = expr.method_name
        if method_name not in methods:
            raise HSharpError(f"Method '{method_name}' not found in base class '{base_name}'")
        
        method = methods[method_name]
        args = [self.eval_expr(arg, env) for arg in expr.args]
        
        # Create new environment for method call
        call_env = Environment(parent=self.global_env)
        call_env.define('self', self_obj)
        if len(args) != len(method.params):
            raise HSharpError(f"Method '{method_name}' expects {len(method.params)} arguments, got {len(args)}")
        
        for param, arg in zip(method.params, args):
            call_env.define(param, arg)
        
        try:
            self.visit_BlockStatement(method.body, call_env)
        except ReturnException as e:
            return e.value
        return None

    def visit_InstanceOfExpression(self, expr, env):
        obj = self.eval_expr(expr.expr, env)
        if not isinstance(obj, dict) or '__class__' not in obj:
            return False
        
        class_obj = obj['__class__']
        type_name = expr.type_name
        
        # Check if object is instance of type_name or its subclass
        def is_instance(class_obj, type_name):
            if class_obj.get('name') == type_name:
                return True
            # Check base class
            base_name = class_obj.get('base')
            if base_name:
                try:
                    base = self.functions.get(base_name)
                    if not base:
                        base = self.global_env.lookup(base_name)
                    if is_instance(base, type_name):
                        return True
                except HSharpError:
                    pass
            # Check interfaces
            interfaces = class_obj.get('implements', [])
            if type_name in interfaces:
                return True
            return False
        
        return is_instance(class_obj, type_name)

    def visit_ArrayLiteral(self, expr, env):
        return [self.eval_expr(e, env) for e in expr.elements]

    def visit_DictLiteral(self, expr, env):
        d = {}
        for key_expr, val_expr in expr.pairs:
            key = self.eval_expr(key_expr, env)
            if not isinstance(key, (str, int)):
                raise HSharpError("Dictionary keys must be strings or integers")
            val = self.eval_expr(val_expr, env)
            d[key] = val
        return d

    def visit_IndexExpression(self, expr, env):
        left = self.eval_expr(expr.left, env)
        index = self.eval_expr(expr.index, env)
        if isinstance(left, list):
            if not isinstance(index, int):
                raise HSharpError("Array index must be integer")
            if index < 0:
                index = len(left) + index
            if index < 0 or index >= len(left):
                raise HSharpError("Array index out of bounds")
            return left[index]
        elif isinstance(left, str):
            if not isinstance(index, int):
                raise HSharpError("String index must be integer")
            if index < 0:
                index = len(left) + index
            if index < 0 or index >= len(left):
                raise HSharpError("String index out of bounds")
            return left[index]
        elif isinstance(left, dict):
            if index not in left:
                return None  # Return nullptr for missing keys
            return left[index]
        else:
            raise HSharpError("Can only index arrays, strings, or dictionaries")

    def visit_AssignmentIndex(self, stmt, env):
        arr = self.eval_expr(stmt.array, env)
        index = self.eval_expr(stmt.index, env)
        value = self.eval_expr(stmt.value, env)
        if isinstance(arr, list):
            if not isinstance(index, int):
                raise HSharpError("Array index must be integer")
            if index < 0:
                index = len(arr) + index
            if index < 0 or index >= len(arr):
                raise HSharpError("Array index out of bounds")
            arr[index] = value
        elif isinstance(arr, dict):
            arr[index] = value
        else:
            raise HSharpError("Can only assign to array or dictionary elements")
        return value

    def visit_AssignmentMember(self, stmt, env):
        obj = self.eval_expr(stmt.left, env)
        if not isinstance(obj, dict) or '__class__' not in obj:
            raise HSharpError('Left side of member assignment is not an object')
        value = self.eval_expr(stmt.value, env)
        obj[stmt.name] = value
        return value

    def visit_DeleteStatement(self, stmt, env):
        target = self.eval_expr(stmt.target, env)
        if isinstance(stmt.target, IndexExpression):
            left = self.eval_expr(stmt.target.left, env)
            index = self.eval_expr(stmt.target.index, env)
            if isinstance(left, list):
                if not isinstance(index, int):
                    raise HSharpError("Array index must be integer")
                if index < 0:
                    index = len(left) + index
                if index < 0 or index >= len(left):
                    raise HSharpError("Array index out of bounds")
                del left[index]
                return None
            elif isinstance(left, dict):
                if index not in left:
                    return None  # Silently ignore missing keys on delete
                del left[index]
                return None
            else:
                raise HSharpError("Can only delete from arrays or dictionaries")
        else:
            raise HSharpError("del target must be an index expression")
        return None

    def visit_InterfaceDeclaration(self, stmt, env):
        # store interface signatures and default implementations; support interface inheritance
        methods = {}
        for s in stmt.body.statements:
            if isinstance(s, Function):
                methods[s.name] = s
            else:
                raise HSharpError('Invalid member in interface')

        # merge bases
        merged_methods = {}
        for base_name in getattr(stmt, 'bases', []) or []:
            base_iface = self.interfaces.get(base_name)
            if base_iface is None:
                raise HSharpError(f"Interface base '{base_name}' not found for interface '{stmt.name}'")
            merged_methods.update(base_iface.get('methods', {}))
        # then overlay this interface's methods
        merged_methods.update(methods)

        iface = {'name': stmt.name, 'methods': merged_methods, 'body': stmt.body, 'bases': getattr(stmt, 'bases', []) or []}
        self.interfaces[stmt.name] = iface

    def visit_UnionDeclaration(self, stmt, env):
        """Store union type descriptor in global functions table."""
        variants = []
        for v in stmt.variants:
            variants.append({'name': v.name, 'fields': v.fields})
        union_obj = {'name': stmt.name, 'variants': variants, '__type__': 'union'}
        self.functions[stmt.name] = union_obj

    def visit_D3SizePowerDeclaration(self, stmt, env):
        d3_obj = {
            '__type': '3dsizepower',
            'name': stmt.name,
            'properties': [],
            'regions': [],
            'region_interfaces': []
        }
        for prop in stmt.properties:
            prop_data = {
                'name': prop.name,
                'is_public': prop.is_public,
                'params': []
            }
            if isinstance(prop.params, list):
                prop_data['params'] = prop.params
            elif isinstance(prop.params, D3CoordinateExpr):
                prop_data['params'] = prop.params.params
            d3_obj['properties'].append(prop_data)
        for item in stmt.body.statements:
            if isinstance(item, D3RegionInterfaceDeclaration):
                iface_obj = self._resolve_d3_region_interface(item, stmt.name)
                d3_obj['region_interfaces'].append(iface_obj)
            elif isinstance(item, D3RegionDeclaration):
                region_obj = self._resolve_d3_region(item, stmt.name, d3_obj)
                d3_obj['regions'].append(region_obj)
        self.functions[stmt.name] = d3_obj
        try:
            env.define(stmt.name, d3_obj)
        except Exception:
            self.global_env.define(stmt.name, d3_obj)

    def visit_D3Em3dDeclaration(self, stmt, env):
        parent = None
        if stmt.parent_d3:
            parent = self.functions.get(stmt.parent_d3)
            if parent is None:
                try:
                    parent = self.global_env.lookup(stmt.parent_d3)
                except HSharpError:
                    raise HSharpError(f"Parent 3dsizepower '{stmt.parent_d3}' not found")
        em3d_obj = {
            '__type': 'em3d',
            '__parent_3d': parent,
            'name': stmt.name,
            'properties': [],
            'regions': [],
            'region_interfaces': []
        }
        if parent:
            for r in parent.get('regions', []):
                em3d_obj['regions'].append(dict(r))
            for ri in parent.get('region_interfaces', []):
                em3d_obj['region_interfaces'].append(dict(ri))
            for p in parent.get('properties', []):
                em3d_obj['properties'].append(dict(p))
        for prop in stmt.properties:
            prop_data = {
                'name': prop.name,
                'is_public': prop.is_public,
                'params': []
            }
            if isinstance(prop.params, list):
                prop_data['params'] = prop.params
            elif isinstance(prop.params, D3CoordinateExpr):
                prop_data['params'] = prop.params.params
            em3d_obj['properties'].append(prop_data)
        for item in stmt.body.statements:
            if isinstance(item, D3RegionInterfaceDeclaration):
                iface_obj = self._resolve_d3_region_interface(item, stmt.name)
                em3d_obj['region_interfaces'].append(iface_obj)
            elif isinstance(item, D3RegionDeclaration):
                region_obj = self._resolve_d3_region(item, stmt.name, em3d_obj)
                em3d_obj['regions'].append(region_obj)
        self.functions[stmt.name] = em3d_obj
        try:
            env.define(stmt.name, em3d_obj)
        except Exception:
            self.global_env.define(stmt.name, em3d_obj)

    def _resolve_d3_region_interface(self, item, parent_name):
        methods = {}
        for m in item.methods:
            methods[m.name] = {'params': m.params, 'body': m.body}
        base_methods = {}
        for bn in item.bases:
            if bn in self.interfaces:
                base_methods.update(self.interfaces[bn].get('methods', {}))
        base_methods.update(methods)
        return {
            '__type': 'region_interface',
            'name': item.name,
            'parent_d3': parent_name,
            'methods': base_methods
        }

    def _resolve_d3_region(self, item, parent_name, d3_obj):
        coords = item.coords
        region_obj = {
            '__type': 'region',
            'name': item.name,
            'parent_d3': parent_name,
            'coords': coords,
            'implements': item.implements,
            'body': item.body,
            'd3_ref': d3_obj
        }
        methods = {}
        classes = {}
        block_env = Environment(parent=self.global_env)
        for s in item.body.statements:
            if isinstance(s, Function):
                methods[s.name] = s
                block_env.define(s.name, s)
            elif isinstance(s, ClassDeclaration):
                self.visit_ClassDeclaration(s, block_env)
                classes[s.name] = self.functions.get(s.name)
            elif isinstance(s, LetStatement):
                self.visit_LetStatement(s, block_env)
            elif isinstance(s, PrintStatement):
                vals = self.eval_expr(s.expr, block_env)
        region_obj['methods'] = methods
        region_obj['classes'] = classes
        region_obj['env'] = block_env
        return region_obj

    def eval_expr(self, expr, env):
        if isinstance(expr, Identifier):
            try:
                return env.lookup(expr.name)
            except HSharpError:
                if expr.name in self.functions:
                    return self.functions[expr.name]
                raise
        elif isinstance(expr, NumberLiteral):
            return expr.value
        elif isinstance(expr, StringLiteral):
            return expr.value
        elif isinstance(expr, NullLiteral):
            return None
        elif isinstance(expr, BooleanLiteral):
            return expr.value
        elif isinstance(expr, ArrayLiteral):
            return self.visit_ArrayLiteral(expr, env)
        elif isinstance(expr, DictLiteral):
            return self.visit_DictLiteral(expr, env)
        elif isinstance(expr, IndexExpression):
            return self.visit_IndexExpression(expr, env)
        elif isinstance(expr, BinaryOp):
            op = expr.op
            if op == TokenType.AND:
                left = self.eval_expr(expr.left, env)
                if not left:
                    return left
                return self.eval_expr(expr.right, env)
            if op == TokenType.OR:
                left = self.eval_expr(expr.left, env)
                if left:
                    return left
                return self.eval_expr(expr.right, env)
            left = self.eval_expr(expr.left, env)
            right = self.eval_expr(expr.right, env)
            if op == TokenType.PLUS:
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                if isinstance(left, list) and isinstance(right, list):
                    return left + right
                self._ensure_number(left, right)
                return left + right
            elif op == TokenType.MINUS:
                self._ensure_number(left, right)
                return left - right
            elif op == TokenType.STAR:
                self._ensure_number(left, right)
                return left * right
            elif op == TokenType.SLASH:
                self._ensure_number(left, right)
                if right == 0:
                    raise HSharpError("Division by zero")
                if isinstance(left, float) or isinstance(right, float):
                    return left / right
                return left // right
            elif op == TokenType.EQEQ:
                return left == right
            elif op == TokenType.MOD:
                self._ensure_number(left, right)
                if right == 0:
                    raise HSharpError("Modulo by zero")
                return left % right
            elif op == TokenType.BANGEQ:
                return left != right
            elif op == TokenType.GT:
                self._ensure_comparable(left, right)
                return left > right
            elif op == TokenType.LT:
                self._ensure_comparable(left, right)
                return left < right
            elif op == TokenType.GTE:
                self._ensure_comparable(left, right)
                return left >= right
            elif op == TokenType.LTE:
                self._ensure_comparable(left, right)
                return left <= right
            elif op == TokenType.IN:
                if isinstance(right, list):
                    return left in right
                if isinstance(right, dict):
                    return left in right
                if isinstance(right, str):
                    if not isinstance(left, str):
                        raise HSharpError("'in' operator with string requires string left operand")
                    return left in right
                raise HSharpError("'in' operator requires list, dict, or string on right side")
            elif op == TokenType.BITAND:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Bitwise operations require integer operands')
                return left & right
            elif op == TokenType.BITOR:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Bitwise operations require integer operands')
                return left | right
            elif op == TokenType.BITXOR:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Bitwise operations require integer operands')
                return left ^ right
            elif op == TokenType.LSHIFT:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Shift operations require integer operands')
                return left << right
            elif op == TokenType.RSHIFT:
                if not isinstance(left, int) or not isinstance(right, int):
                    raise HSharpError('Shift operations require integer operands')
                return left >> right
            else:
                raise HSharpError(f"Unknown operator: {op}")
        elif isinstance(expr, UnaryOp):
            if expr.op == TokenType.NOT:
                val = self.eval_expr(expr.operand, env)
                if not isinstance(val, bool):
                    raise HSharpError("'not' operand must be boolean")
                return not val
            elif expr.op == TokenType.TILDE:
                val = self.eval_expr(expr.operand, env)
                if not isinstance(val, int):
                    raise HSharpError("'~' operand must be integer")
                return ~val
            else:
                raise HSharpError(f"Unknown unary operator: {expr.op}")
        elif isinstance(expr, TernaryOp):
            cond = self.eval_expr(expr.condition, env)
            if cond:
                return self.eval_expr(expr.true_expr, env)
            else:
                return self.eval_expr(expr.false_expr, env)
        elif isinstance(expr, QuaternaryOp):
            cond1 = self.eval_expr(expr.cond1, env)
            if cond1:
                return self.eval_expr(expr.expr1, env)
            cond2 = self.eval_expr(expr.cond2, env)
            if cond2:
                return self.eval_expr(expr.expr2, env)
            return None
        elif isinstance(expr, PointerDereference):
            # pseudo-pointer: evaluate target and return value (no real pointer semantics)
            return self.eval_expr(expr.target, env)
        elif isinstance(expr, NewExpression):
            cname = expr.class_name.name if isinstance(expr.class_name, Identifier) else None
            args = [self.eval_expr(a, env) for a in expr.args]
            if cname in self.functions:
                cls = self.functions[cname]
                inst = {'__class__': cls}
                for k, v in cls.get('fields', {}).items():
                    inst[k] = v
                return inst
            raise HSharpError(f"Class '{cname}' not found")
        elif isinstance(expr, UnionConstructExpression):
            type_name = expr.type_name.name if isinstance(expr.type_name, Identifier) else None
            variant_name = expr.variant_name
            values = [self.eval_expr(v, env) for v in expr.values]
            if type_name in self.functions:
                union_type = self.functions[type_name]
                if not isinstance(union_type, dict) or union_type.get('__type__') != 'union':
                    raise HSharpError(f"'{type_name}' is not a union type")
                variant = None
                for vv in union_type.get('variants', []):
                    if vv['name'] == variant_name:
                        variant = vv
                        break
                if variant is None:
                    raise HSharpError(f"Unknown variant '{variant_name}' for union '{type_name}'")
                if len(values) != len(variant['fields']):
                    raise HSharpError(f"Variant '{variant_name}' expects {len(variant['fields'])} fields, got {len(values)}")
                inst = {}
                inst['__union__'] = type_name
                inst['__variant__'] = variant_name
                for i, fname in enumerate(variant['fields']):
                    inst[fname] = values[i]
                return inst
            raise HSharpError(f"Union type '{type_name}' not found")
        elif isinstance(expr, CallExpression):
            return self.visit_CallExpression(expr, env)
        elif isinstance(expr, Lambda):
            # return a callable representation capturing the current environment
            return {'params': expr.params, 'body': expr.body, 'closure_env': env}
        elif isinstance(expr, MemberExpression):
            left = self.eval_expr(expr.left, env)
            if isinstance(left, dict) and '__class__' in left:
                # return field value if exists
                if expr.name in left:
                    return left[expr.name]
                # fallback to class default field
                class_obj = left['__class__']
                fields = class_obj.get('fields', {})
                if expr.name in fields:
                    return fields[expr.name]
                # methods are not returned directly here
                raise HSharpError(f"Attribute '{expr.name}' not found on instance")
            # property access on dict-like
            if isinstance(left, dict):
                if expr.name in left:
                    return left[expr.name]
            raise HSharpError(f"Cannot access attribute '{expr.name}' on non-object")
        else:
            raise HSharpError(f"Unknown expression: {expr}")

    def _ensure_number(self, a, b):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise HSharpError("Operands must be numbers")

    def _ensure_comparable(self, a, b):
        if not isinstance(a, (int, float, str)) or not isinstance(b, (int, float, str)):
            raise HSharpError("Can only compare numbers or strings")
        if isinstance(a, str) and not isinstance(b, str):
            raise HSharpError("Cannot compare string with non-string")
        if isinstance(b, str) and not isinstance(a, str):
            raise HSharpError("Cannot compare string with non-string")


if __name__ == '__main__':
    from lexer import Lexer
    from parser import Parser
    if len(sys.argv) < 2:
        print("Usage: python interpreter.py <file.hto>")
        sys.exit(1)
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    lexer = Lexer(code)
    parser = Parser(lexer)
    program = parser.parse()
    interp = Interpreter()
    interp.interpret(program)