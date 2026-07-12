"""
gui_tkinter.py — tkinter 后端，为 H# 解释器提供 gui_* host 函数。

H# 的 hwdui 组件库 + zzw_render 渲染引擎通过 zzw_native.hto 调用
gui_create_window / gui_draw_rect / gui_get_events 等底层原语。
这些原语原本只在 Kotlin 编译器实现；本模块用 Python 标准库 tkinter
补齐 Python 解释器端的后端，使 hwdui GUI 程序可在 Python 下运行。

设计：
  - 即时模式绘图：每帧 gui_clear 删掉所有 canvas item，再用 gui_draw_* 重画
  - 轮询式事件：tkinter 回调把事件压入队列，gui_get_events 取出返回
  - win_id 为整数 handle，映射到内部 WindowEntry
"""

import tkinter as tk
from tkinter import font as tkfont
import threading

_WIN_SEQ = 0          # 窗口 id 自增
_WINDOWS = {}         # win_id -> WindowEntry
_CLIPBOARD = ""       # 简易剪贴板（tkinter clipboard 也可，这里自管以避免焦点问题）
_ROOT = None          # 持久的隐藏根窗口（所有 Toplevel 的父）


def _ensure_root():
    """确保存在一个隐藏的 tk.Tk() 根窗口。
    所有可见窗口都用 Toplevel 创建，避免销毁窗口时根窗口被毁
    导致 tkinter 自动重建一个空的 'tk' 窗口。
    """
    global _ROOT
    if _ROOT is None or not _ROOT.winfo_exists():
        _ROOT = tk.Tk()
        _ROOT.withdraw()       # 隐藏根窗口，用户永远看不到
    return _ROOT


class WindowEntry:
    __slots__ = ("root", "canvas", "events", "closed", "w", "h", "bg",
                 "clip", "timers", "_alive")

    def __init__(self, root, canvas, w, h, bg):
        self.root = root
        self.canvas = canvas
        self.events = []          # 待消费的事件队列
        self.closed = False
        self.w = w
        self.h = h
        self.bg = bg
        self.clip = None          # (x, y, w, h) or None
        self.timers = {}
        self._alive = True


def _to_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default


def _to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _unpack_color(c):
    """接受 '#rrggbb' 或 '#rgb' 或 'rgb(...)'，返回 tkinter 可用字符串。"""
    if c is None:
        return "#000000"
    s = str(c).strip()
    if s == "":
        return "#000000"
    if s.startswith("#"):
        return s
    return s


def _font_tuple(family, size, bold):
    fam = str(family).strip() if family else "PingFang SC"
    if fam == "":
        fam = "PingFang SC"
    sz = _to_int(size, 12)
    if sz <= 0:
        sz = 12
    weight = "bold" if bold else "normal"
    return (fam, sz, weight)


# ───────────────────────── 窗口管理 ─────────────────────────

