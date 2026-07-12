"""
hwd_ui.py — HwdUI desktop framework host implementation for H# v0.4.

Backed by Tkinter (ships with Python stdlib, no extra deps).

Architecture:
  - Each widget is a Python dict with method keys (init_*, set_*, add_*, get_*)
    that operate on the underlying Tk widget.
  - `new ClassName()` (H# NewExpression) is intercepted by the interpreter and
    routed to a registered factory that returns one of these dicts.
  - `obj.method(args)` (H# CallExpression on MemberExpression) is intercepted
    by the interpreter; it looks up the key "method" in the dict and calls it.
  - H# closures (fn() { ... }) stored as `onClick` are Python callables; the
    widget triggers them on user interaction.
"""
import os
import sys
import queue
import threading
import traceback

# Defer tkinter import so module load doesn't require X11 (lets us probe)
_tk = None
_ttk = None
_tk_msg = None


def _ensure_tk():
    global _tk, _ttk, _tk_msg
    if _tk is not None:
        return
    try:
        import tkinter as tk
        import tkinter.ttk as ttk
        import tkinter.messagebox as mb
        import tkinter.scrolledtext as st
        _tk = tk
        _ttk = ttk
        _tk_msg = {"mb": mb, "st": st}
    except Exception as exc:
        raise RuntimeError(f"HwdUI requires Tkinter, but import failed: {exc}")


# ========== Theme ==========
_THEME = {
    "bg": "#1e1e1e",
    "bg_soft": "#252526",
    "bg_alt": "#2d2d30",
    "fg": "#d4d4d4",
    "fg_dim": "#858585",
    "border": "#3c3c3c",
    "accent": "#007acc",
    "accent2": "#1f9cf0",
    "purple": "#7c3aed",
    "green": "#10b981",
    "red": "#ef4444",
    "yellow": "#f59e0b",
    "code_bg": "#1a1a1a",
    "code_fg": "#e6e6e6",
}


# ========== App singleton ==========
_app = None
_root = None  # the hidden root window
_windows = []  # open top-level windows (we manage them ourselves)
_run_after_creation = None  # callable invoked when first window is opened
_theme_name = "dark"
# Most recently created Window — used as the default parent for any
# widget created with `new Widget()` so widgets actually appear in the
# window instead of staying inside the hidden app root.
_active_window = None


def _get_app():
    global _app
    _ensure_tk()
    if _app is None:
        _app = _tk.Tk()
        _app.withdraw()  # hide the root; user windows are Toplevel
    return _app


def _parent():
    """Return the active Window (or the app root as a fallback)."""
    return _active_window if _active_window is not None else _get_app()


def _palette():
    return _THEME


# ========== Helper: build a method-bag dict for a widget ==========
def _make_handle(widget, widget_class, defaults=None):
    """Create the dict exposed to H# code.

    widget: the underlying Tk widget (Frame, Label, etc.)
    widget_class: logical class name (e.g., "Label", "Panel") for introspection
    defaults: optional dict of default attribute values (pos/size/bg/text)
    """
    handle = {
        "__hwd_widget__": widget,
        "__hwd_class__": widget_class,
        "__hwd_children__": [],
    }
    if defaults:
        for k, v in defaults.items():
            handle[k] = v
    return handle


def _safe_call(fn, *args):
    """Run a Tk-related call. If we're not on the Tk thread, schedule it."""
    try:
        app = _get_app()
        # All H# code runs in main thread for our purposes, so direct call works.
        return fn(*args)
    except Exception as exc:
        sys.stderr.write(f"[HwdUI] {exc}\n{traceback.format_exc()}\n")
        return None


def _reparent(child, new_parent):
    """Move `child` to be a child of `new_parent` in the Tk hierarchy.

    Tk's default geometry managers (pack/grid) can't mix with place() in
    the same parent, and `place(in_=...)` only changes the layout parent
    without actually reparenting the widget. The widget's real master
    is whatever was passed at construction. We use the low-level Tk
    reparent command to truly move the widget."""
    try:
        child.tk.call('tk', 'manage', 'reparent', child._w, new_parent._w)
    except Exception:
        # Fall back: destroy and recreate would lose state, so swallow.
        pass


