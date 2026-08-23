import sys
import copy
import time
import datetime
import host_functions as _hf
from collections import deque

class BytecodeRuntimeError(Exception):
    pass

class HSharpException(Exception):
    def __init__(self, value):
        self.value = value

class VM:
    def __init__(self, bytecode, consts=None):
        self.instructions = bytecode.get('instructions', [])
        self.consts = bytecode.get('consts', []) if consts is None else consts
        self.stack = []
        self.env = {}
        self.functions = {}
        self.pc = 0
        self.parent = None
        self._exception_handlers = []
        # Names captured from an enclosing lexical scope (closure cells).
        # Populated by CALL_FUNCTION/CALL_VALUE from the callee's func_obj.
        self.freevars = set()
        # Names declared as locals (`let`/params) in the current callable.
        # Used to tell instance-field bare names apart from true locals
        # (mirrors the tree interpreter's InstanceScope).  Populated by the
        # call handlers from the callee's func_obj['local_names'].
        self.local_names = set()
        # Fast locals：由 LOAD_FAST/STORE_FAST 使用，按索引访问的列表，比 dict env 更快
        # fast_names 由编译器在 bytecode 中通过 'FAST_NAMES' 元信息提供
        self.fast_slots = []
        self._fast_name_to_idx = {}
        fn = bytecode.get('fast_names') if isinstance(bytecode, dict) else None
        if fn:
            self._fast_name_to_idx = {n: i for i, n in enumerate(fn)}
            self.fast_slots = [None] * len(fn)
        # 内联缓存（monomorphic inline cache）
        # LOAD_ATTR:  pc -> (class_id, kind, payload)
        #   kind 'direct': payload=name，直接 obj[name]（实例字段/模块属性）
        #   kind 'method': payload=method_name，从 class methods 取并绑定
        # CALL_METHOD: pc -> (class_id, method_name) 命中后直接定位 method dict
        self._attr_cache = {}
        self._method_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        # The class whose method is *currently executing* in this frame.  Used
        # by CALL_SUPER to resolve `super` relative to the active method rather
        # than the (always-leaf) instance class, so a multi-level chain
        # (C extends B extends A) advances C -> B -> A instead of looping.
        self._method_owner = None
        self.builtins = {
            'len': lambda args: len(args[0]) if len(args)==1 else (_ for _ in ()).throw(BytecodeRuntimeError('len() takes 1 arg')),
            'push': lambda args: (args[0].append(args[1]) or None),
            'pop': lambda args: args[0].pop(),
            'read_file': lambda args: open(args[0], 'r', encoding='utf-8').read(),
            'write_file': lambda args: (open(args[0], 'w', encoding='utf-8').write(args[1]) or None),
            'thread_spawn': self._builtin_thread_spawn,
            'thread_join': self._builtin_thread_join,
            'str': lambda args: ("true" if args[0] is True else "false" if args[0] is False else str(args[0])),
            'int': lambda args: int(args[0]),
            'float': lambda args: float(args[0]),
            'type': self._b_type,
            'chan_new': self._b_chan_new,
            'chan_send': self._b_chan_send,
            'chan_recv': self._b_chan_recv,
            'chan_close': self._b_chan_close,
            'chan_size': self._b_chan_size,
            'chan_try_send': self._b_chan_try_send,
            'chan_try_recv': self._b_chan_try_recv,
            'time_ms': self._b_time_ms,
            'parallelism': self._b_parallelism,
            'dzzw_worker_count': self._b_dzzw_worker_count,
            'abs': lambda args: abs(args[0]),
            'min': lambda args: min(args),
            'max': lambda args: max(args),
            'range': lambda args: list(range(args[0])) if len(args) == 1 else list(range(args[0], args[1])),
            'keys': lambda args: list(args[0].keys()),
            'values': lambda args: list(args[0].values()),
            'items': lambda args: list(args[0].items()),
            'has_key': lambda args: (args[1] in args[0]) if (len(args) == 2 and isinstance(args[0], dict)) else False,
            'dict_has': self._b_dict_has,
            'dict_get': self._b_dict_get,
            'dict_keys': self._b_dict_keys,
            'dict_values': self._b_dict_values,
            'dict_items': self._b_dict_items,
            'substring': self._b_substring,
            'ord': self._b_ord,
            'chr': self._b_chr,
            'time_now': self._b_time_now,
            'datetime_now': self._b_datetime_now,
            'input': self._b_input,
        }
        # Host functions (fs_*/io_*/json_*) reused from host_functions.py to
        # narrow the gap with the tree interpreter's backend.  These are pure
        # arg-in/arg-out wrappers over os/json, so registering them directly
        # preserves identical semantics.  Network http_* is intentionally
        # excluded from this stability pass.
        _HOST_FUNC_MAP = {
            'json_parse': 'builtin_net_json_parse',
            'json_stringify': 'builtin_net_json_stringify',
            'fs_exists': 'builtin_fs_exists',
            'fs_is_file': 'builtin_fs_is_file',
            'fs_is_dir': 'builtin_fs_is_dir',
            'fs_mkdir': 'builtin_fs_mkdir',
            'fs_remove': 'builtin_fs_remove',
            'fs_list_dir': 'builtin_fs_list_dir',
            'fs_get_cwd': 'builtin_fs_get_cwd',
            'fs_chdir': 'builtin_fs_chdir',
            'fs_join_path': 'builtin_fs_join_path',
            'fs_get_ext': 'builtin_fs_get_ext',
            'fs_get_basename': 'builtin_fs_get_basename',
            'fs_get_dirname': 'builtin_fs_get_dirname',
            'fs_dir_current': 'builtin_fs_dir_current',
            'fs_path_join': 'builtin_fs_path_join',
            'fs_path_filename': 'builtin_fs_path_filename',
            'fs_path_extension': 'builtin_fs_path_extension',
            'fs_path_is_absolute': 'builtin_fs_path_is_absolute',
            'fs_path_parent': 'builtin_fs_path_parent',
            'fs_temp_dir': 'builtin_fs_temp_dir',
            'fs_cleanup_temp': 'builtin_fs_cleanup_temp',
            'fs_format_size': 'builtin_fs_format_size',
            'fs_validate_path': 'builtin_fs_validate_path',
            'fs_change_extension': 'builtin_fs_change_extension',
            'fs_file_delete': 'builtin_fs_file_delete',
            'fs_file_exists': 'builtin_fs_file_exists',
            'fs_dir_exists': 'builtin_fs_dir_exists',
            'io_append_file': 'builtin_io_append_file',
            'io_read_lines': 'builtin_io_read_lines',
            'io_write_lines': 'builtin_io_write_lines',
            'io_pad_right': 'builtin_io_pad_right',
            'io_csv_parse_line': 'builtin_io_csv_parse_line',
            'io_progress_bar': 'builtin_io_progress_bar',
            'io_display_table': 'builtin_io_display_table',
            'io_file_write': 'builtin_io_file_write',
            'io_file_read': 'builtin_io_file_read',
            'io_file_append': 'builtin_io_file_append',
            'io_file_write_lines': 'builtin_io_file_write_lines',
            'io_file_read_lines': 'builtin_io_file_read_lines',
            'io_kv_write': 'builtin_io_kv_write',
            'io_kv_read': 'builtin_io_kv_read',
            'io_log_info': 'builtin_io_log_info',
            # Date / datetime (pure, parity with tree interpreter)
            'date_now': 'builtin_date_now',
            'date_timestamp': 'builtin_date_timestamp',
            'date_format': 'builtin_date_format',
            'date_parse': 'builtin_date_parse',
            'datetime_timestamp': 'builtin_datetime_timestamp',
            'datetime_format': 'builtin_datetime_format',
            'datetime_parse': 'builtin_datetime_parse',
            'datetime_get_year': 'builtin_datetime_get_year',
            'datetime_is_leap_year': 'builtin_datetime_is_leap_year',
            'datetime_days_in_month': 'builtin_datetime_days_in_month',
            'datetime_format_duration': 'builtin_datetime_format_duration',
            'datetime_today': 'builtin_datetime_today',
            'datetime_timer_start': 'builtin_datetime_timer_start',
            'datetime_timer_elapsed': 'builtin_datetime_timer_elapsed',
            # String / encoding / url (pure)
            'str_contains': 'builtin_str_contains',
            'url_parse': 'builtin_net_url_parse',
            'url_build': 'builtin_net_url_build',
            'base64_encode': 'builtin_net_base64_encode',
            'base64_decode': 'builtin_net_base64_decode',
            # In-memory hash table (pure)
            'htable_create': 'builtin_htable_create',
            'htable_set': 'builtin_htable_set',
            'htable_get': 'builtin_htable_get',
            'htable_has': 'builtin_htable_has',
            'htable_delete': 'builtin_htable_delete',
            'htable_size': 'builtin_htable_size',
            'htable_keys': 'builtin_htable_keys',
            'htable_values': 'builtin_htable_values',
            # Random (pure)
            'rand_int': 'builtin_rand_int',
        }
        for _hname, _fname in _HOST_FUNC_MAP.items():
            _fn = getattr(_hf, _fname, None)
            if _fn is not None:
                self.builtins[_hname] = _fn
        # Math builtins — parity with the tree interpreter's builtin_math_* set
        # (interpreter.py).  Faithful port including domain guards (return None
        # for out-of-domain inputs) so opt matches tree's edge-case behaviour.
        import math as _math
        def _m1(fn, name):
            def impl(args):
                if len(args) != 1:
                    raise BytecodeRuntimeError(f"{name}() takes exactly 1 argument")
                return fn(float(args[0]))
            return impl
        def _m2(fn, name):
            def impl(args):
                if len(args) != 2:
                    raise BytecodeRuntimeError(f"{name}() takes exactly 2 arguments")
                return fn(float(args[0]), float(args[1]))
            return impl
        for _n, _f in (('math_sin', _math.sin), ('math_cos', _math.cos), ('math_tan', _math.tan),
                       ('math_atan', _math.atan), ('math_sinh', _math.sinh), ('math_cosh', _math.cosh),
                       ('math_tanh', _math.tanh), ('math_exp', _math.exp), ('math_floor', _math.floor),
                       ('math_ceil', _math.ceil), ('math_fabs', _math.fabs), ('math_erf', _math.erf),
                       ('math_erfc', _math.erfc), ('math_tgamma', _math.gamma), ('math_lgamma', _math.lgamma)):
            self.builtins[_n] = _m1(_f, _n)
        for _n, _f in (('math_atan2', _math.atan2), ('math_pow', _math.pow), ('math_hypot', _math.hypot)):
            self.builtins[_n] = _m2(_f, _n)
        def _g1(name, fn, dom_ok):
            def impl(args):
                if len(args) != 1:
                    raise BytecodeRuntimeError(f"{name}() takes exactly 1 argument")
                x = float(args[0])
                return fn(x) if dom_ok(x) else None
            return impl
        self.builtins['math_asin'] = _g1('math_asin', _math.asin, lambda x: -1 <= x <= 1)
        self.builtins['math_acos'] = _g1('math_acos', _math.acos, lambda x: -1 <= x <= 1)
        self.builtins['math_log'] = _g1('math_log', _math.log, lambda x: x > 0)
        self.builtins['math_log10'] = _g1('math_log10', _math.log10, lambda x: x > 0)
        self.builtins['math_log2'] = _g1('math_log2', _math.log2, lambda x: x > 0)
        self.builtins['math_sqrt'] = _g1('math_sqrt', _math.sqrt, lambda x: x >= 0)
        def _math_cbrt(args):
            x = float(args[0])
            return x ** (1.0 / 3.0) if x >= 0 else -((-x) ** (1.0 / 3.0))
        self.builtins['math_cbrt'] = _math_cbrt
        def _math_fmod(args):
            if len(args) != 2:
                raise BytecodeRuntimeError("math_fmod() takes exactly 2 arguments")
            y = float(args[1])
            if y == 0:
                return None
            return _math.fmod(float(args[0]), y)
        self.builtins['math_fmod'] = _math_fmod
        # 小对象分配优化：实例 dict 对象池
        # CALL_NEW 创建实例时优先从池中取已清空的 dict，减少 malloc 次数
        self._dict_pool = []
        self._pool_reused = 0
        self._pool_allocated = 0

    def _acquire_instance_dict(self):
        """从对象池取一个已清空的 dict；池空时新建。"""
        if self._dict_pool:
            d = self._dict_pool.pop()
            self._pool_reused += 1
            return d
        self._pool_allocated += 1
        return {}

    def release_instance_dict(self, d):
        """回收一个实例 dict（清空后放回池中，供下次复用）。"""
        if d is None or not isinstance(d, dict):
            return
        d.clear()
        # 限制池大小避免无限增长
        if len(self._dict_pool) < 256:
            self._dict_pool.append(d)

    def run(self):
        # 小对象分配优化：VM 运行期间禁用 Python 周期性 GC（依赖引用计数回收），
        # 消除全堆扫描造成的暂停；运行结束后恢复原状态。
        # 目标：GC 暂停 < 1ms（由 perf_monitor 验证）
        import gc as _gc
        _gc_was_enabled = _gc.isenabled()
        if _gc_was_enabled:
            _gc.disable()
        try:
            return self._run_impl()
        finally:
            if _gc_was_enabled:
                _gc.enable()

    def _run_impl(self):
        instrs = self.instructions
        while self.pc < len(instrs):
            opname, arg = instrs[self.pc]
            self.pc += 1
            try:
                if opname == 'LOAD_CONST':
                    self.stack.append(self.consts[arg])
                elif opname == 'LOAD_NAME':
                    name = arg
                    val = self._lookup_name(name)
                    self.stack.append(val)
                elif opname == 'STORE_NAME':
                    val = self.stack.pop()
                    name = arg
                    if self.freevars and name in self.freevars:
                        # Captured (closure) variable: write through to the
                        # defining environment so all closures share one cell
                        # (e.g. inc/dec/get sharing the same `count`).  The
                        # defining frame may keep the var in a fast slot
                        # (register-allocated), so check both env and slots.
                        node = self.parent
                        while node is not None:
                            if name in node.env:
                                node.env[name] = val
                                break
                            idx = node._fast_name_to_idx.get(name)
                            if idx is not None and 0 <= idx < len(node.fast_slots):
                                node.fast_slots[idx] = val
                                break
                            node = node.parent
                        else:
                            if self.parent is not None:
                                self.parent.env[name] = val
                            else:
                                self.env[name] = val
                    else:
                        # Instance-field bare-name assignment (mirrors the tree
                        # interpreter's InstanceScope): inside a method, a bare
                        # assignment to a name that is a field of `self` and was
                        # NOT declared as a local `let`/param writes through to
                        # the instance rather than shadowing it with a frame
                        # local.  `name not in self.env` is a cheap fast path:
                        # true locals land in env on their first store.
                        if name not in self.env and name not in self.local_names:
                            _self = self.env.get('self')
                            if isinstance(_self, dict) and name in _self:
                                _self[name] = val
                                continue
                        self.env[name] = val
                elif opname == 'MAKE_CLOSURE':
                    # Materialise a closure object that captures the *current*
                    # VM as its defining environment.  A fresh shallow copy is
                    # made per definition site so two calls to the same
                    # enclosing fn keep separate cells (no aliasing of the
                    # shared func_obj const).
                    func_obj = self.consts[arg]
                    closure = dict(func_obj)
                    closure['__closure__'] = self
                    # Evaluate compiled default-argument expressions once, in
                    # the defining environment (mirrors the tree interpreter's
                    # behaviour of evaluating defaults at function-definition
                    # time).  Literal defaults are already plain values and
                    # pass through unchanged.
                    _raw_defaults = closure.get('defaults')
                    if _raw_defaults:
                        _evaluated = []
                        for _d in _raw_defaults:
                            if isinstance(_d, dict) and 'bytecode' in _d:
                                _bc = {'instructions': _d['bytecode'], 'consts': _d.get('consts', [])}
                                _vm_def = VM(_bc)
                                _vm_def.parent = self
                                _vm_def.functions = self.functions
                                _evaluated.append(_vm_def.run())
                            else:
                                _evaluated.append(_d)
                        closure['defaults'] = _evaluated
                    self.stack.append(closure)
                elif opname == 'LOAD_FAST':
                    # arg 为槽位索引；越界时回退到 env 查找（兼容未分配槽位的变量）
                    if 0 <= arg < len(self.fast_slots):
                        self.stack.append(self.fast_slots[arg])
                    else:
                        self.stack.append(self.env.get(arg))
                elif opname == 'STORE_FAST':
                    val = self.stack.pop()
                    if 0 <= arg < len(self.fast_slots):
                        self.fast_slots[arg] = val
                    else:
                        self.env[arg] = val
                elif opname == 'PRINT':
                    val = self.stack.pop()
                    print(val)
                elif opname == 'POP_TOP':
                    self.stack.pop()
                elif opname == 'MAKE_LIST':
                    n = arg
                    items = [self.stack.pop() for _ in range(n)][::-1]
                    self.stack.append(items)
                elif opname == 'MAKE_DICT':
                    n = arg
                    d = {}
                    for _ in range(n):
                        val = self.stack.pop()
                        key = self.stack.pop()
                        d[key] = val
                    self.stack.append(d)
                elif opname == 'GET_ITEM':
                    idx = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left[idx])
                elif opname == 'LOAD_ATTR':
                    name = arg
                    obj = self.stack.pop()
                    # === inline cache 快路径 ===
                    entry = self._attr_cache.get(self.pc - 1)
                    if entry is not None:
                        cid, kind, payload = entry
                        if isinstance(obj, dict):
                            obj_cid = id(obj.get('__class__')) if '__class__' in obj else id(obj)
                            if obj_cid == cid:
                                if kind == 'direct':
                                    if name in obj:
                                        self.stack.append(obj[name])
                                        self._cache_hits += 1
                                        continue
                                elif kind == 'method':
                                    class_obj = obj.get('__class__')
                                    if class_obj is not None and name in class_obj.get('methods', {}):
                                        self.stack.append({'__method__': class_obj['methods'][name], '__self__': obj})
                                        self._cache_hits += 1
                                        continue
                                elif kind == 'class_field':
                                    class_obj = obj.get('__class__')
                                    if class_obj is not None and name in class_obj.get('fields', {}):
                                        self.stack.append(class_obj['fields'][name])
                                        self._cache_hits += 1
                                        continue
                        self._cache_misses += 1
                    # === 慢路径：完整查找 + 填充缓存 ===
                    # object attribute lookup
                    if isinstance(obj, dict):
                        if name in obj:
                            self.stack.append(obj[name])
                            cid = id(obj.get('__class__')) if '__class__' in obj else id(obj)
                            self._attr_cache[self.pc - 1] = (cid, 'direct', name)
                            continue
                        if '__class__' in obj:
                            class_obj = obj['__class__']
                            # check private access: only allowed when caller self == obj
                            private = class_obj.get('private', [])
                            caller_self = self.env.get('self')
                            if name in private and caller_self is not obj:
                                raise BytecodeRuntimeError(f"Private attribute '{name}' access denied")
                            # instance fields defaults
                            fields = class_obj.get('fields', {})
                            if name in fields:
                                self.stack.append(fields[name])
                                self._attr_cache[self.pc - 1] = (id(class_obj), 'class_field', name)
                                continue
                            # methods: return bound method wrapper
                            methods = class_obj.get('methods', {})
                            if name in methods:
                                self.stack.append({'__method__': methods[name], '__self__': obj})
                                self._attr_cache[self.pc - 1] = (id(class_obj), 'method', name)
                                continue
                    raise BytecodeRuntimeError(f"Attribute '{name}' not found on object")
                elif opname == 'STORE_ATTR':
                    name = arg
                    val = self.stack.pop()
                    obj = self.stack.pop()
                    if not isinstance(obj, dict):
                        raise BytecodeRuntimeError('STORE_ATTR target is not an object')
                    # enforce private write
                    class_obj = obj.get('__class__')
                    if class_obj and name in class_obj.get('private', []) and self.env.get('self') is not obj:
                        raise BytecodeRuntimeError(f"Private attribute '{name}' write denied")
                    obj[name] = val
                    self.stack.append(val)
                elif opname == 'SET_ITEM':
                    val = self.stack.pop()
                    idx = self.stack.pop()
                    left = self.stack.pop()
                    left[idx] = val
                    self.stack.append(val)
                elif opname == 'BINARY_ADD':
                    b = self.stack.pop(); a = self.stack.pop()
                    if isinstance(a, str) and not isinstance(b, str):
                        b = str(b)
                    elif isinstance(b, str) and not isinstance(a, str):
                        a = str(a)
                    self.stack.append(a + b)
                elif opname == 'BINARY_SUB':
                    b = self.stack.pop(); a = self.stack.pop(); self.stack.append(a - b)
                elif opname == 'BINARY_MUL':
                    b = self.stack.pop(); a = self.stack.pop(); self.stack.append(a * b)
                elif opname == 'BINARY_DIV':
                    b = self.stack.pop(); a = self.stack.pop();
                    if b == 0:
                        raise BytecodeRuntimeError('division by zero')
                    # Match the tree interpreter: `/` is integer division for
                    # int/int, but true (float) division as soon as either side
                    # is a float (e.g. `5 / 2.0` == 2.5, not 2).
                    if isinstance(a, float) or isinstance(b, float):
                        self.stack.append(a / b)
                    else:
                        self.stack.append(a // b)
                elif opname == 'BINARY_MOD':
                    b = self.stack.pop(); a = self.stack.pop();
                    if b == 0:
                        raise BytecodeRuntimeError('modulo by zero')
                    self.stack.append(a % b)
                elif opname == 'BINARY_BITAND':
                    b = self.stack.pop(); a = self.stack.pop()
                    if not isinstance(a, int) or not isinstance(b, int):
                        raise BytecodeRuntimeError('Bitwise operations require integer operands')
                    self.stack.append(a & b)
                elif opname == 'BINARY_BITOR':
                    b = self.stack.pop(); a = self.stack.pop()
                    if not isinstance(a, int) or not isinstance(b, int):
                        raise BytecodeRuntimeError('Bitwise operations require integer operands')
                    self.stack.append(a | b)
                elif opname == 'BINARY_BITXOR':
                    b = self.stack.pop(); a = self.stack.pop()
                    if not isinstance(a, int) or not isinstance(b, int):
                        raise BytecodeRuntimeError('Bitwise operations require integer operands')
                    self.stack.append(a ^ b)
                elif opname == 'BINARY_LSHIFT':
                    b = self.stack.pop(); a = self.stack.pop()
                    if not isinstance(a, int) or not isinstance(b, int):
                        raise BytecodeRuntimeError('Shift operations require integer operands')
                    self.stack.append(a << b)
                elif opname == 'BINARY_RSHIFT':
                    b = self.stack.pop(); a = self.stack.pop()
                    if not isinstance(a, int) or not isinstance(b, int):
                        raise BytecodeRuntimeError('Shift operations require integer operands')
                    self.stack.append(a >> b)
                elif opname == 'FOR_ITER':
                    # Two possible stack patterns:
                    # Pattern A (new): [..., iterable, ('__ITER__', var1, var2)]
                    # Pattern B (legacy): [..., iterable, sentinel_int]
                    jump_target = arg
                    if not self.stack:
                        raise BytecodeRuntimeError("FOR_ITER with empty stack")
                    
                    top = self.stack[-1]
                    iterable = None
                    var1 = 'i'
                    var2 = None
                    
                    if isinstance(top, dict) and top.get('__is_iter'):
                        # Subsequent iteration - get next item
                        it = top
                        iter_list = it.get('__iterable', [])
                        idx = it.get('__iter_idx', 0)
                        v1 = it.get('__var1', 'i')
                        v2 = it.get('__var2')
                        
                        if idx < len(iter_list):
                            if v2 is not None and '__dict' in it:
                                key = iter_list[idx]
                                self._set_local(v1, key)
                                self._set_local(v2, it['__dict'][key])
                            else:
                                self._set_local(v1, iter_list[idx])
                            it['__iter_idx'] = idx + 1
                        else:
                            self.stack.pop()
                            self.pc = jump_target
                    elif isinstance(top, (tuple, list)) and len(top) == 3 and top[0] == '__ITER__':
                        # Pattern A: first iteration with config tuple/list.
                        # Accept both tuple (in-memory) and list (from JSON
                        # deserialisation of the .hbc const pool).
                        self.stack.pop()
                        var1 = top[1]
                        var2 = top[2]
                        iterable = self.stack.pop()
                        self._for_iter_first(iterable, var1, var2, jump_target)
                    elif isinstance(top, (int, float)) and len(self.stack) >= 2:
                        # Pattern B (legacy): pop sentinel, get iterable from below
                        self.stack.pop()
                        iterable = self.stack.pop()
                        self._for_iter_first(iterable, var1, var2, jump_target)
                    else:
                        # Pattern C: just iterable on stack
                        iterable = self.stack.pop()
                        self._for_iter_first(iterable, var1, var2, jump_target)
                elif opname == 'UNARY_NOT':
                    a = self.stack.pop()
                    if not isinstance(a, bool):
                        raise BytecodeRuntimeError("'not' operand must be boolean")
                    self.stack.append(not a)
                elif opname == 'COMPARE_OP':
                    op = arg
                    b = self.stack.pop(); a = self.stack.pop()
                    if op == 'EQEQ':
                        self.stack.append(a == b)
                    elif op == 'BANGEQ':
                        self.stack.append(a != b)
                    elif op == 'GT':
                        self.stack.append(a > b)
                    elif op == 'LT':
                        self.stack.append(a < b)
                    elif op == 'GTE':
                        self.stack.append(a >= b)
                    elif op == 'LTE':
                        self.stack.append(a <= b)
                    elif op == 'IN':
                        # `a in b`: membership (list/dict) or substring (str).
                        # Mirrors the tree interpreter's visit_BinaryOp IN handling.
                        if isinstance(b, (list, dict)):
                            self.stack.append(a in b)
                        elif isinstance(b, str):
                            if not isinstance(a, str):
                                raise BytecodeRuntimeError(
                                    "'in' operator with string requires string left operand")
                            self.stack.append(a in b)
                        else:
                            raise BytecodeRuntimeError(
                                "'in' operator requires list, dict, or string on right side")
                    else:
                        raise BytecodeRuntimeError(f'Unknown compare op {op}')
                elif opname == 'JUMP_IF_FALSE':
                    target = arg
                    cond = self.stack.pop()
                    if not cond:
                        self.pc = target
                elif opname == 'JUMP':
                    self.pc = arg
                elif opname == 'SETUP_EXCEPT':
                    self._exception_handlers.append((arg, len(self.stack)))
                elif opname == 'POP_EXCEPT':
                    if self._exception_handlers:
                        self._exception_handlers.pop()
                elif opname == 'RAISE':
                    exc = self.stack.pop()
                    raise HSharpException(exc)
                elif opname == 'CALL_FUNCTION':
                    name, argc = arg
                    args = [self.stack.pop() for _ in range(argc)][::-1]
                    # builtins
                    if name in self.builtins:
                        res = self.builtins[name](args)
                        self.stack.append(res)
                    else:
                        func = self._lookup_name(name)
                        if isinstance(func, dict) and 'args' in func and 'bytecode' in func:
                            fargs = func.get('args', [])
                            is_variadic = func.get('is_variadic', False)
                            if is_variadic:
                                # `fn f(...args)` or `fn f(a, b, ...rest)`:
                                # the last param collects trailing args.
                                nfixed = len(fargs) - 1
                                if len(args) < nfixed:
                                    raise BytecodeRuntimeError(
                                        f"Function {name} expects at least {nfixed} args, got {len(args)}")
                            else:
                                args = self._apply_defaults(func, args, name)
                            bc = {'instructions': func['bytecode'], 'consts': func.get('consts', [])}
                            vm2 = VM(bc)
                            vm2.local_names = set(func.get('local_names', []))
                            vm2.parent = func.get('__closure__') or self
                            vm2.freevars = set(func.get('freevars', []))
                            if is_variadic:
                                for i in range(nfixed):
                                    vm2.env[fargs[i]] = args[i]
                                vm2.env[fargs[-1]] = list(args[nfixed:])
                            else:
                                for pname, pval in zip(fargs, args):
                                    vm2.env[pname] = pval
                            vm2.functions = self.functions
                            res = vm2.run()
                            self.stack.append(res)
                        else:
                            raise BytecodeRuntimeError(f'Unknown function: {name}')
                elif opname == 'RETURN_VALUE':
                    if self.stack:
                        return self.stack.pop()
                    return None
                elif opname == 'CALL_METHOD':
                    name, argc = arg
                    args = [self.stack.pop() for _ in range(argc)][::-1]
                    inst = self.stack.pop()
                    # === inline cache 快路径：实例方法调用 ===
                    if isinstance(inst, dict) and '__class__' in inst:
                        entry = self._method_cache.get(self.pc - 1)
                        if entry is not None:
                            cid, methods_ref = entry
                            if id(inst['__class__']) == cid and name in methods_ref:
                                method = methods_ref[name]
                                fargs = method.get('args', [])
                                if len(fargs) == len(args):
                                    bc = {'instructions': method['bytecode'], 'consts': method.get('consts', [])}
                                    vm2 = VM(bc)
                                    vm2.local_names = set(method.get('local_names', []))
                                    vm2.env['self'] = inst
                                    vm2.env['this'] = inst
                                    vm2.parent = self
                                    vm2._method_owner = inst['__class__']
                                    for pname, pval in zip(fargs, args):
                                        vm2.env[pname] = pval
                                    vm2.functions = self.functions
                                    res = vm2.run()
                                    self.stack.append(res)
                                    self._cache_hits += 1
                                    continue
                            self._cache_misses += 1
                    # Special-case: module proxy (dict) attribute call
                    if isinstance(inst, dict) and '__class__' not in inst:
                        # module-like dict or class object (for static methods)
                        # direct attribute (python proxy) call
                        if name in inst:
                            val = inst[name]
                            if callable(val):
                                try:
                                    res = val(*args)
                                    self.stack.append(res)
                                    continue
                                except Exception as e:
                                    raise BytecodeRuntimeError(f"Error calling external function '{name}': {e}")
                            # user-defined function stored as dict (static method on class)
                            if isinstance(val, dict) and 'bytecode' in val:
                                func = val
                                fargs = func.get('args', [])
                                if len(fargs) != len(args):
                                    raise BytecodeRuntimeError(f"Method {name} expects {len(fargs)} args")
                                bc = {'instructions': func['bytecode'], 'consts': func.get('consts', [])}
                                vm2 = VM(bc)
                                vm2.local_names = set(func.get('local_names', []))
                                for pname, pval in zip(fargs, args):
                                    vm2.env[pname] = pval
                                vm2.functions = self.functions
                                res = vm2.run()
                                self.stack.append(res)
                                continue
                            else:
                                raise BytecodeRuntimeError(f"Attribute '{name}' on module is not callable")
                        # support static methods stored under special container
                        static_map = inst.get('__static__') if isinstance(inst, dict) else None
                        if static_map and name in static_map:
                            func = static_map[name]
                            fargs = func.get('args', [])
                            if len(fargs) != len(args):
                                raise BytecodeRuntimeError(f"Method {name} expects {len(fargs)} args")
                            bc = {'instructions': func['bytecode'], 'consts': func.get('consts', [])}
                            vm2 = VM(bc)
                            vm2.local_names = set(func.get('local_names', []))
                            for pname, pval in zip(fargs, args):
                                vm2.env[pname] = pval
                            vm2.functions = self.functions
                            res = vm2.run()
                            self.stack.append(res)
                            continue
                        raise BytecodeRuntimeError(f"Attribute '{name}' not found on module/class")
                    # If inst is a real Python module/object with attribute, try to call it
                    if not isinstance(inst, dict) or '__class__' not in inst:
                        if not isinstance(inst, dict) and hasattr(inst, name):
                            val = getattr(inst, name)
                            if callable(val):
                                try:
                                    res = val(*args)
                                    self.stack.append(res)
                                    continue
                                except Exception as e:
                                    raise BytecodeRuntimeError(f"Error calling external attribute '{name}': {e}")
                            else:
                                raise BytecodeRuntimeError(f"Attribute '{name}' on object is not callable")
                        raise BytecodeRuntimeError(f"CALL_METHOD on non-instance (inst={type(inst).__name__} {str(inst)[:80]})")
                    class_obj = inst['__class__']
                    methods = class_obj.get('methods', {})
                    if name not in methods:
                        raise BytecodeRuntimeError(f"Method '{name}' not found on class")
                    # 填充 inline cache
                    self._method_cache[self.pc - 1] = (id(class_obj), methods)
                    method = methods[name]
                    fargs = method.get('args', [])
                    if len(fargs) != len(args):
                        raise BytecodeRuntimeError(f"Method {name} expects {len(args)} args")
                    bc = {'instructions': method['bytecode'], 'consts': method.get('consts', [])}
                    vm2 = VM(bc)
                    vm2.local_names = set(method.get('local_names', []))
                    # set parameters and self
                    vm2.env['self'] = inst
                    vm2.env['this'] = inst
                    vm2.parent = self
                    vm2._method_owner = class_obj
                    for pname, pval in zip(fargs, args):
                        vm2.env[pname] = pval
                    vm2.functions = self.functions
                    res = vm2.run()
                    self.stack.append(res)
                elif opname == 'CALL_SUPER':
                    name, argc = arg
                    args = [self.stack.pop() for _ in range(argc)][::-1]
                    # Get self from environment
                    inst = self.env.get('self')
                    if inst is None:
                        raise BytecodeRuntimeError("super() can only be called within a method")
                    
                    if not isinstance(inst, dict) or '__class__' not in inst:
                        raise BytecodeRuntimeError("super() can only be called within a class method")
                    
                    class_obj = inst['__class__']
                    # The *active* method's owning class.  For a normal method
                    # call this is the leaf instance class; for a `super` call
                    # it is the parent class whose method we just entered.  Using
                    # the instance's (always-leaf) class as the caller would make
                    # a 3-level chain (C extends B extends A) loop C -> B -> C ...
                    caller_class = self._method_owner if self._method_owner is not None else class_obj
                    # Build the linearised MRO (child -> ... -> root) by
                    # following `base` pointers.  The merged class only stores
                    # the *immediate* parent, so we walk up the chain.
                    mro = []
                    cur = class_obj
                    seen = set()
                    while isinstance(cur, dict):
                        nm = cur.get('name')
                        if nm in seen:
                            break
                        seen.add(nm)
                        mro.append(cur)
                        bn = cur.get('base')
                        if not bn:
                            break
                        nxt = self._lookup_class(bn)
                        if not isinstance(nxt, dict):
                            break
                        cur = nxt

                    # Resolve `super` relative to the *active* method's owning
                    # class, advancing to the next ancestor in the MRO.
                    caller_name = caller_class.get('name')
                    idx = mro_names(mro).index(caller_name) if caller_name in mro_names(mro) else 0
                    # Skip the caller and resolve to the class *after* it in
                    # the MRO (the immediate parent's method, or the nearest
                    # ancestor that defines `name`).
                    target = None
                    for j in range(idx + 1, len(mro)):
                        if name in mro[j].get('methods', {}):
                            target = mro[j]
                            break
                    if target is None:
                        raise BytecodeRuntimeError(f"Method '{name}' not found in any base class of '{caller_name}'")

                    method = target['methods'][name]
                    fargs = method.get('args', [])
                    if len(fargs) != len(args):
                        raise BytecodeRuntimeError(f"Method {name} expects {len(args)} args")

                    bc = {'instructions': method['bytecode'], 'consts': method.get('consts', [])}
                    vm2 = VM(bc)
                    vm2.local_names = set(method.get('local_names', []))
                    vm2.env['self'] = inst
                    vm2.env['this'] = inst
                    vm2.parent = self
                    vm2._method_owner = target
                    for pname, pval in zip(fargs, args):
                        vm2.env[pname] = pval
                    vm2.functions = self.functions
                    res = vm2.run()
                    self.stack.append(res)
                elif opname == 'CALL_VALUE':
                    argc = arg
                    args = [self.stack.pop() for _ in range(argc)][::-1]
                    func = self.stack.pop()
                    # Python callable
                    if callable(func):
                        try:
                            res = func(*args)
                            self.stack.append(res)
                            continue
                        except Exception as e:
                            raise BytecodeRuntimeError(f"Error calling external function: {e}")
                    # compiled H# function object
                    if isinstance(func, dict) and 'bytecode' in func:
                        fargs = func.get('args', [])
                        if len(fargs) != len(args):
                            raise BytecodeRuntimeError(f"Function expects {len(fargs)} args")
                        bc = {'instructions': func['bytecode'], 'consts': func.get('consts', [])}
                        vm2 = VM(bc)
                        vm2.local_names = set(func.get('local_names', []))
                        vm2.parent = func.get('__closure__') or self
                        vm2.freevars = set(func.get('freevars', []))
                        for pname, pval in zip(fargs, args):
                            vm2.env[pname] = pval
                        vm2.functions = self.functions
                        res = vm2.run()
                        self.stack.append(res)
                        continue
                    raise BytecodeRuntimeError('CALL_VALUE on non-callable')
                elif opname == 'INSTANCEOF':
                    type_name = arg
                    obj = self.stack.pop()
                    if not isinstance(obj, dict) or '__class__' not in obj:
                        self.stack.append(False)
                        continue
                    
                    class_obj = obj['__class__']
                    
                    def is_instance(class_obj, type_name):
                        if class_obj.get('name') == type_name:
                            return True
                        # Check base class
                        base_name = class_obj.get('base')
                        if base_name:
                            base = self.env.get(base_name) or self.functions.get(base_name)
                            if base and is_instance(base, type_name):
                                return True
                        # Check interfaces
                        interfaces = class_obj.get('implements', [])
                        if type_name in interfaces:
                            return True
                        return False
                    
                    result = is_instance(class_obj, type_name)
                    self.stack.append(result)
                elif opname == 'CALL_NEW':
                    argc = arg
                    args = [self.stack.pop() for _ in range(argc)][::-1]
                    class_obj = self.stack.pop()
                    if not isinstance(class_obj, dict) or 'methods' not in class_obj:
                        raise BytecodeRuntimeError('CALL_NEW on non-class object')
                    # resolve inheritance chain by merging base classes
                    def resolve_class(cobj):
                        if not isinstance(cobj, dict):
                            return cobj
                        if cobj.get('_is_merged'):
                            # Already-resolved composite: its `base` points at
                            # the *original* ancestor, so re-resolving would
                            # skip an intermediate class and can cycle.  Use it
                            # as-is; its `methods`/`fields` already encode the
                            # full linearised MRO (child overlaid on parent).
                            return cobj
                        base_name = cobj.get('base')
                        if not base_name:
                            return cobj
                        base = self._lookup_class(base_name)
                        if not base:
                            raise BytecodeRuntimeError(f'Base class {base_name} not found')
                        base_resolved = resolve_class(base)
                        merged = {'name': cobj.get('name'), 'base': cobj.get('base'),
                                  'implements': cobj.get('implements', []),
                                  '_is_merged': True,
                                  'methods': {}, 'fields': {}, 'private': []}
                        merged['methods'].update(base_resolved.get('methods', {}))
                        merged['fields'].update(base_resolved.get('fields', {}))
                        merged['private'].extend(base_resolved.get('private', []))
                        # then overlay child
                        merged['methods'].update(cobj.get('methods', {}))
                        merged['fields'].update(cobj.get('fields', {}))
                        merged['private'].extend(cobj.get('private', []))
                        return merged

                    resolved = resolve_class(class_obj)
                    inst = self._acquire_instance_dict()
                    inst['__class__'] = resolved
                    # copy default fields
                    for k, v in resolved.get('fields', {}).items():
                        inst[k] = copy.deepcopy(v)
                    # call constructor if present — but only auto-invoke
                    # it when the supplied arg count matches the
                    # constructor's effective parameter count (excluding
                    # `self`).  This preserves backward compatibility with
                    # the old convention
                    #     `let p = new Point(); p.init(3, 4);`
                    # where `new Point()` should NOT invoke the
                    # constructor, while still supporting the new
                    #     `let p = new Point(3, 4);`
                    # convention.  Both `fn init(...)` and
                    # `fn __init__(...)` are recognised as constructors.
                    methods = resolved.get('methods', {})
                    method = methods.get('__init__') or methods.get('init')
                    if method is not None:
                        fargs = method.get('args', [])
                        # `self` is supplied by the VM, not the caller;
                        # drop it from the arity check and positional
                        # binding (mirrors HVM.kt invokeHFunction).
                        if fargs and fargs[0] == 'self':
                            eff_args = fargs[1:]
                        else:
                            eff_args = fargs
                        if len(eff_args) == len(args):
                            bc = {'instructions': method['bytecode'], 'consts': method.get('consts', [])}
                            vm2 = VM(bc)
                            vm2.local_names = set(method.get('local_names', []))
                            vm2.parent = self
                            vm2.env['self'] = inst
                            vm2.env['this'] = inst
                            for pname, pval in zip(eff_args, args):
                                vm2.env[pname] = pval
                            vm2.functions = self.functions
                            vm2.run()
                    self.stack.append(inst)
                elif opname == 'UNION_MAKE':
                    argc = arg
                    values = [self.stack.pop() for _ in range(argc)][::-1]
                    variant_name = self.stack.pop()
                    union_type = self.stack.pop()
                    if not isinstance(union_type, dict) or union_type.get('__type__') != 'union':
                        raise BytecodeRuntimeError('UNION_MAKE on non-union type')
                    # find the variant
                    variant = None
                    for v in union_type.get('variants', []):
                        if v['name'] == variant_name:
                            variant = v
                            break
                    if variant is None:
                        raise BytecodeRuntimeError(f'Unknown variant {variant_name} for union {union_type["name"]}')
                    if len(values) != len(variant['fields']):
                        raise BytecodeRuntimeError(f'Variant {variant_name} expects {len(variant["fields"])} fields, got {len(values)}')
                    inst = self._acquire_instance_dict()
                    inst['__union__'] = union_type['name']
                    inst['__variant__'] = variant_name
                    for i, fname in enumerate(variant['fields']):
                        inst[fname] = values[i]
                    self.stack.append(inst)
                elif opname == 'HALT':
                    return None
                elif opname == 'IMPORT_NAME':
                    modname = arg
                    try:
                        import importlib
                        mod = importlib.import_module(modname)
                    except Exception as e:
                        raise BytecodeRuntimeError(f"Failed to import Python module '{modname}': {e}")
                    proxy = {}
                    for attr in dir(mod):
                        if attr.startswith('_'):
                            continue
                        try:
                            val = getattr(mod, attr)
                        except Exception:
                            continue
                        proxy[attr] = val
                    self.env[modname] = proxy
                elif opname == 'IMPORT_FILE':
                    # Import a local H# file at runtime by compiling it to
                    # bytecode and running it in a sub-VM that *shares this
                    # frame's env*, so the module's top-level fn/class/let
                    # bindings (compiled to MAKE_CLOSURE/STORE_NAME) land in the
                    # importer's env — the same visibility the tree interpreter
                    # gives `import "file.hto"`.  The previous implementation
                    # used a throwaway tree Interpreter with a fresh env and a
                    # fresh functions dict, so imported names never reached the
                    # VM (e.g. `tokenize` after `import "bootstrap/tokenize.hto"`).
                    path = arg
                    # mirror the tree interpreter: a bare module path gets a
                    # `.hto` suffix appended (e.g. import "bootstrap/math_extended")
                    if not path.endswith('.hto'):
                        path += '.hto'
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            code = f.read()
                    except Exception:
                        # fall back to resolving against HSHARP_PATH entries
                        import os as _os
                        _resolved = None
                        for _p in _os.environ.get('HSHARP_PATH', '').split(_os.pathsep):
                            if _p and _os.path.exists(_os.path.join(_p, path)):
                                _resolved = _os.path.join(_p, path)
                                break
                        if _resolved is None:
                            raise BytecodeRuntimeError(f"Failed to read import file '{path}'")
                        with open(_resolved, 'r', encoding='utf-8') as f:
                            code = f.read()
                    try:
                        from lexer import Lexer
                        from parser import Parser
                        from compiler import Compiler
                        lexer = Lexer(code)
                        parser = Parser(lexer)
                        program = parser.parse()
                        comp = Compiler(use_hcompiler=True)
                        bc = comp.compile(program)
                        vm2 = VM(bc)
                        vm2.env = self.env
                        vm2.functions = self.functions
                        vm2.builtins = self.builtins
                        vm2.parent = self
                        vm2.run()
                    except Exception as e:
                        raise BytecodeRuntimeError(f"Error importing H# file '{path}': {e}")
                else:
                    raise BytecodeRuntimeError(f'Unknown opcode: {opname}')
            except HSharpException as exc:
                handler_found = False
                # unwind handlers until we find a valid handler target
                while self._exception_handlers:
                    target, stack_height = self._exception_handlers.pop()
                    if target is None:
                        continue
                    # restore stack to saved height and push exception value
                    self.stack = self.stack[:stack_height]
                    self.stack.append(exc.value)
                    self.pc = target
                    handler_found = True
                    break
                if not handler_found:
                    # no local handler; propagate to caller VM or host
                    raise
            except BytecodeRuntimeError as exc:
                # Turn runtime errors (arity mismatch, unknown opcode,
                # type errors, etc.) into catchable H# exceptions so
                # user `try/catch` can handle them.
                handler_found = False
                while self._exception_handlers:
                    target, stack_height = self._exception_handlers.pop()
                    if target is None:
                        continue
                    self.stack = self.stack[:stack_height]
                    self.stack.append(str(exc))
                    self.pc = target
                    handler_found = True
                    break
                if not handler_found:
                    raise
            except (IndexError, KeyError, TypeError, ZeroDivisionError, ValueError, AttributeError) as exc:
                # Python built-in errors raised by host operations on
                # lists/dicts/strings should be catchable from H#.
                handler_found = False
                while self._exception_handlers:
                    target, stack_height = self._exception_handlers.pop()
                    if target is None:
                        continue
                    self.stack = self.stack[:stack_height]
                    self.stack.append(str(exc))
                    self.pc = target
                    handler_found = True
                    break
                if not handler_found:
                    raise BytecodeRuntimeError(str(exc))

        return None

    def _builtin_thread_spawn(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError('thread_spawn(func) takes exactly 1 argument')
        fn = args[0]
        import threading

        def target_callable():
            try:
                if isinstance(fn, dict) and 'bytecode' in fn:
                    vm = VM({'instructions': fn['bytecode'], 'consts': fn.get('consts', [])})
                    vm.run()
                elif callable(fn):
                    fn()
                else:
                    raise BytecodeRuntimeError('Unsupported callable passed to thread_spawn')
            except Exception as e:
                sys.__stderr__.write(f"Thread error: {e}\n")

        t = threading.Thread(target=target_callable)
        t.start()
        return t

    def _builtin_thread_join(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError('thread_join(t) takes exactly 1 argument')
        t = args[0]
        try:
            t.join()
            return None
        except Exception as e:
            raise BytecodeRuntimeError(f'Error joining thread: {e}')

    # ── Channel builtins (mirror interpreter.builtin_chan_*; raise
    #    BytecodeRuntimeError so user `try/catch` in --opt mode can catch) ──
    def _b_input(self, args):
        if len(args) > 1:
            raise BytecodeRuntimeError("input() takes at most 1 argument")
        try:
            if args:
                prompt = args[0]
                if not isinstance(prompt, str):
                    raise BytecodeRuntimeError("input() argument must be a string")
                return input(prompt)
            else:
                return input()
        except EOFError:
            # Mirror the tree interpreter: EOF on the input stream yields
            # H#'s `nullptr` (Python None) so read-until-EOF loops terminate.
            return None

    def _b_dict_has(self, args):
        if len(args) != 2:
            raise BytecodeRuntimeError("dict_has(dict, key) takes exactly 2 arguments")
        d = args[0]
        if not isinstance(d, dict):
            raise BytecodeRuntimeError("First argument must be a dictionary")
        return args[1] in d

    def _b_dict_get(self, args):
        if len(args) < 2:
            raise BytecodeRuntimeError("dict_get(dict, key[, default]) requires at least 2 arguments")
        d = args[0]
        if not isinstance(d, dict):
            raise BytecodeRuntimeError("First argument must be a dictionary")
        key = args[1]
        if key in d:
            return d[key]
        if len(args) >= 3:
            return args[2]
        return None

    def _b_dict_keys(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("dict_keys(dict) takes 1 argument")
        d = args[0]
        if not isinstance(d, dict):
            raise BytecodeRuntimeError("First argument must be a dictionary")
        return list(d.keys())

    def _b_dict_values(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("dict_values(dict) takes 1 argument")
        d = args[0]
        if not isinstance(d, dict):
            raise BytecodeRuntimeError("First argument must be a dictionary")
        return list(d.values())

    def _b_dict_items(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("dict_items(dict) takes 1 argument")
        d = args[0]
        if not isinstance(d, dict):
            raise BytecodeRuntimeError("First argument must be a dictionary")
        return list(d.items())

    def _b_substring(self, args):
        # substring(string, start, length) — mirrors host_functions.builtin_substring
        if len(args) < 3:
            raise BytecodeRuntimeError("substring requires 3 arguments")
        s = str(args[0])
        start = int(args[1])
        length = int(args[2])
        return s[start:start + length]

    def _b_ord(self, args):
        if len(args) < 1:
            raise BytecodeRuntimeError("ord requires 1 argument")
        ch = str(args[0])
        return ord(ch[0]) if len(ch) > 0 else 0

    def _b_chr(self, args):
        if len(args) < 1:
            raise BytecodeRuntimeError("chr requires 1 argument")
        return chr(int(args[0]))

    def _b_time_now(self, args):
        return int(time.time() * 1000)

    def _b_datetime_now(self, args):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _b_type(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("type() takes exactly 1 argument")
        v = args[0]
        if isinstance(v, dict):
            if v.get('__htype__') is not None:
                return str(v.get('__htype__'))
            if '__class__' in v:
                cls = v['__class__']
                if isinstance(cls, dict):
                    return str(cls.get('name', 'object'))
                return 'object'
            if 'methods' in v:
                return str(v.get('name', 'class'))
            return 'dict'
        if isinstance(v, list):
            return 'list'
        if isinstance(v, str):
            return 'string'
        if isinstance(v, bool):
            return 'bool'
        if isinstance(v, int):
            return 'number'
        if isinstance(v, float):
            return 'number'
        if v is None:
            return 'nullptr'
        if callable(v):
            return 'function'
        return type(v).__name__

    def _b_chan_new(self, args):
        import threading
        cap = int(args[0]) if args else 0
        return {'__htype__': 'channel', 'capacity': cap, 'items': [],
                'closed': False, 'cond': threading.Condition()}

    def _b_chan_send(self, args):
        import threading, time
        if len(args) != 2:
            raise BytecodeRuntimeError("chan_send(ch, value) takes exactly 2 arguments")
        ch, v = args[0], args[1]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_send: first argument must be a channel")
        cond = ch['cond']
        cap = ch.get('capacity', 0)
        with cond:
            if cap:
                deadline = time.time() + 30.0
                while len(ch['items']) >= cap:
                    if ch.get('closed'):
                        raise BytecodeRuntimeError("chan_send on closed channel")
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise BytecodeRuntimeError(
                            "chan_send timed out (channel full, no receiver)")
                    cond.wait(remaining)
            if ch.get('closed'):
                raise BytecodeRuntimeError("chan_send on closed channel")
            ch['items'].append(v)
            cond.notify_all()
        return None

    def _b_chan_recv(self, args):
        import threading, time
        if len(args) != 1:
            raise BytecodeRuntimeError("chan_recv(ch) takes exactly 1 argument")
        ch = args[0]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_recv: argument must be a channel")
        cond = ch['cond']
        with cond:
            deadline = time.time() + 30.0
            while len(ch['items']) == 0:
                if ch.get('closed'):
                    raise BytecodeRuntimeError("chan_recv on closed and empty channel")
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise BytecodeRuntimeError(
                        "chan_recv timed out (channel empty, no sender)")
                cond.wait(remaining)
            v = ch['items'].pop(0)
            cond.notify_all()
            return v

    def _b_chan_close(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("chan_close(ch) takes exactly 1 argument")
        ch = args[0]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_close: argument must be a channel")
        # Idempotent: closing an already-closed channel is a no-op (does not raise).
        ch['closed'] = True
        # Wake any sender/recv blocked on this channel so they raise the proper
        # "closed" error immediately instead of waiting out the timeout.
        with ch['cond']:
            ch['cond'].notify_all()
        return None

    def _b_chan_size(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("chan_size(ch) takes exactly 1 argument")
        ch = args[0]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_size: argument must be a channel")
        return len(ch['items'])

    def _b_chan_try_send(self, args):
        if len(args) != 2:
            raise BytecodeRuntimeError("chan_try_send(ch, value) takes exactly 2 arguments")
        ch, v = args[0], args[1]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_try_send: first argument must be a channel")
        if ch.get('closed'):
            raise BytecodeRuntimeError("chan_try_send on closed channel")
        cap = ch.get('capacity', 0)
        if cap and len(ch['items']) >= cap:
            return False
        ch['items'].append(v)
        return True

    def _b_chan_try_recv(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("chan_try_recv(ch) takes exactly 1 argument")
        ch = args[0]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_try_recv: argument must be a channel")
        if len(ch['items']) > 0:
            return ch['items'].pop(0)
        return None

    def _b_time_ms(self, args):
        import time
        return int(time.time() * 1000)

    def _b_parallelism(self, args):
        import os
        return int(os.cpu_count() or 4)

    def _b_dzzw_worker_count(self, args):
        import os
        return int(os.cpu_count() or 4)

    def _for_iter_first(self, iterable, var1, var2, jump_target):
        """Handle the first iteration of a for-in loop."""
        if isinstance(iterable, (list, tuple)):
            it = {'__iter_idx': 0, '__iterable': iterable, '__var1': var1, '__var2': var2, '__is_iter': True}
            self.stack.append(it)
            if 0 < len(iterable):
                self._set_local(var1, iterable[0])
                it['__iter_idx'] = 1
            else:
                self.stack.pop()
                self.pc = jump_target
        elif isinstance(iterable, dict):
            keys = list(iterable.keys())
            if var2 is not None:
                it = {'__iter_idx': 0, '__iterable': keys, '__var1': var1, '__var2': var2, '__dict': iterable, '__is_iter': True}
                self.stack.append(it)
                if 0 < len(keys):
                    self._set_local(var1, keys[0])
                    self._set_local(var2, iterable[keys[0]])
                    it['__iter_idx'] = 1
                else:
                    self.stack.pop()
                    self.pc = jump_target
            else:
                it = {'__iter_idx': 0, '__iterable': keys, '__var1': var1, '__var2': var2, '__is_iter': True}
                self.stack.append(it)
                if 0 < len(keys):
                    self._set_local(var1, keys[0])
                    it['__iter_idx'] = 1
                else:
                    self.stack.pop()
                    self.pc = jump_target
        elif isinstance(iterable, str):
            # Iterate a string character by character (matches the tree
            # interpreter's `for c in "abc"` semantics).
            chars = list(iterable)
            it = {'__iter_idx': 0, '__iterable': chars, '__var1': var1,
                  '__var2': var2, '__is_iter': True}
            self.stack.append(it)
            if 0 < len(chars):
                self._set_local(var1, chars[0])
                it['__iter_idx'] = 1
            else:
                self.stack.pop()
                self.pc = jump_target
        else:
            raise BytecodeRuntimeError(f"Cannot iterate over {type(iterable).__name__}")

    def _set_local(self, name, val):
        """Write a named local, respecting fast-slot allocation.

        The register allocator rewrites LOAD_NAME/STORE_NAME for fast-eligible
        locals into LOAD_FAST/STORE_FAST (indexed slots), but opcodes that bind
        a name by string — chiefly FOR_ITER for loop variables — must still
        honour that allocation, otherwise a later LOAD_FAST reads a stale None.
        """
        idx = self._fast_name_to_idx.get(name)
        if idx is not None and 0 <= idx < len(self.fast_slots):
            self.fast_slots[idx] = val
        else:
            # Instance-field bare-name assignment (mirrors the tree
            # interpreter's InstanceScope): a bare assignment to a name that
            # is a field of `self` (and was NOT declared as a local `let` in
            # this method) writes to the instance, not a method-local.
            if name not in self.local_names:
                _self = self.env.get('self')
                if isinstance(_self, dict) and name in _self:
                    _self[name] = val
                    return
            self.env[name] = val

    def _lookup_class(self, name):
        """Resolve a class name for inheritance (`extends` / `super`).

        Class objects bound at top level are register-allocated into fast
        slots by FastLocalAllocator, so a plain `env.get(name)` misses them.
        Walk the same chain as `_lookup_name` (env -> fast slots -> functions
        -> parent), but return None instead of raising so callers can emit a
        precise "Base class '<x>' not found" diagnostic.
        """
        node = self
        while node is not None:
            if name in node.env:
                return node.env[name]
            idx = node._fast_name_to_idx.get(name)
            if idx is not None and 0 <= idx < len(node.fast_slots):
                val = node.fast_slots[idx]
                if val is not None:
                    return val
            if name in node.functions:
                return node.functions[name]
            node = node.parent
        return None

    def _lookup_name(self, name):
        # search local env, then fast slots, then functions, then parent
        # chain, then builtins.  Fast slots are populated by the register
        # allocator (FastLocalAllocator) for the *current* frame's locals,
        # so name resolution must consult them too: a CALL_FUNCTION whose
        # callee is a fast-allocated top-level function, or a closure
        # capturing a fast-allocated variable from an enclosing frame.
        node = self
        while node is not None:
            if name in node.env:
                return node.env[name]
            idx = node._fast_name_to_idx.get(name)
            if idx is not None and 0 <= idx < len(node.fast_slots):
                return node.fast_slots[idx]
            if name in node.functions:
                return node.functions[name]
            node = node.parent
        # Instance-field bare-name resolution (mirrors InstanceScope): inside
        # a method, an unresolved bare name that is a field of `self` resolves
        # to `self.<name>` — unless it was declared as a local `let` (tracked
        # via func['local_names']).
        if name not in self.local_names:
            _self = self.env.get('self')
            if isinstance(_self, dict) and name in _self:
                return _self[name]
        if name in self.builtins:
            return self.builtins[name]
        raise BytecodeRuntimeError(f"Undefined name: {name}")

    def _apply_defaults(self, func, args, name):
        """Fill missing trailing args from func['defaults'].

        `func` is the dict form of an H# function object.  `defaults`
        is aligned with the *tail* of `args` (Python convention)."""
        fargs = func.get('args', [])
        defaults = func.get('defaults', [])
        n_def = len(defaults)
        if not n_def:
            if len(args) != len(fargs):
                raise BytecodeRuntimeError(
                    f"Function {name} expects {len(fargs)} args, got {len(args)}")
            return args
        min_args = len(fargs) - n_def
        if len(args) == len(fargs):
            return args
        if min_args <= len(args) < len(fargs):
            skip = len(args) - min_args
            return list(args) + list(defaults[skip:])
        raise BytecodeRuntimeError(
            f"Function {name} expects {len(fargs)} args (min {min_args}), got {len(args)}")


def mro_names(mro):
    """Class-name list for an MRO (list of class dicts), in chain order."""
    return [c.get('name') for c in mro if isinstance(c, dict)]