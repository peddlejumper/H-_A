"""
H# Register Allocation
Implements register allocation for the H# bytecode compiler
Uses graph coloring algorithm for efficient register assignment
"""

class RegisterAllocator:
    """
    Simple register allocator using linear scan algorithm
    Suitable for H# bytecode generation
    """
    
    def __init__(self, num_registers=8):
        self.num_registers = num_registers
        self.registers = [f"R{i}" for i in range(num_registers)]
        self.available_registers = list(self.registers)
        self.variable_to_register = {}
        self.register_to_variable = {}
        self.spilled_variables = set()
        self.live_ranges = {}
        
    def allocate(self, instructions):
        """
        Allocate registers for a sequence of instructions
        Returns optimized instructions with register assignments
        """
        # Step 1: Analyze live ranges
        self.analyze_live_ranges(instructions)
        
        # Step 2: Allocate registers
        allocated_instructions = []
        for instr in instructions:
            allocated = self.allocate_instruction(instr)
            allocated_instructions.extend(allocated)
        
        return allocated_instructions
    
    def analyze_live_ranges(self, instructions):
        """Analyze variable live ranges"""
        self.live_ranges.clear()
        
        for idx, instr in enumerate(instructions):
            op = instr[0]
            arg = instr[1] if len(instr) > 1 else None
            
            # Track definitions (writes)
            if op in ['STORE_NAME', 'STORE_GLOBAL']:
                var_name = arg
                if var_name not in self.live_ranges:
                    self.live_ranges[var_name] = {'start': idx, 'end': idx}
                else:
                    self.live_ranges[var_name]['end'] = idx
            
            # Track uses (reads)
            elif op in ['LOAD_NAME', 'LOAD_GLOBAL']:
                var_name = arg
                if var_name not in self.live_ranges:
                    self.live_ranges[var_name] = {'start': idx, 'end': idx}
                else:
                    self.live_ranges[var_name]['start'] = min(
                        self.live_ranges[var_name]['start'], idx
                    )
                    self.live_ranges[var_name]['end'] = max(
                        self.live_ranges[var_name]['end'], idx
                    )
    
    def allocate_instruction(self, instr):
        """Allocate registers for a single instruction"""
        op = instr[0]
        arg = instr[1] if len(instr) > 1 else None
        
        # Variable load - assign register
        if op == 'LOAD_NAME':
            var_name = arg
            if var_name in self.variable_to_register:
                reg = self.variable_to_register[var_name]
                return [('LOAD_REG', reg)]
            else:
                # Need to allocate a new register
                reg = self.allocate_register(var_name)
                if reg:
                    return [('LOAD_NAME_TO_REG', var_name, reg)]
                else:
                    # Spill to memory
                    self.spilled_variables.add(var_name)
                    return [('LOAD_NAME', var_name)]
        
        # Variable store - release register
        elif op == 'STORE_NAME':
            var_name = arg
            if var_name in self.variable_to_register:
                reg = self.variable_to_register[var_name]
                self.free_register(reg)
                del self.variable_to_register[var_name]
                if reg in self.register_to_variable:
                    del self.register_to_variable[reg]
            return [('STORE_NAME', var_name)]
        
        # Binary operations - use registers
        elif op.startswith('BINARY_') or op.startswith('COMPARE_'):
            return self.allocate_binary_op(instr)
        
        # Function calls
        elif op == 'CALL_FUNCTION':
            return self.allocate_call(instr)
        
        # Default: pass through
        return [instr]
    
    def allocate_register(self, var_name):
        """Allocate a register for a variable"""
        if self.available_registers:
            reg = self.available_registers.pop(0)
            self.variable_to_register[var_name] = reg
            self.register_to_variable[reg] = var_name
            return reg
        return None
    
    def free_register(self, reg):
        """Free a register"""
        if reg not in self.available_registers:
            self.available_registers.append(reg)
            self.available_registers.sort()
    
    def allocate_binary_op(self, instr):
        """Allocate registers for binary operations"""
        op = instr[0]
        # Assume operands are already in R0 and R1
        result_reg = 'R0'
        return [
            (op + '_REG', result_reg)
        ]
    
    def allocate_call(self, instr):
        """Allocate registers for function calls"""
        op = instr[0]
        arg_count = instr[1] if len(instr) > 1 else 0
        return [(op, arg_count)]
    
    def get_spill_code(self, var_name):
        """Generate spill code for a variable"""
        return [
            ('SPILL_STORE', var_name),
            ('SPILL_LOAD', var_name)
        ]
    
    def get_stats(self):
        """Get allocation statistics"""
        return {
            'total_registers': self.num_registers,
            'used_registers': self.num_registers - len(self.available_registers),
            'spilled_variables': len(self.spilled_variables),
            'active_mappings': len(self.variable_to_register)
        }