def _apply_geometry(ch, handle, parent):
    """Apply stored _x/_y/_w/_h to the widget using place() with `parent`
    as the layout master. Called from add_child (and after reparent)."""
    kw = {}
    if "_x" in handle and "_y" in handle:
        kw["x"] = int(handle["_x"])
        kw["y"] = int(handle["_y"])
    if "_w" in handle and "_h" in handle:
        kw["width"] = int(handle["_w"])
        kw["height"] = int(handle["_h"])
    if not kw:
        return
    kw["in_"] = parent
    try:
        ch.place(**kw)
    except Exception:
        pass


def _store_xy(handle, x, y):
    handle["_x"] = int(x)
    handle["_y"] = int(y)


def _store_wh(handle, w, h):
    handle["_w"] = int(w)
    handle["_h"] = int(h)


# ========== Widget factories ==========
def make_window(title, w, h):
    global _active_window
    _ensure_tk()
    app = _get_app()
    win = _tk.Toplevel(app)
    try:
        win.title(str(title))
    except Exception:
        pass
    try:
        win.geometry(f"{int(w)}x{int(h)}")
    except Exception:
        pass
    try:
        win.configure(bg=_THEME["bg"])
    except Exception:
        pass

    handle = _make_handle(win, "Window", {"title": str(title), "w": int(w), "h": int(h)})
    # Track this window so child widgets are created as its children.
    _active_window = win

    def close():
        try:
            win.destroy()
        except Exception:
            pass

    def open_():
        try:
            win.deiconify()
            win.lift()
        except Exception:
            pass

    def add_child(child_handle):
        ch = child_handle.get("__hwd_widget__")
        if ch is not None:
            _reparent(ch, win)
            _apply_geometry(ch, child_handle, win)
        handle["__hwd_children__"].append(child_handle)

    def set_size(nw, nh):
        try:
            win.geometry(f"{int(nw)}x{int(nh)}")
        except Exception:
            pass

    def set_title(t):
        try:
            win.title(str(t))
        except Exception:
            pass

    def set_bg(c):
        try:
            win.configure(bg=str(c))
        except Exception:
            pass

    def set_fg(c):
        # Windows don't have a meaningful foreground, but accept for API parity
        handle["fg"] = str(c)

    def apply_theme():
        try:
            win.configure(bg=_THEME["bg"])
        except Exception:
            pass

    handle["close"] = close
    handle["open"] = open_
    handle["add_child"] = add_child
    handle["set_size"] = set_size
    handle["set_title"] = set_title
    handle["set_bg_color"] = set_bg
    handle["set_fg_color"] = set_fg
    handle["set_color"] = set_fg
    handle["apply_theme"] = apply_theme
    _windows.append(handle)
    return handle


def make_panel(class_id="panel"):
    _ensure_tk()
    frame = _tk.Frame(_parent(), bg=_THEME["bg_soft"], highlightthickness=1,
                      highlightbackground=_THEME["border"])
    handle = _make_handle(frame, "Panel", {"id": str(class_id)})

    def add_child(child):
        ch = child.get("__hwd_widget__")
        if ch is not None:
            _reparent(ch, frame)
            _apply_geometry(ch, child, frame)

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            frame.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            frame.place_configure(width=int(w), height=int(h))
        except Exception:
            try:
                frame.configure(width=int(w), height=int(h))
            except Exception:
                pass

    def set_bg(c):
        try:
            frame.configure(bg=str(c))
        except Exception:
            pass

    handle["add_child"] = add_child
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    handle["set_bg_color"] = set_bg
    handle["init_panel"] = lambda *_a, **_k: None  # noop
    return handle


