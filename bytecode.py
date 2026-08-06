import sys
import copy
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
        self.builtins = {
            'len': lambda args: len(args[0]) if len(args)==1 else (_ for _ in ()).throw(BytecodeRuntimeError('len() takes 1 arg')),
            'push': lambda args: (args[0].append(args[1]) or None),
            'pop': lambda args: args[0].pop(),
            'read_file': lambda args: open(args[0], 'r', encoding='utf-8').read(),
            'write_file': lambda args: (open(args[0], 'w', encoding='utf-8').write(args[1]) or None),
            'thread_spawn': self._builtin_thread_spawn,
            'thread_join': self._builtin_thread_join,
            'str': lambda args: str(args[0]),
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
            'min': lambda args: min(args[0]),
            'max': lambda args: max(args[0]),
            'range': lambda args: list(range(args[0])) if len(args) == 1 else list(range(args[0], args[1])),
            'keys': lambda args: list(args[0].keys()),
            'values': lambda args: list(args[0].values()),
            'items': lambda args: list(args[0].items()),
            'has_key': lambda args: args[0] in args[1] if len(args)==2 else False,
        }
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
                    self.stack.append(a // b)
                elif opname == 'BINARY_MOD':
                    b = self.stack.pop(); a = self.stack.pop();
                    if b == 0:
                        raise BytecodeRuntimeError('modulo by zero')
                    self.stack.append(a % b)
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
                                    vm2.env['self'] = inst
                                    vm2.parent = self
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
                    # set parameters and self
                    vm2.env['self'] = inst
                    vm2.parent = self
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
                    base_name = class_obj.get('base')
                    if not base_name:
                        raise BytecodeRuntimeError(f"Class '{class_obj.get('name', 'Unknown')}' has no parent class")
                    
                    # Get base class
                    base = self.env.get(base_name) or self.functions.get(base_name)
                    if not base:
                        raise BytecodeRuntimeError(f"Base class '{base_name}' not found")
                    
                    if not isinstance(base, dict) or 'methods' not in base:
                        raise BytecodeRuntimeError(f"'{base_name}' is not a valid class")
                    
                    # Get method from base class
                    methods = base.get('methods', {})
                    if name not in methods:
                        raise BytecodeRuntimeError(f"Method '{name}' not found in base class '{base_name}'")
                    
                    method = methods[name]
                    fargs = method.get('args', [])
                    if len(fargs) != len(args):
                        raise BytecodeRuntimeError(f"Method {name} expects {len(args)} args")
                    
                    bc = {'instructions': method['bytecode'], 'consts': method.get('consts', [])}
                    vm2 = VM(bc)
                    vm2.env['self'] = inst
                    vm2.parent = self
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
                        base_name = cobj.get('base')
                        if not base_name:
                            return cobj
                        base = self.env.get(base_name) or self.functions.get(base_name)
                        if not base:
                            raise BytecodeRuntimeError(f'Base class {base_name} not found')
                        base_resolved = resolve_class(base)
                        merged = {'name': cobj.get('name'), 'methods': {}, 'fields': {}, 'private': []}
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
                            vm2.parent = self
                            vm2.env['self'] = inst
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
                    # import a local H# file at runtime: parse and interpret in the current environment
                    path = arg
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            code = f.read()
                    except Exception as e:
                        raise BytecodeRuntimeError(f"Failed to read import file '{path}': {e}")
                    try:
                        from lexer import Lexer
                        from parser import Parser
                        from interpreter import Interpreter
                        lexer = Lexer(code)
                        parser = Parser(lexer)
                        program = parser.parse()
                        interp = Interpreter(global_env=None, functions=self.functions)
                        # interpret into a fresh interpreter but share top-level env with this VM
                        interp.interpret(program, env=None)
                        # merge interfaces if present
                        if hasattr(interp, 'interfaces'):
                            # store into this VM as needed (not used heavily in bytecode VM)
                            pass
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
        cap = int(args[0]) if args else 0
        return {'__htype__': 'channel', 'capacity': cap, 'items': [], 'closed': False}

    def _b_chan_send(self, args):
        if len(args) != 2:
            raise BytecodeRuntimeError("chan_send(ch, value) takes exactly 2 arguments")
        ch, v = args[0], args[1]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_send: first argument must be a channel")
        if ch.get('closed'):
            raise BytecodeRuntimeError("chan_send on closed channel")
        cap = ch.get('capacity', 0)
        if cap and len(ch['items']) >= cap:
            raise BytecodeRuntimeError("chan_send on full bounded channel (would block)")
        ch['items'].append(v)
        return None

    def _b_chan_recv(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("chan_recv(ch) takes exactly 1 argument")
        ch = args[0]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_recv: argument must be a channel")
        if len(ch['items']) > 0:
            return ch['items'].pop(0)
        if ch.get('closed'):
            raise BytecodeRuntimeError("chan_recv on closed and empty channel")
        raise BytecodeRuntimeError("chan_recv on empty channel (would block)")

    def _b_chan_close(self, args):
        if len(args) != 1:
            raise BytecodeRuntimeError("chan_close(ch) takes exactly 1 argument")
        ch = args[0]
        if not isinstance(ch, dict) or ch.get('__htype__') != 'channel':
            raise BytecodeRuntimeError("chan_close: argument must be a channel")
        # Idempotent: closing an already-closed channel is a no-op (does not raise).
        ch['closed'] = True
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
            self.env[name] = val

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