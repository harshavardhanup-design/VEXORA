"""VEXORA Modern Fluent Design Theme System.

Provides high-DPI aware Windows 11 styling, colors, typography, and QSS stylesheets.
"""
from __future__ import annotations

# Color Palette Tokens
BG_MAIN = "#0A0B0E"
BG_SIDEBAR = "#0E1017"
BG_CARD = "#141722"
BG_CARD_HOVER = "#1B1F2E"
BG_INPUT = "#12141D"
BORDER_SUBTLE = "#1F2333"
BORDER_HOVER = "#2F364D"
BORDER_FOCUS = "#00D2FF"

# Accent Colors
ACCENT_PRIMARY = "#00F2FE"       # Electric Cyan
ACCENT_SECONDARY = "#4FACFE"     # Bright Blue
ACCENT_NEON = "#00F5A0"          # Neon Mint
ACCENT_LIME = "#B7FF3C"          # Vexora Signature Lime (preserved for compatibility)
ACCENT_WARNING = "#FFB300"       # Amber
ACCENT_DANGER = "#FF4565"        # Coral Red
ACCENT_SUCCESS = "#00E676"       # Emerald Green

# Typography Colors
TEXT_PRIMARY = "#F3F5F9"
TEXT_SECONDARY = "#A0A6B8"
TEXT_MUTED = "#646B82"
TEXT_DISABLED = "#43485A"