def make_label(initial="", align="left"):
    _ensure_tk()
    lbl = _tk.Label(_parent(), text=str(initial), bg=_THEME["bg_soft"],
                    fg=_THEME["fg"], font=("Helvetica", 11), anchor="w",
                    justify=align, wraplength=600)
    handle = _make_handle(lbl, "Label", {"text": str(initial), "align": str(align)})

    def set_text(t):
        try:
            lbl.configure(text=str(t))
        except Exception:
            pass
        handle["text"] = str(t)

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            lbl.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            lbl.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def set_bg(c):
        try:
            lbl.configure(bg=str(c))
        except Exception:
            pass

    def set_fg(c):
        try:
            lbl.configure(fg=str(c))
        except Exception:
            pass
        handle["fg"] = str(c)

    def set_text_align(a):
        handle["align"] = str(a)
        try:
            j = {"left": "left", "center": "center", "right": "right"}.get(str(a), "left")
            lbl.configure(justify=j)
        except Exception:
            pass

    def set_word_wrap(b):
        try:
            lbl.configure(wraplength=0 if not b else 600)
        except Exception:
            pass
        handle["word_wrap"] = bool(b)

    def set_font_size(n):
        try:
            cur = lbl.cget("font")
            if isinstance(cur, str):
                lbl.configure(font=(cur, int(n)))
            else:
                # cur is a tuple like ("Helvetica", 11)
                fam = cur[0] if cur else "Helvetica"
                lbl.configure(font=(fam, int(n)))
        except Exception:
            pass
        handle["font_size"] = int(n)

    def set_font_family(fam):
        try:
            # Take the first font name from a comma list
            name = str(fam).split(",")[0].strip() or "Helvetica"
            cur = lbl.cget("font")
            size = 11
            if isinstance(cur, tuple) and len(cur) >= 2:
                size = cur[1]
            lbl.configure(font=(name, int(size)))
        except Exception:
            pass
        handle["font_family"] = str(fam)

    def init_label(t=""):
        set_text(t)

    handle["init_label"] = init_label
    handle["set_text"] = set_text
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    handle["set_bg_color"] = set_bg
    handle["set_fg_color"] = set_fg
    handle["set_color"] = set_fg
    handle["set_text_align"] = set_text_align
    handle["set_word_wrap"] = set_word_wrap
    handle["set_font_size"] = set_font_size
    handle["set_font_family"] = set_font_family
    return handle


def _set_handler(handle, attr, value):
    """Helper for the onClick / onSelect pattern: assigning via a method
    call (`btn.onClick(fn() {...})`) requires `onClick` to be a callable
    that stores the value back into the dict."""
    handle[attr] = value


def make_button(text=""):
    _ensure_tk()
    btn = _tk.Button(_parent(), text=str(text), bg=_THEME["accent"],
                     fg="white", activebackground=_THEME["accent2"],
                     activeforeground="white", relief="flat", padx=10, pady=4)
    handle = _make_handle(btn, "Button", {"text": str(text)})

    def set_text(t):
        try:
            btn.configure(text=str(t))
        except Exception:
            pass
        handle["text"] = str(t)

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            btn.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            btn.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def set_bg(c):
        try:
            btn.configure(bg=str(c), activebackground=str(c))
        except Exception:
            pass

    def set_fg(c):
        try:
            btn.configure(fg=str(c), activeforeground=str(c))
        except Exception:
            pass
        handle["fg"] = str(c)

    def set_font_size(n):
        try:
            cur = btn.cget("font")
            if isinstance(cur, str):
                btn.configure(font=(cur, int(n)))
            else:
                fam = cur[0] if cur else "Helvetica"
                btn.configure(font=(fam, int(n)))
        except Exception:
            pass
        handle["font_size"] = int(n)

    def _fire():
        cb = handle.get("onClick")
        if cb is not None and callable(cb):
            try:
                cb()
            except Exception as exc:
                sys.stderr.write(f"[HwdUI] onClick: {exc}\n{traceback.format_exc()}\n")

    btn.configure(command=_fire)

    def init_button(t=""):
        set_text(t)

    # Default onClick is a setter so `btn.onClick(fn(){...})` works as
    # "install click handler" — the actual click fires whatever's stored
    # in handle["onClick"] (which the setter overwrites with the lambda).
    def on_click_setter(cb=None):
        handle["onClick"] = cb

    handle["init_button"] = init_button
    handle["set_text"] = set_text
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    handle["set_bg_color"] = set_bg
    handle["set_fg_color"] = set_fg
    handle["set_color"] = set_fg
    handle["set_font_size"] = set_font_size
    handle["onClick"] = on_click_setter
    return handle