def gui_create_window(title, w, h, bg):
    global _WIN_SEQ
    _ensure_root()          # 确保隐藏根窗口存在
    _WIN_SEQ += 1
    wid = _WIN_SEQ
    width = _to_int(w, 800)
    height = _to_int(h, 600)
    bgcolor = _unpack_color(bg) if bg else "#1e1e1e"

    root = tk.Toplevel()    # 所有可见窗口都是 Toplevel，根窗口隐藏不销毁
    root.title(str(title) if title else "H# Window")
    root.geometry(f"{width}x{height}")
    root.configure(bg=bgcolor)
    root.minsize(120, 80)

    canvas = tk.Canvas(root, width=width, height=height, bg=bgcolor,
                       highlightthickness=0, bd=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    entry = WindowEntry(root, canvas, width, height, bgcolor)
    _WINDOWS[wid] = entry

    # 关闭事件
    def _on_close():
        entry.events.append({"type": "close"})
        entry.closed = True
        try:
            root.destroy()
        except Exception:
            pass
        entry._alive = False

    root.protocol("WM_DELETE_WINDOW", _on_close)

    # 尺寸变化
    def _on_resize(event):
        if event.widget is canvas or event.widget is root:
            entry.w = max(1, event.width)
            entry.h = max(1, event.height)
            entry.events.append({"type": "resize", "x": entry.w, "y": entry.h})

    root.bind("<Configure>", _on_resize)

    # 鼠标
    def _mk_btn(btn_type):
        def _h(event):
            entry.events.append({
                "type": "mouse_down", "button": btn_type,
                "x": event.x, "y": event.y
            })
        return _h

    def _mk_mouse_up(btn_type):
        def _h(event):
            entry.events.append({
                "type": "mouse_up", "button": btn_type,
                "x": event.x, "y": event.y
            })
        return _h

    def _on_motion(event):
        entry.events.append({"type": "mouse_move", "x": event.x, "y": event.y})

    for btn, name in [("<Button-1>", "left"), ("<Button-3>", "right"),
                      ("<Button-2>", "middle")]:
        canvas.bind(btn, _mk_btn(name))
        canvas.bind(btn.replace("Button", "ButtonRelease"), _mk_mouse_up(name))
    canvas.bind("<Motion>", _on_motion)

    # 键盘
    def _on_key(event):
        ch = event.char
        key = event.keysym
        entry.events.append({"type": "key_down", "key": key, "char": ch})

    def _on_key_up(event):
        entry.events.append({"type": "key_up", "key": event.keysym, "char": event.char})

    root.bind("<KeyPress>", _on_key)
    root.bind("<KeyRelease>", _on_key_up)

    root.update_idletasks()
    return wid


def gui_destroy_window(wid):
    e = _WINDOWS.get(_to_int(wid))
    if e and e._alive:
        try:
            e.root.destroy()
        except Exception:
            pass
        e._alive = False


def gui_show_window(wid):
    e = _WINDOWS.get(_to_int(wid))
    if e and e._alive:
        try:
            e.root.deiconify()
        except Exception:
            pass
    return 0


def gui_hide_window(wid):
    e = _WINDOWS.get(_to_int(wid))
    if e and e._alive:
        try:
            e.root.withdraw()
        except Exception:
            pass
    return 0


def gui_set_window_title(wid, title):
    e = _WINDOWS.get(_to_int(wid))
    if e and e._alive:
        try:
            e.root.title(str(title))
        except Exception:
            pass
    return 0


def gui_set_window_size(wid, w, h):
    e = _WINDOWS.get(_to_int(wid))
    if e and e._alive:
        ww = _to_int(w, 800); hh = _to_int(h, 600)
        e.w = ww; e.h = hh
        try:
            e.root.geometry(f"{ww}x{hh}")
        except Exception:
            pass
    return 0


def gui_get_window_size(wid):
    e = _WINDOWS.get(_to_int(wid))
    if e:
        return [e.w, e.h]
    return [0, 0]


# ───────────────────────── 绘图原语 ─────────────────────────

def _canvas(wid):
    e = _WINDOWS.get(_to_int(wid))
    if not e or not e._alive:
        return None, None
    return e, e.canvas


def gui_clear(wid, color):
    e, c = _canvas(wid)
    if c is None:
        return 0
    bg = _unpack_color(color) if color else e.bg
    e.bg = bg
    c.delete("all")
    try:
        c.config(bg=bg)
    except Exception:
        pass
    return 0


def gui_draw_rect(wid, x, y, w, h, color, fill):
    e, c = _canvas(wid)
    if c is None:
        return 0
    x1 = _to_float(x); y1 = _to_float(y)
    x2 = x1 + _to_float(w, 1); y2 = y1 + _to_float(h, 1)
    col = _unpack_color(color)
    if fill:
        c.create_rectangle(x1, y1, x2, y2, fill=col, outline=col)
    else:
        c.create_rectangle(x1, y1, x2, y2, outline=col, width=1)
    return 0


def gui_draw_rounded_rect(wid, x, y, w, h, radius, color, fill):
    """绘制真正的圆角矩形。
    用 4 个 PIESLICE 弧（填充）或 ARC 弧（描边）+ 矩形/线段拼接。
    """
    e, c = _canvas(wid)
    if c is None:
        return 0
    x1 = _to_float(x); y1 = _to_float(y)
    x2 = x1 + _to_float(w, 1); y2 = y1 + _to_float(h, 1)
    r = _to_float(radius, 6)
    col = _unpack_color(color)

    # 半径不能超过宽高的一半
    min_half = min(x2 - x1, y2 - y1) / 2.0
    if r > min_half:
        r = min_half
    if r < 1:
        # 太小，退化为普通矩形
        if fill:
            c.create_rectangle(x1, y1, x2, y2, fill=col, outline=col)
        else:
            c.create_rectangle(x1, y1, x2, y2, outline=col, width=1)
        return 0

    if fill:
        # 四角饼图（填充色 = 描边色，避免缝隙）
        c.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90,
                     style=tk.PIESLICE, fill=col, outline=col)
        c.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90,
                     style=tk.PIESLICE, fill=col, outline=col)
        c.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90,
                     style=tk.PIESLICE, fill=col, outline=col)
        c.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90,
                     style=tk.PIESLICE, fill=col, outline=col)
        # 中间两条矩形填满
        c.create_rectangle(x1 + r, y1, x2 - r, y2, fill=col, outline=col)
        c.create_rectangle(x1, y1 + r, x2, y2 - r, fill=col, outline=col)
    else:
        # 仅描边：4 段弧 + 4 条直线
        c.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90,
                     style=tk.ARC, outline=col, width=1)
        c.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90,
                     style=tk.ARC, outline=col, width=1)
        c.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90,
                     style=tk.ARC, outline=col, width=1)
        c.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90,
                     style=tk.ARC, outline=col, width=1)
        c.create_line(x1 + r, y1, x2 - r, y1, fill=col, width=1)
        c.create_line(x1 + r, y2, x2 - r, y2, fill=col, width=1)
        c.create_line(x1, y1 + r, x1, y2 - r, fill=col, width=1)
        c.create_line(x2, y1 + r, x2, y2 - r, fill=col, width=1)
    return 0


