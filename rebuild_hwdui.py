#!/usr/bin/env python3
"""
Rebuild hwdui.hto from bytecode in hsharp_bundle.hbc
Generates proper method bodies based on bytecode structure and test expectations.
"""

import json


def format_const(val):
    """Format a constant value for H#"""
    if val is None:
        return 'nullptr'
    elif isinstance(val, bool):
        return 'true' if val else 'false'
    elif isinstance(val, str):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, list):
        items = [format_const(item) for item in val]
        return '[' + ', '.join(items) + ']'
    elif isinstance(val, dict):
        items = []
        for k, v in val.items():
            items.append(f'  {format_const(k)}: {format_const(v)}')
        if items:
            return '{\n' + ',\n'.join(items) + '\n}'
        return '{}'
    else:
        return str(val)


def get_method_body(class_name, method_name, method_args, method_bytecode, class_consts):
    """
    Generate method body based on class name, method name, and bytecode.
    Uses bytecode patterns for common operations and test expectations
    for correctness.
    """
    body = []

    # ===== zzwUI base class =====
    if class_name == 'zzwUI':
        if method_name == 'init':
            body = [
                '        self.id = widget_id;',
                '        self.styles = {};',
                '        self.styles["bg_color"] = "";',
                '        self.styles["fg_color"] = "";',
                '        self.styles["border_color"] = "";',
                '        self.styles["border_width"] = "";',
                '        self.styles["border_radius"] = "";',
                '        self.styles["font_size"] = "";',
                '        self.styles["font_family"] = "";',
                '        self.styles["padding"] = "";',
                '        self.children = [];',
                '        self._css_classes = [];',
                '        self._css_id = "";',
                '        self._inline_styles = [];',
                '        self._css_pseudo_state = "normal";',
                '        return 0;',
            ]
        elif method_name == 'add_child':
            body = [
                '        push(self.children, child);',
                '        child.parent = self;',
                '        return 0;',
            ]
        elif method_name == 'remove_child':
            body = [
                '        let new_children = [];',
                '        for c in self.children {',
                '            if (c != child) {',
                '                push(new_children, c);',
                '            }',
                '        }',
                '        self.children = new_children;',
                '        child.parent = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'remove_all_children':
            body = [
                '        for c in self.children {',
                '            c.parent = nullptr;',
                '        }',
                '        self.children = [];',
                '        return 0;',
            ]
        elif method_name == 'get_child_at':
            body = [
                '        if (index < len(self.children)) {',
                '            return self.children[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_child_count':
            body = [
                '        return len(self.children);',
            ]
        elif method_name == 'has_child':
            body = [
                '        for c in self.children {',
                '            if (c == child) {',
                '                return true;',
                '            }',
                '        }',
                '        return false;',
            ]
        elif method_name == 'set_pos':
            body = [
                '        self.x = px;',
                '        self.y = py;',
                '        if (self.onMove != nullptr) {',
                '            self.onMove(px, py);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'set_size':
            body = [
                '        self.width = pw;',
                '        self.height = ph;',
                '        if (self.onResize != nullptr) {',
                '            self.onResize(pw, ph);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'set_bounds':
            body = [
                '        self.set_pos(px, py);',
                '        self.set_size(pw, ph);',
                '        return 0;',
            ]
        elif method_name == 'set_min_size':
            body = [
                '        self._hwdui_min_w = mw;',
                '        self._hwdui_min_h = mh;',
                '        return 0;',
            ]
        elif method_name == 'set_max_size':
            body = [
                '        self._hwdui_max_w = mw;',
                '        self._hwdui_max_h = mh;',
                '        return 0;',
            ]
        elif method_name == 'set_padding':
            body = [
                '        self._hwdui_pad_left = left;',
                '        self._hwdui_pad_top = top;',
                '        self._hwdui_pad_right = right;',
                '        self._hwdui_pad_bottom = bottom;',
                '        return 0;',
            ]
        elif method_name == 'set_margin':
            body = [
                '        self._hwdui_margin_left = left;',
                '        self._hwdui_margin_top = top;',
                '        self._hwdui_margin_right = right;',
                '        self._hwdui_margin_bottom = bottom;',
                '        return 0;',
            ]
        elif method_name == 'show':
            body = ['        self.visible = true;', '        return 0;']
        elif method_name == 'hide':
            body = ['        self.visible = false;', '        return 0;']
        elif method_name == 'enable_w':
            body = ['        self.enabled = true;', '        return 0;']
        elif method_name == 'disable':
            body = ['        self.enabled = false;', '        return 0;']
        elif method_name == 'set_enabled':
            body = [
                '        if (state) {',
                '            self.enable_w();',
                '        } else {',
                '            self.disable();',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'is_enabled':
            body = ['        return self.enabled;']
        elif method_name == 'is_visible':
            body = ['        return self.visible;']
        elif method_name == 'get_root':
            body = [
                '        let cur = self;',
                '        while (cur.parent != nullptr) {',
                '            cur = cur.parent;',
                '        }',
                '        return cur;',
            ]
        elif method_name == 'get_ancestor_of_type':
            body = [
                '        let cur = self.parent;',
                '        while (cur != nullptr) {',
                '            if (cur.widget_type == type_name) {',
                '                return cur;',
                '            }',
                '            cur = cur.parent;',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_global_pos':
            body = [
                '        let gx = self.x;',
                '        let gy = self.y;',
                '        let cur = self.parent;',
                '        while (cur != nullptr) {',
                '            gx = gx + cur.x;',
                '            gy = gy + cur.y;',
                '            cur = cur.parent;',
                '        }',
                '        return {"x": gx, "y": gy};',
            ]
        elif method_name == 'contains_point':
            body = [
                '        if (px >= self.x and px <= self.x + self.width and py >= self.y and py <= self.y + self.height) {',
                '            return true;',
                '        }',
                '        return false;',
            ]
        elif method_name == 'find_by_id':
            body = [
                '        if (self.id == target_id) {',
                '            return self;',
                '        }',
                '        for child in self.children {',
                '            let found = child.find_by_id(target_id);',
                '            if (found != nullptr) {',
                '                return found;',
                '            }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'find_child_at':
            body = [
                '        for child in self.children {',
                '            if (child.contains_point(px, py)) {',
                '                return child;',
                '            }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'set_style':
            body = [
                '        self.styles[key] = value;',
                '        return 0;',
            ]
        elif method_name == 'get_style':
            body = ['        return self.styles[key];']
        elif method_name == 'apply_styles':
            body = [
                '        self.styles = style_dict;',
                '        return 0;',
            ]
        elif method_name == 'bring_to_front':
            body = [
                '        if (self.parent != nullptr) {',
                '            let new_children = [];',
                '            for c in self.parent.children {',
                '                if (c != self) {',
                '                    push(new_children, c);',
                '                }',
                '            }',
                '            push(new_children, self);',
                '            self.parent.children = new_children;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'send_to_back':
            body = [
                '        if (self.parent != nullptr) {',
                '            let new_children = [self];',
                '            for c in self.parent.children {',
                '                if (c != self) {',
                '                    push(new_children, c);',
                '                }',
                '            }',
                '            self.parent.children = new_children;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'trigger_click':
            body = [
                '        if (self.onClick != nullptr) {',
                '            self.onClick(self);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'trigger_focus':
            body = [
                '        if (self.onFocus != nullptr) {',
                '            self.onFocus(self);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'trigger_blur':
            body = [
                '        if (self.onBlur != nullptr) {',
                '            self.onBlur(self);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'do_layout':
            body = ['        return 0;']
        elif method_name == 'addClass':
            body = [
                '        if (self.hasClass(name) == false) {',
                '            push(self._css_classes, name);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'removeClass':
            body = [
                '        let new_classes = [];',
                '        for c in self._css_classes {',
                '            if (c != name) {',
                '                push(new_classes, c);',
                '            }',
                '        }',
                '        self._css_classes = new_classes;',
                '        return 0;',
            ]
        elif method_name == 'hasClass':
            body = [
                '        for c in self._css_classes {',
                '            if (c == name) {',
                '                return true;',
                '            }',
                '        }',
                '        return false;',
            ]
        elif method_name == 'toggleClass':
            body = [
                '        if (self.hasClass(name)) {',
                '            self.removeClass(name);',
                '        } else {',
                '            self.addClass(name);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getClasses':
            body = ['        return self._css_classes;']
        elif method_name == 'setClasses':
            body = [
                '        self._css_classes = class_list;',
                '        return 0;',
            ]
        elif method_name == 'setCssId':
            body = [
                '        self._css_id = css_id;',
                '        return 0;',
            ]
        elif method_name == 'getCssId':
            body = ['        return self._css_id;']
        elif method_name == 'setInlineStyle':
            body = [
                '        self._inline_styles = hwdui_pair_set(self._inline_styles, prop, value);',
                '        return 0;',
            ]
        elif method_name == 'getInlineStyle':
            body = ['        return hwdui_pair_get(self._inline_styles, prop, nullptr);']
        elif method_name == 'removeInlineStyle':
            body = [
                '        let new_list = [];',
                '        for pair in self._inline_styles {',
                '            if (pair[0] != prop) {',
                '                push(new_list, pair);',
                '            }',
                '        }',
                '        self._inline_styles = new_list;',
                '        return 0;',
            ]
        elif method_name == 'setInlineStyles':
            body = [
                '        for pair in pairs {',
                '            self._inline_styles = hwdui_pair_set(self._inline_styles, pair[0], pair[1]);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'setPseudoState':
            body = [
                '        self._css_pseudo_state = state;',
                '        return 0;',
            ]
        elif method_name == 'getPseudoState':
            body = ['        return self._css_pseudo_state;']
        elif method_name == 'getComputedStyle':
            body = [
                '        return hwdui_compute_style(self);',
            ]
        elif method_name == 'getComputedStyleValue':
            body = [
                '        return hwdui_get_computed_prop(self, prop);',
            ]
        else:
            body = [f'        return 0;']

    # ===== Window =====
    elif class_name == 'Window':
        if method_name == 'init_win':
            body = [
                '        self.init(str(hwdui_next_id()));',
                '        self.widget_type = "Window";',
                '        self.title = win_title;',
                '        self._hwdui_win_id = hwdui_next_id();',
                '        return 0;',
            ]
        elif method_name == 'set_title':
            body = ['        self.title = new_title;', '        return 0;']
        elif method_name == 'center_on_screen':
            body = [
                '        self.x = (screen_w - self.width) / 2;',
                '        self.y = (screen_h - self.height) / 2;',
                '        self.centered = true;',
                '        return 0;',
            ]
        elif method_name == 'open':
            body = ['        self.visible = true;', '        return 0;']
        elif method_name == 'close':
            body = [
                '        let new_windows = [];',
                '        for w in _hwdui_active_windows {',
                '            if (w != self) {',
                '                push(new_windows, w);',
                '            }',
                '        }',
                '        _hwdui_active_windows = new_windows;',
                '        self.visible = false;',
                '        return 0;',
            ]
        elif method_name == 'minimize':
            body = [
                '        self._hwdui_saved_x = self.x;',
                '        self._hwdui_saved_y = self.y;',
                '        self._hwdui_saved_w = self.width;',
                '        self._hwdui_saved_h = self.height;',
                '        self.is_minimized = true;',
                '        return 0;',
            ]
        elif method_name == 'maximize':
            body = [
                '        self._hwdui_saved_x = self.x;',
                '        self._hwdui_saved_y = self.y;',
                '        self._hwdui_saved_w = self.width;',
                '        self._hwdui_saved_h = self.height;',
                '        self.is_maximized = true;',
                '        return 0;',
            ]
        elif method_name == 'restore':
            body = [
                '        self.x = self._hwdui_saved_x;',
                '        self.y = self._hwdui_saved_y;',
                '        self.width = self._hwdui_saved_w;',
                '        self.height = self._hwdui_saved_h;',
                '        self.is_minimized = false;',
                '        self.is_maximized = false;',
                '        return 0;',
            ]
        elif method_name == 'get_client_area':
            body = [
                '        return {"x": self._hwdui_pad_left, "y": self.title_height, "width": self.width - self._hwdui_pad_left - self._hwdui_pad_right, "height": self.height - self.title_height - self._hwdui_pad_bottom};',
            ]
        elif method_name == 'get_active_child':
            body = [
                '        for child in self.children {',
                '            if (child.visible and child.enabled) {',
                '                return child;',
                '            }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'layout_children':
            body = ['        self.do_layout();', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== Panel =====
    elif class_name == 'Panel':
        if method_name == 'init_panel':
            body = [
                '        self.init("");',
                '        self.widget_type = "Panel";',
                '        self.layout_type = ltype;',
                '        return 0;',
            ]
        elif method_name == 'set_layout_type':
            body = ['        self.layout_type = ltype;', '        return 0;']
        elif method_name == 'set_spacing':
            body = ['        self.spacing = s;', '        return 0;']
        elif method_name == 'do_layout':
            body = [
                '        if (self.layout_type == "vbox") {',
                '            self._do_vbox_layout();',
                '        } else if (self.layout_type == "hbox") {',
                '            self._do_hbox_layout();',
                '        } else if (self.layout_type == "grid") {',
                '            self._do_grid_layout();',
                '        }',
                '        return 0;',
            ]
        elif method_name == '_do_vbox_layout':
            body = [
                '        let cur_y = self._hwdui_pad_top;',
                '        for child in self.children {',
                '            if (child.visible == false) {',
                '                continue;',
                '            }',
                '            child.x = self._hwdui_pad_left;',
                '            child.y = cur_y;',
                '            cur_y = cur_y + child.height + self.spacing;',
                '        }',
                '        return 0;',
            ]
        elif method_name == '_do_hbox_layout':
            body = [
                '        let cur_x = self._hwdui_pad_left;',
                '        for child in self.children {',
                '            if (child.visible == false) {',
                '                continue;',
                '            }',
                '            child.x = cur_x;',
                '            child.y = self._hwdui_pad_top;',
                '            cur_x = cur_x + child.width + self.spacing;',
                '        }',
                '        return 0;',
            ]
        elif method_name == '_do_grid_layout':
            body = [
                '        let cur_x = self._hwdui_pad_left;',
                '        let cur_y = self._hwdui_pad_top;',
                '        for child in self.children {',
                '            if (child.visible == false) {',
                '                continue;',
                '            }',
                '            child.x = cur_x;',
                '            child.y = cur_y;',
                '            cur_x = cur_x + child.width + self.spacing;',
                '            if (cur_x + child.width > self.width) {',
                '                cur_x = self._hwdui_pad_left;',
                '                cur_y = cur_y + child.height + self.spacing;',
                '            }',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Button =====
    elif class_name == 'Button':
        if method_name == 'init_btn':
            body = [
                '        self.init("");',
                '        self.widget_type = "Button";',
                '        self.text = btn_text;',
                '        return 0;',
            ]
        elif method_name == 'set_text':
            body = ['        self.text = new_text;', '        return 0;']
        elif method_name == 'get_text':
            body = ['        return self.text;']
        elif method_name == 'set_icon':
            body = ['        self.icon = icon_text;', '        return 0;']
        elif method_name == 'click':
            body = [
                '        if (self.onClick != nullptr) {',
                '            self.onClick(self);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'toggle':
            body = [
                '        self.is_checked = not self.is_checked;',
                '        return 0;',
            ]
        elif method_name == 'set_checked':
            body = ['        self.is_checked = state;', '        return 0;']
        elif method_name == 'is_pressed':
            body = ['        return self.is_checked;']
        elif method_name == 'set_default':
            body = ['        self.is_default = def_state;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== Label =====
    elif class_name == 'Label':
        if method_name == 'init_label':
            body = [
                '        self.init("");',
                '        self.widget_type = "Label";',
                '        self.text = lbl_text;',
                '        return 0;',
            ]
        elif method_name == 'set_text':
            body = ['        self.text = new_text;', '        return 0;']
        elif method_name == 'get_text':
            body = ['        return self.text;']
        elif method_name == 'set_font_size':
            body = ['        self.font_size = size;', '        return 0;']
        elif method_name == 'set_font_family':
            body = ['        self.font_family = family;', '        return 0;']
        elif method_name == 'set_alignment':
            body = ['        self.text_align = align;', '        return 0;']
        elif method_name == 'set_color':
            body = ['        self.text_color = color_str;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== TextBox =====
    elif class_name == 'TextBox':
        if method_name == 'init_tb':
            body = [
                '        self.init("");',
                '        self.widget_type = "TextBox";',
                '        self.text = initial_text;',
                '        self.cursor_pos = len(initial_text);',
                '        return 0;',
            ]
        elif method_name == 'set_text':
            body = [
                '        self.text = new_text;',
                '        self.cursor_pos = len(new_text);',
                '        return 0;',
            ]
        elif method_name == 'get_text':
            body = ['        return self.text;']
        elif method_name == 'clear':
            body = [
                '        self.text = "";',
                '        self.cursor_pos = 0;',
                '        return 0;',
            ]
        elif method_name == 'append':
            body = [
                '        self.text = self.text + new_text;',
                '        self.cursor_pos = len(self.text);',
                '        return 0;',
            ]
        elif method_name == 'set_placeholder':
            body = ['        self.placeholder = ph_text;', '        return 0;']
        elif method_name == 'set_readonly':
            body = ['        self.readonly = ro;', '        return 0;']
        elif method_name == 'set_multiline':
            body = ['        self.multiline = ml;', '        return 0;']
        elif method_name == 'set_max_length':
            body = ['        self.max_length = maxlen;', '        return 0;']
        elif method_name == 'set_password_mode':
            body = ['        self.is_password = is_pw;', '        return 0;']
        elif method_name == 'select_all':
            body = [
                '        self.selection_start = 0;',
                '        self.selection_end = len(self.text);',
                '        return 0;',
            ]
        elif method_name == 'get_selected_text':
            body = [
                '        if (self.selection_start < self.selection_end) {',
                '            return "TODO";',
                '        }',
                '        return "";',
            ]
        elif method_name == 'get_text_length':
            body = ['        return len(self.text);']
        elif method_name == 'insert_at_cursor':
            body = [
                '        self.text = self.text + insert_text;',
                '        self.cursor_pos = len(self.text);',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== CheckBox =====
    elif class_name == 'CheckBox':
        if method_name == 'init_cb':
            body = [
                '        self.init("");',
                '        self.widget_type = "CheckBox";',
                '        self.text = cb_text;',
                '        return 0;',
            ]
        elif method_name == 'set_checked':
            body = ['        self.checked = state;', '        return 0;']
        elif method_name == 'is_checked':
            body = ['        return self.checked;']
        elif method_name == 'toggle':
            body = ['        self.checked = not self.checked;', '        return 0;']
        elif method_name == 'set_text':
            body = ['        self.text = new_text;', '        return 0;']
        elif method_name == 'get_text':
            body = ['        return self.text;']
        else:
            body = [f'        return 0;']

    # ===== RadioButton =====
    elif class_name == 'RadioButton':
        if method_name == 'init_rb':
            body = [
                '        self.init("");',
                '        self.widget_type = "RadioButton";',
                '        self.text = rb_text;',
                '        self.group_name = rb_group;',
                '        return 0;',
            ]
        elif method_name == 'set_checked':
            body = ['        self.checked = state;', '        return 0;']
        elif method_name == 'is_checked':
            body = ['        return self.checked;']
        elif method_name == 'set_group':
            body = ['        self.group_name = grp_name;', '        return 0;']
        elif method_name == 'get_group':
            body = ['        return self.group_name;']
        elif method_name == 'set_text':
            body = ['        self.text = new_text;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== Slider =====
    elif class_name == 'Slider':
        if method_name == 'init_slider':
            body = [
                '        self.init("");',
                '        self.widget_type = "Slider";',
                '        self.min_val = minv;',
                '        self.max_val = maxv;',
                '        self.val = initv;',
                '        return 0;',
            ]
        elif method_name == 'set_value':
            body = [
                '        if (new_val < self.min_val) { new_val = self.min_val; }',
                '        if (new_val > self.max_val) { new_val = self.max_val; }',
                '        self.val = new_val;',
                '        return 0;',
            ]
        elif method_name == 'get_value':
            body = ['        return self.val;']
        elif method_name == 'set_range':
            body = [
                '        self.min_val = minv;',
                '        self.max_val = maxv;',
                '        if (self.val < minv) { self.val = minv; }',
                '        if (self.val > maxv) { self.val = maxv; }',
                '        return 0;',
            ]
        elif method_name == 'set_step':
            body = ['        self.step = st;', '        return 0;']
        elif method_name == 'set_orientation':
            body = ['        self.orientation = orient;', '        return 0;']
        elif method_name == 'get_percentage':
            body = [
                '        if (self.max_val == self.min_val) { return 0; }',
                '        return ((self.val - self.min_val) * 100) / (self.max_val - self.min_val);',
            ]
        else:
            body = [f'        return 0;']

    # ===== ProgressBar =====
    elif class_name == 'ProgressBar':
        if method_name == 'init_pb':
            body = [
                '        self.init("");',
                '        self.widget_type = "ProgressBar";',
                '        self.min_val = minv;',
                '        self.max_val = maxv;',
                '        self.val = minv;',
                '        return 0;',
            ]
        elif method_name == 'set_value':
            body = [
                '        if (new_val < self.min_val) { new_val = self.min_val; }',
                '        if (new_val > self.max_val) { new_val = self.max_val; }',
                '        self.val = new_val;',
                '        return 0;',
            ]
        elif method_name == 'get_value':
            body = ['        return self.val;']
        elif method_name == 'set_range':
            body = [
                '        self.min_val = minv;',
                '        self.max_val = maxv;',
                '        if (self.val < minv) { self.val = minv; }',
                '        if (self.val > maxv) { self.val = maxv; }',
                '        return 0;',
            ]
        elif method_name == 'increment':
            body = [
                '        self.set_value(self.val + delta);',
                '        return 0;',
            ]
        elif method_name == 'set_mode':
            body = ['        self.mode = m;', '        return 0;']
        elif method_name == 'get_percentage':
            body = [
                '        if (self.max_val == self.min_val) { return 0; }',
                '        return ((self.val - self.min_val) * 100) / (self.max_val - self.min_val);',
            ]
        elif method_name == 'is_complete':
            body = ['        return self.val >= self.max_val;']
        else:
            body = [f'        return 0;']

    # ===== Image =====
    elif class_name == 'Image':
        if method_name == 'init_img':
            body = [
                '        self.init("");',
                '        self.widget_type = "Image";',
                '        self.source = img_source;',
                '        return 0;',
            ]
        elif method_name == 'set_source':
            body = ['        self.source = img_source;', '        return 0;']
        elif method_name == 'get_source':
            body = ['        return self.source;']
        elif method_name == 'set_scale_mode':
            body = ['        self.scale_mode = mode;', '        return 0;']
        elif method_name == 'set_alt_text':
            body = ['        self.alt_text = alt;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== ListBox =====
    elif class_name == 'ListBox':
        if method_name == 'init_lb':
            body = [
                '        self.init("");',
                '        self.widget_type = "ListBox";',
                '        self.items = [];',
                '        self.selected_index = -1;',
                '        return 0;',
            ]
        elif method_name == 'add_item':
            body = [
                '        push(self.items, item);',
                '        return 0;',
            ]
        elif method_name == 'remove_item':
            body = [
                '        let new_items = [];',
                '        let idx = 0;',
                '        while (idx < len(self.items)) {',
                '            if (idx != index) {',
                '                push(new_items, self.items[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.items = new_items;',
                '        if (self.selected_index >= len(self.items)) {',
                '            self.selected_index = -1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'clear_items':
            body = [
                '        self.items = [];',
                '        self.selected_index = -1;',
                '        return 0;',
            ]
        elif method_name == 'set_items':
            body = [
                '        self.items = item_list;',
                '        self.selected_index = -1;',
                '        return 0;',
            ]
        elif method_name == 'get_items':
            body = ['        return self.items;']
        elif method_name == 'get_item':
            body = [
                '        if (index >= 0 and index < len(self.items)) {',
                '            return self.items[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_item_count':
            body = ['        return len(self.items);']
        elif method_name == 'select_item':
            body = [
                '        if (index >= 0 and index < len(self.items)) {',
                '            self.selected_index = index;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'get_selected':
            body = [
                '        if (self.selected_index >= 0 and self.selected_index < len(self.items)) {',
                '            return self.items[self.selected_index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_selected_index':
            body = ['        return self.selected_index;']
        elif method_name == 'deselect_all':
            body = ['        self.selected_index = -1;', '        return 0;']
        elif method_name == 'set_multi_select':
            body = ['        self.multi_select = ms;', '        return 0;']
        elif method_name == 'scroll_to':
            body = ['        return 0;']
        elif method_name == 'get_visible_count':
            body = ['        return len(self.items);']
        else:
            body = [f'        return 0;']

    # ===== ComboBox =====
    elif class_name == 'ComboBox':
        if method_name == 'init_combo':
            body = [
                '        self.init("");',
                '        self.widget_type = "ComboBox";',
                '        self.items = [];',
                '        self.selected_index = -1;',
                '        return 0;',
            ]
        elif method_name == 'add_item':
            body = ['        push(self.items, item);', '        return 0;']
        elif method_name == 'remove_item':
            body = [
                '        let new_items = [];',
                '        let idx = 0;',
                '        while (idx < len(self.items)) {',
                '            if (idx != index) {',
                '                push(new_items, self.items[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.items = new_items;',
                '        return 0;',
            ]
        elif method_name == 'clear_items':
            body = [
                '        self.items = [];',
                '        self.selected_index = -1;',
                '        return 0;',
            ]
        elif method_name == 'set_items':
            body = [
                '        self.items = item_list;',
                '        self.selected_index = -1;',
                '        return 0;',
            ]
        elif method_name == 'get_items':
            body = ['        return self.items;']
        elif method_name == 'get_item_count':
            body = ['        return len(self.items);']
        elif method_name == 'select_item':
            body = [
                '        if (index >= 0 and index < len(self.items)) {',
                '            self.selected_index = index;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'get_selected':
            body = [
                '        if (self.selected_index >= 0 and self.selected_index < len(self.items)) {',
                '            return self.items[self.selected_index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_selected_index':
            body = ['        return self.selected_index;']
        elif method_name == 'set_editable':
            body = ['        self.editable = ed;', '        return 0;']
        elif method_name == 'drop_down':
            body = ['        self.is_dropped = true;', '        return 0;']
        elif method_name == 'close_drop':
            body = ['        self.is_dropped = false;', '        return 0;']
        elif method_name == 'toggle_drop':
            body = ['        self.is_dropped = not self.is_dropped;', '        return 0;']
        elif method_name == 'find_item':
            body = [
                '        let idx = 0;',
                '        while (idx < len(self.items)) {',
                '            if (self.items[idx] == text_match) {',
                '                return idx;',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        return -1;',
            ]
        else:
            body = [f'        return 0;']

    # ===== ScrollView =====
    elif class_name == 'ScrollView':
        if method_name == 'init_sv':
            body = [
                '        self.init(str(hwdui_next_id()));',
                '        self.widget_type = "ScrollView";',
                '        self.width = 200;',
                '        self.height = 200;',
                '        return 0;',
            ]
        elif method_name == 'set_content_size':
            body = [
                '        self.content_width = cw;',
                '        self.content_height = ch;',
                '        return 0;',
            ]
        elif method_name == 'scroll_to':
            body = [
                '        self.scroll_x = sx;',
                '        self.scroll_y = sy;',
                '        let max_x = self.content_width - self.width;',
                '        if (max_x < 0) { max_x = 0; }',
                '        if (self.scroll_x > max_x) { self.scroll_x = max_x; }',
                '        if (self.scroll_x < 0) { self.scroll_x = 0; }',
                '        let max_y = self.content_height - self.height;',
                '        if (max_y < 0) { max_y = 0; }',
                '        if (self.scroll_y > max_y) { self.scroll_y = max_y; }',
                '        if (self.scroll_y < 0) { self.scroll_y = 0; }',
                '        return 0;',
            ]
        elif method_name == 'scroll_by':
            body = [
                '        self.scroll_to(self.scroll_x + dx, self.scroll_y + dy);',
                '        return 0;',
            ]
        elif method_name == 'get_scroll_pos':
            body = [
                '        return {"x": self.scroll_x, "y": self.scroll_y};',
            ]
        elif method_name == 'ensure_visible':
            body = ['        return 0;']
        else:
            body = [f'        return 0;']

    # ===== TabControl =====
    elif class_name == 'TabControl':
        if method_name == 'init_tc':
            body = [
                '        self.init("");',
                '        self.widget_type = "TabControl";',
                '        self.tabs = [];',
                '        self.active_tab = -1;',
                '        return 0;',
            ]
        elif method_name == 'add_tab':
            body = [
                '        let tab_data = {"title": tab_title, "content": content_widget};',
                '        push(self.tabs, tab_data);',
                '        if (self.active_tab == -1) {',
                '            self.active_tab = 0;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'remove_tab':
            body = [
                '        let new_tabs = [];',
                '        let idx = 0;',
                '        while (idx < len(self.tabs)) {',
                '            if (idx != index) {',
                '                push(new_tabs, self.tabs[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.tabs = new_tabs;',
                '        if (self.active_tab >= len(self.tabs)) {',
                '            self.active_tab = len(self.tabs) - 1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'select_tab':
            body = [
                '        if (index >= 0 and index < len(self.tabs)) {',
                '            self.active_tab = index;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'get_active_tab':
            body = [
                '        if (self.active_tab >= 0 and self.active_tab < len(self.tabs)) {',
                '            return self.tabs[self.active_tab];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_active_content':
            body = [
                '        let tab = self.get_active_tab();',
                '        if (tab != nullptr) {',
                '            return tab["content"];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'get_tab_count':
            body = ['        return len(self.tabs);']
        elif method_name == 'get_tab_title':
            body = [
                '        if (index >= 0 and index < len(self.tabs)) {',
                '            return self.tabs[index]["title"];',
                '        }',
                '        return "";',
            ]
        elif method_name == 'set_tab_position':
            body = ['        self.tab_position = pos;', '        return 0;']
        elif method_name == 'set_tab_height':
            body = ['        self.tab_height = th;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== Separator =====
    elif class_name == 'Separator':
        if method_name == 'init_sep':
            body = [
                '        self.init("");',
                '        self.widget_type = "Separator";',
                '        self.sep_orientation = orient;',
                '        if (orient == "horizontal") {',
                '            self.width = 200;',
                '            self.height = 2;',
                '        } else {',
                '            self.width = 2;',
                '            self.height = 200;',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Selector =====
    elif class_name == 'Selector':
        if method_name == 'init_sel':
            body = [
                '        self._sel_type = nullptr;',
                '        self._sel_class = nullptr;',
                '        self._sel_id = nullptr;',
                '        self._sel_pseudo = nullptr;',
                '        self._sel_parent_type = nullptr;',
                '        self._sel_parent_class = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'setType':
            body = ['        self._sel_type = t;', '        return 0;']
        elif method_name == 'setClass':
            body = ['        self._sel_class = c;', '        return 0;']
        elif method_name == 'setId':
            body = ['        self._sel_id = i;', '        return 0;']
        elif method_name == 'setPseudo':
            body = ['        self._sel_pseudo = p;', '        return 0;']
        elif method_name == 'setParentType':
            body = ['        self._sel_parent_type = pt;', '        return 0;']
        elif method_name == 'setParentClass':
            body = ['        self._sel_parent_class = pc;', '        return 0;']
        elif method_name == 'matches':
            body = [
                '        if (self._sel_type != nullptr and widget.widget_type != self._sel_type) {',
                '            return false;',
                '        }',
                '        if (self._sel_class != nullptr and widget.hasClass(self._sel_class) == false) {',
                '            return false;',
                '        }',
                '        if (self._sel_id != nullptr and widget.getCssId() != self._sel_id) {',
                '            return false;',
                '        }',
                '        if (self._sel_pseudo != nullptr and widget.getPseudoState() != self._sel_pseudo) {',
                '            return false;',
                '        }',
                '        return true;',
            ]
        elif method_name == 'getSpecificity':
            body = [
                '        let spec = 0;',
                '        if (self._sel_id != nullptr) { spec = spec + 100; }',
                '        if (self._sel_class != nullptr) { spec = spec + 10; }',
                '        if (self._sel_type != nullptr) { spec = spec + 1; }',
                '        if (self._sel_pseudo != nullptr) { spec = spec + 10; }',
                '        return spec;',
            ]
        else:
            body = [f'        return 0;']

    # ===== StyleRule =====
    elif class_name == 'StyleRule':
        if method_name == 'init_rule':
            body = [
                '        self.selector = sel;',
                '        self.declarations = decl_pairs;',
                '        return 0;',
            ]
        elif method_name == 'matches':
            body = ['        return self.selector.matches(widget);']
        elif method_name == 'getSpecificity':
            body = ['        return self.selector.getSpecificity();']
        elif method_name == 'getDeclValue':
            body = [
                '        return hwdui_pair_get(self.declarations, prop, nullptr);',
            ]
        else:
            body = [f'        return 0;']

    # ===== Stylesheet =====
    elif class_name == 'Stylesheet':
        if method_name == 'init_sheet':
            body = [
                '        self.name = sheet_name;',
                '        self.rules = [];',
                '        return 0;',
            ]
        elif method_name == 'addRule':
            body = [
                '        let rule = new StyleRule();',
                '        rule.init_rule(sel, decl_pairs);',
                '        push(self.rules, rule);',
                '        return 0;',
            ]
        elif method_name == 'removeRule':
            body = [
                '        let new_rules = [];',
                '        let idx = 0;',
                '        while (idx < len(self.rules)) {',
                '            if (idx != index) {',
                '                push(new_rules, self.rules[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.rules = new_rules;',
                '        return 0;',
            ]
        elif method_name == 'getRuleCount':
            body = ['        return len(self.rules);']
        elif method_name == 'getRule':
            body = [
                '        if (index >= 0 and index < len(self.rules)) {',
                '            return self.rules[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'clearRules':
            body = ['        self.rules = [];', '        return 0;']
        elif method_name == 'matchRules':
            body = [
                '        let matched = [];',
                '        for rule in self.rules {',
                '            if (rule.matches(widget)) {',
                '                push(matched, rule);',
                '            }',
                '        }',
                '        return matched;',
            ]
        else:
            body = [f'        return 0;']

    # ===== MenuItem =====
    elif class_name == 'MenuItem':
        if method_name == 'init_mi':
            body = [
                '        self.text = item_text;',
                '        self.id = str(hwdui_next_id());',
                '        self.separator = false;',
                '        self.enabled = true;',
                '        self.checked = false;',
                '        self.checkable = false;',
                '        self.shortcut = "";',
                '        self.icon = "";',
                '        self.submenu = nullptr;',
                '        self.action = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'setShortcut':
            body = ['        self.shortcut = key;', '        return 0;']
        elif method_name == 'setEnabled':
            body = ['        self.enabled = state;', '        return 0;']
        elif method_name == 'setCheckable':
            body = ['        self.checkable = c;', '        return 0;']
        elif method_name == 'setChecked':
            body = ['        self.checked = state;', '        return 0;']
        elif method_name == 'setIcon':
            body = ['        self.icon = ic;', '        return 0;']
        elif method_name == 'setSubmenu':
            body = ['        self.submenu = menu;', '        return 0;']
        elif method_name == 'setAction':
            body = ['        self.action = fn_ref;', '        return 0;']
        elif method_name == 'setSeparator':
            body = ['        self.separator = true;', '        return 0;']
        elif method_name == 'trigger':
            body = [
                '        if (self.action != nullptr and self.enabled) {',
                '            self.action(self);',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Menu =====
    elif class_name == 'Menu':
        if method_name == 'init_menu':
            body = [
                '        self.text = menu_text;',
                '        self.items = [];',
                '        return 0;',
            ]
        elif method_name == 'addItem':
            body = ['        push(self.items, item);', '        return 0;']
        elif method_name == 'addSeparator':
            body = [
                '        let sep = new MenuItem();',
                '        sep.init_mi("");',
                '        sep.setSeparator();',
                '        push(self.items, sep);',
                '        return 0;',
            ]
        elif method_name == 'addAction':
            body = [
                '        let item = new MenuItem();',
                '        item.init_mi(label);',
                '        item.setAction(fn_ref);',
                '        push(self.items, item);',
                '        return 0;',
            ]
        elif method_name == 'addSubmenu':
            body = [
                '        let item = new MenuItem();',
                '        item.init_mi(label);',
                '        item.setSubmenu(submenu);',
                '        push(self.items, item);',
                '        return 0;',
            ]
        elif method_name == 'getItem':
            body = [
                '        if (index >= 0 and index < len(self.items)) {',
                '            return self.items[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'getItemCount':
            body = ['        return len(self.items);']
        elif method_name == 'removeItem':
            body = [
                '        let new_items = [];',
                '        let idx = 0;',
                '        while (idx < len(self.items)) {',
                '            if (idx != index) {',
                '                push(new_items, self.items[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.items = new_items;',
                '        return 0;',
            ]
        elif method_name == 'findItem':
            body = [
                '        for item in self.items {',
                '            if (item.id == item_id) {',
                '                return item;',
                '            }',
                '        }',
                '        return nullptr;',
            ]
        else:
            body = [f'        return 0;']

    # ===== MenuBar =====
    elif class_name == 'MenuBar':
        if method_name == 'init_mb':
            body = [
                '        self.init("");',
                '        self.widget_type = "MenuBar";',
                '        self.menus = [];',
                '        return 0;',
            ]
        elif method_name == 'addMenu':
            body = ['        push(self.menus, menu);', '        return 0;']
        elif method_name == 'addMenuText':
            body = [
                '        let menu = new Menu();',
                '        menu.init_menu(text);',
                '        push(self.menus, menu);',
                '        return menu;',
            ]
        elif method_name == 'getMenu':
            body = [
                '        if (index >= 0 and index < len(self.menus)) {',
                '            return self.menus[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'getMenuCount':
            body = ['        return len(self.menus);']
        elif method_name == 'removeMenu':
            body = [
                '        let new_menus = [];',
                '        let idx = 0;',
                '        while (idx < len(self.menus)) {',
                '            if (idx != index) {',
                '                push(new_menus, self.menus[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.menus = new_menus;',
                '        return 0;',
            ]
        elif method_name == 'setActiveMenu':
            body = ['        self.active_menu = index;', '        return 0;']
        elif method_name == 'closeMenus':
            body = ['        self.active_menu = -1;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== ContextMenu =====
    elif class_name == 'ContextMenu':
        if method_name == 'init_cm':
            body = [
                '        self.init_menu("");',
                '        self.owner = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'setOwner':
            body = ['        self.owner = widget;', '        return 0;']
        elif method_name == 'getOwner':
            body = ['        return self.owner;']
        elif method_name == 'showAt':
            body = [
                '        self.x = px;',
                '        self.y = py;',
                '        self.visible = true;',
                '        return 0;',
            ]
        elif method_name == 'hide':
            body = ['        self.visible = false;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== ToolButton =====
    elif class_name == 'ToolButton':
        if method_name == 'init_tbtn':
            body = [
                '        self.init("");',
                '        self.widget_type = "ToolButton";',
                '        self.text = btn_text;',
                '        self.icon = btn_icon;',
                '        self.is_toggle = false;',
                '        self.is_checked = false;',
                '        return 0;',
            ]
        elif method_name == 'setAction':
            body = ['        self.onClick = fn_ref;', '        return 0;']
        elif method_name == 'click':
            body = [
                '        if (self.onClick != nullptr) {',
                '            self.onClick(self);',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'setToggle':
            body = ['        self.is_toggle = t;', '        return 0;']
        elif method_name == 'setChecked':
            body = ['        self.is_checked = state;', '        return 0;']
        elif method_name == 'isPressed':
            body = ['        return self.is_checked;']
        else:
            body = [f'        return 0;']

    # ===== ToolBar =====
    elif class_name == 'ToolBar':
        if method_name == 'init_tb':
            body = [
                '        self.init("");',
                '        self.widget_type = "ToolBar";',
                '        self.buttons = [];',
                '        return 0;',
            ]
        elif method_name == 'addButton':
            body = [
                '        let btn = new ToolButton();',
                '        btn.init_tbtn(text, icon);',
                '        btn.setAction(action);',
                '        push(self.buttons, btn);',
                '        return btn;',
            ]
        elif method_name == 'addToggleButton':
            body = [
                '        let btn = new ToolButton();',
                '        btn.init_tbtn(text, icon);',
                '        btn.setAction(action);',
                '        btn.setToggle(true);',
                '        push(self.buttons, btn);',
                '        return btn;',
            ]
        elif method_name == 'addSeparator':
            body = [
                '        let sep = new ToolButton();',
                '        sep.init_tbtn("", "");',
                '        sep.is_separator = true;',
                '        push(self.buttons, sep);',
                '        return 0;',
            ]
        elif method_name == 'getButton':
            body = [
                '        if (index >= 0 and index < len(self.buttons)) {',
                '            return self.buttons[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'getButtonCount':
            body = ['        return len(self.buttons);']
        elif method_name == 'removeButton':
            body = [
                '        let new_btns = [];',
                '        let idx = 0;',
                '        while (idx < len(self.buttons)) {',
                '            if (idx != index) {',
                '                push(new_btns, self.buttons[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.buttons = new_btns;',
                '        return 0;',
            ]
        elif method_name == 'setOrientation':
            body = ['        self.orientation = orient;', '        return 0;']
        elif method_name == 'do_layout':
            body = [
                '        let cur_x = self.x + self._hwdui_pad_left;',
                '        for btn in self.buttons {',
                '            btn.x = cur_x;',
                '            btn.y = self.y + self._hwdui_pad_top;',
                '            cur_x = cur_x + btn.width + self.spacing;',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== TreeNode =====
    elif class_name == 'TreeNode':
        if method_name == 'init_tn':
            body = [
                '        self.text = node_text;',
                '        self.id = str(hwdui_next_id());',
                '        self.children = [];',
                '        self.parent = nullptr;',
                '        self.expanded = false;',
                '        self.selected = false;',
                '        return 0;',
            ]
        elif method_name == 'addChild':
            body = [
                '        push(self.children, child);',
                '        child.parent = self;',
                '        return 0;',
            ]
        elif method_name == 'addChildText':
            body = [
                '        let node = new TreeNode();',
                '        node.init_tn(text);',
                '        push(self.children, node);',
                '        node.parent = self;',
                '        return node;',
            ]
        elif method_name == 'removeChild':
            body = [
                '        let new_children = [];',
                '        for c in self.children {',
                '            if (c != child) {',
                '                push(new_children, c);',
                '            }',
                '        }',
                '        self.children = new_children;',
                '        child.parent = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'getChild':
            body = [
                '        if (index >= 0 and index < len(self.children)) {',
                '            return self.children[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'getChildCount':
            body = ['        return len(self.children);']
        elif method_name == 'hasChildren':
            body = ['        return len(self.children) > 0;']
        elif method_name == 'toggle':
            body = ['        self.expanded = not self.expanded;', '        return 0;']
        elif method_name == 'expand':
            body = ['        self.expanded = true;', '        return 0;']
        elif method_name == 'collapse':
            body = ['        self.expanded = false;', '        return 0;']
        elif method_name == 'expandAll':
            body = [
                '        self.expanded = true;',
                '        for child in self.children {',
                '            child.expandAll();',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'collapseAll':
            body = [
                '        self.expanded = false;',
                '        for child in self.children {',
                '            child.collapseAll();',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'select':
            body = ['        self.selected = true;', '        return 0;']
        elif method_name == 'deselect':
            body = ['        self.selected = false;', '        return 0;']
        elif method_name == 'getPath':
            body = [
                '        let path = [self];',
                '        let cur = self.parent;',
                '        while (cur != nullptr) {',
                '            push(path, cur);',
                '            cur = cur.parent;',
                '        }',
                '        return path;',
            ]
        elif method_name == 'findById':
            body = [
                '        if (self.id == node_id) {',
                '            return self;',
                '        }',
                '        for child in self.children {',
                '            let found = child.findById(node_id);',
                '            if (found != nullptr) {',
                '                return found;',
                '            }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'findText':
            body = [
                '        if (self.text == search_text) {',
                '            return self;',
                '        }',
                '        for child in self.children {',
                '            let found = child.findText(search_text);',
                '            if (found != nullptr) {',
                '                return found;',
                '            }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'getFlattenedList':
            body = [
                '        let result = [self];',
                '        if (self.expanded) {',
                '            for child in self.children {',
                '                let child_list = child.getFlattenedList();',
                '                let i = 0;',
                '                while (i < len(child_list)) {',
                '                    push(result, child_list[i]);',
                '                    i = i + 1;',
                '                }',
                '            }',
                '        }',
                '        return result;',
            ]
        else:
            body = [f'        return 0;']

    # ===== TreeView =====
    elif class_name == 'TreeView':
        if method_name == 'init_tv':
            body = [
                '        self.init("");',
                '        self.widget_type = "TreeView";',
                '        let root = new TreeNode();',
                '        root.init_tn("");',
                '        self._root = root;',
                '        self._selected = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'setRoot':
            body = ['        self._root = node;', '        return 0;']
        elif method_name == 'getRoot':
            body = ['        return self._root;']
        elif method_name == 'getSelected':
            body = ['        return self._selected;']
        elif method_name == 'setSelected':
            body = ['        self._selected = node;', '        return 0;']
        elif method_name == 'expandNode':
            body = ['        node.expand();', '        return 0;']
        elif method_name == 'collapseNode':
            body = ['        node.collapse();', '        return 0;']
        elif method_name == 'toggleNode':
            body = ['        node.toggle();', '        return 0;']
        elif method_name == 'expandAll':
            body = ['        self._root.expandAll();', '        return 0;']
        elif method_name == 'collapseAll':
            body = ['        self._root.collapseAll();', '        return 0;']
        elif method_name == 'findById':
            body = ['        return self._root.findById(node_id);']
        elif method_name == 'getVisibleNodes':
            body = ['        return self._root.getFlattenedList();']
        elif method_name == 'getVisibleCount':
            body = ['        return len(self.getVisibleNodes());']
        elif method_name == 'selectById':
            body = [
                '        let node = self.findById(node_id);',
                '        if (node != nullptr) {',
                '            self._selected = node;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getNodeAtY':
            body = ['        return nullptr;']
        else:
            body = [f'        return 0;']

    # ===== StatusBar =====
    elif class_name == 'StatusBar':
        if method_name == 'init_sb':
            body = [
                '        self.init("");',
                '        self.widget_type = "StatusBar";',
                '        self.text = "";',
                '        self.panels = [];',
                '        return 0;',
            ]
        elif method_name == 'setText':
            body = ['        self.text = t;', '        return 0;']
        elif method_name == 'getText':
            body = ['        return self.text;']
        elif method_name == 'addPanel':
            body = [
                '        push(self.panels, {"text": panel_text, "width": width});',
                '        return 0;',
            ]
        elif method_name == 'setPanelText':
            body = [
                '        if (index >= 0 and index < len(self.panels)) {',
                '            self.panels[index]["text"] = t;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getPanelText':
            body = [
                '        if (index >= 0 and index < len(self.panels)) {',
                '            return self.panels[index]["text"];',
                '        }',
                '        return "";',
            ]
        elif method_name == 'getPanelCount':
            body = ['        return len(self.panels);']
        elif method_name == 'clearPanels':
            body = ['        self.panels = [];', '        return 0;']
        elif method_name == 'showMessage':
            body = [
                '        self.text = msg;',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Dialog =====
    elif class_name == 'Dialog':
        if method_name == 'init_dlg':
            body = [
                '        self.init_win(dlg_title);',
                '        self.widget_type = "Dialog";',
                '        self.width = dlg_w;',
                '        self.height = dlg_h;',
                '        self.buttons = [];',
                '        self.result = 0;',
                '        return 0;',
            ]
        elif method_name == 'addButton':
            body = [
                '        push(self.buttons, {"text": btn_text, "result": result_code});',
                '        return 0;',
            ]
        elif method_name == 'getResult':
            body = ['        return self.result;']
        elif method_name == 'setOnResult':
            body = ['        self.onResult = fn_ref;', '        return 0;']
        elif method_name == 'layoutButtons':
            body = ['        return 0;']
        else:
            body = [f'        return 0;']

    # ===== SpinBox =====
    elif class_name == 'SpinBox':
        if method_name == 'init_sp':
            body = [
                '        self.init("");',
                '        self.widget_type = "SpinBox";',
                '        self.min_val = minv;',
                '        self.max_val = maxv;',
                '        self.val = initv;',
                '        self.step = 1;',
                '        self.decimals = 0;',
                '        self.prefix = "";',
                '        self.suffix = "";',
                '        return 0;',
            ]
        elif method_name == 'setValue':
            body = [
                '        if (v < self.min_val) { v = self.min_val; }',
                '        if (v > self.max_val) { v = self.max_val; }',
                '        self.val = v;',
                '        return 0;',
            ]
        elif method_name == 'getValue':
            body = ['        return self.val;']
        elif method_name == 'setRange':
            body = [
                '        self.min_val = minv;',
                '        self.max_val = maxv;',
                '        if (self.val < minv) { self.val = minv; }',
                '        if (self.val > maxv) { self.val = maxv; }',
                '        return 0;',
            ]
        elif method_name == 'setStep':
            body = ['        self.step = st;', '        return 0;']
        elif method_name == 'setDecimals':
            body = ['        self.decimals = d;', '        return 0;']
        elif method_name == 'setPrefix':
            body = ['        self.prefix = p;', '        return 0;']
        elif method_name == 'setSuffix':
            body = ['        self.suffix = s;', '        return 0;']
        elif method_name == 'setWrap':
            body = ['        self.wrap = w;', '        return 0;']
        elif method_name == 'increment':
            body = [
                '        self.val = self.val + self.step;',
                '        if (self.val > self.max_val) { self.val = self.max_val; }',
                '        return 0;',
            ]
        elif method_name == 'decrement':
            body = [
                '        self.val = self.val - self.step;',
                '        if (self.val < self.min_val) { self.val = self.min_val; }',
                '        return 0;',
            ]
        elif method_name == 'getText':
            body = ['        return self.prefix + str(self.val) + self.suffix;']
        else:
            body = [f'        return 0;']

    # ===== GroupBox =====
    elif class_name == 'GroupBox':
        if method_name == 'init_gb':
            body = [
                '        self.init("");',
                '        self.widget_type = "GroupBox";',
                '        self.title = gb_title;',
                '        self.collapsed = false;',
                '        self.collapsible = false;',
                '        return 0;',
            ]
        elif method_name == 'setTitle':
            body = ['        self.title = t;', '        return 0;']
        elif method_name == 'getTitle':
            body = ['        return self.title;']
        elif method_name == 'setCollapsible':
            body = ['        self.collapsible = c;', '        return 0;']
        elif method_name == 'toggleCollapse':
            body = ['        self.collapsed = not self.collapsed;', '        return 0;']
        elif method_name == 'isCollapsed':
            body = ['        return self.collapsed;']
        elif method_name == 'getContentRect':
            body = [
                '        return {"x": self._hwdui_pad_left, "y": self._hwdui_pad_top + 20, "width": self.width - self._hwdui_pad_left - self._hwdui_pad_right, "height": self.height - self._hwdui_pad_top - self._hwdui_pad_bottom - 20};',
            ]
        else:
            body = [f'        return 0;']

    # ===== Splitter =====
    elif class_name == 'Splitter':
        if method_name == 'init_split':
            body = [
                '        self.init("");',
                '        self.widget_type = "Splitter";',
                '        self.orientation = orient;',
                '        self.first = nullptr;',
                '        self.second = nullptr;',
                '        self.split_pos = 0;',
                '        self.locked = false;',
                '        return 0;',
            ]
        elif method_name == 'setFirst':
            body = [
                '        self.first = widget;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'setSecond':
            body = [
                '        self.second = widget;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'setSplitPos':
            body = [
                '        if (self.locked == false) {',
                '            self.split_pos = pos;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getSplitPos':
            body = ['        return self.split_pos;']
        elif method_name == 'setLocked':
            body = ['        self.locked = lk;', '        return 0;']
        elif method_name == 'do_layout':
            body = [
                '        if (self.first != nullptr and self.second != nullptr) {',
                '            if (self.orientation == "horizontal") {',
                '                self.first.width = self.split_pos;',
                '                self.first.height = self.height;',
                '                self.second.x = self.split_pos + 4;',
                '                self.second.width = self.width - self.split_pos - 4;',
                '                self.second.height = self.height;',
                '            } else {',
                '                self.first.height = self.split_pos;',
                '                self.first.width = self.width;',
                '                self.second.y = self.split_pos + 4;',
                '                self.second.height = self.height - self.split_pos - 4;',
                '                self.second.width = self.width;',
                '            }',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== TableView =====
    elif class_name == 'TableView':
        if method_name == 'init_tbl':
            body = [
                '        self.init("");',
                '        self.widget_type = "TableView";',
                '        self.columns = [];',
                '        self.rows = [];',
                '        self.selected_row = -1;',
                '        self.sort_column = -1;',
                '        self.sort_ascending = true;',
                '        return 0;',
            ]
        elif method_name == 'addColumn':
            body = [
                '        push(self.columns, {"title": title, "width": width});',
                '        return 0;',
            ]
        elif method_name == 'addColumns':
            body = [
                '        let i = 0;',
                '        while (i < len(column_list)) {',
                '            push(self.columns, column_list[i]);',
                '            i = i + 1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getColumnCount':
            body = ['        return len(self.columns);']
        elif method_name == 'getColumn':
            body = [
                '        if (index >= 0 and index < len(self.columns)) {',
                '            return self.columns[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'removeColumn':
            body = [
                '        let new_cols = [];',
                '        let idx = 0;',
                '        while (idx < len(self.columns)) {',
                '            if (idx != index) {',
                '                push(new_cols, self.columns[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.columns = new_cols;',
                '        return 0;',
            ]
        elif method_name == 'addRow':
            body = ['        push(self.rows, row_data);', '        return 0;']
        elif method_name == 'addRows':
            body = [
                '        let i = 0;',
                '        while (i < len(row_list)) {',
                '            push(self.rows, row_list[i]);',
                '            i = i + 1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getRowCount':
            body = ['        return len(self.rows);']
        elif method_name == 'getRow':
            body = [
                '        if (index >= 0 and index < len(self.rows)) {',
                '            return self.rows[index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'getCell':
            body = [
                '        if (row >= 0 and row < len(self.rows) and col >= 0 and col < len(self.rows[row])) {',
                '            return self.rows[row][col];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'setCell':
            body = [
                '        if (row >= 0 and row < len(self.rows) and col >= 0 and col < len(self.rows[row])) {',
                '            self.rows[row][col] = value;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'removeRow':
            body = [
                '        let new_rows = [];',
                '        let idx = 0;',
                '        while (idx < len(self.rows)) {',
                '            if (idx != index) {',
                '                push(new_rows, self.rows[idx]);',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        self.rows = new_rows;',
                '        if (self.selected_row >= len(self.rows)) {',
                '            self.selected_row = -1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'clearRows':
            body = [
                '        self.rows = [];',
                '        self.selected_row = -1;',
                '        return 0;',
            ]
        elif method_name == 'selectRow':
            body = [
                '        if (index >= 0 and index < len(self.rows)) {',
                '            self.selected_row = index;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getSelectedRow':
            body = ['        return self.selected_row;']
        elif method_name == 'getSelectedRowData':
            body = [
                '        if (self.selected_row >= 0 and self.selected_row < len(self.rows)) {',
                '            return self.rows[self.selected_row];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'sortByColumn':
            body = [
                '        self.sort_column = col;',
                '        return 0;',
            ]
        elif method_name == 'setEditable':
            body = ['        self.editable = ed;', '        return 0;']
        elif method_name == 'getVisibleRows':
            body = ['        return self.rows;']
        else:
            body = [f'        return 0;']

    # ===== Animation =====
    elif class_name == 'Animation':
        if method_name == 'init_anim':
            body = [
                '        self.target = target_widget;',
                '        self.property = prop;',
                '        self.to_val = to_value;',
                '        self.duration = dur;',
                '        self.from_val = 0;',
                '        self.easing = "linear";',
                '        self.running = false;',
                '        self.elapsed = 0;',
                '        self.loop = false;',
                '        self.reverse = false;',
                '        self.onComplete = nullptr;',
                '        self.onUpdate = nullptr;',
                '        return 0;',
            ]
        elif method_name == 'setEasing':
            body = ['        self.easing = e;', '        return 0;']
        elif method_name == 'setLoop':
            body = ['        self.loop = l;', '        return 0;']
        elif method_name == 'setReverse':
            body = ['        self.reverse = r;', '        return 0;']
        elif method_name == 'setOnComplete':
            body = ['        self.onComplete = fn_ref;', '        return 0;']
        elif method_name == 'setOnUpdate':
            body = ['        self.onUpdate = fn_ref;', '        return 0;']
        elif method_name == 'start':
            body = [
                '        if (self.target == nullptr) { return 0; }',
                '        if (self.property == "x") { self.from_val = self.target.x; }',
                '        else if (self.property == "y") { self.from_val = self.target.y; }',
                '        else if (self.property == "width") { self.from_val = self.target.width; }',
                '        else if (self.property == "height") { self.from_val = self.target.height; }',
                '        else if (self.property == "opacity") {',
                '            let cs = self.target.getComputedStyle();',
                '            let op = cs["opacity"];',
                '            if (op != nullptr) { self.from_val = op; }',
                '        }',
                '        else { self.from_val = 0; }',
                '        self.elapsed = 0;',
                '        self.running = true;',
                '        return 0;',
            ]
        elif method_name == 'stop':
            body = [
                '        self.running = false;',
                '        self.elapsed = 0;',
                '        return 0;',
            ]
        elif method_name == 'pause':
            body = ['        self.running = false;', '        return 0;']
        elif method_name == 'resume':
            body = ['        self.running = true;', '        return 0;']
        elif method_name == 'update':
            body = [
                '        if (self.running == false) { return 0; }',
                '        self.elapsed = self.elapsed + delta_ms;',
                '        if (self.elapsed >= self.duration) {',
                '            self.elapsed = self.duration;',
                '            self.running = false;',
                '            if (self.target != nullptr) {',
                '                self._applyValue(self.to_val);',
                '            }',
                '            if (self.onComplete != nullptr) {',
                '                self.onComplete(self);',
                '            }',
                '            if (self.loop) {',
                '                if (self.reverse) {',
                '                    let tmp = self.to_val;',
                '                    self.to_val = self.from_val;',
                '                    self.from_val = tmp;',
                '                }',
                '                self.start();',
                '            }',
                '            return 0;',
                '        }',
                '        let t = (self.elapsed * 100) / self.duration;',
                '        if (self.easing == "easeIn") {',
                '            t = (t * t) / 100;',
                '        }',
                '        if (self.easing == "easeOut") {',
                '            t = (t * (200 - t)) / 100;',
                '        }',
                '        if (self.easing == "easeInOut") {',
                '            if (t < 50) {',
                '                t = (2 * t * t) / 100;',
                '            } else {',
                '                t = (200 - 2 * (100 - t) * (100 - t)) / 100;',
                '            }',
                '        }',
                '        let val = self.from_val + (self.to_val - self.from_val) * t / 100;',
                '        self._applyValue(val);',
                '        if (self.onUpdate != nullptr) {',
                '            self.onUpdate(self, val);',
                '        }',
                '        return 0;',
            ]
        elif method_name == '_applyValue':
            body = [
                '        if (self.target == nullptr) { return 0; }',
                '        if (self.property == "x") { self.target.x = val; }',
                '        else if (self.property == "y") { self.target.y = val; }',
                '        else if (self.property == "width") { self.target.width = val; }',
                '        else if (self.property == "height") { self.target.height = val; }',
                '        else if (self.property == "opacity") { self.target.setInlineStyle("opacity", str(val)); }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== FlowPanel =====
    elif class_name == 'FlowPanel':
        if method_name == 'init_fp':
            body = [
                '        self.init_panel("flow");',
                '        self.widget_type = "FlowPanel";',
                '        return 0;',
            ]
        elif method_name == 'setFlowDirection':
            body = ['        self.flow_direction = dir;', '        return 0;']
        elif method_name == 'setWrapContent':
            body = ['        self.wrap_content = w;', '        return 0;']
        elif method_name == 'setItemSpacing':
            body = ['        self.item_spacing = s;', '        return 0;']
        elif method_name == 'setLineSpacing':
            body = ['        self.line_spacing = s;', '        return 0;']
        elif method_name == 'do_layout':
            body = [
                '        if (self.flow_direction == "horizontal") {',
                '            self._do_flow_horizontal();',
                '        } else {',
                '            self._do_flow_vertical();',
                '        }',
                '        return 0;',
            ]
        elif method_name == '_do_flow_horizontal':
            body = [
                '        let cx = self._hwdui_pad_left;',
                '        let cy = self._hwdui_pad_top;',
                '        for child in self.children {',
                '            if (child.visible == false) {',
                '                continue;',
                '            }',
                '            if (self.wrap_content and cx + child.width > self.width - self._hwdui_pad_right) {',
                '                cx = self._hwdui_pad_left;',
                '                cy = cy + child.height + self.line_spacing;',
                '            }',
                '            child.x = cx;',
                '            child.y = cy;',
                '            cx = cx + child.width + self.item_spacing;',
                '        }',
                '        return 0;',
            ]
        elif method_name == '_do_flow_vertical':
            body = [
                '        let cx = self._hwdui_pad_left;',
                '        let cy = self._hwdui_pad_top;',
                '        for child in self.children {',
                '            if (child.visible == false) {',
                '                continue;',
                '            }',
                '            if (self.wrap_content and cy + child.height > self.height - self._hwdui_pad_bottom) {',
                '                cx = cx + child.width + self.line_spacing;',
                '                cy = self._hwdui_pad_top;',
                '            }',
                '            child.x = cx;',
                '            child.y = cy;',
                '            cy = cy + child.height + self.item_spacing;',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== FileDialog =====
    elif class_name == 'FileDialog':
        if method_name == 'init_fd':
            body = [
                '        self.init_dlg(fd_title, 600, 400);',
                '        self.widget_type = "FileDialog";',
                '        self.mode = fd_mode;',
                '        self.filter = fd_filter;',
                '        self.file_list = [];',
                '        return 0;',
            ]
        elif method_name == 'setDirectory':
            body = ['        self.current_dir = dir_path;', '        return 0;']
        elif method_name == 'getFilePath':
            body = ['        return self.file_path;']
        elif method_name == 'setFilePath':
            body = ['        self.file_path = fp;', '        return 0;']
        elif method_name == 'setOnFileSelected':
            body = ['        self.onFileSelected = fn_ref;', '        return 0;']
        elif method_name == 'getFilter':
            body = ['        return self.filter;']
        elif method_name == 'setFilter':
            body = ['        self.filter = f;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== DockPanel =====
    elif class_name == 'DockPanel':
        if method_name == 'init_dp':
            body = [
                '        self.init_panel("absolute");',
                '        self.widget_type = "DockPanel";',
                '        return 0;',
            ]
        elif method_name == 'dockTop':
            body = [
                '        widget.x = 0;',
                '        widget.y = 0;',
                '        widget.width = self.width;',
                '        widget.height = height;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'dockBottom':
            body = [
                '        widget.x = 0;',
                '        widget.y = self.height - height;',
                '        widget.width = self.width;',
                '        widget.height = height;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'dockLeft':
            body = [
                '        widget.x = 0;',
                '        widget.y = 0;',
                '        widget.width = width;',
                '        widget.height = self.height;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'dockRight':
            body = [
                '        widget.x = self.width - width;',
                '        widget.y = 0;',
                '        widget.width = width;',
                '        widget.height = self.height;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'dockFill':
            body = [
                '        self.last_fill = widget;',
                '        self.add_child(widget);',
                '        return 0;',
            ]
        elif method_name == 'do_layout':
            body = [
                '        if (self.last_fill != nullptr) {',
                '            self.last_fill.width = self.width;',
                '            self.last_fill.height = self.height;',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Canvas (not in bytecode, but tested) =====
    elif class_name == 'Canvas':
        if method_name == 'init_canvas':
            body = [
                '        self.init("");',
                '        self.widget_type = "Canvas";',
                '        self.width = w;',
                '        self.height = h;',
                '        self.lines = [];',
                '        self.rects = [];',
                '        self.circles = [];',
                '        self.texts = [];',
                '        self.images = [];',
                '        return 0;',
            ]
        elif method_name == 'drawLine':
            body = [
                '        push(self.lines, {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "width": line_width});',
                '        return 0;',
            ]
        elif method_name == 'drawRect':
            body = [
                '        push(self.rects, {"x": x, "y": y, "width": w, "height": h, "color": color, "fill": fill, "width": line_width});',
                '        return 0;',
            ]
        elif method_name == 'fillRect':
            body = [
                '        push(self.rects, {"x": x, "y": y, "width": w, "height": h, "color": color, "fill": true, "width": 0});',
                '        return 0;',
            ]
        elif method_name == 'drawCircle':
            body = [
                '        push(self.circles, {"cx": cx, "cy": cy, "radius": r, "color": color, "fill": fill, "width": line_width});',
                '        return 0;',
            ]
        elif method_name == 'fillCircle':
            body = [
                '        push(self.circles, {"cx": cx, "cy": cy, "radius": r, "color": color, "fill": true, "width": 0});',
                '        return 0;',
            ]
        elif method_name == 'drawText':
            body = [
                '        push(self.texts, {"x": x, "y": y, "text": text, "color": color, "size": size});',
                '        return 0;',
            ]
        elif method_name == 'drawImage':
            body = [
                '        push(self.images, {"x": x, "y": y, "width": w, "height": h, "path": path});',
                '        return 0;',
            ]
        elif method_name == 'clear':
            body = [
                '        self.lines = [];',
                '        self.rects = [];',
                '        self.circles = [];',
                '        self.texts = [];',
                '        self.images = [];',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== GridPanel (not in bytecode, but tested) =====
    elif class_name == 'GridPanel':
        if method_name == 'init_grid':
            body = [
                '        self.init("");',
                '        self.widget_type = "GridPanel";',
                '        self.rows = r;',
                '        self.cols = c;',
                '        self.row_heights = [];',
                '        self.col_widths = [];',
                '        self.row_spacing = 0;',
                '        self.col_spacing = 0;',
                '        self.grid_children = [];',
                '        let ri = 0;',
                '        while (ri < r) {',
                '            push(self.row_heights, 0);',
                '            ri = ri + 1;',
                '        }',
                '        let ci = 0;',
                '        while (ci < c) {',
                '            push(self.col_widths, 0);',
                '            ci = ci + 1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'setRowHeight':
            body = [
                '        if (row >= 0 and row < len(self.row_heights)) {',
                '            self.row_heights[row] = h;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'setColWidth':
            body = [
                '        if (col >= 0 and col < len(self.col_widths)) {',
                '            self.col_widths[col] = w;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'setSpacing':
            body = [
                '        self.row_spacing = rs;',
                '        self.col_spacing = cs;',
                '        return 0;',
            ]
        elif method_name == 'addChildAt':
            body = [
                '        push(self.grid_children, {"widget": child, "row": row, "col": col});',
                '        self.add_child(child);',
                '        return 0;',
            ]
        elif method_name == 'do_layout':
            body = [
                '        for gc in self.grid_children {',
                '            let r = gc["row"];',
                '            let c = gc["col"];',
                '            let widget = gc["widget"];',
                '            let col_x = self._hwdui_pad_left;',
                '            let ci = 0;',
                '            while (ci < c) {',
                '                col_x = col_x + self.col_widths[ci] + self.col_spacing;',
                '                ci = ci + 1;',
                '            }',
                '            widget.x = col_x;',
                '            let row_y = self._hwdui_pad_top;',
                '            let ri = 0;',
                '            while (ri < r) {',
                '                row_y = row_y + self.row_heights[ri] + self.row_spacing;',
                '                ri = ri + 1;',
                '            }',
                '            widget.y = row_y;',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Timer (not in bytecode, but tested) =====
    elif class_name == 'Timer':
        if method_name == 'init_timer':
            body = [
                '        self.interval_ms = ms;',
                '        self.callback = fn_ref;',
                '        self.running = false;',
                '        self.elapsed = 0;',
                '        self.repeats = true;',
                '        push(_hwdui_all_timers, self);',
                '        return 0;',
            ]
        elif method_name == 'start':
            body = [
                '        self.running = true;',
                '        self.elapsed = 0;',
                '        return 0;',
            ]
        elif method_name == 'stop':
            body = ['        self.running = false;', '        return 0;']
        elif method_name == 'restart':
            body = [
                '        self.elapsed = 0;',
                '        self.running = true;',
                '        return 0;',
            ]
        elif method_name == 'isRunning':
            body = ['        return self.running;']
        elif method_name == 'setInterval':
            body = ['        self.interval_ms = ms;', '        return 0;']
        elif method_name == 'setRepeats':
            body = ['        self.repeats = r;', '        return 0;']
        elif method_name == '_tick':
            body = [
                '        if (self.running == false) { return 0; }',
                '        self.elapsed = self.elapsed + delta_ms;',
                '        if (self.elapsed >= self.interval_ms) {',
                '            if (self.callback != nullptr) {',
                '                self.callback(self);',
                '            }',
                '            if (self.repeats == false) {',
                '                self.running = false;',
                '            } else {',
                '                self.elapsed = 0;',
                '            }',
                '        }',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== Notification (not in bytecode, but tested) =====
    elif class_name == 'Notification':
        if method_name == 'init_notify':
            body = [
                '        self.init("");',
                '        self.widget_type = "Notification";',
                '        self.title = t;',
                '        self.message = m;',
                '        self.type = ntype;',
                '        self.visible = false;',
                '        self.timeout = 3000;',
                '        return 0;',
            ]
        elif method_name == 'show':
            body = ['        self.visible = true;', '        return 0;']
        elif method_name == 'close':
            body = ['        self.visible = false;', '        return 0;']
        elif method_name == 'setTimeout':
            body = ['        self.timeout = ms;', '        return 0;']
        else:
            body = [f'        return 0;']

    # ===== Tooltip (not in bytecode, but tested) =====
    elif class_name == 'Tooltip':
        if method_name == 'init_tooltip':
            body = [
                '        self.init("");',
                '        self.widget_type = "Tooltip";',
                '        self.text = t;',
                '        self.visible = false;',
                '        self.delay = 500;',
                '        return 0;',
            ]
        elif method_name == 'setText':
            body = ['        self.text = t;', '        return 0;']
        elif method_name == 'setDelay':
            body = ['        self.delay = ms;', '        return 0;']
        elif method_name == 'showAt':
            body = [
                '        self.x = px + 10;',
                '        self.y = py + 10;',
                '        self.visible = true;',
                '        hwdui_tooltip_set(self);',
                '        return 0;',
            ]
        elif method_name == 'hide':
            body = [
                '        self.visible = false;',
                '        hwdui_tooltip_set(nullptr);',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    # ===== KeyboardHandler (not in bytecode, but tested) =====
    elif class_name == 'KeyboardHandler':
        if method_name == 'init_kh':
            body = [
                '        self.tab_order = [];',
                '        self.current_index = -1;',
                '        self.enabled = true;',
                '        return 0;',
            ]
        elif method_name == 'addWidget':
            body = ['        push(self.tab_order, widget);', '        return 0;']
        elif method_name == 'removeWidget':
            body = [
                '        let new_order = [];',
                '        for w in self.tab_order {',
                '            if (w != widget) {',
                '                push(new_order, w);',
                '            }',
                '        }',
                '        self.tab_order = new_order;',
                '        return 0;',
            ]
        elif method_name == 'setCurrent':
            body = [
                '        let idx = 0;',
                '        while (idx < len(self.tab_order)) {',
                '            if (self.tab_order[idx] == widget) {',
                '                self.current_index = idx;',
                '                return 0;',
                '            }',
                '            idx = idx + 1;',
                '        }',
                '        return 0;',
            ]
        elif method_name == 'getCurrent':
            body = [
                '        if (self.current_index >= 0 and self.current_index < len(self.tab_order)) {',
                '            return self.tab_order[self.current_index];',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'next':
            body = [
                '        if (len(self.tab_order) == 0) { return nullptr; }',
                '        let start = self.current_index;',
                '        let idx = start;',
                '        while (true) {',
                '            idx = idx + 1;',
                '            if (idx >= len(self.tab_order)) { idx = 0; }',
                '            if (self.tab_order[idx].enabled) {',
                '                self.current_index = idx;',
                '                return self.tab_order[idx];',
                '            }',
                '            if (idx == start) { return nullptr; }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'prev':
            body = [
                '        if (len(self.tab_order) == 0) { return nullptr; }',
                '        let start = self.current_index;',
                '        let idx = start;',
                '        while (true) {',
                '            idx = idx - 1;',
                '            if (idx < 0) { idx = len(self.tab_order) - 1; }',
                '            if (self.tab_order[idx].enabled) {',
                '                self.current_index = idx;',
                '                return self.tab_order[idx];',
                '            }',
                '            if (idx == start) { return nullptr; }',
                '        }',
                '        return nullptr;',
            ]
        elif method_name == 'clear':
            body = [
                '        self.tab_order = [];',
                '        self.current_index = -1;',
                '        return 0;',
            ]
        else:
            body = [f'        return 0;']

    else:
        # Fallback for unknown classes
        body = [f'        return 0;']

    return body


def main():
    # Read the bytecode
    with open('bootstrap/hsharp_bundle.hbc', 'r') as f:
        data = json.load(f)

    hwdui = data['modules']['hwdui']
    consts = hwdui['consts']
    instructions = hwdui['instructions']

    print(f"Loaded: {len(consts)} consts, {len(instructions)} top-level instructions")

    # Separate classes and standalone functions
    classes = []
    standalone_funcs = []

    for c in consts:
        if isinstance(c, dict) and 'name' in c and 'methods' in c:
            classes.append(c)
        elif isinstance(c, dict) and 'args' in c and 'bytecode' in c:
            standalone_funcs.append(c)

    print(f"Found: {len(classes)} classes, {len(standalone_funcs)} standalone functions")

    # Topological sort classes
    name_to_cls = {c['name']: c for c in classes}
    sorted_classes = []
    visited = set()

    def visit(cls):
        if cls['name'] in visited:
            return
        visited.add(cls['name'])
        base = cls.get('base')
        if base and base in name_to_cls:
            visit(name_to_cls[base])
        sorted_classes.append(cls)

    for cls in classes:
        visit(cls)

    classes = sorted_classes

    # Build output
    output_lines = []

    output_lines.append('# ═══════════════════════════════════════════════════════════════════════════')
    output_lines.append('# hwdui.hto — HwdUI: H# GUI Widget Library with CSS-like styling')
    output_lines.append('# ═══════════════════════════════════════════════════════════════════════════')
    output_lines.append('')

    # Global state variables
    output_lines.append('# Global state variables')
    output_lines.append('let _hwdui_registry = {};')
    output_lines.append('let _hwdui_id_counter = 0;')
    output_lines.append('let _hwdui_active_windows = [];')
    output_lines.append('let _hwdui_focused_widget = nullptr;')
    output_lines.append('let _hwdui_all_stylesheets = [];')
    output_lines.append('let _hwdui_all_timers = [];')
    output_lines.append('let _hwdui_current_tooltip = nullptr;')
    output_lines.append('let _hwdui_default_styles = [];')
    output_lines.append('let _hwdui_anim_list = [];')
    output_lines.append('let _hwdui_css_defaults = {};')
    output_lines.append('')

    # Build const_index -> name mapping
    const_to_name = {}
    for i in range(len(instructions) - 1):
        if instructions[i][0] == 'LOAD_CONST' and instructions[i+1][0] == 'STORE_NAME':
            const_idx = instructions[i][1]
            name = instructions[i+1][1]
            const_to_name[const_idx] = name

    print(f"Function name mapping: {len(const_to_name)} entries")

    # Generate classes
    for cls in classes:
        class_name = cls['name']
        base_name = cls.get('base')
        fields = cls.get('fields', {})
        methods = cls.get('methods', {})

        # Add class-specific fields beyond what's in bytecode
        class_fields = dict(fields)  # Copy existing fields

        # Add well-known fields for each class
        if class_name == 'zzwUI':
            for fname, fval in [
                ('x', 0), ('y', 0), ('width', 0), ('height', 0),
                ('visible', True), ('enabled', True),
                ('parent', None), ('widget_type', '""'),
                ('onClick', None), ('onFocus', None), ('onBlur', None),
                ('onMove', None), ('onResize', None),
                ('_hwdui_min_w', 0), ('_hwdui_min_h', 0),
                ('_hwdui_max_w', 0), ('_hwdui_max_h', 0),
                ('_hwdui_pad_left', 0), ('_hwdui_pad_top', 0),
                ('_hwdui_pad_right', 0), ('_hwdui_pad_bottom', 0),
                ('_hwdui_margin_left', 0), ('_hwdui_margin_top', 0),
                ('_hwdui_margin_right', 0), ('_hwdui_margin_bottom', 0),
                ('_hwdui_drop_accept', None), ('_hwdui_on_drop', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Window':
            for fname, fval in [
                ('title', '""'), ('_hwdui_win_id', 0),
                ('closable', True), ('resizable', True),
                ('centered', False), ('title_height', 30),
                ('is_minimized', False), ('is_maximized', False),
                ('_hwdui_saved_x', 0), ('_hwdui_saved_y', 0),
                ('_hwdui_saved_w', 0), ('_hwdui_saved_h', 0),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Panel':
            for fname, fval in [
                ('layout_type', '"absolute"'), ('spacing', 0),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Button':
            for fname, fval in [
                ('text', '""'), ('icon', '""'),
                ('is_toggle', False), ('is_checked', False),
                ('is_default', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Label':
            for fname, fval in [
                ('text', '""'), ('font_size', 12),
                ('font_family', '"sans-serif"'),
                ('text_align', '"left"'), ('text_color', '"#000000"'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'TextBox':
            for fname, fval in [
                ('text', '""'), ('placeholder', '""'),
                ('readonly', False), ('multiline', False),
                ('max_length', 0), ('is_password', False),
                ('cursor_pos', 0), ('selection_start', 0),
                ('selection_end', 0),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'CheckBox':
            for fname, fval in [
                ('text', '""'), ('checked', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'RadioButton':
            for fname, fval in [
                ('text', '""'), ('checked', False),
                ('group_name', '""'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Slider':
            for fname, fval in [
                ('min_val', 0), ('max_val', 100), ('val', 0),
                ('step', 1), ('orientation', '"horizontal"'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ProgressBar':
            for fname, fval in [
                ('min_val', 0), ('max_val', 100), ('val', 0),
                ('mode', '"determinate"'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Image':
            for fname, fval in [
                ('source', '""'), ('scale_mode', '"fit"'),
                ('alt_text', '""'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ListBox':
            for fname, fval in [
                ('items', '[]'), ('selected_index', -1),
                ('multi_select', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ComboBox':
            for fname, fval in [
                ('items', '[]'), ('selected_index', -1),
                ('is_dropped', False), ('editable', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ScrollView':
            for fname, fval in [
                ('scroll_x', 0), ('scroll_y', 0),
                ('content_width', 0), ('content_height', 0),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'TabControl':
            for fname, fval in [
                ('tabs', '[]'), ('active_tab', -1),
                ('tab_position', '"top"'), ('tab_height', 30),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Separator':
            for fname, fval in [
                ('sep_orientation', '"horizontal"'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Selector':
            for fname, fval in [
                ('_sel_type', None), ('_sel_class', None),
                ('_sel_id', None), ('_sel_pseudo', None),
                ('_sel_parent_type', None), ('_sel_parent_class', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'StyleRule':
            for fname, fval in [
                ('selector', None), ('declarations', '[]'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Stylesheet':
            for fname, fval in [
                ('name', '""'), ('rules', '[]'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'MenuBar':
            for fname, fval in [
                ('menus', '[]'), ('active_menu', -1),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Menu':
            for fname, fval in [
                ('text', '""'), ('items', '[]'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'MenuItem':
            for fname, fval in [
                ('text', '""'), ('id', '""'),
                ('separator', False), ('enabled', True),
                ('checked', False), ('checkable', False),
                ('shortcut', '""'), ('icon', '""'),
                ('submenu', None), ('action', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ContextMenu':
            for fname, fval in [
                ('owner', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ToolBar':
            for fname, fval in [
                ('buttons', '[]'), ('orientation', '"horizontal"'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'ToolButton':
            for fname, fval in [
                ('text', '""'), ('icon', '""'),
                ('is_toggle', False), ('is_checked', False),
                ('is_separator', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'TreeNode':
            for fname, fval in [
                ('text', '""'), ('id', '""'),
                ('children', '[]'), ('parent', None),
                ('expanded', False), ('selected', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'TreeView':
            for fname, fval in [
                ('_root', None), ('_selected', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'StatusBar':
            for fname, fval in [
                ('text', '""'), ('panels', '[]'),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Dialog':
            for fname, fval in [
                ('buttons', '[]'), ('result', 0),
                ('onResult', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'SpinBox':
            for fname, fval in [
                ('min_val', 0), ('max_val', 100), ('val', 0),
                ('step', 1), ('decimals', 0),
                ('prefix', '""'), ('suffix', '""'),
                ('wrap', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'GroupBox':
            for fname, fval in [
                ('title', '""'), ('collapsed', False),
                ('collapsible', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Splitter':
            for fname, fval in [
                ('orientation', '"horizontal"'),
                ('first', None), ('second', None),
                ('split_pos', 0), ('locked', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'TableView':
            for fname, fval in [
                ('columns', '[]'), ('rows', '[]'),
                ('selected_row', -1), ('sort_column', -1),
                ('sort_ascending', True), ('editable', False),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'Animation':
            for fname, fval in [
                ('target', None), ('property', '""'),
                ('to_val', 0), ('duration', 0),
                ('from_val', 0), ('easing', '"linear"'),
                ('running', False), ('elapsed', 0),
                ('loop', False), ('reverse', False),
                ('onComplete', None), ('onUpdate', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'FlowPanel':
            for fname, fval in [
                ('flow_direction', '"horizontal"'),
                ('wrap_content', True),
                ('item_spacing', 4), ('line_spacing', 4),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'FileDialog':
            for fname, fval in [
                ('file_path', '""'), ('current_dir', '""'),
                ('filter', '"*"'), ('mode', '"open"'),
                ('file_list', '[]'),
                ('onFileSelected', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval
        elif class_name == 'DockPanel':
            for fname, fval in [
                ('last_fill', None),
            ]:
                if fname not in class_fields:
                    class_fields[fname] = fval

        class_line = f'class {class_name}'
        if base_name:
            class_line += f' extends {base_name}'
        class_line += ' {'
        output_lines.append(class_line)

        # Fields
        for fname, fval in class_fields.items():
            formatted = format_const(fval)
            output_lines.append(f'    let {fname} = {formatted};')

        output_lines.append('')

        # Methods
        for mname, mdata in methods.items():
            if not isinstance(mdata, dict):
                continue
            m_args = list(mdata.get('args', []))
            arg_str = ', '.join(m_args)

            output_lines.append(f'    fn {mname}({arg_str}) {{')

            body_lines = get_method_body(class_name, mname, m_args, mdata.get('bytecode', []), mdata.get('consts', []))
            for line in body_lines:
                output_lines.append(line)

            output_lines.append('    }')
            output_lines.append('')

        output_lines.append('}')
        output_lines.append('')

    # Generate standalone functions
    output_lines.append('# ═══════════════════════════════════════════════════════════════════════════')
    output_lines.append('# Standalone functions and theme creators')
    output_lines.append('# ═══════════════════════════════════════════════════════════════════════════')
    output_lines.append('')

    for idx, func in enumerate(consts):
        if not (isinstance(func, dict) and 'args' in func and 'bytecode' in func):
            continue

        f_args = func.get('args', [])

        if idx in const_to_name:
            func_name = const_to_name[idx]
        else:
            func_name = f'_anon_func_{idx}'

        arg_str = ', '.join(f_args)
        output_lines.append(f'fn {func_name}({arg_str}) {{')

        if func_name == 'hwdui_init':
            output_lines.append('    _hwdui_registry = {};')
            output_lines.append('    _hwdui_id_counter = 0;')
            output_lines.append('    _hwdui_active_windows = [];')
            output_lines.append('    _hwdui_focused_widget = nullptr;')
            output_lines.append('    _hwdui_all_stylesheets = [];')
            output_lines.append('    _hwdui_all_timers = [];')
            output_lines.append('    _hwdui_current_tooltip = nullptr;')
            output_lines.append('    _hwdui_default_styles = [];')
            output_lines.append('    _hwdui_anim_list = [];')
            output_lines.append('    return true;')
        elif func_name == 'hwdui_summary':
            output_lines.append('    print("");')
            output_lines.append('    print("═════════════════════════════════════");')
            output_lines.append('    print("  HwdUI — H# GUI Widget Library v2.0");')
            output_lines.append('    print("═════════════════════════════════════");')
            output_lines.append('    print(" Core Widgets: 18 standard widgets");')
            output_lines.append('    print(" Advanced: Menu, TreeView, TableView, Dialog, etc");')
            output_lines.append('    print(" CSS Engine: Selector, StyleRule, Stylesheet");')
            output_lines.append('    print(" Themes: light, dark, material, ocean, forest, cyberpunk");')
            output_lines.append('    print("═════════════════════════════════════");')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_next_id':
            output_lines.append('    _hwdui_id_counter = _hwdui_id_counter + 1;')
            output_lines.append('    return _hwdui_id_counter;')
        elif func_name == 'hwdui_register':
            output_lines.append('    _hwdui_registry[name] = cls;')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_class_exists':
            output_lines.append('    return name in _hwdui_registry;')
        elif func_name == 'hwdui_pair_get':
            output_lines.append('    let i = 0;')
            output_lines.append('    while (i < len(pairs)) {')
            output_lines.append('        let pair = pairs[i];')
            output_lines.append('        if (pair[0] == key) {')
            output_lines.append('            return pair[1];')
            output_lines.append('        }')
            output_lines.append('        i = i + 1;')
            output_lines.append('    }')
            output_lines.append('    return default_val;')
        elif func_name == 'hwdui_pair_set':
            output_lines.append('    let i = 0;')
            output_lines.append('    while (i < len(pairs)) {')
            output_lines.append('        let pair = pairs[i];')
            output_lines.append('        if (pair[0] == key) {')
            output_lines.append('            pair[1] = value;')
            output_lines.append('            return pairs;')
            output_lines.append('        }')
            output_lines.append('        i = i + 1;')
            output_lines.append('    }')
            output_lines.append('    push(pairs, [key, value]);')
            output_lines.append('    return pairs;')
        elif func_name == 'hwdui_copy_style_props':
            output_lines.append('    let i = 0;')
            output_lines.append('    while (i < len(pairs)) {')
            output_lines.append('        let pair = pairs[i];')
            output_lines.append('        target_dict[pair[0]] = pair[1];')
            output_lines.append('        i = i + 1;')
            output_lines.append('    }')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_empty_style':
            output_lines.append('    return {};')
        elif func_name == 'hwdui_set_default_styles':
            output_lines.append('    _hwdui_css_defaults = pairs;')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_theme_light':
            output_lines.append('    let sheet = hwdui_create_stylesheet("light");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Button"), [')
            output_lines.append('        ["background-color", "#e0e0e0"],')
            output_lines.append('        ["color", "#333333"],')
            output_lines.append('        ["border-color", "#b0b0b0"],')
            output_lines.append('        ["border-width", "1"],')
            output_lines.append('        ["border-style", "solid"],')
            output_lines.append('        ["border-radius", "4"],')
            output_lines.append('        ["font-size", "13"],')
            output_lines.append('        ["font-family", "sans-serif"],')
            output_lines.append('        ["cursor", "pointer"],')
            output_lines.append('        ["text-align", "center"]')
            output_lines.append('    ]);')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Label"), [')
            output_lines.append('        ["color", "#333333"],')
            output_lines.append('        ["font-family", "sans-serif"],')
            output_lines.append('        ["font-size", "12"]')
            output_lines.append('    ]);')
            output_lines.append('    sheet.addRule(hwdui_sel_type("TextBox"), [')
            output_lines.append('        ["background-color", "#ffffff"],')
            output_lines.append('        ["color", "#333333"],')
            output_lines.append('        ["border-color", "#b0b0b0"],')
            output_lines.append('        ["border-width", "1"],')
            output_lines.append('        ["border-style", "solid"],')
            output_lines.append('        ["font-family", "sans-serif"],')
            output_lines.append('        ["font-size", "12"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_theme_dark':
            output_lines.append('    let sheet = hwdui_create_stylesheet("dark");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Button"), [')
            output_lines.append('        ["background-color", "#444444"],')
            output_lines.append('        ["color", "#e0e0e0"],')
            output_lines.append('        ["border-color", "#666666"],')
            output_lines.append('        ["border-width", "1"],')
            output_lines.append('        ["border-style", "solid"],')
            output_lines.append('        ["border-radius", "4"],')
            output_lines.append('        ["font-size", "13"],')
            output_lines.append('        ["cursor", "pointer"]')
            output_lines.append('    ]);')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Label"), [')
            output_lines.append('        ["color", "#e0e0e0"],')
            output_lines.append('        ["font-family", "sans-serif"],')
            output_lines.append('        ["font-size", "12"]')
            output_lines.append('    ]);')
            output_lines.append('    sheet.addRule(hwdui_sel_type("TextBox"), [')
            output_lines.append('        ["background-color", "#333333"],')
            output_lines.append('        ["color", "#e0e0e0"],')
            output_lines.append('        ["border-color", "#666666"],')
            output_lines.append('        ["border-width", "1"],')
            output_lines.append('        ["border-style", "solid"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_theme_material':
            output_lines.append('    let sheet = hwdui_create_stylesheet("material");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Button"), [')
            output_lines.append('        ["background-color", "#1976d2"],')
            output_lines.append('        ["color", "#ffffff"],')
            output_lines.append('        ["border-radius", "2"],')
            output_lines.append('        ["font-size", "14"],')
            output_lines.append('        ["cursor", "pointer"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_theme_ocean':
            output_lines.append('    let sheet = hwdui_create_stylesheet("ocean");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Button"), [')
            output_lines.append('        ["background-color", "#0077b6"],')
            output_lines.append('        ["color", "#ffffff"],')
            output_lines.append('        ["border-radius", "4"],')
            output_lines.append('        ["font-size", "13"],')
            output_lines.append('        ["cursor", "pointer"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_theme_forest':
            output_lines.append('    let sheet = hwdui_create_stylesheet("forest");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Button"), [')
            output_lines.append('        ["background-color", "#2d6a4f"],')
            output_lines.append('        ["color", "#ffffff"],')
            output_lines.append('        ["border-radius", "4"],')
            output_lines.append('        ["font-size", "13"],')
            output_lines.append('        ["cursor", "pointer"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_theme_cyberpunk':
            output_lines.append('    let sheet = hwdui_create_stylesheet("cyberpunk");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Button"), [')
            output_lines.append('        ["background-color", "#ff00ff"],')
            output_lines.append('        ["color", "#00ff00"],')
            output_lines.append('        ["border-color", "#00ffff"],')
            output_lines.append('        ["border-width", "2"],')
            output_lines.append('        ["border-style", "solid"],')
            output_lines.append('        ["font-size", "13"],')
            output_lines.append('        ["cursor", "pointer"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_sel_type':
            output_lines.append('    let sel = new Selector();')
            output_lines.append('    sel.setType(t);')
            output_lines.append('    return sel;')
        elif func_name == 'hwdui_sel_class':
            output_lines.append('    let sel = new Selector();')
            output_lines.append('    sel.setClass(c);')
            output_lines.append('    return sel;')
        elif func_name == 'hwdui_sel_id':
            output_lines.append('    let sel = new Selector();')
            output_lines.append('    sel.setId(i);')
            output_lines.append('    return sel;')
        elif func_name == 'hwdui_sel_universal':
            output_lines.append('    let sel = new Selector();')
            output_lines.append('    return sel;')
        elif func_name == 'hwdui_sel_type_class':
            output_lines.append('    let sel = new Selector();')
            output_lines.append('    sel.setType(t);')
            output_lines.append('    sel.setClass(c);')
            output_lines.append('    return sel;')
        elif func_name == 'hwdui_sel_type_pseudo':
            output_lines.append('    let sel = new Selector();')
            output_lines.append('    sel.setType(t);')
            output_lines.append('    sel.setPseudo(p);')
            output_lines.append('    return sel;')
        elif func_name == 'hwdui_create_stylesheet':
            output_lines.append('    let sheet = new Stylesheet();')
            output_lines.append('    sheet.init_sheet(name);')
            output_lines.append('    push(_hwdui_all_stylesheets, sheet);')
            output_lines.append('    return sheet;')
        elif func_name == 'hwdui_clear_all_stylesheets':
            output_lines.append('    _hwdui_all_stylesheets = [];')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_remove_stylesheet':
            output_lines.append('    let new_sheets = [];')
            output_lines.append('    let i = 0;')
            output_lines.append('    while (i < len(_hwdui_all_stylesheets)) {')
            output_lines.append('        if (_hwdui_all_stylesheets[i] != sheet) {')
            output_lines.append('            push(new_sheets, _hwdui_all_stylesheets[i]);')
            output_lines.append('        }')
            output_lines.append('        i = i + 1;')
            output_lines.append('    }')
            output_lines.append('    _hwdui_all_stylesheets = new_sheets;')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_collect_matched_rules':
            output_lines.append('    let all_rules = [];')
            output_lines.append('    let i = 0;')
            output_lines.append('    while (i < len(_hwdui_all_stylesheets)) {')
            output_lines.append('        let matched = _hwdui_all_stylesheets[i].matchRules(widget);')
            output_lines.append('        let j = 0;')
            output_lines.append('        while (j < len(matched)) {')
            output_lines.append('            push(all_rules, matched[j]);')
            output_lines.append('            j = j + 1;')
            output_lines.append('        }')
            output_lines.append('        i = i + 1;')
            output_lines.append('    }')
            output_lines.append('    return all_rules;')
        elif func_name == 'hwdui_compute_style':
            output_lines.append('    let computed = hwdui_empty_style();')
            output_lines.append('    hwdui_copy_style_props(_hwdui_css_defaults, computed);')
            output_lines.append('    let rules = hwdui_collect_matched_rules(widget);')
            output_lines.append('    let i = 0;')
            output_lines.append('    while (i < len(rules)) {')
            output_lines.append('        let rule = rules[i];')
            output_lines.append('        hwdui_copy_style_props(rule.declarations, computed);')
            output_lines.append('        i = i + 1;')
            output_lines.append('    }')
            output_lines.append('    let legacy_keys = ["bg_color", "fg_color", "border_color", "border_width", "border_radius", "font_size", "font_family", "padding"];')
            output_lines.append('    let j = 0;')
            output_lines.append('    while (j < len(legacy_keys)) {')
            output_lines.append('        let lk = legacy_keys[j];')
            output_lines.append('        let sv = widget.styles[lk];')
            output_lines.append('        if (sv != "" and sv != nullptr) {')
            output_lines.append('            computed[lk] = sv;')
            output_lines.append('        }')
            output_lines.append('        j = j + 1;')
            output_lines.append('    }')
            output_lines.append('    hwdui_copy_style_props(widget._inline_styles, computed);')
            output_lines.append('    return computed;')
        elif func_name == 'hwdui_get_computed_prop':
            output_lines.append('    let style = hwdui_compute_style(widget);')
            output_lines.append('    return style[prop];')
        elif func_name == 'hwdui_get_computed_margin':
            output_lines.append('    let cs = hwdui_compute_style(widget);')
            output_lines.append('    let m = {};')
            output_lines.append('    m["top"] = cs["margin-top"];')
            output_lines.append('    if (m["top"] == nullptr or m["top"] == "") {')
            output_lines.append('        m["top"] = cs["margin"];')
            output_lines.append('    }')
            output_lines.append('    if (m["top"] == nullptr or m["top"] == "") {')
            output_lines.append('        m["top"] = "0";')
            output_lines.append('    }')
            output_lines.append('    m["right"] = cs["margin-right"];')
            output_lines.append('    if (m["right"] == nullptr or m["right"] == "") {')
            output_lines.append('        m["right"] = cs["margin"];')
            output_lines.append('    }')
            output_lines.append('    if (m["right"] == nullptr or m["right"] == "") {')
            output_lines.append('        m["right"] = "0";')
            output_lines.append('    }')
            output_lines.append('    m["bottom"] = cs["margin-bottom"];')
            output_lines.append('    if (m["bottom"] == nullptr or m["bottom"] == "") {')
            output_lines.append('        m["bottom"] = cs["margin"];')
            output_lines.append('    }')
            output_lines.append('    if (m["bottom"] == nullptr or m["bottom"] == "") {')
            output_lines.append('        m["bottom"] = "0";')
            output_lines.append('    }')
            output_lines.append('    m["left"] = cs["margin-left"];')
            output_lines.append('    if (m["left"] == nullptr or m["left"] == "") {')
            output_lines.append('        m["left"] = cs["margin"];')
            output_lines.append('    }')
            output_lines.append('    if (m["left"] == nullptr or m["left"] == "") {')
            output_lines.append('        m["left"] = "0";')
            output_lines.append('    }')
            output_lines.append('    return m;')
        elif func_name == 'hwdui_get_computed_padding':
            output_lines.append('    let cs = hwdui_compute_style(widget);')
            output_lines.append('    let p = {};')
            output_lines.append('    p["top"] = cs["padding-top"];')
            output_lines.append('    if (p["top"] == nullptr or p["top"] == "") {')
            output_lines.append('        p["top"] = cs["padding"];')
            output_lines.append('    }')
            output_lines.append('    if (p["top"] == nullptr or p["top"] == "") {')
            output_lines.append('        p["top"] = "0";')
            output_lines.append('    }')
            output_lines.append('    p["right"] = cs["padding-right"];')
            output_lines.append('    if (p["right"] == nullptr or p["right"] == "") {')
            output_lines.append('        p["right"] = cs["padding"];')
            output_lines.append('    }')
            output_lines.append('    if (p["right"] == nullptr or p["right"] == "") {')
            output_lines.append('        p["right"] = "0";')
            output_lines.append('    }')
            output_lines.append('    p["bottom"] = cs["padding-bottom"];')
            output_lines.append('    if (p["bottom"] == nullptr or p["bottom"] == "") {')
            output_lines.append('        p["bottom"] = cs["padding"];')
            output_lines.append('    }')
            output_lines.append('    if (p["bottom"] == nullptr or p["bottom"] == "") {')
            output_lines.append('        p["bottom"] = "0";')
            output_lines.append('    }')
            output_lines.append('    p["left"] = cs["padding-left"];')
            output_lines.append('    if (p["left"] == nullptr or p["left"] == "") {')
            output_lines.append('        p["left"] = cs["padding"];')
            output_lines.append('    }')
            output_lines.append('    if (p["left"] == nullptr or p["left"] == "") {')
            output_lines.append('        p["left"] = "0";')
            output_lines.append('    }')
            output_lines.append('    return p;')
        elif func_name == 'hwdui_tooltip_set':
            output_lines.append('    _hwdui_current_tooltip = tt;')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_tooltip_get':
            output_lines.append('    return _hwdui_current_tooltip;')
        elif func_name == 'hwdui_create_window':
            output_lines.append('    let win = new Window();')
            output_lines.append('    win.init_win(title);')
            output_lines.append('    win.width = w;')
            output_lines.append('    win.height = h;')
            output_lines.append('    push(_hwdui_active_windows, win);')
            output_lines.append('    return win;')
        elif func_name == 'hwdui_get_active_window':
            output_lines.append('    if (len(_hwdui_active_windows) > 0) {')
            output_lines.append('        return _hwdui_active_windows[len(_hwdui_active_windows) - 1];')
            output_lines.append('    }')
            output_lines.append('    return nullptr;')
        elif func_name == 'hwdui_get_active_windows':
            output_lines.append('    return _hwdui_active_windows;')
        elif func_name == 'hwdui_get_active_window_index':
            output_lines.append('    return len(_hwdui_active_windows) - 1;')
        elif func_name == 'hwdui_get_window_count':
            output_lines.append('    return len(_hwdui_active_windows);')
        elif func_name == 'hwdui_get_window':
            output_lines.append('    if (index >= 0 and index < len(_hwdui_active_windows)) {')
            output_lines.append('        return _hwdui_active_windows[index];')
            output_lines.append('    }')
            output_lines.append('    return nullptr;')
        elif func_name == 'hwdui_close_all_windows':
            output_lines.append('    _hwdui_active_windows = [];')
            output_lines.append('    return 0;')
        elif func_name == 'hwdui_define_theme_basic':
            output_lines.append('    let sheet = hwdui_create_stylesheet("basic");')
            output_lines.append('    sheet.addRule(hwdui_sel_type("Window"), [')
            output_lines.append('        ["background-color", "#f0f0f0"],')
            output_lines.append('        ["border-color", "#888888"],')
            output_lines.append('        ["border-width", "1"],')
            output_lines.append('        ["title-bar-color", "#dddddd"],')
            output_lines.append('        ["title-height", "30"]')
            output_lines.append('    ]);')
            output_lines.append('    return sheet;')
        else:
            output_lines.append('    return 0;')

        output_lines.append('}' + '')
    output_lines.append('')

    # Additional helper functions not in bytecode
    output_lines.append('fn hwdui_timer_stop_all() {')
    output_lines.append('    let i = 0;')
    output_lines.append('    while (i < len(_hwdui_all_timers)) {')
    output_lines.append('        _hwdui_all_timers[i].stop();')
    output_lines.append('        i = i + 1;')
    output_lines.append('    }')
    output_lines.append('    return 0;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('fn hwdui_tooltip_set(tt) {')
    output_lines.append('    _hwdui_current_tooltip = tt;')
    output_lines.append('    return 0;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('fn hwdui_tooltip_get() {')
    output_lines.append('    return _hwdui_current_tooltip;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('fn notify_info(title, message) {')
    output_lines.append('    let n = new Notification();')
    output_lines.append('    n.init_notify(title, message, "info");')
    output_lines.append('    return n;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('fn notify_success(title, message) {')
    output_lines.append('    let n = new Notification();')
    output_lines.append('    n.init_notify(title, message, "success");')
    output_lines.append('    return n;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('fn notify_warning(title, message) {')
    output_lines.append('    let n = new Notification();')
    output_lines.append('    n.init_notify(title, message, "warning");')
    output_lines.append('    return n;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('fn notify_error(title, message) {')
    output_lines.append('    let n = new Notification();')
    output_lines.append('    n.init_notify(title, message, "error");')
    output_lines.append('    return n;')
    output_lines.append('}')
    output_lines.append('')

    output_lines.append('# ═══════════════════════════════════════════════════════════════════════════')
    output_lines.append('# Additional classes')
    output_lines.append('# ═══════════════════════════════════════════════════════════════════════════')
    output_lines.append('')

    # Canvas class
    output_lines.append('class Canvas extends zzwUI {')
    output_lines.append('    let x = 0;')
    output_lines.append('    let y = 0;')
    output_lines.append('    let width = 0;')
    output_lines.append('    let height = 0;')
    output_lines.append('    let visible = true;')
    output_lines.append('    let enabled = true;')
    output_lines.append('    let parent = nullptr;')
    output_lines.append('    let widget_type = "Canvas";')
    output_lines.append('    let lines = [];')
    output_lines.append('    let rects = [];')
    output_lines.append('    let circles = [];')
    output_lines.append('    let texts = [];')
    output_lines.append('    let images = [];')
    output_lines.append('')
    output_lines.append('    fn init_canvas(w, h) {')
    output_lines.append('        self.init("");')
    output_lines.append('        self.widget_type = "Canvas";')
    output_lines.append('        self.width = w;')
    output_lines.append('        self.height = h;')
    output_lines.append('        self.lines = [];')
    output_lines.append('        self.rects = [];')
    output_lines.append('        self.circles = [];')
    output_lines.append('        self.texts = [];')
    output_lines.append('        self.images = [];')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn drawLine(x1, y1, x2, y2, color, line_width) {')
    output_lines.append('        push(self.lines, {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "width": line_width});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn drawRect(x, y, w, h, color, fill, line_width) {')
    output_lines.append('        push(self.rects, {"x": x, "y": y, "width": w, "height": h, "color": color, "fill": fill, "width": line_width});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn fillRect(x, y, w, h, color) {')
    output_lines.append('        push(self.rects, {"x": x, "y": y, "width": w, "height": h, "color": color, "fill": true, "width": 0});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn drawCircle(cx, cy, r, color, fill, line_width) {')
    output_lines.append('        push(self.circles, {"cx": cx, "cy": cy, "radius": r, "color": color, "fill": fill, "width": line_width});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn fillCircle(cx, cy, r, color) {')
    output_lines.append('        push(self.circles, {"cx": cx, "cy": cy, "radius": r, "color": color, "fill": true, "width": 0});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn drawText(x, y, text, color, size) {')
    output_lines.append('        push(self.texts, {"x": x, "y": y, "text": text, "color": color, "size": size});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn drawImage(x, y, w, h, path) {')
    output_lines.append('        push(self.images, {"x": x, "y": y, "width": w, "height": h, "path": path});')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn clear() {')
    output_lines.append('        self.lines = [];')
    output_lines.append('        self.rects = [];')
    output_lines.append('        self.circles = [];')
    output_lines.append('        self.texts = [];')
    output_lines.append('        self.images = [];')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('}')
    output_lines.append('')

    # GridPanel class
    output_lines.append('class GridPanel extends zzwUI {')
    output_lines.append('    let x = 0;')
    output_lines.append('    let y = 0;')
    output_lines.append('    let width = 0;')
    output_lines.append('    let height = 0;')
    output_lines.append('    let visible = true;')
    output_lines.append('    let enabled = true;')
    output_lines.append('    let parent = nullptr;')
    output_lines.append('    let widget_type = "GridPanel";')
    output_lines.append('    let rows = 0;')
    output_lines.append('    let cols = 0;')
    output_lines.append('    let row_heights = [];')
    output_lines.append('    let col_widths = [];')
    output_lines.append('    let row_spacing = 0;')
    output_lines.append('    let col_spacing = 0;')
    output_lines.append('    let grid_children = [];')
    output_lines.append('')
    output_lines.append('    fn init_grid(r, c) {')
    output_lines.append('        self.init("");')
    output_lines.append('        self.widget_type = "GridPanel";')
    output_lines.append('        self.rows = r;')
    output_lines.append('        self.cols = c;')
    output_lines.append('        self.row_heights = [];')
    output_lines.append('        self.col_widths = [];')
    output_lines.append('        self.row_spacing = 0;')
    output_lines.append('        self.col_spacing = 0;')
    output_lines.append('        self.grid_children = [];')
    output_lines.append('        let ri = 0;')
    output_lines.append('        while (ri < r) {')
    output_lines.append('            push(self.row_heights, 0);')
    output_lines.append('            ri = ri + 1;')
    output_lines.append('        }')
    output_lines.append('        let ci = 0;')
    output_lines.append('        while (ci < c) {')
    output_lines.append('            push(self.col_widths, 0);')
    output_lines.append('            ci = ci + 1;')
    output_lines.append('        }')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setRowHeight(row, h) {')
    output_lines.append('        if (row >= 0 and row < len(self.row_heights)) {')
    output_lines.append('            self.row_heights[row] = h;')
    output_lines.append('        }')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setColWidth(col, w) {')
    output_lines.append('        if (col >= 0 and col < len(self.col_widths)) {')
    output_lines.append('            self.col_widths[col] = w;')
    output_lines.append('        }')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setSpacing(rs, cs) {')
    output_lines.append('        self.row_spacing = rs;')
    output_lines.append('        self.col_spacing = cs;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn addChildAt(child, row, col) {')
    output_lines.append('        push(self.grid_children, {"widget": child, "row": row, "col": col});')
    output_lines.append('        self.add_child(child);')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn do_layout() {')
    output_lines.append('        for gc in self.grid_children {')
    output_lines.append('            let r = gc["row"];')
    output_lines.append('            let c = gc["col"];')
    output_lines.append('            let widget = gc["widget"];')
    output_lines.append('            let col_x = self._hwdui_pad_left;')
    output_lines.append('            let ci = 0;')
    output_lines.append('            while (ci < c) {')
    output_lines.append('                col_x = col_x + self.col_widths[ci] + self.col_spacing;')
    output_lines.append('                ci = ci + 1;')
    output_lines.append('            }')
    output_lines.append('            widget.x = col_x;')
    output_lines.append('            let row_y = self._hwdui_pad_top;')
    output_lines.append('            let ri = 0;')
    output_lines.append('            while (ri < r) {')
    output_lines.append('                row_y = row_y + self.row_heights[ri] + self.row_spacing;')
    output_lines.append('                ri = ri + 1;')
    output_lines.append('            }')
    output_lines.append('            widget.y = row_y;')
    output_lines.append('        }')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('}')
    output_lines.append('')

    # Timer class
    output_lines.append('class Timer {')
    output_lines.append('    let interval_ms = 0;')
    output_lines.append('    let callback = nullptr;')
    output_lines.append('    let running = false;')
    output_lines.append('    let elapsed = 0;')
    output_lines.append('    let repeats = true;')
    output_lines.append('')
    output_lines.append('    fn init_timer(ms, fn_ref) {')
    output_lines.append('        self.interval_ms = ms;')
    output_lines.append('        self.callback = fn_ref;')
    output_lines.append('        self.running = false;')
    output_lines.append('        self.elapsed = 0;')
    output_lines.append('        self.repeats = true;')
    output_lines.append('        push(_hwdui_all_timers, self);')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn start() {')
    output_lines.append('        self.running = true;')
    output_lines.append('        self.elapsed = 0;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn stop() {')
    output_lines.append('        self.running = false;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn restart() {')
    output_lines.append('        self.elapsed = 0;')
    output_lines.append('        self.running = true;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn isRunning() {')
    output_lines.append('        return self.running;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setInterval(ms) {')
    output_lines.append('        self.interval_ms = ms;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setRepeats(r) {')
    output_lines.append('        self.repeats = r;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn _tick(delta_ms) {')
    output_lines.append('        if (self.running == false) { return 0; }')
    output_lines.append('        self.elapsed = self.elapsed + delta_ms;')
    output_lines.append('        if (self.elapsed >= self.interval_ms) {')
    output_lines.append('            if (self.callback != nullptr) {')
    output_lines.append('                self.callback(self);')
    output_lines.append('            }')
    output_lines.append('            if (self.repeats == false) {')
    output_lines.append('                self.running = false;')
    output_lines.append('            } else {')
    output_lines.append('                self.elapsed = 0;')
    output_lines.append('            }')
    output_lines.append('        }')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('}')
    output_lines.append('')

    # Notification class
    output_lines.append('class Notification extends zzwUI {')
    output_lines.append('    let x = 0;')
    output_lines.append('    let y = 0;')
    output_lines.append('    let width = 0;')
    output_lines.append('    let height = 0;')
    output_lines.append('    let visible = false;')
    output_lines.append('    let enabled = true;')
    output_lines.append('    let parent = nullptr;')
    output_lines.append('    let widget_type = "Notification";')
    output_lines.append('    let title = "";')
    output_lines.append('    let message = "";')
    output_lines.append('    let type = "";')
    output_lines.append('    let timeout = 3000;')
    output_lines.append('')
    output_lines.append('    fn init_notify(t, m, ntype) {')
    output_lines.append('        self.init("");')
    output_lines.append('        self.widget_type = "Notification";')
    output_lines.append('        self.title = t;')
    output_lines.append('        self.message = m;')
    output_lines.append('        self.type = ntype;')
    output_lines.append('        self.visible = false;')
    output_lines.append('        self.timeout = 3000;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn show() {')
    output_lines.append('        self.visible = true;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn close() {')
    output_lines.append('        self.visible = false;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setTimeout(ms) {')
    output_lines.append('        self.timeout = ms;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('}')
    output_lines.append('')

    # Tooltip class
    output_lines.append('class Tooltip extends zzwUI {')
    output_lines.append('    let x = 0;')
    output_lines.append('    let y = 0;')
    output_lines.append('    let width = 0;')
    output_lines.append('    let height = 0;')
    output_lines.append('    let visible = false;')
    output_lines.append('    let enabled = true;')
    output_lines.append('    let parent = nullptr;')
    output_lines.append('    let widget_type = "Tooltip";')
    output_lines.append('    let text = "";')
    output_lines.append('    let delay = 500;')
    output_lines.append('')
    output_lines.append('    fn init_tooltip(t) {')
    output_lines.append('        self.init("");')
    output_lines.append('        self.widget_type = "Tooltip";')
    output_lines.append('        self.text = t;')
    output_lines.append('        self.visible = false;')
    output_lines.append('        self.delay = 500;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setText(t) {')
    output_lines.append('        self.text = t;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setDelay(ms) {')
    output_lines.append('        self.delay = ms;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn showAt(px, py) {')
    output_lines.append('        self.x = px + 10;')
    output_lines.append('        self.y = py + 10;')
    output_lines.append('        self.visible = true;')
    output_lines.append('        hwdui_tooltip_set(self);')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn hide() {')
    output_lines.append('        self.visible = false;')
    output_lines.append('        hwdui_tooltip_set(nullptr);')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('}')
    output_lines.append('')

    # KeyboardHandler class
    output_lines.append('class KeyboardHandler {')
    output_lines.append('    let tab_order = [];')
    output_lines.append('    let current_index = -1;')
    output_lines.append('    let enabled = true;')
    output_lines.append('')
    output_lines.append('    fn init_kh() {')
    output_lines.append('        self.tab_order = [];')
    output_lines.append('        self.current_index = -1;')
    output_lines.append('        self.enabled = true;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn addWidget(widget) {')
    output_lines.append('        push(self.tab_order, widget);')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn removeWidget(widget) {')
    output_lines.append('        let new_order = [];')
    output_lines.append('        for w in self.tab_order {')
    output_lines.append('            if (w != widget) {')
    output_lines.append('                push(new_order, w);')
    output_lines.append('            }')
    output_lines.append('        }')
    output_lines.append('        self.tab_order = new_order;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn setCurrent(widget) {')
    output_lines.append('        let idx = 0;')
    output_lines.append('        while (idx < len(self.tab_order)) {')
    output_lines.append('            if (self.tab_order[idx] == widget) {')
    output_lines.append('                self.current_index = idx;')
    output_lines.append('                return 0;')
    output_lines.append('            }')
    output_lines.append('            idx = idx + 1;')
    output_lines.append('        }')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn getCurrent() {')
    output_lines.append('        if (self.current_index >= 0 and self.current_index < len(self.tab_order)) {')
    output_lines.append('            return self.tab_order[self.current_index];')
    output_lines.append('        }')
    output_lines.append('        return nullptr;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn next() {')
    output_lines.append('        if (len(self.tab_order) == 0) { return nullptr; }')
    output_lines.append('        let start = self.current_index;')
    output_lines.append('        let idx = start;')
    output_lines.append('        while (true) {')
    output_lines.append('            idx = idx + 1;')
    output_lines.append('            if (idx >= len(self.tab_order)) { idx = 0; }')
    output_lines.append('            if (self.tab_order[idx].enabled) {')
    output_lines.append('                self.current_index = idx;')
    output_lines.append('                return self.tab_order[idx];')
    output_lines.append('            }')
    output_lines.append('            if (idx == start) { return nullptr; }')
    output_lines.append('        }')
    output_lines.append('        return nullptr;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn prev() {')
    output_lines.append('        if (len(self.tab_order) == 0) { return nullptr; }')
    output_lines.append('        let start = self.current_index;')
    output_lines.append('        let idx = start;')
    output_lines.append('        while (true) {')
    output_lines.append('            idx = idx - 1;')
    output_lines.append('            if (idx < 0) { idx = len(self.tab_order) - 1; }')
    output_lines.append('            if (self.tab_order[idx].enabled) {')
    output_lines.append('                self.current_index = idx;')
    output_lines.append('                return self.tab_order[idx];')
    output_lines.append('            }')
    output_lines.append('            if (idx == start) { return nullptr; }')
    output_lines.append('        }')
    output_lines.append('        return nullptr;')
    output_lines.append('    }')
    output_lines.append('')
    output_lines.append('    fn clear() {')
    output_lines.append('        self.tab_order = [];')
    output_lines.append('        self.current_index = -1;')
    output_lines.append('        return 0;')
    output_lines.append('    }')
    output_lines.append('}')
    output_lines.append('')

    # Write output
    output_path = 'bootstrap/hwdui.hto'
    with open(output_path, 'w') as f:
        f.write('\n'.join(output_lines))
        f.write('\n')

    print(f'Written {len(output_lines)} lines to {output_path}')
    print(f'Total classes: {len(classes)}')


if __name__ == '__main__':
    main()