def make_textbox(initial="", password=False):
    _ensure_tk()
    # NOTE: `show` is an Entry-only option. For multi-line Text we can't
    # mask content, so password mode is a no-op visual flag (handled in
    # set_password if a real mask is needed in the future).
    txt = _tk.Text(_parent(), bg=_THEME["code_bg"], fg=_THEME["code_fg"],
                   insertbackground=_THEME["code_fg"], relief="flat",
                   font=("Menlo", 11), wrap="word", height=3)
    if initial:
        try:
            txt.insert("1.0", str(initial))
        except Exception:
            pass
    handle = _make_handle(txt, "TextBox", {"text": str(initial), "password": bool(password)})

    def get_text():
        try:
            return txt.get("1.0", "end-1c")
        except Exception:
            return ""

    def set_text(t):
        try:
            txt.delete("1.0", "end")
            txt.insert("1.0", str(t))
        except Exception:
            pass
        handle["text"] = str(t)
        _fire_on_change()

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            txt.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            txt.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def set_bg(c):
        try:
            txt.configure(bg=str(c))
        except Exception:
            pass

    def set_fg(c):
        try:
            txt.configure(fg=str(c), insertbackground=str(c))
        except Exception:
            pass
        handle["fg"] = str(c)

    def set_font_size(n):
        try:
            cur = txt.cget("font")
            if isinstance(cur, str):
                txt.configure(font=(cur, int(n)))
            else:
                fam = cur[0] if cur else "Menlo"
                txt.configure(font=(fam, int(n)))
        except Exception:
            pass
        handle["font_size"] = int(n)

    def set_font_family(fam):
        try:
            name = str(fam).split(",")[0].strip() or "Menlo"
            cur = txt.cget("font")
            size = 11
            if isinstance(cur, tuple) and len(cur) >= 2:
                size = cur[1]
            txt.configure(font=(name, int(size)))
        except Exception:
            pass
        handle["font_family"] = str(fam)

    def set_multi_line(b):
        try:
            txt.configure(wrap="word" if b else "none")
        except Exception:
            pass
        handle["multi_line"] = bool(b)

    def set_word_wrap(b):
        try:
            txt.configure(wrap="word" if b else "none")
        except Exception:
            pass
        handle["word_wrap"] = bool(b)

    def set_password(b):
        # `show` is an Entry-only option; Tk Text widgets cannot mask
        # content. We just record the flag for callers that want to
        # branch on it (e.g. for a single-line Entry in the future).
        handle["password"] = bool(b)

    def set_placeholder(s):
        # Plain Tk Text has no native placeholder; store it and prefill
        # when text is empty.
        handle["_placeholder"] = str(s)
        try:
            cur = txt.get("1.0", "end-1c")
            if not cur:
                txt.delete("1.0", "end")
                txt.insert("1.0", str(s))
        except Exception:
            pass

    def _fire_on_change():
        cb = handle.get("onChange")
        if cb is not None and callable(cb):
            try:
                cb()
            except Exception as exc:
                sys.stderr.write(f"[HwdUI] onChange: {exc}\n")

    def _on_key(_evt=None):
        _fire_on_change()
        return None  # let the key event propagate

    def _on_return(_evt=None):
        cb = handle.get("onEnter")
        if cb is not None and callable(cb):
            try:
                cb()
            except Exception as exc:
                sys.stderr.write(f"[HwdUI] onEnter: {exc}\n")
        return "break"  # consume Enter so it doesn't insert a newline

    txt.bind("<KeyRelease>", _on_key)
    txt.bind("<Return>", _on_return)

    def init_textbox():
        pass

    handle["init_textbox"] = init_textbox
    handle["get_text"] = get_text
    handle["set_text"] = set_text
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    handle["set_bg_color"] = set_bg
    handle["set_fg_color"] = set_fg
    handle["set_color"] = set_fg
    handle["set_font_size"] = set_font_size
    handle["set_font_family"] = set_font_family
    handle["set_multi_line"] = set_multi_line
    handle["set_word_wrap"] = set_word_wrap
    handle["set_password"] = set_password
    handle["set_placeholder"] = set_placeholder
    return handle


def make_listbox():
    _ensure_tk()
    lb = _tk.Listbox(_get_app(), bg=_THEME["bg_alt"], fg=_THEME["fg"],
                     selectbackground=_THEME["accent"], relief="flat",
                     font=("Helvetica", 10), highlightthickness=0)
    handle = _make_handle(lb, "ListBox", {"items": [], "onSelect": None})

    def _sync(items):
        try:
            lb.delete(0, "end")
            for it in items or []:
                lb.insert("end", str(it))
        except Exception:
            pass
        handle["items"] = list(items or [])

    def set_items(items):
        _sync(items or [])

    def add_item(s):
        try:
            lb.insert("end", str(s))
        except Exception:
            pass
        handle.setdefault("items", []).append(str(s))

    def clear():
        _sync([])

    def set_selected(i):
        try:
            lb.selection_clear(0, "end")
            lb.selection_set(int(i))
            lb.activate(int(i))
            lb.see(int(i))
        except Exception:
            pass

    def get_selected():
        try:
            sel = lb.curselection()
            if sel:
                return int(sel[0])
        except Exception:
            pass
        return -1

    def get_selected_index():
        return get_selected()

    def get_item(i):
        try:
            items = handle.get("items") or []
            if 0 <= int(i) < len(items):
                return items[int(i)]
        except Exception:
            pass
        return ""

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            lb.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            lb.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def _on_select(evt):
        cb = handle.get("onSelect")
        if cb is not None and callable(cb):
            try:
                cb(get_selected())
            except Exception as exc:
                sys.stderr.write(f"[HwdUI] onSelect: {exc}\n")

    lb.bind("<<ListboxSelect>>", _on_select)

    def init_listbox():
        pass

    # onChange is an alias for onSelect (used by H# code)
    def on_change_setter(cb=None):
        handle["onSelect"] = cb

    handle["init_listbox"] = init_listbox
    handle["set_items"] = set_items
    handle["add_item"] = add_item
    handle["clear"] = clear
    handle["set_selected"] = set_selected
    handle["get_selected"] = get_selected
    handle["get_selected_index"] = get_selected_index
    handle["get_item"] = get_item
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    handle["onChange"] = on_change_setter
    return handle


