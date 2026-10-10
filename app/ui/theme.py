"""VEXORA Snapdragon® AI Lab & HP Copilot+ Edition Theme System.

Executive dark glassmorphic design featuring Snapdragon Crimson (#FF1A40),
Qualcomm Electric Cyan (#00D2FF), and HP Titanium Slate typography.
"""
from __future__ import annotations

# Color Palette Tokens
BG_MAIN = "#08090C"
BG_SIDEBAR = "#0C0E14"
BG_CARD = "#11141E"
BG_CARD_HOVER = "#181C2A"
BG_INPUT = "#0F121A"
BORDER_SUBTLE = "#1C2130"
BORDER_HOVER = "#2A3249"
BORDER_FOCUS = "#00D2FF"

# Snapdragon & Qualcomm Accents
ACCENT_PRIMARY = "#FF1A40"        # Primary Brand Accent (Snapdragon Crimson)
ACCENT_SNAPDRAGON = "#FF1A40"     # Snapdragon Fire Crimson
ACCENT_QUALCOMM = "#00D2FF"       # Qualcomm Electric Cyan
ACCENT_NEON = "#00F5A0"           # Hexagon NPU Green
ACCENT_SUCCESS = "#00F5A0"        # Success Green
ACCENT_LIME = "#B7FF3C"           # Legacy Lime compatibility
ACCENT_WARNING = "#FFB300"        # Amber
ACCENT_DANGER = "#FF2E50"         # Coral Red
ACCENT_HP_SLATE = "#E2E8F0"       # HP Titanium

# Typography Colors
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED = "#64748B"
TEXT_DISABLED = "#334155"


def get_stylesheet(assistant_name: str = "VEXORA") -> str:
    """Return complete Snapdragon® AI Lab Copilot+ stylesheet."""
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
        letter-spacing: 2px;
        color: {TEXT_PRIMARY};
        padding: 4px 0px;
    }}

    #Tagline {{
        color: {ACCENT_SNAPDRAGON};
        font-size: 9px;
        font-weight: 900;
        letter-spacing: 1.8px;
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
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF1A40, stop:1 #FF4D6D);
        color: #FFFFFF;
        font-weight: 850;
    }}

    #Local {{
        color: {ACCENT_QUALCOMM};
        font-size: 10px;
        font-weight: 850;
        letter-spacing: 1.2px;
        padding: 6px 10px;
        background: rgba(0, 210, 255, 0.08);
        border: 1px solid rgba(0, 210, 255, 0.25);
        border-radius: 8px;
    }}

    /* Headers & Typography */
    #Hero {{
        font-size: 27px;
        font-weight: 850;
        letter-spacing: -0.4px;
        color: {TEXT_PRIMARY};
    }}

    #Muted, #CardSub, #Footer, #Hint, #SettingsRowDescription {{
        color: {TEXT_MUTED};
        font-size: 12px;
        line-height: 1.4;
    }}

    #Section {{
        font-size: 16px;
        font-weight: 850;
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
        color: {ACCENT_QUALCOMM};
        font-size: 12px;
        font-weight: 700;
    }}

    /* Inputs & Combos */
    QLineEdit, QComboBox, QPlainTextEdit {{
        background: {BG_INPUT};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 9px;
        color: {TEXT_PRIMARY};
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {ACCENT_SNAPDRAGON};
        selection-color: #FFF;
    }}

    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{
        border: 1px solid {ACCENT_QUALCOMM};
        background: #131722;
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
        selection-background-color: {ACCENT_SNAPDRAGON};
        selection-color: #FFF;
        padding: 4px;
    }}

    /* Action Buttons */
    #Action, QPushButton {{
        background: #151924;
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 9px;
        padding: 8px 14px;
        color: {TEXT_PRIMARY};
        font-size: 12px;
        font-weight: 700;
        text-align: center;
    }}

    #Action:hover, QPushButton:hover {{
        background: #1E2333;
        border: 1px solid {BORDER_HOVER};
        color: #FFF;
    }}

    #Action:pressed, QPushButton:pressed {{
        background: {ACCENT_SNAPDRAGON};
        color: #FFF;
        font-weight: 850;
    }}

    #Action[pulse="true"] {{
        border: 1px solid {ACCENT_QUALCOMM};
        background: rgba(0, 210, 255, 0.15);
    }}

    #SuggestionButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF1A40, stop:1 #FF4D6D);
        border: 0;
        border-radius: 9px;
        color: #FFFFFF;
        font-size: 12px;
        font-weight: 850;
        padding: 8px 16px;
    }}

    #SuggestionButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF4D6D, stop:1 #FF1A40);
    }}

    /* Chat Messages & Avatars */
    #UserMessage {{
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 6px 12px;
    }}

    #AIMessage {{
        background: rgba(0, 210, 255, 0.02);
        border: 1px solid rgba(0, 210, 255, 0.1);
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
        background: {ACCENT_QUALCOMM};
        color: #060709;
    }}

    #AvatarAI {{
        background: #1A1F2C;
        border: 1px solid {ACCENT_SNAPDRAGON};
        color: {ACCENT_SNAPDRAGON};
    }}

    #MessageName {{
        font-size: 12px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
    }}

    #MessageBody {{
        font-size: 13px;
        line-height: 1.55;
        color: #E2E8F0;
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
        color: {ACCENT_QUALCOMM};
    }}

    #TypingDots {{
        color: {ACCENT_SNAPDRAGON};
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
        border: 1px solid {ACCENT_QUALCOMM};
    }}

    #Composer QPlainTextEdit {{
        background: transparent;
        border: 0;
        color: {TEXT_PRIMARY};
        font-size: 13px;
        padding: 4px 8px;
    }}

    #Send {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF1A40, stop:1 #FF4D6D);
        border: 0;
        border-radius: 10px;
        min-width: 36px;
        min-height: 36px;
        font-weight: 900;
        font-size: 16px;
        color: #FFFFFF;
    }}

    #Send:hover {{
        background: {ACCENT_QUALCOMM};
        color: #000;
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

    #ComposerModel {{
        background: #151924;
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        color: {ACCENT_QUALCOMM};
        font-size: 11px;
        font-weight: 750;
        padding: 6px 12px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}

    QScrollBar::handle:vertical {{
        background: #202636;
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: #2F374E;
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

    /* Progress Bars */
    QProgressBar {{
        background: #151926;
        border: 0;
        border-radius: 4px;
        text-align: center;
        color: {TEXT_MUTED};
        font-size: 9px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF1A40, stop:1 #00D2FF);
        border-radius: 4px;
    }}
    """
