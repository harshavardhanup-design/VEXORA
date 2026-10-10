"""Modern Fluent dialogs for VEXORA: Permission Gate and Command Palette."""
from __future__ import annotations
from core.qt_compat import *
from app.ui.theme import (
    BG_CARD, BG_INPUT, BORDER_SUBTLE, BORDER_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_PRIMARY, ACCENT_DANGER, ACCENT_WARNING, ACCENT_SUCCESS
)


class PermissionDialog(QDialog):
    """Modern, high-visibility permission confirmation dialog for protected computer actions."""

    def __init__(self, parent, action_name: str, explanation: str, risk_level: str = "moderate"):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Action Authorization Required")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG_CARD};
                border: 1px solid {BORDER_HOVER};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Risk Header Badge
        risk_color = ACCENT_DANGER if risk_level == "high" else (ACCENT_WARNING if risk_level == "moderate" else ACCENT_PRIMARY)
        risk_text = f"● {risk_level.upper()} RISK ACTION"

        badge = QLabel(risk_text)
        badge.setStyleSheet(f"""
            color: {risk_color};
            font-size: 11px;
            font-weight: 850;
            letter-spacing: 1px;
            padding: 4px 8px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid {risk_color};
            border-radius: 6px;
        """)
        layout.addWidget(badge)

        # Title
        title = QLabel(f"Allow {action_name}?")
        title.setStyleSheet(f"""
            font-size: 19px;
            font-weight: 850;
            color: {TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        # Explanation Box
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            background: {BG_INPUT};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 10px;
            padding: 12px;
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(6)

        desc = QLabel(explanation)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; line-height: 1.4;")
        info_layout.addWidget(desc)

        safety_note = QLabel("✓ Audited in %APPDATA%\\VEXORA\\action_audit.jsonl")
        safety_note.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        info_layout.addWidget(safety_note)

        layout.addWidget(info_frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Deny & Block")
        self.btn_cancel.setStyleSheet(f"""
            background: #202330;
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 8px;
            padding: 9px 16px;
            color: {TEXT_PRIMARY};
            font-weight: 700;
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_allow = QPushButton("Approve & Execute")
        self.btn_allow.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F2FE, stop:1 #4FACFE);
            border: 0;
            border-radius: 8px;
            padding: 9px 20px;
            color: #060709;
            font-weight: 850;
        """)
        self.btn_allow.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_allow)
        layout.addLayout(btn_layout)


class CommandPaletteDialog(QDialog):
    """Floating Spotlight Command Bar for quick actions and questions (Ctrl+K / Alt+Space)."""

    def __init__(self, parent, on_execute_callback):
        super().__init__(parent)
        self.on_execute = on_execute_callback
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(580)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG_CARD};
                border: 1px solid {BORDER_HOVER};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Input row
        in_row = QHBoxLayout()
        in_row.setSpacing(10)
        icon = QLabel("✦")
        icon.setStyleSheet(f"color: {ACCENT_PRIMARY}; font-size: 18px; font-weight: 900;")
        in_row.addWidget(icon)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Search actions, ask VEXORA, or type a command…")
        self.input_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_INPUT};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                color: {TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT_PRIMARY};
            }}
        """)
        self.input_edit.returnPressed.connect(self._run_current)
        self.input_edit.textChanged.connect(self._filter_items)
        in_row.addWidget(self.input_edit, 1)
        layout.addLayout(in_row)

        # Suggested actions list
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(260)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: 0;
                color: {TEXT_PRIMARY};
                outline: none;
            }}
            QListWidget::item {{
                padding: 9px 12px;
                border-radius: 8px;
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background: rgba(255, 255, 255, 0.04);
            }}
            QListWidget::item:selected {{
                background: rgba(255, 26, 64, 0.16);
                border: 1px solid rgba(255, 26, 64, 0.35);
                color: #FFFFFF;
                font-weight: 750;
            }}
        """)

        self.all_items = [
            ("⚡ Benchmark Qualcomm Hexagon NPU", "benchmark npu"),
            ("🔋 Check PC Health & Battery", "How is my PC?"),
            ("🌱 Enterprise ESG & Carbon Report", "esg report"),
            ("📷 Capture Screen & Analyze", "__capture_screen__"),
            ("🧮 Open Calculator", "open calculator"),
            ("📝 Open Notepad", "launch notepad"),
            ("📁 Open Downloads Folder", "Open Downloads"),
            ("⚙️ Open Windows Settings", "open windows settings"),
            ("🔍 Show Running Apps", "Show running apps"),
            ("📋 Show Recent Files", "Show recent files"),
            ("📊 Inspect System Specifications", "Show system specifications"),
            ("💼 Workday Workspace Setup", "Prepare my workspace")
        ]
        self.current_filtered = list(self.all_items)
        self._populate_list(self.all_items)

        self.list_widget.itemDoubleClicked.connect(self._on_item_chosen)
        layout.addWidget(self.list_widget)

        hint = QLabel("Esc to close • Enter to execute • ↑↓ to navigate")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(hint)

    def showEvent(self, e):
        super().showEvent(e)
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + max(0, (parent_geo.width() - self.width()) // 2)
            y = parent_geo.y() + max(40, (parent_geo.height() - self.height()) // 3)
            self.move(x, y)
        self.input_edit.setFocus()

    def _populate_list(self, items):
        self.list_widget.clear()
        self.current_filtered = items
        for label, _ in items:
            self.list_widget.addItem(label)
        if items:
            self.list_widget.setCurrentRow(0)

    def _filter_items(self, text):
        q = (text or '').strip().lower()
        if not q:
            self._populate_list(self.all_items)
            return
        matches = [(lbl, cmd) for (lbl, cmd) in self.all_items if q in lbl.lower() or q in cmd.lower()]
        if not matches:
            matches = [(f"✦ Ask VEXORA: \"{text.strip()}\"", text.strip())]
        self._populate_list(matches)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Down:
            curr = self.list_widget.currentRow()
            if curr < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(curr + 1)
            return
        elif e.key() == Qt.Key.Key_Up:
            curr = self.list_widget.currentRow()
            if curr > 0:
                self.list_widget.setCurrentRow(curr - 1)
            return
        elif e.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(e)

    def _run_current(self):
        text = self.input_edit.text().strip()
        row = self.list_widget.currentRow()
        if row >= 0 and row < len(self.current_filtered):
            target_cmd = self.current_filtered[row][1]
            if text and not any(text.lower() in lbl.lower() for lbl, _ in self.all_items):
                target_cmd = text
            self.accept()
            self.on_execute(target_cmd)
        elif text:
            self.accept()
            self.on_execute(text)

    def _on_item_chosen(self, item):
        row = self.list_widget.row(item)
        if 0 <= row < len(self.current_filtered):
            self.accept()
            self.on_execute(self.current_filtered[row][1])