def make_menubar():
    handle = _make_handle(None, "MenuBar", {"_menus": []})

    def add_menu(menu):
        handle["_menus"].append(menu)

    def init_menubar():
        pass

    handle["init_menubar"] = init_menubar
    handle["add_menu"] = add_menu
    handle["add_child"] = add_menu
    return handle


def make_menu(title=""):
    handle = _make_handle(None, "Menu", {"title": str(title), "_items": []})

    def add_item(item):
        handle["_items"].append(item)

    def init_menu(t=""):
        handle["title"] = str(t)

    handle["init_menu"] = init_menu
    handle["add_item"] = add_item
    return handle


def make_toolbar():
    handle = _make_handle(None, "ToolBar", {"_buttons": []})

    def add_tool_button(btn):
        handle["_buttons"].append(btn)

    def set_pos(x, y):
        handle["_x"] = int(x)
        handle["_y"] = int(y)

    def set_size(w, h):
        handle["_w"] = int(w)
        handle["_h"] = int(h)

    def init_toolbar():
        pass

    handle["init_toolbar"] = init_toolbar
    handle["add_tool_button"] = add_tool_button
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    handle["add_child"] = lambda x: handle["_buttons"].append(x)
    return handle


def make_toolbutton(text=""):
    handle = _make_handle(None, "ToolButton", {"text": str(text)})

    def init_tool_button(t=""):
        handle["text"] = str(t)

    def on_click_setter(cb=None):
        handle["onClick"] = cb

    handle["init_tool_button"] = init_tool_button
    handle["onClick"] = on_click_setter
    return handle


def make_menuitem(text=""):
    handle = _make_handle(None, "MenuItem", {"text": str(text)})

    def init_menu_item(t=""):
        handle["text"] = str(t)

    def on_click_setter(cb=None):
        handle["onClick"] = cb

    handle["init_menu_item"] = init_menu_item
    handle["onClick"] = on_click_setter
    return handle


def make_statusbar():
    _ensure_tk()
    frm = _tk.Frame(_parent(), bg=_THEME["bg_soft"], height=22)
    left = _tk.Label(frm, text="", bg=_THEME["bg_soft"], fg=_THEME["fg"],
                     anchor="w", padx=8, font=("Helvetica", 10))
    right = _tk.Label(frm, text="", bg=_THEME["bg_soft"], fg=_THEME["fg_dim"],
                      anchor="e", padx=8, font=("Helvetica", 10))
    left.pack(side="left", fill="x", expand=True)
    right.pack(side="right", fill="x")
    handle = _make_handle(frm, "StatusBar", {"_left": "", "_right": ""})

    def set_left(t):
        try:
            left.configure(text=str(t))
        except Exception:
            pass
        handle["_left"] = str(t)

    def set_right(t):
        try:
            right.configure(text=str(t))
        except Exception:
            pass
        handle["_right"] = str(t)

    def set_bg(c):
        try:
            frm.configure(bg=str(c))
            left.configure(bg=str(c))
            right.configure(bg=str(c))
        except Exception:
            pass

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            frm.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            frm.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def init_statusbar():
        pass

    handle["init_statusbar"] = init_statusbar
    handle["set_left"] = set_left
    handle["set_right"] = set_right
    handle["set_bg_color"] = set_bg
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    return handle