class LinearScanAllocator(RegisterAllocator):
    """
    Linear Scan Register Allocator
    More efficient than simple allocation
    """
    
    def __init__(self, num_registers=8):
        super().__init__(num_registers)
        self.active_intervals = []
    
    def allocate_with_intervals(self, intervals):
        """
        Allocate registers using linear scan with live intervals
        intervals: list of (var_name, start, end) tuples
        """
        # Sort intervals by start position
        sorted_intervals = sorted(intervals, key=lambda x: x[1])
        
        allocations = {}
        
        for var_name, start, end in sorted_intervals:
            # Expire old intervals
            self.explore_old_intervals(start)
            
            if len(self.active_intervals) < self.num_registers:
                # Allocate register
                reg = self.allocate_register(var_name)
                allocations[var_name] = reg
                self.active_intervals.append((var_name, start, end, reg))
            else:
                # Spill: choose variable with longest remaining range
                spill_candidate = self.find_spill_candidate(end)
                if spill_candidate:
                    self.spill_variable(spill_candidate)
                    reg = self.allocate_register(var_name)
                    allocations[var_name] = reg
                    self.active_intervals.append((var_name, start, end, reg))
                else:
                    # Spill current variable
                    self.spilled_variables.add(var_name)
        
        return allocations
    
    def explore_old_intervals(self, current_pos):
        """Remove intervals that have ended"""
        new_active = []
        for var_name, start, end, reg in self.active_intervals:
            if end >= current_pos:
                new_active.append((var_name, start, end, reg))
            else:
                self.free_register(reg)
                if var_name in self.variable_to_register:
                    del self.variable_to_register[var_name]
        
        self.active_intervals = new_active
    
    def find_spill_candidate(self, current_end):
        """Find the best candidate to spill"""
        if not self.active_intervals:
            return None
        
        # Spill the one with the longest remaining range
        return max(self.active_intervals, key=lambda x: x[2])[0]
    
    def spill_variable(self, var_name):
        """Spill a variable to memory"""
        if var_name in self.variable_to_register:
            reg = self.variable_to_register[var_name]
            self.free_register(reg)
            del self.variable_to_register[var_name]
            self.spilled_variables.add(var_name)
        
        self.active_intervals = [
            interval for interval in self.active_intervals
            if interval[0] != var_name
        ]


def integrate_with_compiler(compiler, program):
    """
    Integrate register allocation with the enhanced compiler
    This is a placeholder showing how to integrate
    """
    # Step 1: Compile to intermediate representation
    bytecode = compiler.compile(program)

    # Step 2: Apply register allocation
    allocator = LinearScanAllocator(num_registers=8)
    optimized_instructions = allocator.allocate(bytecode['instructions'])

    # Step 3: Update bytecode
    bytecode['instructions'] = optimized_instructions
    bytecode['register_stats'] = allocator.get_stats()

    return bytecode


class LiveRangeAnalyzer:
    """
    修正后的活跃区间分析
    修复原 RegisterAllocator.analyze_live_ranges 的 bug：
      - 原实现把 STORE_NAME 当作区间结束并立即释放，导致变量在循环中被错误回收
      - 本实现先收集所有 def/use 位置，再对每个变量计算 [first_def_or_use, last_use]
    """

    def __init__(self):
        self.ranges = {}  # var_name -> [start, end]

    def analyze(self, instructions):
        self.ranges = {}
        # 第一遍：记录每个变量的所有出现位置
        occurrences = {}  # var_name -> set of pc
        for pc, instr in enumerate(instructions):
            op = instr[0]
            arg = instr[1] if len(instr) > 1 else None
            if op in ('LOAD_NAME', 'STORE_NAME', 'LOAD_GLOBAL', 'STORE_GLOBAL'):
                if arg is None:
                    continue
                occurrences.setdefault(arg, set()).add(pc)
            elif op == 'CALL_FUNCTION' and isinstance(arg, tuple) and len(arg) == 2:
                # CALL_FUNCTION 的 arg 是 (name, argc)，name 是被调用函数名，属于 use
                name = arg[0]
                if isinstance(name, str):
                    occurrences.setdefault(name, set()).add(pc)

        # 第二遍：计算区间
        for var, pcs in occurrences.items():
            if pcs:
                self.ranges[var] = [min(pcs), max(pcs)]
        return self.ranges

    def get_range(self, var_name):
        return self.ranges.get(var_name)