def gui_draw_line(wid, x1, y1, x2, y2, color, width):
    e, c = _canvas(wid)
    if c is None:
        return 0
    lw = _to_float(width, 1)
    if lw < 1:
        lw = 1
    c.create_line(_to_float(x1), _to_float(y1), _to_float(x2), _to_float(y2),
                  fill=_unpack_color(color), width=lw)
    return 0


def gui_draw_circle(wid, cx, cy, r, color, fill):
    e, c = _canvas(wid)
    if c is None:
        return 0
    rr = _to_float(r, 1)
    x = _to_float(cx); y = _to_float(cy)
    col = _unpack_color(color)
    if fill:
        c.create_oval(x - rr, y - rr, x + rr, y + rr, fill=col, outline=col)
    else:
        c.create_oval(x - rr, y - rr, x + rr, y + rr, outline=col, width=1)
    return 0


def gui_draw_arc(wid, x, y, w, h, start_angle, extent, color, fill):
    e, c = _canvas(wid)
    if c is None:
        return 0
    x1 = _to_float(x); y1 = _to_float(y)
    x2 = x1 + _to_float(w, 1); y2 = y1 + _to_float(h, 1)
    col = _unpack_color(color)
    sa = _to_float(start_angle, 0); ex = _to_float(extent, 90)
    if fill:
        c.create_arc(x1, y1, x2, y2, start=sa, extent=ex, style=tk.PIESLICE,
                     fill=col, outline=col)
    else:
        c.create_arc(x1, y1, x2, y2, start=sa, extent=ex, style=tk.ARC,
                     outline=col, width=1)
    return 0


def gui_draw_polygon(wid, points, color, fill):
    e, c = _canvas(wid)
    if c is None:
        return 0
    pts = []
    if points:
        for p in points:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                pts.append(_to_float(p[0]))
                pts.append(_to_float(p[1]))
    if len(pts) < 6:
        return 0
    col = _unpack_color(color)
    if fill:
        c.create_polygon(*pts, fill=col, outline=col)
    else:
        c.create_polygon(*pts, fill="", outline=col, width=1)
    return 0


