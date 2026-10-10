"""Modern custom widgets for VEXORA: Metric cards, Message cards with code blocks, and Battery meters."""
from __future__ import annotations
import html
import re
from core.qt_compat import *
from app.ui.theme import (
    BG_CARD, BG_INPUT, BORDER_SUBTLE, BORDER_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_PRIMARY, ACCENT_NEON, ACCENT_DANGER, ACCENT_WARNING, ACCENT_SUCCESS
)


class ModernMetricCard(QFrame):
    """Sleek metric card featuring value, title, and mini progress bar."""

    def __init__(self, title: str, subtitle: str = "", value: str = "--", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setMinimumWidth(140)
        self.setMinimumHeight(105)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setObjectName("CardTitle")
        layout.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("CardValue")
        layout.addWidget(self.lbl_value)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #1A1D2B;
                border: 0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F2FE, stop:1 #4FACFE);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("CardSub")
        layout.addWidget(self.lbl_sub)

    def set_data(self, value: str, sub: str = None, percent: float = None):
        self.lbl_value.setText(value)
        if sub is not None:
            self.lbl_sub.setText(sub)
        if percent is not None:
            self.progress_bar.setValue(max(0, min(100, int(percent))))


class ModernBatteryIcon(QWidget):
    """Animated canvas battery icon."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0
        self.charging = False
        self.phase = 0
        self.setFixedSize(40, 26)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(350)

    def set_state(self, level, charging):
        self.level = 0 if level is None else level
        self.charging = charging
        self.update()

    def _tick(self):
        if self.charging:
            self.phase = (self.phase + 1) % 20
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#43485A'), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(2, 4, 32, 18, 4, 4)
        p.drawRoundedRect(34, 9, 3, 8, 1, 1)

        fill_width = max(2, int(28 * (self.level / 100)))
        fill_color = QColor(ACCENT_DANGER) if self.level <= 20 else QColor(ACCENT_NEON)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill_color)
        p.drawRoundedRect(4, 6, fill_width, 14, 2, 2)

        if self.charging:
            p.setBrush(QColor(0, 245, 160, 90 + int(80 * (self.phase / 19))))
            p.drawEllipse(6, 7, 20, 12)


class ModernBatteryWidget(QFrame):
    """Status bar / header battery monitor widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BatteryPanel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        self.icon = ModernBatteryIcon()
        layout.addWidget(self.icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.title_label = QLabel("Battery")
        self.title_label.setObjectName("BatteryState")
        self.desc_label = QLabel("Reading telemetry…")
        self.desc_label.setObjectName("BatteryDetail")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        layout.addLayout(text_layout)

    def set_state(self, level, charging):
        self.icon.set_state(level, charging)
        if level is None:
            self.title_label.setText("Battery N/A")
            self.desc_label.setText("AC / Desktop power")
        elif charging:
            self.title_label.setText(f"Charging • {level:.0f}%")
            self.desc_label.setText("Connected to power")
        else:
            self.title_label.setText(f"Battery • {level:.0f}%")
            self.desc_label.setText("Running on battery")


class ModernMessageWidget(QFrame):
    """Formatted chat message supporting copy, regenerate, and code block styling."""

    def __init__(self, role: str, text: str, copy_cb, regen_cb, assistant_name: str = "VEXORA", page_key=None, parent=None):
        super().__init__(parent)
        self.page_key = page_key
        self.raw_text = text
        self.setObjectName("UserMessage" if role == "user" else "AIMessage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(8)

        avatar = QLabel("YOU" if role == "user" else assistant_name[:1])
        avatar.setObjectName("AvatarUser" if role == "user" else "AvatarAI")
        header.addWidget(avatar)

        name_lbl = QLabel("You" if role == "user" else assistant_name)
        name_lbl.setObjectName("MessageName")
        header.addWidget(name_lbl)
        header.addStretch()

        if role == "ai":
            badge = QLabel("ASSISTANT")
            badge.setStyleSheet(f"color: {ACCENT_PRIMARY}; font-size: 9px; font-weight: 800; letter-spacing: 1px;")
            header.addWidget(badge)

        layout.addLayout(header)

        # Body
        self.body = QLabel(text)
        self.body.setObjectName("MessageBody")
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._format_body(text)
        layout.addWidget(self.body)

        # Actions Row
        if role == "ai":
            actions = QHBoxLayout()
            actions.setSpacing(6)

            btn_copy = QPushButton("Copy Text")
            btn_copy.setObjectName("MsgAction")
            btn_copy.clicked.connect(lambda: copy_cb(self))
            actions.addWidget(btn_copy)

            btn_regen = QPushButton("Regenerate")
            btn_regen.setObjectName("MsgAction")
            btn_regen.clicked.connect(lambda: regen_cb(self))
            actions.addWidget(btn_regen)

            actions.addStretch()
            layout.addLayout(actions)

    def set_text(self, text: str):
        self.raw_text = text
        self._format_body(text)

    def _format_body(self, text: str):
        # Clean formatted representation
        if "```" in text:
            # Basic HTML code block formatting for Qt RichText
            escaped = html.escape(text)
            formatted = re.sub(
                r'```([a-zA-Z0-9_-]*)\n(.*?)```',
                r'<pre style="background:#0D0F16; border:1px solid #1F2333; border-radius:8px; padding:10px; font-family:Consolas, monospace; color:#00F2FE;">\2</pre>',
                escaped,
                flags=re.DOTALL
            )
            formatted = formatted.replace('\n', '<br>')
            self.body.setTextFormat(Qt.TextFormat.RichText)
            self.body.setText(formatted)
        else:
            self.body.setTextFormat(Qt.TextFormat.PlainText)
            self.body.setText(text)