class PeepholeOptimizer:
    """
    窥孔优化：在已生成的指令流上做局部模式匹配，减少指令数。
    目标：减少 VM 指令数（对应“寄存器分配升级”的验证项 bytecode profile）。
    """

    def __init__(self):
        self.removed = 0
        self.coalesced = 0

    def run(self, instructions):
        instrs = list(instructions)
        # Pass 1: 删除 LOAD_CONST 后紧跟 POP_TOP（计算后丢弃）
        changed = True
        while changed:
            changed = False
            out = []
            i = 0
            while i < len(instrs):
                cur = instrs[i]
                nxt = instrs[i + 1] if i + 1 < len(instrs) else None
                if (nxt is not None
                        and cur[0] == 'LOAD_CONST'
                        and nxt[0] == 'POP_TOP'):
                    # 跳过这两条
                    self.removed += 2
                    i += 2
                    changed = True
                    continue
                # LOAD_NAME x; POP_TOP → 丢弃（无副作用）
                if (nxt is not None
                        and cur[0] == 'LOAD_NAME'
                        and nxt[0] == 'POP_TOP'):
                    self.removed += 2
                    i += 2
                    changed = True
                    continue
                out.append(cur)
                i += 1
            instrs = out

        # Pass 2: 合并连续的 STORE_NAME x; LOAD_NAME x → STORE_FAST_CACHE（保留栈值）
        # 这里用 LOAD_NAME 之前的 STORE 结果仍在栈顶是不成立的（STORE 会 pop），
        # 所以改为：LOAD_NAME x 紧跟 STORE_NAME x（值未变）→ 删除两条
        out = []
        i = 0
        while i < len(instrs):
            cur = instrs[i]
            nxt = instrs[i + 1] if i + 1 < len(instrs) else None
            if (nxt is not None
                    and cur[0] == 'LOAD_NAME' and nxt[0] == 'STORE_NAME'
                    and cur[1] == nxt[1]):
                self.coalesced += 2
                i += 2
                continue
            out.append(cur)
            i += 1
        return out


class FastLocalAllocator:
    """
    Fast Locals 分配器
    为函数/顶层作用域内的局部变量分配固定槽位，把 LOAD_NAME/STORE_NAME
    改写为 LOAD_FAST(idx)/STORE_FAST(idx)，使 VM 用列表索引访问而非 dict 查找。
    同时附带活跃区间统计，用于 bytecode profile。
    """

    def __init__(self):
        self.slot_map = {}        # var_name -> slot index
        self.fast_names = []      # slot index -> var_name
        self.stats = {
            'locals_allocated': 0,
            'instructions_rewritten': 0,
            'live_ranges': {},
        }

    def allocate(self, instructions):
        analyzer = LiveRangeAnalyzer()
        ranges = analyzer.analyze(instructions)
        self.stats['live_ranges'] = {k: v for k, v in ranges.items()}

        # 为所有出现过的 LOAD_NAME/STORE_NAME 变量分配槽位
        # （CALL_FUNCTION 的 name 是函数名，不分配槽位，保持 LOAD_NAME）
        for pc, instr in enumerate(instructions):
            op = instr[0]
            arg = instr[1] if len(instr) > 1 else None
            if op in ('LOAD_NAME', 'STORE_NAME') and isinstance(arg, str):
                if arg not in self.slot_map:
                    self.slot_map[arg] = len(self.fast_names)
                    self.fast_names.append(arg)

        self.stats['locals_allocated'] = len(self.fast_names)

        # 改写指令
        new_instrs = []
        for instr in instructions:
            op = instr[0]
            arg = instr[1] if len(instr) > 1 else None
            if op == 'LOAD_NAME' and isinstance(arg, str) and arg in self.slot_map:
                new_instrs.append(('LOAD_FAST', self.slot_map[arg]))
                self.stats['instructions_rewritten'] += 1
            elif op == 'STORE_NAME' and isinstance(arg, str) and arg in self.slot_map:
                new_instrs.append(('STORE_FAST', self.slot_map[arg]))
                self.stats['instructions_rewritten'] += 1
            else:
                new_instrs.append(instr)
        return new_instrs

    def get_fast_names(self):
        return self.fast_names


def optimize_bytecode(bytecode):
    """
    对编译器输出的 bytecode 应用寄存器分配升级：
      1. 窥孔优化减少指令数
      2. Fast locals 分配加速变量访问
    返回更新后的 bytecode（含 fast_names 元信息与统计）。
    """
    instrs = bytecode.get('instructions', [])

    peephole = PeepholeOptimizer()
    instrs = peephole.run(instrs)

    allocator = FastLocalAllocator()
    instrs = allocator.allocate(instrs)

    bytecode['instructions'] = instrs
    bytecode['fast_names'] = allocator.get_fast_names()
    bytecode['opt_stats'] = {
        'peephole_removed': peephole.removed,
        'peephole_coalesced': peephole.coalesced,
        **allocator.stats,
    }
    return bytecode
