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
