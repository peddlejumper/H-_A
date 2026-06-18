#!/usr/bin/env python3
"""
═══ zzw UI v6.0 — 可视化功能演示 ═══
H# GUI Library Gallery — 500+ Features Showcase
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import random

# ═══════════════════════════════════════════════════════════════════════════
# 全局样式表 — 现代极简设计
# ═══════════════════════════════════════════════════════════════════════════

MAIN_STYLE = """
QMainWindow, QWidget {
    background-color: #0f1119;
    color: #e0e0e0;
    font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

QMenuBar {
    background: #161822;
    color: #c0c4cc;
    border-bottom: 1px solid #252840;
    padding: 2px;
}
QMenuBar::item:selected {
    background: #252840;
    border-radius: 4px;
}
QMenu {
    background: #1a1d2e;
    border: 1px solid #313556;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #313556;
}

QStatusBar {
    background: #161822;
    color: #6b7394;
    border-top: 1px solid #252840;
    font-size: 12px;
}

QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #6b7394;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #7c8cf8;
    border-bottom: 2px solid #7c8cf8;
}
QTabBar::tab:hover:!selected {
    color: #a0a8d0;
}

QToolBar {
    background: #161822;
    border: none;
    padding: 4px;
    spacing: 4px;
}
"""

CARD_STYLE = """
QFrame#card {
    background: #161a26;
    border: 1px solid #252840;
    border-radius: 12px;
    padding: 16px;
}
"""

BUTTON_PRIMARY = """
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7378f5, stop:1 #9b6ff8);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5355e0, stop:1 #7b4de0);
}
"""

BUTTON_SUCCESS = """
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #34d399);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #12c78a, stop:1 #3de0a8);
}
"""

BUTTON_DANGER = """
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #f87171);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f15050, stop:1 #f98080);
}
"""

BUTTON_OUTLINE = """
QPushButton {
    background: transparent;
    color: #7c8cf8;
    border: 1.5px solid #313556;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background: rgba(124, 140, 248, 0.08);
    border-color: #7c8cf8;
}
"""

INPUT_STYLE = """
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #121420;
    color: #e0e0e0;
    border: 1px solid #252840;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: #6366f1;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1.5px solid #6366f1;
    background: #141722;
}
QLineEdit::placeholder {
    color: #4a5078;
}
"""

COMBO_STYLE = """
QComboBox {
    background: #121420;
    color: #e0e0e0;
    border: 1px solid #252840;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    min-width: 120px;
}
QComboBox:focus {
    border: 1.5px solid #6366f1;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background: #1a1d2e;
    color: #e0e0e0;
    border: 1px solid #313556;
    border-radius: 8px;
    selection-background-color: #313556;
}
"""

SLIDER_STYLE = """
QSlider::groove:horizontal {
    background: #252840;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #6366f1;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #7c8cf8;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
    border-radius: 3px;
}
"""

PROGRESS_STYLE = """
QProgressBar {
    background: #252840;
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    font-size: 10px;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #10b981);
    border-radius: 6px;
}
"""

CHECKBOX_STYLE = """
QCheckBox {
    color: #c0c4cc;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #313556;
    border-radius: 4px;
    background: #121420;
}
QCheckBox::indicator:checked {
    background: #6366f1;
    border-color: #6366f1;
}
QCheckBox::indicator:hover {
    border-color: #6366f1;
}
"""

RADIO_STYLE = """
QRadioButton {
    color: #c0c4cc;
    font-size: 13px;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #313556;
    border-radius: 9px;
    background: #121420;
}
QRadioButton::indicator:checked {
    background: #6366f1;
    border-color: #6366f1;
}
"""

SCROLLBAR_STYLE = """
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #252840;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #313556;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #252840;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

LIST_STYLE = """
QListWidget {
    background: #121420;
    color: #e0e0e0;
    border: 1px solid #252840;
    border-radius: 8px;
    padding: 4px;
    font-size: 13px;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #313556;
    color: #a0a8d0;
}
QListWidget::item:hover:!selected {
    background: #1e2240;
}
"""

TREE_STYLE = """
QTreeWidget {
    background: #121420;
    color: #e0e0e0;
    border: 1px solid #252840;
    border-radius: 8px;
    font-size: 13px;
    outline: none;
}
QTreeWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QTreeWidget::item:selected {
    background: #313556;
}
QTreeWidget::item:hover:!selected {
    background: #1e2240;
}
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    border-image: none;
}
"""

TABLE_STYLE = """
QTableWidget {
    background: #121420;
    color: #e0e0e0;
    border: 1px solid #252840;
    border-radius: 8px;
    gridline-color: #1e2240;
    font-size: 13px;
    outline: none;
}
QTableWidget::item {
    padding: 6px 10px;
}
QTableWidget::item:selected {
    background: #313556;
    color: #a0a8d0;
}
QHeaderView::section {
    background: #161822;
    color: #6b7394;
    border: none;
    border-bottom: 2px solid #252840;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
}
"""

DOCK_STYLE = """
QDockWidget {
    color: #e0e0e0;
    titlebar-close-icon: none;
}
QDockWidget::title {
    background: #161822;
    padding: 8px 12px;
    border-bottom: 1px solid #252840;
}
"""