def gui_draw_text(wid, x, y, text, color, font_size, bold, font_family):
    e, c = _canvas(wid)
    if c is None:
        return 0
    ft = _font_tuple(font_family, font_size, bold)
    col = _unpack_color(color)
    # anchor=NW: tkinter 把文本包围盒左上角放在 (x, y)。
    # H# 约定 y 是文字顶部 → 直接用 y，不需要加 ascent。
    c.create_text(_to_float(x), _to_float(y), text=str(text),
                  fill=col, font=ft, anchor=tk.NW)
    return 0


def gui_draw_text_centered(wid, x, y, text, color, font_size, bold):
    e, c = _canvas(wid)
    if c is None:
        return 0
    ft = _font_tuple("PingFang SC", font_size, bold)
    col = _unpack_color(color)
    c.create_text(_to_float(x), _to_float(y), text=str(text),
                  fill=col, font=ft, anchor=tk.CENTER)
    return 0


def gui_measure_text(text, font_size, bold):
    try:
        ft = _font_tuple("PingFang SC", font_size, bold)
        f = tkfont.Font(font=ft)
        return [f.measure(str(text) if text else ""), f.metrics("linespace")]
    except Exception:
        return [len(str(text)) * _to_int(font_size, 12), _to_int(font_size, 12) + 4]


def gui_draw_image(wid, x, y, w, h, color):
    # 简易实现：画一个矩形占位
    return gui_draw_rect(wid, x, y, w, h, color, True)


def gui_set_clip(wid, x, y, w, h):
    e, c = _canvas(wid)
    if c is None:
        return 0
    e.clip = (_to_int(x), _to_int(y), _to_int(w), _to_int(h))
    return 0


def gui_clear_clip(wid):
    e, c = _canvas(wid)
    if c is None:
        return 0
    e.clip = None
    return 0


# ───────────────────────── 事件 ─────────────────────────

def gui_get_events(wid):
    e = _WINDOWS.get(_to_int(wid))
    if not e:
        return []
    out = e.events
    e.events = []
    return out


def gui_update(wid):
    e = _WINDOWS.get(_to_int(wid))
    if e and e._alive:
        try:
            e.root.update_idletasks()
        except Exception:
            pass
    return 0


def gui_start_event_loop():
    return 0


def gui_stop_event_loop():
    for e in list(_WINDOWS.values()):
        if e._alive:
            try:
                e.root.quit()
            except Exception:
                pass
    return 0


def gui_poll_events():
    # 处理所有挂起的 tkinter 事件（触发回调 → 压入事件队列）
    for e in list(_WINDOWS.values()):
        if e._alive:
            try:
                e.root.update()
            except Exception:
                pass
    return 0


def gui_set_timer(wid, timer_id, delay_ms, callback_name):
    # 简化：不实际调度（H# 侧多为轮询），仅记录
    e = _WINDOWS.get(_to_int(wid))
    if e:
        e.timers[_to_int(timer_id)] = (delay_ms, callback_name)
    return 0


def gui_clear_timer(wid, timer_id):
    e = _WINDOWS.get(_to_int(wid))
    if e:
        e.timers.pop(_to_int(timer_id), None)
    return 0


# ───────────────────────── 屏幕/剪贴板 ─────────────────────────

def gui_get_screen_size():
    try:
        r = _ensure_root()      # 复用隐藏根，不再创建额外的 tk.Tk()
        return [r.winfo_screenwidth(), r.winfo_screenheight()]
    except Exception:
        return [1920, 1080]


def gui_get_mouse_pos():
    for e in _WINDOWS.values():
        if e._alive:
            try:
                x = e.root.winfo_pointerx() - e.root.winfo_rootx()
                y = e.root.winfo_pointery() - e.root.winfo_rooty()
                return [x, y]
            except Exception:
                pass
    return [0, 0]