def make_tabcontrol():
    """A simple horizontal tab strip. Each add_tab() inserts a Label
    styled as a tab. We don't implement a real Notebook because the IDE
    uses the tab strip only as a visual header; the actual content area
    is rendered separately by the parent panel."""
    _ensure_tk()
    frm = _tk.Frame(_parent(), bg=_THEME["bg_alt"], height=24)
    handle = _make_handle(frm, "TabControl", {"tabs": []})
    _tab_labels = []

    def _relayout():
        for i, lbl in enumerate(_tab_labels):
            try:
                lbl.pack(side="left", padx=(2, 2), pady=2)
            except Exception:
                pass

    def add_tab(title):
        try:
            lbl = _tk.Label(frm, text=str(title), bg=_THEME["bg_soft"],
                            fg=_THEME["fg"], padx=10, pady=2,
                            font=("Helvetica", 10))
            _tab_labels.append(lbl)
            handle["tabs"].append(str(title))
            _relayout()
        except Exception:
            pass

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            frm.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            frm.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def init_tabcontrol():
        pass

    handle["init_tabcontrol"] = init_tabcontrol
    handle["add_tab"] = add_tab
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    return handle


# ========== Entry points (called from H#) ==========
def hwdui_init():
    _ensure_tk()
    _get_app()
    return True


def hwdui_theme_dark():
    global _theme_name
    _theme_name = "dark"
    return True


def hwdui_create_window(title, w, h):
    return make_window(title, w, h)


def ui_run():
    """Block until all windows are closed, then return."""
    _ensure_tk()
    app = _get_app()
    try:
        app.mainloop()
    except Exception as exc:
        sys.stderr.write(f"[HwdUI] mainloop error: {exc}\n")


def ui_quit():
    _ensure_tk()
    app = _get_app()
    try:
        app.quit()
    except Exception:
        pass


def notify_info(title, message):
    _ensure_tk()
    _tk_msg["mb"].showinfo(str(title), str(message))


def notify_error(title, message):
    _ensure_tk()
    _tk_msg["mb"].showerror(str(title), str(message))


def notify_warning(title, message):
    _ensure_tk()
    _tk_msg["mb"].showwarning(str(title), str(message))


def make_checkbox(initial_text="", checked=False):
    _ensure_tk()
    var = _tk.BooleanVar(value=bool(checked))
    cb = _tk.Checkbutton(_parent(), text=str(initial_text),
                         variable=var, bg=_THEME["bg_soft"],
                         fg=_THEME["fg"], selectcolor=_THEME["bg_alt"],
                         activebackground=_THEME["bg_soft"],
                         activeforeground=_THEME["fg"],
                         font=("Helvetica", 11))
    handle = _make_handle(cb, "CheckBox", {"text": str(initial_text), "checked": bool(checked)})

    def set_text(t):
        try:
            cb.configure(text=str(t))
        except Exception:
            pass
        handle["text"] = str(t)

    def set_checked(b):
        try:
            var.set(bool(b))
        except Exception:
            pass
        handle["checked"] = bool(b)

    def is_checked():
        return bool(var.get())

    def set_pos(x, y):
        _store_xy(handle, x, y)
        try:
            cb.place(x=int(x), y=int(y))
        except Exception:
            pass

    def set_size(w, h):
        _store_wh(handle, w, h)
        try:
            cb.place_configure(width=int(w), height=int(h))
        except Exception:
            pass

    def init_checkbox():
        pass

    handle["init_checkbox"] = init_checkbox
    handle["set_text"] = set_text
    handle["set_checked"] = set_checked
    handle["is_checked"] = is_checked
    handle["get_checked"] = is_checked
    handle["set_pos"] = set_pos
    handle["set_size"] = set_size
    return handle


# ========== Widget registry ==========
WIDGET_FACTORIES = {
    "Window": make_window,
    "Panel": make_panel,
    "Label": make_label,
    "Button": make_button,
    "TextBox": make_textbox,
    "ListBox": make_listbox,
    "MenuBar": make_menubar,
    "Menu": make_menu,
    "MenuItem": make_menuitem,
    "ToolBar": make_toolbar,
    "ToolButton": make_toolbutton,
    "StatusBar": make_statusbar,
    "TabControl": make_tabcontrol,
    "CheckBox": make_checkbox,
}


def make_widget(class_name, args):
    """Dispatch new WidgetClass(args) to the right factory."""
    factory = WIDGET_FACTORIES.get(class_name)
    if factory is None:
        raise RuntimeError(f"HwdUI: unknown widget class '{class_name}'")
    return factory(*args)


def get_theme():
    return dict(_THEME)
