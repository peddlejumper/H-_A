"""
H# IO Module
Provides file I/O and console input/output functions
"""

import os
import sys

def io_read_file(args):
    """Read entire file content"""
    if len(args) < 1:
        raise Exception("read_file requires 1 argument (path)")
    
    path = str(args[0])
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        return None

def io_write_file(args):
    """Write content to file"""
    if len(args) < 2:
        raise Exception("write_file requires 2 arguments (path, content)")
    
    path = str(args[0])
    content = str(args[1])
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        return False

def io_append_file(args):
    """Append content to file"""
    if len(args) < 2:
        raise Exception("append_file requires 2 arguments (path, content)")
    
    path = str(args[0])
    content = str(args[1])
    
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        return False

def io_file_exists(args):
    """Check if file exists"""
    if len(args) < 1:
        raise Exception("file_exists requires 1 argument (path)")
    
    path = str(args[0])
    return os.path.exists(path)

def io_delete_file(args):
    """Delete a file"""
    if len(args) < 1:
        raise Exception("delete_file requires 1 argument (path)")
    
    path = str(args[0])
    try:
        os.remove(path)
        return True
    except:
        return False

def io_read_lines(args):
    """Read file as list of lines"""
    if len(args) < 1:
        raise Exception("read_lines requires 1 argument (path)")
    
    path = str(args[0])
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except:
        return []

def io_getcwd(args=None):
    """Get current working directory"""
    return os.getcwd()

def io_chdir(args):
    """Change current directory"""
    if len(args) < 1:
        raise Exception("chdir requires 1 argument (path)")
    
    path = str(args[0])
    try:
        os.chdir(path)
        return True
    except:
        return False

def io_listdir(args=None):
    """List directory contents"""
    path = "."
    if args and len(args) >= 1:
        path = str(args[0])
    
    try:
        return os.listdir(path)
    except:
        return []

def io_mkdir(args):
    """Create directory"""
    if len(args) < 1:
        raise Exception("mkdir requires 1 argument (path)")
    
    path = str(args[0])
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except:
        return False

def io_print(args):
    """Print to stdout"""
    output = " ".join(str(arg) for arg in args)
    print(output)
    return None

def io_input(args=None):
    """Read input from stdin"""
    prompt = ""
    if args and len(args) >= 1:
        prompt = str(args[0])
    
    try:
        return input(prompt)
    except EOFError:
        return None

def io_print_error(args):
    """Print to stderr"""
    output = " ".join(str(arg) for arg in args)
    print(output, file=sys.stderr)
    return None