def gui_beep():
    try:
        for e in _WINDOWS.values():
            if e._alive:
                e.root.bell()
                break
    except Exception:
        pass
    return 0


def gui_clipboard_copy(text):
    global _CLIPBOARD
    _CLIPBOARD = str(text) if text else ""
    for e in _WINDOWS.values():
        if e._alive:
            try:
                e.root.clipboard_clear()
                e.root.clipboard_append(_CLIPBOARD)
            except Exception:
                pass
            break
    return 0


def gui_clipboard_paste():
    if _CLIPBOARD:
        return _CLIPBOARD
    for e in _WINDOWS.values():
        if e._alive:
            try:
                return e.root.clipboard_get()
            except Exception:
                pass
            break
    return ""


# ───────────────────────── 颜色 ─────────────────────────

def gui_parse_color(hex_color):
    s = _unpack_color(hex_color)
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return [0, 0, 0]
    try:
        return [int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)]
    except Exception:
        return [0, 0, 0]


def gui_color_to_hex(r, g, b):
    try:
        return "#%02x%02x%02x" % (_to_int(r) & 255, _to_int(g) & 255, _to_int(b) & 255)
    except Exception:
        return "#000000"


def gui_lerp_color(c1, c2, t):
    a = gui_parse_color(c1)
    b = gui_parse_color(c2)
    tt = _to_float(t, 0.0)
    if tt < 0: tt = 0.0
    if tt > 1: tt = 1.0
    return gui_color_to_hex(
        int(a[0] + (b[0] - a[0]) * tt),
        int(a[1] + (b[1] - a[1]) * tt),
        int(a[2] + (b[2] - a[2]) * tt),
    )


# ───────────────────────── 注册表 ─────────────────────────

GUI_FUNCTIONS = {
    "gui_create_window": gui_create_window,
    "gui_destroy_window": gui_destroy_window,
    "gui_show_window": gui_show_window,
    "gui_hide_window": gui_hide_window,
    "gui_set_window_title": gui_set_window_title,
    "gui_set_window_size": gui_set_window_size,
    "gui_get_window_size": gui_get_window_size,
    "gui_clear": gui_clear,
    "gui_draw_rect": gui_draw_rect,
    "gui_draw_rounded_rect": gui_draw_rounded_rect,
    "gui_draw_line": gui_draw_line,
    "gui_draw_circle": gui_draw_circle,
    "gui_draw_arc": gui_draw_arc,
    "gui_draw_polygon": gui_draw_polygon,
    "gui_draw_text": gui_draw_text,
    "gui_draw_text_centered": gui_draw_text_centered,
    "gui_measure_text": gui_measure_text,
    "gui_draw_image": gui_draw_image,
    "gui_set_clip": gui_set_clip,
    "gui_clear_clip": gui_clear_clip,
    "gui_get_events": gui_get_events,
    "gui_update": gui_update,
    "gui_start_event_loop": gui_start_event_loop,
    "gui_stop_event_loop": gui_stop_event_loop,
    "gui_poll_events": gui_poll_events,
    "gui_set_timer": gui_set_timer,
    "gui_clear_timer": gui_clear_timer,
    "gui_get_screen_size": gui_get_screen_size,
    "gui_get_mouse_pos": gui_get_mouse_pos,
    "gui_beep": gui_beep,
    "gui_clipboard_copy": gui_clipboard_copy,
    "gui_clipboard_paste": gui_clipboard_paste,
    "gui_parse_color": gui_parse_color,
    "gui_color_to_hex": gui_color_to_hex,
    "gui_lerp_color": gui_lerp_color,
}


def register(interpreter):
    """把 gui_* 函数注册到解释器的 builtins。

    H# 解释器调用 builtins 时传入单个 args 列表，因此每个函数
    需要包一层把 args 展开为位置参数。
    """
    for name, fn in GUI_FUNCTIONS.items():
        def _make_wrapper(f):
            def _h(args):
                return f(*args)
            return _h
        interpreter.builtins[name] = _make_wrapper(fn)
