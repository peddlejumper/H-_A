"""
H# DateTime Module
Provides date and time manipulation functions
"""

import time
from datetime import datetime, timedelta

def dt_now(args=None):
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)

def dt_timestamp_to_date(args):
    """Convert timestamp to date string"""
    if len(args) < 1:
        raise Exception("timestamp_to_date requires 1 argument")
    
    timestamp = float(args[0]) / 1000.0  # Convert ms to seconds
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def dt_format(args):
    """Format timestamp with custom format"""
    if len(args) < 2:
        raise Exception("format requires 2 arguments (timestamp, format)")
    
    timestamp = float(args[0]) / 1000.0
    fmt = str(args[1])
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(fmt)

def dt_parse(args):
    """Parse date string to timestamp"""
    if len(args) < 2:
        raise Exception("parse requires 2 arguments (date_string, format)")
    
    date_str = str(args[0])
    fmt = str(args[1])
    
    try:
        dt = datetime.strptime(date_str, fmt)
        return int(dt.timestamp() * 1000)
    except:
        return None

def dt_year(args=None):
    """Get current year"""
    return datetime.now().year

def dt_month(args=None):
    """Get current month (1-12)"""
    return datetime.now().month

def dt_day(args=None):
    """Get current day of month (1-31)"""
    return datetime.now().day

def dt_hour(args=None):
    """Get current hour (0-23)"""
    return datetime.now().hour

def dt_minute(args=None):
    """Get current minute (0-59)"""
    return datetime.now().minute

def dt_second(args=None):
    """Get current second (0-59)"""
    return datetime.now().second

def dt_weekday(args=None):
    """Get current weekday (0=Monday, 6=Sunday)"""
    return datetime.now().weekday()

def dt_add_days(args):
    """Add days to timestamp"""
    if len(args) < 2:
        raise Exception("add_days requires 2 arguments (timestamp, days)")
    
    timestamp = float(args[0]) / 1000.0
    days = int(args[1])
    
    dt = datetime.fromtimestamp(timestamp)
    new_dt = dt + timedelta(days=days)
    return int(new_dt.timestamp() * 1000)

def dt_add_hours(args):
    """Add hours to timestamp"""
    if len(args) < 2:
        raise Exception("add_hours requires 2 arguments (timestamp, hours)")
    
    timestamp = float(args[0]) / 1000.0
    hours = int(args[1])
    
    dt = datetime.fromtimestamp(timestamp)
    new_dt = dt + timedelta(hours=hours)
    return int(new_dt.timestamp() * 1000)

def dt_diff(args):
    """Calculate difference between two timestamps"""
    if len(args) < 2:
        raise Exception("diff requires 2 arguments (timestamp1, timestamp2)")
    
    ts1 = float(args[0])
    ts2 = float(args[1])
    
    diff_ms = ts2 - ts1
    return {
        'milliseconds': diff_ms,
        'seconds': diff_ms / 1000,
        'minutes': diff_ms / (1000 * 60),
        'hours': diff_ms / (1000 * 60 * 60),
        'days': diff_ms / (1000 * 60 * 60 * 24)
    }

def dt_sleep(args):
    """Sleep for specified milliseconds"""
    if len(args) < 1:
        raise Exception("sleep requires 1 argument (milliseconds)")
    
    ms = int(args[0])
    time.sleep(ms / 1000.0)
    return None

def dt_perf_counter(args=None):
    """Get high-resolution performance counter"""
    return time.perf_counter()

def dt_iso_format(args=None):
    """Get current time in ISO format"""
    return datetime.now().isoformat()

def dt_unix_timestamp(args=None):
    """Get current Unix timestamp in seconds"""
    return int(time.time())