def make_card(widget=None):
    """Wrap widget in a card frame"""
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet(CARD_STYLE)
    if widget:
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(widget)
    return card

def section_label(text):
    """Create a section header"""
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #e8eaed; margin-top: 8px; margin-bottom: 4px;")
    return lbl

def sub_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 13px; color: #6b7394; margin-bottom: 12px;")
    return lbl

def small_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #a0a8d0; margin-top: 8px; margin-bottom: 6px;")
    return lbl

def themed_btn(text, style=BUTTON_PRIMARY):
    btn = QPushButton(text)
    btn.setStyleSheet(style)
    btn.setCursor(Qt.PointingHandCursor)
    return btn

def themed_input(placeholder=""):
    inp = QLineEdit()
    inp.setPlaceholderText(placeholder)
    inp.setStyleSheet(INPUT_STYLE)
    return inp


# ═══════════════════════════════════════════════════════════════════════════
# 主窗口 — zzw UI Gallery
# ═══════════════════════════════════════════════════════════════════════════

class ZzwUIGallery(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("zzw UI v6.0 — Gallery")
        self.resize(1300, 780)
        self.setMinimumSize(1100, 650)
        
        # 暗色调窗口背景
        self.setStyleSheet(MAIN_STYLE)
        
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_central()
        self._setup_dock()
        
        # 居中
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width()-1300)//2, (screen.height()-780)//2)

    def _setup_menubar(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("文件")
        file_menu.addAction("新建窗口").triggered.connect(lambda: self._show_msg("新建"))
        file_menu.addAction("打开...").triggered.connect(lambda: self._show_msg("打开"))
        file_menu.addSeparator()
        file_menu.addAction("退出").triggered.connect(self.close)
        
        edit_menu = mb.addMenu("编辑")
        edit_menu.addAction("撤销")
        edit_menu.addAction("重做")
        
        view_menu = mb.addMenu("视图")
        for theme in ["Ocean", "Forest", "Material", "Dark", "Cyberpunk"]:
            view_menu.addAction(f"主题: {theme}")
        
        help_menu = mb.addMenu("帮助")
        help_menu.addAction("关于 zzw UI").triggered.connect(self._show_about)

    def _setup_statusbar(self):
        sb = self.statusBar()
        self.status_label = QLabel("Ready — zzw UI v6.0 | 318 classes | 500 features")
        sb.addWidget(self.status_label)
        
        theme_badge = QLabel("  Dark Theme  ")
        theme_badge.setStyleSheet("background: #313556; color: #a0a8d0; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
        sb.addPermanentWidget(theme_badge)

    def _setup_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0,0,0,0)
        main.setSpacing(0)
        
        # ── 左侧导航 ──
        nav = self._create_nav()
        main.addWidget(nav)
        
        # ── 右侧内容 ──
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: #0f1119;")
        
        self.content_stack.addWidget(self._page_buttons())
        self.content_stack.addWidget(self._page_inputs())
        self.content_stack.addWidget(self._page_displays())
        self.content_stack.addWidget(self._page_data())
        self.content_stack.addWidget(self._page_layouts())
        self.content_stack.addWidget(self._page_v600())
        
        main.addWidget(self.content_stack, 1)

    def _create_nav(self):
        nav = QFrame()
        nav.setFixedWidth(220)
        nav.setStyleSheet("QFrame { background: #13151f; border-right: 1px solid #1e2240; }")
        layout = QVBoxLayout(nav)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)
        
        # Logo
        logo = QLabel("  ◈  zzw UI")
        logo.setStyleSheet("font-size: 18px; font-weight: 800; color: #e0e0e0; padding: 8px 4px 16px 4px;")
        layout.addWidget(logo)
        
        # 菜单项
        nav_items = [
            ("📋 按钮与触发器", 0, True),
            ("✏️ 输入与表单", 1, None),
            ("📊 展示与进度", 2, None),
            ("🗂️ 数据与列表", 3, None),
            ("📐 布局与容器", 4, None),
            ("✨ v6.0 新功能", 5, None),
        ]
        
        self.nav_btns = []
        for text, index, active in nav_items:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            if active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #252840; color: #a0a8d0;
                        border: none; border-radius: 8px;
                        padding: 10px 14px; font-size: 13px; font-weight: 600;
                        text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent; color: #6b7394;
                        border: none; border-radius: 8px;
                        padding: 10px 14px; font-size: 13px; font-weight: 500;
                        text-align: left;
                    }
                    QPushButton:hover { background: #1a1d2e; color: #a0a8d0; }
                """)
            btn.clicked.connect(lambda checked, i=index: self._switch_page(i))
            layout.addWidget(btn)
            self.nav_btns.append(btn)
        
        layout.addStretch()
        
        # 底部版本号
        ver = QLabel("v6.0 · 500 Features")
        ver.setStyleSheet("color: #3a4060; font-size: 11px; padding: 12px 4px;")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)
        
        return nav

    def _switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            if i == index:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #252840; color: #a0a8d0;
                        border: none; border-radius: 8px;
                        padding: 10px 14px; font-size: 13px; font-weight: 600;
                        text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent; color: #6b7394;
                        border: none; border-radius: 8px;
                        padding: 10px 14px; font-size: 13px; font-weight: 500;
                        text-align: left;
                    }
                    QPushButton:hover { background: #1a1d2e; color: #a0a8d0; }
                """)

    def _setup_dock(self):
        """右侧属性面板"""
        dock = QDockWidget("检查器", self)
        dock.setStyleSheet(DOCK_STYLE)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        
        inspector = QWidget()
        insp_layout = QVBoxLayout(inspector)
        insp_layout.setContentsMargins(12,12,12,12)
        insp_layout.setSpacing(10)
        
        insp_layout.addWidget(QLabel("zzw UI v6.0"))
        insp_layout.addWidget(themed_btn("运行 Demo"))
        
        insp_layout.addStretch()
        
        # 统计信息
        stats_label = QLabel(
            "📦 318 个类\n"
            "⚡ 182 个函数\n"
            "🎨 25+ 主题\n"
            "🏗️ 26 个功能板块"
        )
        stats_label.setStyleSheet("color: #6b7394; font-size: 12px; line-height: 1.6;")
        insp_layout.addWidget(stats_label)
        
        dock.setWidget(inspector)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    # ═══════════════════════════════════════════════════════════════
    # 页面 1: 按钮与触发器
    # ═══════════════════════════════════════════════════════════════

    def _page_buttons(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } " + SCROLLBAR_STYLE)
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(32, 24, 32, 32)
        ly.setSpacing(20)
        
        # 标题
        ly.addWidget(section_label("按钮与触发器"))
        ly.addWidget(sub_label("ToggleButton, IconButton, SplitButton, DropDownButton, FlatButton, ToggleSwitch 等"))
        
        # 基础按钮行
        ly.addWidget(small_title("基础按钮变体"))
        row1 = QHBoxLayout()
        row1.addWidget(themed_btn("Primary", BUTTON_PRIMARY))
        row1.addWidget(themed_btn("Success", BUTTON_SUCCESS))
        row1.addWidget(themed_btn("Danger", BUTTON_DANGER))
        row1.addWidget(themed_btn("Outline", BUTTON_OUTLINE))
        row1.addStretch()
        ly.addLayout(row1)
        ly.addWidget(make_card(QWidget()))  # spacer card doesn't matter
        
        # Toggle 按钮
        ly.addWidget(small_title("Toggle 按钮 — ToggleButton"))
        toggle_row = QHBoxLayout()
        for label, emoji in [("Bold", "B"), ("Italic", "I"), ("Underline", "U"), ("Strike", "S")]:
            tb = QPushButton(f"  {emoji}  {label}")
            tb.setCheckable(True)
            tb.setCursor(Qt.PointingHandCursor)
            tb.setStyleSheet(BUTTON_OUTLINE)
            toggle_row.addWidget(tb)
        toggle_row.addStretch()
        ly.addLayout(toggle_row)
        
        # Icon Buttons
        ly.addWidget(small_title("Icon 按钮 — IconButton"))
        icon_row = QHBoxLayout()
        for icon_text in ["❤️", "⭐", "🔍", "⚙️", "📁", "💾", "↩️", "🔄"]:
            ib = QPushButton(icon_text)
            ib.setFixedSize(44, 44)
            ib.setCursor(Qt.PointingHandCursor)
            ib.setStyleSheet("""
                QPushButton {
                    background: #161a26; color: #a0a8d0;
                    border: 1px solid #252840; border-radius: 10px;
                    font-size: 18px;
                }
                QPushButton:hover { background: #252840; border-color: #6366f1; }
            """)
            icon_row.addWidget(ib)
        icon_row.addStretch()
        ly.addLayout(icon_row)
        
        # ToggleSwitch
        ly.addWidget(small_title("ToggleSwitch — 开关"))
        switch_row = QHBoxLayout()
        for i in range(3):
            sw = QCheckBox(f"选项 {i+1}")
            sw.setStyleSheet(CHECKBOX_STYLE)
            switch_row.addWidget(sw)
        switch_row.addStretch()
        ly.addLayout(switch_row)
        
        # SplitButton & DropDown
        ly.addWidget(small_title("SplitButton / DropDownButton"))
        drop_row = QHBoxLayout()
        for text in ["文件 ▼", "编辑 ▼", "视图 ▼", "帮助 ▼"]:
            db = QPushButton(text)
            db.setCursor(Qt.PointingHandCursor)
            db.setStyleSheet(BUTTON_OUTLINE.replace("border-radius: 8px", "border-radius: 8px 0 0 8px").replace("padding: 10px 24px", "padding: 10px 14px"))
            drop_row.addWidget(db)
        drop_row.addStretch()
        ly.addLayout(drop_row)
        
        # ButtonGroup
        ly.addWidget(small_title("ButtonGroup — 按钮组"))
        bg_row = QHBoxLayout()
        bg = QButtonGroup(self)
        for label in ["全部", "图片", "文档", "音频", "视频"]:
            rb = QRadioButton(label)
            rb.setStyleSheet(RADIO_STYLE)
            bg.addButton(rb)
            bg_row.addWidget(rb)
        bg.buttons()[0].setChecked(True)
        bg_row.addStretch()
        ly.addLayout(bg_row)
        
        ly.addStretch()
        scroll.setWidget(w)
        return scroll

    # ═══════════════════════════════════════════════════════════════
    # 页面 2: 输入与表单
    # ═══════════════════════════════════════════════════════════════

    def _page_inputs(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } " + SCROLLBAR_STYLE)
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(32, 24, 32, 32)
        ly.setSpacing(20)
        
        ly.addWidget(section_label("输入与表单"))
        ly.addWidget(sub_label("TextBox, PasswordBox, SearchBox, MaskedTextBox, AutoCompleteBox, RichTextBox, CodeEditor 等"))
        
        # 表单布局
        form = QGridLayout()
        form.setVerticalSpacing(16)
        form.setHorizontalSpacing(20)
        
        fields = [
            ("用户名", "请输入用户名", "text"),
            ("邮箱", "user@example.com", "text"),
            ("密码", "••••••••", "password"),
            ("搜索", "搜索...", "text"),
            ("电话号码", "+86 138-0000-0000", "text"),
            ("地址", "请输入地址", "text"),
            ("城市", "请选择城市", "combo"),
            ("备注", "添加备注...", "textarea"),
        ]
        
        for row, (label, placeholder, ftype) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #a0a8d0; font-size: 13px; font-weight: 500;")
            form.addWidget(lbl, row, 0)
            
            if ftype == "combo":
                inp = QComboBox()
                inp.addItems(["北京", "上海", "深圳", "杭州", "成都"])
                inp.setStyleSheet(COMBO_STYLE)
                inp.setEditable(True)
            elif ftype == "textarea":
                inp = QTextEdit()
                inp.setPlaceholderText(placeholder)
                inp.setMaximumHeight(80)
                inp.setStyleSheet(INPUT_STYLE)
            elif ftype == "password":
                inp = QLineEdit()
                inp.setPlaceholderText(placeholder)
                inp.setEchoMode(QLineEdit.Password)
                inp.setStyleSheet(INPUT_STYLE)
            else:
                inp = themed_input(placeholder)
            
            form.addWidget(inp, row, 1)
        
        ly.addLayout(form)
        
        # Checkbox 和 Radio 行
        ly.addWidget(small_title("CheckBox / RadioButton"))
        ck_row = QHBoxLayout()
        for label in ["接受条款", "订阅通知", "记住密码"]:
            cb = QCheckBox(label)
            cb.setStyleSheet(CHECKBOX_STYLE)
            ck_row.addWidget(cb)
        ck_row.addStretch()
        ly.addLayout(ck_row)
        
        # NumericUpDown / SpinBox / Stepper
        ly.addWidget(small_title("NumericUpDown / SpinBox / Stepper"))
        num_row = QHBoxLayout()
        for label, mn, mx, v in [("数量", 0, 100, 1), ("百分比", 0, 100, 50), ("步长", 0, 1000, 10)]:
            nl = QLabel(label)
            nl.setStyleSheet("color: #6b7394; font-size: 12px;")
            num_row.addWidget(nl)
            sp = QSpinBox()
            sp.setRange(mn, mx); sp.setValue(v)
            sp.setStyleSheet(INPUT_STYLE)
            num_row.addWidget(sp)
        num_row.addStretch()
        ly.addLayout(num_row)
        
        # Slider 行
        ly.addWidget(small_title("Slider"))
        for label in ["音量", "亮度", "对比度"]:
            sl_row = QHBoxLayout()
            nl = QLabel(label)
            nl.setStyleSheet("color: #6b7394; font-size: 12px; min-width: 50px;")
            sl_row.addWidget(nl)
            sl = QSlider(Qt.Horizontal); sl.setValue(random.randint(20, 80))
            sl.setStyleSheet(SLIDER_STYLE)
            sl_row.addWidget(sl, 1)
            val = QLabel(str(sl.value())+"%")
            val.setStyleSheet("color: #a0a8d0; font-size: 12px; min-width: 36px;")
            sl.valueChanged.connect(lambda v, l=val: l.setText(f"{v}%"))
            sl_row.addWidget(val)
            ly.addLayout(sl_row)
        
        # Date/Time
        ly.addWidget(small_title("DatePicker / TimePicker / DateTimePicker"))
        dt_row = QHBoxLayout()
        cal = QCalendarWidget()
        cal.setStyleSheet("""
            QCalendarWidget { background: #121420; color: #e0e0e0; border-radius: 8px; }
            QCalendarWidget QToolButton { color: #a0a8d0; border: none; padding: 6px; }
            QCalendarWidget QMenu { background: #1a1d2e; }
        """)
        cal.setMaximumSize(280, 220)
        dt_row.addWidget(cal)
        dt_col = QVBoxLayout()
        te = QTimeEdit(QTime.currentTime())
        te.setStyleSheet(INPUT_STYLE)
        dt_col.addWidget(te)
        de = QDateEdit(QDate.currentDate())
        de.setStyleSheet(INPUT_STYLE)
        de.setCalendarPopup(True)
        dt_col.addWidget(de)
        dte = QDateTimeEdit(QDateTime.currentDateTime())
        dte.setStyleSheet(INPUT_STYLE)
        dte.setCalendarPopup(True)
        dt_col.addWidget(dte)
        dt_row.addLayout(dt_col)
        ly.addLayout(dt_row)
        
        # ColorPicker
        ly.addWidget(small_title("ColorPicker"))
        cp_row = QHBoxLayout()
        for color in ["#6366f1", "#10b981", "#ef4444", "#f59e0b", "#ec4899", "#06b6d4", "#8b5cf6", "#14b8a6"]:
            cb = QPushButton()
            cb.setFixedSize(32, 32)
            cb.setCursor(Qt.PointingHandCursor)
            cb.setStyleSheet(f"""
                QPushButton {{ background: {color}; border-radius: 16px; border: 2px solid transparent; }}
                QPushButton:hover {{ border-color: white; }}
            """)
            def make_click(col):
                return lambda: self._show_msg(f"选中颜色: {col}")
            cb.clicked.connect(make_click(color))
            cp_row.addWidget(cb)
        cp_row.addStretch()
        ly.addLayout(cp_row)
        
        ly.addStretch()
        scroll.setWidget(w)
        return scroll

    # ═══════════════════════════════════════════════════════════════
    # 页面 3: 展示与进度
    # ═══════════════════════════════════════════════════════════════

    def _page_displays(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } " + SCROLLBAR_STYLE)
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(32, 24, 32, 32)
        ly.setSpacing(20)
        
        ly.addWidget(section_label("展示与进度"))
        ly.addWidget(sub_label("ProgressBar, CircularProgress, Rating, Badge, Separator, Image, Notification 等"))
        
        # Progress
        ly.addWidget(small_title("ProgressBar"))
        for val in [25, 50, 75, 100]:
            p_row = QHBoxLayout()
            nl = QLabel(f"{val}%")
            nl.setStyleSheet("color: #6b7394; font-size: 12px; min-width: 36px;")
            p_row.addWidget(nl)
            pb = QProgressBar()
            pb.setValue(val)
            pb.setStyleSheet(PROGRESS_STYLE)
            p_row.addWidget(pb, 1)
            ly.addLayout(p_row)
        
        # 圆形进度模拟
        ly.addWidget(small_title("CircularProgress"))
        circ_row = QHBoxLayout()
        for pct in [25, 50, 75, 90]:
            circ = self._make_circular_progress(pct, 62)
            circ_row.addWidget(circ)
        circ_row.addStretch()
        ly.addLayout(circ_row)
        
        # Rating
        ly.addWidget(small_title("Rating"))
        rate_row = QHBoxLayout()
        stars_label = QLabel("★★★★★")
        stars_label.setStyleSheet("font-size: 28px; color: #f59e0b;")
        rate_row.addWidget(stars_label)
        rate_val = QLabel("4.8 / 5.0")
        rate_val.setStyleSheet("color: #a0a8d0; font-size: 16px; font-weight: 600; margin-left: 10px;")
        rate_row.addWidget(rate_val)
        rate_row.addStretch()
        ly.addLayout(rate_row)
        
        # Badges
        ly.addWidget(small_title("Badge"))
        badge_row = QHBoxLayout()
        for text, color in [("新", "#ef4444"), ("热", "#f59e0b"), ("推荐", "#10b981"), ("v6.0", "#6366f1")]:
            b = QLabel(f"  {text}  ")
            b.setStyleSheet(f"background: {color}; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;")
            badge_row.addWidget(b)
        badge_row.addStretch()
        ly.addLayout(badge_row)
        
        # Notifications
        ly.addWidget(small_title("Notification / Toast"))
        notif_types = [("✓ 操作成功", "#10b981"), ("⚠ 请注意", "#f59e0b"), ("✕ 发生错误", "#ef4444"), ("ℹ 提示信息", "#6366f1")]
        for msg, color in notif_types:
            nf = QFrame()
            nf.setStyleSheet(f"""
                QFrame {{ background: {color}18; border: 1px solid {color}40; border-radius: 8px; padding: 10px 16px; }}
                QLabel {{ color: {color}; font-size: 13px; }}
            """)
            nl = QHBoxLayout(nf)
            nl.addWidget(QLabel(msg))
            ly.addWidget(nf)
        
        # Canvas 模拟
        ly.addWidget(small_title("Canvas 绘图"))
        canvas = self._make_mini_canvas()
        ly.addWidget(canvas)
        
        ly.addStretch()
        scroll.setWidget(w)
        return scroll

    def _make_circular_progress(self, pct, size):
        """创建圆形进度指示器"""
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        
        # 背景圆弧
        pen = QPen(QColor("#252840"), 5)
        p.setPen(pen)
        p.drawArc(6, 6, size-12, size-12, 0, 360*16)
        
        # 进度圆弧
        pen = QPen()
        gradient = QConicalGradient(size/2, size/2, 90)
        gradient.setColorAt(0, QColor("#6366f1"))
        gradient.setColorAt(1, QColor("#10b981"))
        pen.setBrush(gradient)
        pen.setWidth(5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        span = int(pct * 3.6 * 16)  # convert to 1/16 degree
        p.drawArc(6, 6, size-12, size-12, 90*16, -span)
        
        # 文字
        p.setPen(QColor("#e0e0e0"))
        font = QFont()
        font.setPixelSize(size//5)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, f"{pct}%")
        
        p.end()
        
        lbl = QLabel()
        lbl.setPixmap(pix)
        lbl.setFixedSize(size+10, size+10)
        return lbl

    def _make_mini_canvas(self):
        w = 400; h = 140
        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        
        # 网格背景
        p.setPen(QPen(QColor("#1a1d2e"), 0.5))
        for x in range(0, w, 20):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 20):
            p.drawLine(0, y, w, y)
        
        # 线条
        pen = QPen(QColor("#6366f1"), 2)
        p.setPen(pen)
        p.drawLine(20, h-40, 80, 60)
        p.drawLine(80, 60, 160, 90)
        p.drawLine(160, 90, 260, 40)
        p.drawLine(260, 40, 380, 80)
        
        # 数据点
        points = [(80, 60), (160, 90), (260, 40)]
        pen = QPen(QColor("#10b981"), 2)
        p.setPen(pen)
        for x, y in points:
            p.setBrush(QBrush(QColor("#10b981")))
            p.drawEllipse(QPointF(x, y), 5, 5)
        
        # 矩形
        p.setPen(QPen(QColor("#f59e0b"), 2))
        p.setBrush(QColor("#f59e0b33"))
        p.drawRect(320, 30, 60, 40)
        
        # 圆
        p.setPen(QPen(QColor("#ef4444"), 2))
        p.setBrush(QColor("#ef444433"))
        p.drawEllipse(QPointF(250, 100), 20, 20)
        
        p.end()
        
        frame = QFrame()
        frame.setStyleSheet("border: 1px solid #252840; border-radius: 8px;")
        l = QVBoxLayout(frame)
        lbl = QLabel()
        lbl.setPixmap(pix)
        lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(lbl)
        return frame

    # ═══════════════════════════════════════════════════════════════
    # 页面 4: 数据与列表
    # ═══════════════════════════════════════════════════════════════

    def _page_data(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } " + SCROLLBAR_STYLE)
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(32, 24, 32, 32)
        ly.setSpacing(20)
        
        ly.addWidget(section_label("数据与列表"))
        ly.addWidget(sub_label("ListView, TableView, DataGridView, PropertyGrid, TreeView, ComboBox, ListBox 等"))
        
        # ComboBox + ListBox 行
        data_row = QHBoxLayout()
        # ListBox
        lb_w = QWidget()
        lb_ly = QVBoxLayout(lb_w)
        lb_ly.setContentsMargins(0,0,0,0)
        lb_ly.addWidget(small_title("ListBox"))
        lb = QListWidget()
        lb.addItems(["JavaScript", "Python", "H#", "Rust", "Go", "TypeScript", "C++", "Kotlin"])
        lb.setStyleSheet(LIST_STYLE)
        lb.setMaximumHeight(180)
        lb_ly.addWidget(lb)
        data_row.addWidget(lb_w)
        
        # TreeView
        tr_w = QWidget()
        tr_ly = QVBoxLayout(tr_w)
        tr_ly.setContentsMargins(0,0,0,0)
        tr_ly.addWidget(small_title("TreeView"))
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setStyleSheet(TREE_STYLE)
        tree.setMaximumHeight(180)
        root = QTreeWidgetItem(tree, ["zzw UI"])
        for sec in ["Core", "Widgets", "Containers", "Data", "Systems"]:
            child = QTreeWidgetItem(root, [sec])
            for sub in ["A", "B", "C"]:
                QTreeWidgetItem(child, [f"{sub}-Component"])
        tree.expandAll()
        tr_ly.addWidget(tree)
        data_row.addWidget(tr_w)
        ly.addLayout(data_row)
        
        # TableView / DataGridView
        ly.addWidget(small_title("TableView / DataGridView"))
        table = QTableWidget(5, 5)
        table.setStyleSheet(TABLE_STYLE)
        headers = ["名称", "版本", "状态", "进度", "操作"]
        table.setHorizontalHeaderLabels(headers)
        data = [
            ["zzw-ui-core", "6.0", "✓ Active", "100%", "查看"],
            ["zzw-code", "2.0", "✓ Active", "85%", "查看"],
            ["zzw-docs", "1.5", "⟳ Updating", "60%", "查看"],
            ["zzw-deploy", "1.0", "✕ Error", "30%", "查看"],
            ["zzw-test", "0.8", "⏸ Paused", "45%", "查看"],
        ]
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                if c == 2:
                    item.setForeground(QColor("#10b981") if "Active" in val else QColor("#f59e0b") if "Updating" in val else QColor("#ef4444"))
                if c == 3:
                    pb = QProgressBar()
                    pb.setValue(int(val.replace("%","")))
                    pb.setStyleSheet(PROGRESS_STYLE)
                    table.setCellWidget(r, c, pb)
                else:
                    table.setItem(r, c, item)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setMaximumHeight(240)
        ly.addWidget(table)
        
        # PropertyGrid 模拟
        ly.addWidget(small_title("PropertyGrid"))
        pg = QTableWidget(6, 2)
        pg.setStyleSheet(TABLE_STYLE)
        pg.setHorizontalHeaderLabels(["属性", "值"])
        props = [
            ("theme", "dark"),
            ("font-family", "sans-serif"),
            ("font-size", "13px"),
            ("border-radius", "8px"),
            ("opacity", "1.0"),
            ("transition", "0.3s ease"),
        ]
        for r, (k, v) in enumerate(props):
            pg.setItem(r, 0, QTableWidgetItem(k))
            pg.setItem(r, 1, QTableWidgetItem(v))
        pg.horizontalHeader().setStretchLastSection(True)
        pg.verticalHeader().setVisible(False)
        pg.setMaximumHeight(240)
        ly.addWidget(pg)
        
        ly.addStretch()
        scroll.setWidget(w)
        return scroll

    # ═══════════════════════════════════════════════════════════════
    # 页面 5: 布局与容器
    # ═══════════════════════════════════════════════════════════════

    def _page_layouts(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } " + SCROLLBAR_STYLE)
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(32, 24, 32, 32)
        ly.setSpacing(20)
        
        ly.addWidget(section_label("布局与容器"))
        ly.addWidget(sub_label("Window, Panel, DockPanel, GridPanel, StackPanel, FlowPanel, TabControl, Splitter, Accordion, ScrollView 等"))
        
        # TabControl
        ly.addWidget(small_title("TabControl — 选项卡"))
        tabs = QTabWidget()
        for i, name in enumerate(["窗口", "面板", "网格", "拆分"]):
            tab_page = QWidget()
            tab_ly = QVBoxLayout(tab_page)
            tab_ly.addWidget(QLabel(f"这是 {name} 选项卡的内容区域"))
            tab_ly.addWidget(themed_btn(f"{name} 操作"))
            tabs.addTab(tab_page, name)
        ly.addWidget(tabs)
        
        # Accordion 模拟
        ly.addWidget(small_title("Accordion — 折叠面板"))
        for title, content in [("面板设置", "这里是面板设置的详细内容"), ("高级选项", "这里是高级选项的内容"), ("关于", "版本 6.0 · 2026")]:
            group = QGroupBox(title)
            group.setStyleSheet("""
                QGroupBox { color: #a0a8d0; font-weight: 600; border: 1px solid #252840; border-radius: 8px; margin-top: 12px; padding: 16px 12px 12px 12px; }
                QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            """)
            gl = QVBoxLayout(group)
            gl.addWidget(QLabel(content))
            ly.addWidget(group)
        
        # Splitter
        ly.addWidget(small_title("Splitter / SplitPane — 分割面板"))
        splitter = QSplitter(Qt.Horizontal)
        left_panel = QTextEdit()
        left_panel.setPlaceholderText("左侧面板")
        left_panel.setStyleSheet(INPUT_STYLE)
        right_panel = QTextEdit()
        right_panel.setPlaceholderText("右侧面板")
        right_panel.setStyleSheet(INPUT_STYLE)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 350])
        splitter.setMaximumHeight(200)
        ly.addWidget(splitter)
        
        # GridPanel 模拟
        ly.addWidget(small_title("GridPanel — 网格布局"))
        grid = QGridLayout()
        grid.setSpacing(8)
        for r in range(3):
            for c in range(4):
                cell = QPushButton(f"[{r},{c}]")
                cell.setFixedSize(80, 80)
                colors = ["#6366f1", "#10b981", "#f59e0b", "#ef4444"]
                cell.setStyleSheet(f"background: {colors[c]}22; border: 1px solid {colors[c]}44; border-radius: 8px; color: {colors[c]}; font-weight: 600;")
                grid.addWidget(cell, r, c)
        ly.addLayout(grid)
        
        ly.addStretch()
        scroll.setWidget(w)
        return scroll

    # ═══════════════════════════════════════════════════════════════
    # 页面 6: v6.0 新功能
    # ═══════════════════════════════════════════════════════════════

    def _page_v600(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } " + SCROLLBAR_STYLE)
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(32, 24, 32, 32)
        ly.setSpacing(20)
        
        ly.addWidget(section_label("✨ v6.0 新功能"))
        ly.addWidget(sub_label("26 个功能板块，318 个类，500 个高级 GUI 功能"))
        
        # 功能卡片网格
        features = [
            ("🎨", "25+ 主题", "sunset, neon, minimal, glass, aurora..."),
            ("🖌️", "动画系统", "Keyframe, Spring, Morph, Shake..."),
            ("📊", "图表", "Line, Bar, Pie, Scatter, Radar..."),
            ("📋", "MVVM 架构", "ViewModel, Command, DataBinding..."),
            ("🔗", "停靠系统", "DockManager, FloatingWindow..."),
            ("🎵", "媒体控件", "AudioPlayer, VideoPlayer, Waveform..."),
            ("🖨️", "打印导出", "PDF, HTML, CSV, Image Export..."),
            ("♿", "无障碍", "ScreenReader, Magnifier, FocusIndicator..."),
            ("🌐", "网络控件", "WebSocket, HTTP, NetworkStatus..."),
            ("🔍", "高级输入", "OTP, CreditCard, IPAddress, Currency..."),
            ("💾", "序列化", "Serializer, Deserializer..."),
            ("🧩", "虚拟化", "VirtualizingStackPanel, LazyLoad..."),
        ]
        
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (emoji, title, desc) in enumerate(features):
            card = QFrame()
            card.setStyleSheet("QFrame { background: #161a26; border: 1px solid #252840; border-radius: 12px; padding: 16px; } QFrame:hover { border-color: #6366f1; }")
            cl = QVBoxLayout(card)
            cl.setSpacing(6)
            
            emoji_lbl = QLabel(f"{emoji}  {title}")
            emoji_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #e0e0e0;")
            cl.addWidget(emoji_lbl)
            
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("font-size: 12px; color: #6b7394;")
            desc_lbl.setWordWrap(True)
            cl.addWidget(desc_lbl)
            
            row = i // 3
            col = i % 3
            grid.addWidget(card, row, col)
        
        ly.addLayout(grid)
        
        # 实时时钟 (模拟 Timer)
        ly.addWidget(small_title("Timer — 实时时钟"))
        clock_row = QHBoxLayout()
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("font-size: 42px; font-weight: 800; color: #6366f1; font-family: 'SF Mono', monospace;")
        self._update_clock()
        clock_row.addWidget(self.clock_label)
        clock_row.addStretch()
        ly.addLayout(clock_row)
        
        # 时钟更新定时器
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        
        # 动画演示
        ly.addWidget(small_title("Animation Demo"))
        anim_row = QHBoxLayout()
        self.anim_ball = QLabel()
        self.anim_ball.setFixedSize(40, 40)
        self.anim_ball.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #ec4899); border-radius: 20px;")
        anim_row.addWidget(self.anim_ball)
        anim_row.addStretch()
        ly.addLayout(anim_row)
        
        self.anim_timer = QTimer()
        self.anim_offset = 0
        self.anim_direction = 1
        def anim_update():
            self.anim_offset += 2 * self.anim_direction
            if self.anim_offset > 200 or self.anim_offset < 0:
                self.anim_direction *= -1
            self.anim_ball.move(32 + self.anim_offset, self.anim_ball.y() or 0)
            self.anim_ball.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #ec4899);
                border-radius: 20px;
                margin-left: {self.anim_offset}px;
            """)
        self.anim_timer.timeout.connect(anim_update)
        self.anim_timer.start(15)
        
        # 版本信息
        ly.addWidget(section_label("版本信息"))
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setStyleSheet(INPUT_STYLE + "QTextEdit { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }")
        info_text.setMaximumHeight(220)
        info_text.setText(
            "═════════════════════════════════════\n"
            "  zzw UI — H# GUI Widget Library v6.0\n"
            "═════════════════════════════════════\n"
            "  Total Classes: 318\n"
            "  Total Functions: 182\n"
            "  Total Features: 500\n"
            "  File Lines: 21,072\n"
            "\n"
            "  26 Feature Sections:\n"
            "  ├── §1-4  Advanced Input & Display\n"
            "  ├── §5    Layout System (20 classes)\n"
            "  ├── §6    Dialogs/Popups (20 classes)\n"
            "  ├── §7    Animation System (15 classes)\n"
            "  ├── §8    System Managers (15 classes)\n"
            "  ├── §9    Theme Presets (20 themes)\n"
            "  ├── §10-11 Utility Functions (40 functions)\n"
            "  ├── §12   Widget Extensions (50 methods)\n"
            "  ├── §13   MVVM Architecture (15 classes)\n"
            "  ├── §14   Visual Effects (25 classes)\n"
            "  ├── §15   Docking System (15 classes)\n"
            "  ├── §16   Charts (20 classes)\n"
            "  ├── §17   Validation (10 classes)\n"
            "  ├── §18   Virtualization (10 classes)\n"
            "  ├── §19   Specialized Input (15 classes)\n"
            "  ├── §20   Navigation (10 classes)\n"
            "  ├── §21   Media/Audio (10 classes)\n"
            "  ├── §22   Printing/Export (10 classes)\n"
            "  ├── §23   Accessibility (10 classes)\n"
            "  ├── §24   Summary\n"
            "  ├── §25   Network (6 classes)\n"
            "  └── §26   Utilities (6 functions)\n"
            "═════════════════════════════════════"
        )
        ly.addWidget(info_text)
        
        ly.addStretch()
        scroll.setWidget(w)
        return scroll

    def _update_clock(self):
        from datetime import datetime
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))

    def _show_msg(self, msg):
        self.status_label.setText(msg)

    def _show_about(self):
        QMessageBox.about(self, "关于 zzw UI",
            "<h2>zzw UI v6.0</h2>"
            "<p>H# GUI 组件库</p>"
            "<p>318 个类 · 182 个函数 · <b>500 个高级 GUI 功能</b></p>"
            "<p>26 个功能板块 · 21,072 行代码 · 25+ 主题预设</p>"
            "<hr>"
            "<p style='color: #666;'>Built with H# Language & PyQt5</p>"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("zzw UI Gallery")
    
    # 设置应用图标字体
    font = QFont("-apple-system, 'Segoe UI', 'PingFang SC', sans-serif")
    font.setPointSize(10)
    app.setFont(font)
    
    gallery = ZzwUIGallery()
    gallery.show()
    
    sys.exit(app.exec_())