def get_stylesheet(assistant_name: str = "VEXORA") -> str:
    """Return complete, polished Windows 11 Fluent dark stylesheet."""
    return f"""
    * {{
        font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, system-ui, sans-serif;
        outline: none;
    }}

    QMainWindow, QWidget {{
        background: {BG_MAIN};
        color: {TEXT_PRIMARY};
    }}

    /* Sidebar Navigation */
    #Sidebar {{
        background: {BG_SIDEBAR};
        border-right: 1px solid {BORDER_SUBTLE};
    }}

    #Brand {{
        font-size: 26px;
        font-weight: 900;
        letter-spacing: 2.5px;
        color: {TEXT_PRIMARY};
        padding: 4px 0px;
    }}

    #Tagline {{
        color: {ACCENT_PRIMARY};
        font-size: 9px;
        font-weight: 800;
        letter-spacing: 2px;
    }}

    #Nav, #NavActive {{
        border: 0;
        text-align: left;
        padding: 11px 14px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        color: {TEXT_SECONDARY};
        background: transparent;
    }}

    #Nav:hover {{
        background: {BG_CARD};
        color: {TEXT_PRIMARY};
    }}

    #NavActive {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F2FE, stop:1 #4FACFE);
        color: #060709;
        font-weight: 850;
    }}

    #Local {{
        color: {ACCENT_NEON};
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1.2px;
        padding: 6px 10px;
        background: rgba(0, 245, 160, 0.08);
        border: 1px solid rgba(0, 245, 160, 0.2);
        border-radius: 8px;
    }}

    /* Headers & Typography */
    #Hero {{
        font-size: 28px;
        font-weight: 850;
        letter-spacing: -0.5px;
        color: {TEXT_PRIMARY};
    }}

    #Muted, #CardSub, #Footer, #Hint, #SettingsRowDescription {{
        color: {TEXT_MUTED};
        font-size: 12px;
        line-height: 1.4;
    }}

    #Section {{
        font-size: 16px;
        font-weight: 800;
        letter-spacing: -0.2px;
    }}

    #SectionSmall, #SettingsSectionTitle {{
        font-size: 13px;
        font-weight: 850;
        letter-spacing: 0.8px;
        color: {TEXT_PRIMARY};
    }}

    #SettingsRowTitle {{
        font-size: 13px;
        font-weight: 750;
        color: {TEXT_PRIMARY};
    }}

    /* Card Panels */
    #MetricCard, #ChatPanel, #QuickPanel, #BatteryPanel, #FeatureCard, #SuggestionCard, 
    #SpecCard, #SpecHero, #SettingsCard, #AgentVisualPanel, #WorkspaceStrip {{
        background: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 14px;
    }}

    #MetricCard:hover, #FeatureCard:hover, #SuggestionCard:hover, #SpecCard:hover, #SettingsCard:hover {{
        border: 1px solid {BORDER_HOVER};
        background: {BG_CARD_HOVER};
    }}

    #CardTitle {{
        color: {TEXT_MUTED};
        font-size: 10px;
        font-weight: 850;
        letter-spacing: 1.2px;
    }}

    #CardValue {{
        font-size: 26px;
        font-weight: 900;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.5px;
    }}

    /* Settings Page Specific Tokens */
    #SettingsScroll {{
        background: transparent;
        border: 0;
    }}

    #SettingsHost {{
        background: transparent;
    }}

    #SettingsRow {{
        background: {BG_INPUT};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 11px;
    }}

    #SettingsRow:hover {{
        border: 1px solid {BORDER_HOVER};
    }}

    #SettingsStatus {{
        background: {BG_INPUT};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 10px;
        padding: 8px 12px;
    }}

    #SettingsStatusText {{
        color: {ACCENT_PRIMARY};
        font-size: 12px;
        font-weight: 700;
    }}

    /* Inputs, ComboBoxes, and Controls */
    QLineEdit, QComboBox, QPlainTextEdit {{
        background: {BG_INPUT};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 9px;
        color: {TEXT_PRIMARY};
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {ACCENT_PRIMARY};
        selection-color: #000;
    }}

    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{
        border: 1px solid {ACCENT_PRIMARY};
        background: #151824;
    }}

    QComboBox::drop-down {{
        border: 0;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        color: {TEXT_PRIMARY};
        selection-background-color: {ACCENT_PRIMARY};
        selection-color: #060709;
        padding: 4px;
    }}

    /* Action Buttons */
    #Action, QPushButton {{
        background: #171A26;
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 9px;
        padding: 8px 14px;
        color: {TEXT_PRIMARY};
        font-size: 12px;
        font-weight: 700;
        text-align: center;
    }}

    #Action:hover, QPushButton:hover {{
        background: #202436;
        border: 1px solid {BORDER_HOVER};
        color: #FFF;
    }}

    #Action:pressed, QPushButton:pressed {{
        background: {ACCENT_PRIMARY};
        color: #060709;
        font-weight: 850;
    }}

    #Action[pulse="true"] {{
        border: 1px solid {ACCENT_NEON};
        background: rgba(0, 245, 160, 0.15);
    }}

    #SuggestionButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F2FE, stop:1 #4FACFE);
        border: 0;
        border-radius: 9px;
        color: #060709;
        font-size: 12px;
        font-weight: 850;
        padding: 8px 16px;
    }}

    #SuggestionButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4FACFE, stop:1 #00F2FE);
    }}

    /* Chat Messages & Avatars */
    #UserMessage {{
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 6px 12px;
    }}

    #AIMessage {{
        background: rgba(0, 242, 254, 0.02);
        border: 1px solid rgba(0, 242, 254, 0.08);
        border-radius: 12px;
        padding: 6px 12px;
    }}

    #AvatarUser, #AvatarAI {{
        min-width: 26px;
        max-width: 26px;
        min-height: 26px;
        max-height: 26px;
        border-radius: 13px;
        text-align: center;
        font-size: 9px;
        font-weight: 900;
    }}

    #AvatarUser {{
        background: {ACCENT_PRIMARY};
        color: #060709;
    }}

    #AvatarAI {{
        background: #181B28;
        border: 1px solid {ACCENT_PRIMARY};
        color: {ACCENT_PRIMARY};
    }}

    #MessageName {{
        font-size: 12px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
    }}

    #MessageBody {{
        font-size: 13px;
        line-height: 1.55;
        color: #E2E6F0;
    }}

    #MsgAction {{
        background: transparent;
        border: 0;
        color: {TEXT_MUTED};
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 700;
    }}

    #MsgAction:hover {{
        color: {ACCENT_PRIMARY};
    }}

    #TypingDots {{
        color: {ACCENT_PRIMARY};
        font-size: 14px;
        font-weight: 900;
    }}

    /* Composer */
    #Composer {{
        background: {BG_INPUT};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 14px;
    }}

    #Composer:focus-within {{
        border: 1px solid {ACCENT_PRIMARY};
    }}

    #Composer QPlainTextEdit {{
        background: transparent;
        border: 0;
        color: {TEXT_PRIMARY};
        font-size: 13px;
        padding: 4px 8px;
    }}

    #Send {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F2FE, stop:1 #4FACFE);
        border: 0;
        border-radius: 10px;
        min-width: 36px;
        min-height: 36px;
        font-weight: 900;
        font-size: 16px;
        color: #060709;
    }}

    #Send:hover {{
        background: {ACCENT_NEON};
    }}

    #Stop {{
        background: #252838;
        border: 1px solid {BORDER_HOVER};
        border-radius: 10px;
        min-width: 36px;
        min-height: 36px;
        font-size: 11px;
        font-weight: 800;
        color: {ACCENT_DANGER};
    }}

    #Stop:hover {{
        background: {ACCENT_DANGER};
        color: #FFF;
    }}

    #ComposerModel {{
        background: #171A26;
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        color: {ACCENT_PRIMARY};
        font-size: 11px;
        font-weight: 750;
        padding: 6px 12px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: #25293B;
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: #363B54;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        height: 0;
    }}

    /* Status Bar */
    QStatusBar {{
        background: {BG_SIDEBAR};
        color: {TEXT_MUTED};
        border-top: 1px solid {BORDER_SUBTLE};
        font-size: 11px;
        padding: 3px 12px;
    }}

    QStatusBar::item {{
        border: 0;
    }}

    /* Progress Bars */
    QProgressBar {{
        background: #171926;
        border: 0;
        border-radius: 4px;
        text-align: center;
        color: {TEXT_MUTED};
        font-size: 9px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F2FE, stop:1 #4FACFE);
        border-radius: 4px;
    }}
    """
