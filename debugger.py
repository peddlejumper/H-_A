"""
H# Debugger Support
Provides debugging capabilities for H# programs
"""

class Debugger:
    """Simple debugger for H# interpreter"""
    
    def __init__(self):
        self.breakpoints = set()  # Line numbers
        self.enabled = False
        self.current_line = 0
        self.variables = {}
        self.call_stack = []
        self.step_mode = False
    
    def set_breakpoint(self, line):
        """Set a breakpoint at specified line"""
        self.breakpoints.add(line)
    
    def clear_breakpoint(self, line):
        """Clear a breakpoint"""
        self.breakpoints.discard(line)
    
    def clear_all_breakpoints(self):
        """Clear all breakpoints"""
        self.breakpoints.clear()
    
    def enable(self):
        """Enable debugger"""
        self.enabled = True
    
    def disable(self):
        """Disable debugger"""
        self.enabled = False
    
    def check_breakpoint(self, line):
        """Check if execution should stop at this line"""
        if not self.enabled:
            return False
        
        if line in self.breakpoints or self.step_mode:
            return True
        return False
    
    def on_line(self, line, env, filename="<unknown>"):
        """Called when interpreter reaches a new line"""
        self.current_line = line
        self.variables = dict(env.vars) if hasattr(env, 'vars') else {}
        
        if self.check_breakpoint(line):
            self.interactive_debug(filename, line)
    
    def on_function_call(self, func_name, args):
        """Called when a function is called"""
        self.call_stack.append({
            'function': func_name,
            'args': args,
            'line': self.current_line
        })
    
    def on_function_return(self, return_value):
        """Called when a function returns"""
        if self.call_stack:
            self.call_stack.pop()
    
    def interactive_debug(self, filename, line):
        """Interactive debugging session"""
        print(f"\n🔍 Breakpoint at {filename}:{line}")
        
        while True:
            try:
                cmd = input("(dbg) ").strip().lower()
                
                if cmd == 'c' or cmd == 'continue':
                    self.step_mode = False
                    break
                elif cmd == 'n' or cmd == 'next':
                    self.step_mode = True
                    break
                elif cmd == 's' or cmd == 'step':
                    self.step_mode = True
                    break
                elif cmd == 'bt' or cmd == 'backtrace':
                    self.print_backtrace()
                elif cmd == 'p' or cmd == 'print':
                    var_name = input("Variable: ").strip()
                    self.print_variable(var_name)
                elif cmd == 'l' or cmd == 'list':
                    self.list_variables()
                elif cmd == 'h' or cmd == 'help':
                    self.print_help()
                elif cmd == 'q' or cmd == 'quit':
                    raise KeyboardInterrupt
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'h' for help")
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nExiting debugger...")
                break
    
    def print_backtrace(self):
        """Print call stack"""
        print("\nCall Stack:")
        if not self.call_stack:
            print("  (empty)")
        else:
            for i, frame in enumerate(reversed(self.call_stack)):
                print(f"  #{i}: {frame['function']}() at line {frame['line']}")
    
    def print_variable(self, name):
        """Print value of a variable"""
        if name in self.variables:
            print(f"  {name} = {self.variables[name]}")
        else:
            print(f"  Variable '{name}' not found")
    
    def list_variables(self):
        """List all variables in current scope"""
        print("\nVariables:")
        if not self.variables:
            print("  (none)")
        else:
            for name, value in self.variables.items():
                print(f"  {name} = {value}")
    
    def print_help(self):
        """Print debugger help"""
        print("\nDebugger Commands:")
        print("  c, continue  - Continue execution")
        print("  n, next      - Execute next line")
        print("  s, step      - Step into function")
        print("  bt           - Show backtrace")
        print("  p <var>      - Print variable")
        print("  l            - List variables")
        print("  h            - Show this help")
        print("  q            - Quit debugger")


class DebugInterpreter:
    """Wrapper to add debugging support to interpreter"""
    
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.debugger = Debugger()
    
    def enable_debugging(self):
        """Enable debugging"""
        self.debugger.enable()
    
    def set_breakpoint(self, line):
        """Set breakpoint"""
        self.debugger.set_breakpoint(line)
    
    def run_with_debug(self, program, filename="<input>"):
        """Run program with debugging support"""
        # This would need integration with the actual interpreter
        # For now, just a placeholder showing the concept
        print("Debug mode enabled")
        print(f"Breakpoints: {self.debugger.breakpoints}")
        
        # Run normally for now
        self.interpreter.interpret(program)
