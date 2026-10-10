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
