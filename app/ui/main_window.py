import os
import subprocess
import platform
import time
from datetime import datetime
import re
from core.qt_compat import (
    Qt, QTimer, Signal, QObject, QRunnable, QThreadPool, QColor, QPainter, QPen,
    QKeyEvent, QShortcut, QAction, QKeySequence, QApplication
)
from core.qt_compat import *
from core.platform_compat import compatibility_report, capabilities
from core.windows11 import detect_profile, preferred_refresh_ms, ui_scale_hint
from monitoring.pc_health import PcHealth
from agent.command_router import handle_result, approve, cancel, get_agent
from tools.vision import capture_screen, vision_status
from tools.settings_tool import open_windows_settings, settings_status, open_windows_settings_page
from tools.system_actions import open_safe_app, open_workspace_folder
from tools.everyday import recent_files, workday_summary
from tools.see_engine import screenshot as see_screenshot, inspect_screen, ocr_image
from tools.workflow import build_workflow
from agent.planner import plan as build_agent_plan
from tools.visuals import agent_stage_data, workload_profile
from tools.ui_understanding import observe_image
from agent.model_router import choose as choose_model_route
from agent.audit import record as audit_record
from tools.action_engine import execute as execute_action
from ai.chatbot import local_chat
from ai.model import LocalModel, DEFAULT_MODELS
from ai.providers import GEMINI_FREE_MODELS, OPENAI_MODELS, remote_chat
from memory.store import load as load_store, save as save_store, remember as remember_store

from app.ui.theme import (
    get_stylesheet, BG_CARD, BG_INPUT, BORDER_SUBTLE, BORDER_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_PRIMARY, ACCENT_NEON, ACCENT_DANGER, ACCENT_WARNING, ACCENT_SUCCESS
)
from app.ui.dialogs import PermissionDialog, CommandPaletteDialog
from app.ui.widgets import ModernMetricCard, ModernBatteryWidget, ModernMessageWidget


class ChatSignals(QObject):
    finished = Signal(int, str, str, str)


class ChatWorker(QRunnable):
    def __init__(self, request_id, key, text, history, context):
        super().__init__()
        self.request_id = request_id
        self.key = key
        self.text = text
        self.history = history
        self.context = context
        self.signals = ChatSignals()

    def run(self):
        try:
            reply = local_chat(self.text, self.history, self.context)
            self.signals.finished.emit(self.request_id, self.key, self.text, reply)
        except Exception as e:
            self.signals.finished.emit(
                self.request_id, self.key, self.text,
                f"I hit a local processing error while answering that. Please try again. ({type(e).__name__})"
            )


class ModelTestSignals(QObject):
    result = Signal(bool, str)


class ModelTestWorker(QRunnable):
    """Non-blocking background worker to test model connections without freezing the UI."""

    def __init__(self, provider, model, context, host=None):
        super().__init__()
        self.provider = provider
        self.model = model
        self.context = context
        self.host = host
        self.signals = ModelTestSignals()

    def run(self):
        try:
            t0 = time.monotonic()
            if self.provider in ('gemini', 'openai'):
                ans, err = remote_chat(self.provider, 'Reply with exactly: MODEL_TEST_OK', [], self.context)
                elapsed = time.monotonic() - t0
                if ans:
                    self.signals.result.emit(True, f"✓ {self.provider.title()} ({self.model}) responded in {elapsed:.1f}s.")
                else:
                    self.signals.result.emit(False, f"✕ {err or 'Remote model request failed.'}")
            elif self.provider == 'ollama':
                lm = LocalModel('ollama', self.model, self.host or None)
                res = lm.test_connection()
                elapsed = time.monotonic() - t0
                if res.get('ok'):
                    self.signals.result.emit(True, f"✓ Ollama ({self.model}) verified in {elapsed:.1f}s.")
                else:
                    self.signals.result.emit(False, f"✕ {res.get('message', 'Ollama connection failed.')}")
            else:
                self.signals.result.emit(True, "✓ Offline deterministic fallback engine is online.")
        except Exception as e:
            self.signals.result.emit(False, f"✕ Test error: {type(e).__name__}: {e}")


# Preserved for API compatibility with existing references
class BatteryIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.level = 0
        self.charging = False
        self.setFixedSize(40, 26)

    def set_state(self, level, charging):
        self.level = 0 if level is None else level
        self.charging = charging
        self.update()


class BatteryWidget(ModernBatteryWidget):
    """Modern battery widget maintaining legacy class compatibility."""
    pass


class Composer(QPlainTextEdit):
    submit = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedHeight(54)
        self.setPlaceholderText('Ask your assistant about your PC, tasks, files, screen, or workflows…')

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Return and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submit.emit()
            return
        super().keyPressEvent(e)


class Message(ModernMessageWidget):
    """Modern message card preserving legacy class name."""
    pass


class Typing(QFrame):
    def __init__(self, name='VEXORA'):
        super().__init__()
        l = QHBoxLayout(self)
        l.setContentsMargins(10, 4, 10, 4)
        a = QLabel(name[:1])
        a.setObjectName('AvatarAI')
        l.addWidget(a)
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-weight: 750; color: #00F2FE;")
        l.addWidget(self.name_label)
        self.d = QLabel('•')
        self.d.setObjectName('TypingDots')
        l.addWidget(self.d)
        l.addStretch()
        self.n = 0
        self.t = QTimer(self)
        self.t.timeout.connect(self.tick)
        self.t.start(240)

    def tick(self):
        self.n = (self.n + 1) % 4
        self.d.setText('  '.join(['•'] * (self.n + 1)))


class MainWindow(QMainWindow):
    NAV = [
        ('⌂  Overview', 'Overview'),
        ('✦  Ask VEXORA', 'Ask VEXORA'),
        ('▣  My Work', 'My Work'),
        ('◌  Productivity', 'Productivity'),
        ('▤  System Specifications', 'System Specifications'),
        ('⚙  Settings', 'Settings')
    ]

    def __init__(self):
        super().__init__()
        self.resize(1440, 900)
        self.setMinimumSize(1040, 680)
        self.health = PcHealth()
        self.agent = get_agent()
        self.pages = {}
        self.sessions = {}
        self.queue = []
        self.current_query = ''
        stored = load_store()
        self.settings = {
            'assistant_name': 'VEXORA',
            'model_provider': 'offline',
            'model_name': 'llama3.2',
            'ollama_host': 'http://127.0.0.1:11434',
            'animations': True,
            'fast_replies': True,
            'local_only': True,
            'auto_scroll': True,
            'focus_mode': False,
            'online_knowledge': True,
            'use_local_model': True,
            'everyday_mode': True,
            'require_action_confirmation': True,
            'ocr_enabled': False,
            'screen_context': True,
            'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'feedback_enabled': True,
            'reduce_motion': False,
            'start_page': 'Overview'
        }
        self.settings.update(stored.get('settings') or {})

        loaded_name = str(self.settings.get('assistant_name', 'VEXORA') or 'VEXORA').strip()
        self.settings['assistant_name'] = loaded_name if re.fullmatch(r'[A-Za-z]{1,6}', loaded_name) else 'VEXORA'

        self.tasks = stored.get('tasks') or []
        self.memory = stored.get('memory') or []
        self.typing = QTimer(self)
        self.typing.timeout.connect(self.type_next)
        self.thread_pool = QThreadPool.globalInstance()
        self.request_id = 0
        self.last_request = {}
        self._health_cache = None
        self._health_cache_ms = 0
        self._spec_cache = None
        self._spec_cache_ms = 0
        self._last_refresh_ms = 0
        self._transition_timer = QTimer(self)
        self._transition_timer.setSingleShot(True)
        self._transition_timer.timeout.connect(lambda: None)
        self.assistant_name = self.settings.get('assistant_name', 'VEXORA') or 'VEXORA'
        self.setWindowTitle(f'{self.assistant_name} v5.8 Professional — Your AI for the entire computer')

        self.build()
        self.statusBar().showMessage('● SYSTEM ONLINE  •  v5.8 Professional  •  Windows 11 Native  •  Protected Actions Enabled')
        self.install_shortcuts()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(preferred_refresh_ms())
        self.refresh()

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Sidebar Navigation
        side = QFrame()
        side.setObjectName('Sidebar')
        side.setFixedWidth(240)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(20, 24, 16, 20)
        sl.setSpacing(10)

        self.brand_label = QLabel(self.assistant_name)
        brand = self.brand_label
        brand.setObjectName('Brand')
        tag = QLabel('SEE • THINK • ACT')
        tag.setObjectName('Tagline')
        sl.addWidget(brand)
        sl.addWidget(tag)
        sl.addSpacing(18)

        self.nav = []
        for i, (label, key) in enumerate(self.NAV):
            b = QPushButton(label)
            b.setObjectName('NavActive' if i == 0 else 'Nav')
            b.clicked.connect(lambda _, k=key: self.navigate(k))
            self.nav.append(b)
            sl.addWidget(b)

        sl.addStretch()

        # Spotlight Hint
        spot_btn = QPushButton("✦ Quick Command (Ctrl+K)")
        spot_btn.setStyleSheet("""
            background: rgba(0, 242, 254, 0.08);
            border: 1px solid rgba(0, 242, 254, 0.2);
            border-radius: 9px;
            color: #00F2FE;
            font-size: 11px;
            font-weight: 800;
            padding: 8px 12px;
        """)
        spot_btn.clicked.connect(self.open_command_palette)
        sl.addWidget(spot_btn)

        vs = vision_status()
        v = QLabel('●  VISION READY' if vs['screenshot'] else '●  VISION LIMITED')
        v.setObjectName('Local')
        sl.addWidget(v)

        main.addWidget(side)

        # Pages Stack
        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)

        for _, key in self.NAV:
            self.pages[key] = self.make_page(key)
            self.stack.addWidget(self.pages[key])

        start_pref = self.settings.get('start_page', 'Overview')
        self.navigate(start_pref if start_pref in dict(self.NAV).values() else 'Overview')
        self.style_ui()

    def header(self, p, title, sub):
        h = QHBoxLayout()
        v = QVBoxLayout()
        a = QLabel(title.replace('VEXORA', self.assistant_name))
        a.setObjectName('Hero')
        b = QLabel(sub)
        b.setObjectName('Muted')
        v.addWidget(a)
        v.addWidget(b)
        h.addLayout(v)
        h.addStretch()
        bat = ModernBatteryWidget()
        h.addWidget(bat)
        p.battery = bat
        return h

    def make_page(self, key):
        p = QWidget()
        l = QVBoxLayout(p)
        l.setContentsMargins(32, 24, 32, 18)
        l.setSpacing(14)

        titles = {
            'Overview': ('Good day.', 'Your high-performance Windows command center.'),
            'Ask VEXORA': (f'Ask {self.assistant_name}.', 'Reasoning, computer actions, screen perception and planning.'),
            'My Work': ('My Work & Workspace.', 'Continuity, project tasks, and recent computer activity.'),
            'Productivity': ('Productivity & Focus.', 'Real-time telemetry, memory load, and system optimization.'),
            'System Specifications': ('System Specifications.', 'Comprehensive hardware, platform, OS and runtime specs.'),
            'Settings': ('Settings & Preferences.', 'Control AI models, security permissions, and Windows integration.')
        }

        l.addLayout(self.header(p, *titles[key]))

        if key == 'Overview':
            self.overview(p, l)
        elif key == 'Ask VEXORA':
            self.chat_dashboard(p, l, key, [
                ('What I can do','__capabilities__'),
                ('PC health', 'How is my PC?'),
                ('Recent work', 'Show recent files'),
                ('Running apps', 'Show running apps'),
                ('Capture screen', '__capture_screen__'),
                ('Agent plan', 'Plan opening Calculator'),
                ('System specs', 'Show system specifications'),
                ('Read screen', 'Read the text on my screen'),
                ('Workday setup', 'Prepare my workspace')
            ])
        elif key == 'My Work':
            self.work(p, l)
        elif key == 'Productivity':
            self.productivity(p, l)
        elif key == 'System Specifications':
            self.specifications(p, l)
        else:
            self.settings_page(p, l)

        f = QLabel(f'{self.assistant_name} v5.8 Professional • {key} • Local-First • Permission-Gated Safety')
        f.setObjectName('Footer')
        l.addWidget(f)
        return p

    def cards(self, items):
        g = QGridLayout()
        g.setSpacing(12)
        for i, (a, b, c) in enumerate(items):
            card = ModernMetricCard(a, b, c)
            g.addWidget(card, 0, i)
        return g

    def overview(self, p, l):
        active = sum(not t.get('done') for t in self.tasks)
        l.addLayout(self.cards([
            ('CPU', 'Live utilization', '--'),
            ('MEMORY', 'RAM utilization', '--'),
            ('STORAGE', 'Primary drive', '--'),
            ('TASKS', 'Active workspace', str(active)),
            ('AI', 'Active backend', self.backend_label())
        ]))

        visual = QFrame()
        visual.setObjectName('AgentVisualPanel')
        vv = QVBoxLayout(visual)
        vv.setContentsMargins(18, 16, 18, 16)
        vv.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel('AUTONOMOUS AGENT PULSE')
        title.setObjectName('SectionSmall')
        status = QLabel('SEE • THINK • ACT • VERIFY • RECOVER')
        status.setStyleSheet("color: #00F2FE; font-size: 10px; font-weight: 850; letter-spacing: 1.5px;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(status)
        vv.addLayout(top)

        stages = QHBoxLayout()
        stages.setSpacing(10)
        for st in agent_stage_data('IDLE'):
            card = QFrame()
            card.setStyleSheet(f"""
                background: {BG_INPUT};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 10px;
                padding: 10px;
            """)
            cv = QVBoxLayout(card)
            cv.setContentsMargins(8, 8, 8, 8)
            cv.setSpacing(6)

            name = QLabel(st.name)
            name.setStyleSheet("font-size: 11px; font-weight: 800; color: #FFF;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(st.progress)
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setObjectName('StageBar')

            state = QLabel(st.state.upper())
            state.setStyleSheet("font-size: 9px; font-weight: 800; color: #646B82; letter-spacing: 1px;")

            cv.addWidget(name)
            cv.addWidget(bar)
            cv.addWidget(state)
            stages.addWidget(card)
        vv.addLayout(stages)

        workload = workload_profile(self.tasks, 0, 0)
        wr = QHBoxLayout()
        wr.addWidget(QLabel(f"WORKLOAD: {workload['tasks_pending']} pending • {workload['tasks_done']} completed"))
        wr.addStretch()
        wr.addWidget(QLabel(f"COMPLETION RATE: {workload['completion_percent']:.0f}%"))
        vv.addLayout(wr)
        l.addWidget(visual)

        # Quick command bar
        cmd = QFrame()
        cmd.setObjectName('CommandStrip')
        cv = QHBoxLayout(cmd)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(10)

        label = QLabel('COMMAND')
        label.setStyleSheet("color: #00F2FE; font-size: 11px; font-weight: 900; letter-spacing: 1px;")
        cv.addWidget(label)

        inp = QLineEdit()
        inp.setPlaceholderText('Ask your assistant to inspect, plan, open apps, or capture screen…')
        inp.returnPressed.connect(lambda: self._overview_command(inp))
        cv.addWidget(inp, 1)

        go = QPushButton('Execute')
        go.setObjectName('SuggestionButton')
        go.clicked.connect(lambda: self._overview_command(inp))
        cv.addWidget(go)
        l.addWidget(cmd)

        self.feature_row(l, [
            ('SYSTEM PULSE', 'Inspect the current PC state & metrics.', 'How is my PC?'),
            ('WORK CONTINUITY', 'Inspect recent files and pending tasks.', 'Show recent files'),
            ('SCREEN VISION', 'Capture and inspect the current display.', '__capture_screen__'),
            ('AGENT PLANNER', 'Build a permission-gated automation plan.', 'Plan opening Calculator')
        ])

        self.workspace_shortcuts(l)
        note = QLabel('Core actions remain permission-gated. Dangerous operations fail closed and require explicit approval.')
        note.setObjectName('Hint')
        l.addWidget(note)

    def _overview_command(self, inp):
        text = inp.text().strip()
        if not text:
            return
        inp.clear()
        self._feature_command(text)

    def workspace_shortcuts(self, l):
        box = QFrame()
        box.setObjectName('WorkspaceStrip')
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel('QUICK SYSTEM SHORTCUTS')
        title.setObjectName('SectionSmall')
        hint = QLabel('Instant access to essential directories and workday setup.')
        hint.setObjectName('Hint')
        top.addWidget(title)
        top.addStretch()
        top.addWidget(hint)
        v.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(10)
        for label, cmd in [
            ('Downloads Folder', 'Open Downloads'),
            ('Documents Folder', 'Open Documents'),
            ('Workday Workspace', 'Prepare my workspace'),
            ('Windows Settings', 'open windows settings')
        ]:
            b = QPushButton(label)
            b.setObjectName('Action')
            b.setMinimumHeight(40)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setToolTip(cmd)
            b.clicked.connect(lambda _, x=cmd: self._feature_command(x))
            row.addWidget(b)
        v.addLayout(row)
        l.addWidget(box)

    def chat_dashboard(self, p, l, key, quick):
        row = QHBoxLayout()
        row.setSpacing(14)

        panel = QFrame()
        panel.setObjectName('ChatPanel')
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(10)

        top = QHBoxLayout()
        s = QLabel(self.assistant_name)
        s.setObjectName('Section')
        st = QLabel('Private • ' + self.backend_label())
        st.setStyleSheet("color: #00F2FE; font-size: 11px; font-weight: 750;")
        top.addWidget(s)
        top.addStretch()
        top.addWidget(st)
        pl.addLayout(top)

        scroll = QScrollArea()
        scroll.setObjectName('ChatScroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        host = QWidget()
        chat = QVBoxLayout(host)
        chat.setContentsMargins(8, 8, 8, 8)
        chat.setSpacing(10)
        chat.addStretch()
        scroll.setWidget(host)
        pl.addWidget(scroll, 1)

        typing = Typing(self.assistant_name)
        typing.setVisible(False)
        pl.addWidget(typing)

        # Quick prompt pills above composer
        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)
        for p_label, p_cmd in [
            ("⚡ PC Health", "How is my PC?"),
            ("📷 Screen Shot", "__capture_screen__"),
            ("🔍 Active Apps", "Show running apps"),
            ("📋 Recent Files", "Show recent files")
        ]:
            pb = QPushButton(p_label)
            pb.setStyleSheet("""
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid #1F2333;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                color: #A0A6B8;
            """)
            pb.clicked.connect(lambda _, c=p_cmd, k=key: self.command(k, c, True))
            pill_row.addWidget(pb)
        pill_row.addStretch()
        pl.addLayout(pill_row)

        comp = QFrame()
        comp.setObjectName('Composer')
        cr = QHBoxLayout(comp)
        cr.setContentsMargins(10, 8, 10, 8)
        cr.setSpacing(8)

        inp = Composer()
        inp.submit.connect(lambda _checked=False, k=key: self.send(k))
        cr.addWidget(inp, 1)

        model_box = QComboBox()
        model_box.setObjectName('ComposerModel')
        model_box.setToolTip('Select AI Model Backend')
        self._populate_model_selector(model_box)
        model_box.currentIndexChanged.connect(lambda _=0, combo=model_box: self._composer_model_changed(combo))
        cr.addWidget(model_box)

        stop = QPushButton('Stop')
        stop.setObjectName('Stop')
        stop.setVisible(False)
        stop.clicked.connect(self.stop)
        cr.addWidget(stop)

        send = QPushButton('↑')
        send.setObjectName('Send')
        send.clicked.connect(lambda _checked=False, k=key: self._send_with_feedback(k))
        cr.addWidget(send)
        pl.addWidget(comp)

        hint = QLabel('Press Enter to send • Shift + Enter for a new line • Esc to stop generation')
        hint.setObjectName('Hint')
        pl.addWidget(hint)
        row.addWidget(panel, 1)

        # Quick Action side panel
        q = QFrame()
        q.setObjectName('QuickPanel')
        q.setMinimumWidth(300)
        q.setMaximumWidth(340)
        ql = QVBoxLayout(q)
        ql.setContentsMargins(14, 14, 14, 14)
        ql.setSpacing(10)

        head = QLabel('Core actions')
        head.setObjectName('SectionSmall')
        ql.addWidget(head)

        hint2 = QLabel('9 responsive actions • selected AI model is used for general chat')
        hint2.setObjectName('Hint')
        hint2.setWordWrap(True)
        ql.addWidget(hint2)

        filter_box = QLineEdit()
        filter_box.setObjectName('QuickFilter')
        filter_box.setPlaceholderText('Filter actions…')
        filter_box.setClearButtonEnabled(True)
        ql.addWidget(filter_box)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        action_buttons = []

        for i, (label, cmd) in enumerate(quick[:9]):
            b = QPushButton(label)
            b.setObjectName('Action')
            b.setProperty('quick_label', label.lower())
            b.setMinimumHeight(44)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setToolTip(cmd)
            b.clicked.connect(lambda _, x=cmd, k=key, btn=b: self._responsive_action(k, x, btn))
            grid.addWidget(b, i // 2, i % 2)
            action_buttons.append(b)

        ql.addLayout(grid)
        filter_box.textChanged.connect(lambda value, buttons=action_buttons: self.filter_quick_actions(value, buttons))
        ql.addStretch()
        row.addWidget(q)
        l.addLayout(row, 1)

        self.sessions[key] = {
            'scroll': scroll,
            'chat': chat,
            'input': inp,
            'stop': stop,
            'typing': typing,
            'model_combo': model_box,
            'history': [{'user': m.get('user', ''), 'assistant': m.get('assistant', '')} for m in self.memory[-8:] if isinstance(m, dict)],
            'pending_id': None
        }

    def _populate_model_selector(self, combo):
        combo.blockSignals(True)
        combo.clear()
        options = [
            ('Auto • Local fallback', 'offline', 'llama3.2'),
            ('Ollama • Local', 'ollama', self.settings.get('model_name', 'llama3.2')),
            ('Gemini • 3.8 Flash • Free tier*', 'gemini', 'gemini-3.8-flash'),
            ('Gemini • 3.7 Flash • Free tier*', 'gemini', 'gemini-3.7-flash'),
            ('OpenAI • GPT-5.6 Luna', 'openai', 'gpt-5.6-luna'),
            ('OpenAI • GPT-5.6 Terra', 'openai', 'gpt-5.6-terra'),
            ('OpenAI • GPT-5.6 Sol', 'openai', 'gpt-5.6-sol'),
        ]
        for label, provider, model in options:
            combo.addItem(label, (provider, model))
        provider = self.settings.get('model_provider', 'offline')
        model = self.settings.get('model_name', 'llama3.2')
        for i in range(combo.count()):
            data = combo.itemData(i)
            if isinstance(data, tuple) and data == (provider, model):
                combo.setCurrentIndex(i)
                break
        combo.blockSignals(False)

    def _composer_model_changed(self, combo):
        data = combo.currentData() or ('offline', 'llama3.2')
        provider, model = data if isinstance(data, tuple) else (str(data), 'llama3.2')
        self.settings['model_provider'] = provider
        self.settings['model_name'] = model
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.model_status_text(f'Chat backend: {self.backend_label()}')
        self._feedback()

    def _safe_persist_settings(self):
        data = dict(self.settings)
        data['gemini_api_key'] = ''
        data['openai_api_key'] = ''
        return data

    def _send_with_feedback(self, key):
        self._feedback()
        self.send(key)

    def _responsive_action(self, key, cmd, button=None):
        if button is not None:
            button.setProperty('pulse', 'true')
            button.style().unpolish(button)
            button.style().polish(button)
            QTimer.singleShot(140, lambda b=button: (b.setProperty('pulse', 'false'), b.style().unpolish(b), b.style().polish(b)))
        self._feedback()
        self.command(key, cmd, True)

    def _feedback(self):
        if self.settings.get('feedback_enabled', True):
            try:
                QApplication.beep()
            except Exception:
                pass

    def model_status_text(self, text):
        if hasattr(self, 'model_status'):
            self.model_status.setText(text)

    def capabilities_text(self):
        name = self.assistant_name
        return (
            f"Here is what I can do right now:\n\n"
            f"• Answer general questions using the selected AI model.\n"
            f"• Inspect PC health, CPU, RAM, storage, battery and running apps.\n"
            f"• Show detailed system specifications.\n"
            f"• Capture the screen and optionally read visible text with OCR.\n"
            f"• Build permission-gated plans for supported computer actions.\n"
            f"• Calculate expressions and explain technical topics.\n"
            f"• Create, review and complete My Work tasks.\n"
            f"• Prepare a practical workday workspace folder on Desktop.\n"
            f"• Read recent files and help with recent computer activity.\n"
            f"• Open Windows Settings and selected safe applications.\n"
            f"• Keep contextual task and chat memory locally.\n"
            f"• Provide study, productivity and focused next-action guidance.\n\n"
            f"Protected computer actions require approval; unrestricted shell access is not provided."
        )

    def install_shortcuts(self):
        self.shortcut_palette = QShortcut(QKeySequence('Ctrl+K'), self)
        self.shortcut_palette.activated.connect(self.open_command_palette)
        self.shortcut_stop = QShortcut(QKeySequence('Esc'), self)
        self.shortcut_stop.activated.connect(self.stop)
        for idx, (_, key) in enumerate(self.NAV, 1):
            sc = QShortcut(QKeySequence(f'Ctrl+{idx}'), self)
            sc.activated.connect(lambda k=key: self.navigate(k))

    def open_command_palette(self):
        dlg = CommandPaletteDialog(self, lambda cmd: self._feature_command(cmd))
        dlg.exec_() if hasattr(dlg, 'exec_') else dlg.exec()

    def focus_command(self):
        session = self.sessions.get(self.current_page)
        if not session:
            self.navigate('Ask VEXORA')
            session = self.sessions.get('Ask VEXORA')
        if session:
            session['input'].setFocus()
            session['input'].selectAll()
            self.statusBar().showMessage('Command focus • type a request and press Enter', 2500)

    def filter_quick_actions(self, value, buttons):
        q = (value or '').strip().lower()
        visible = 0
        for b in buttons:
            show = not q or q in str(b.property('quick_label') or b.text()).lower()
            b.setVisible(show)
            visible += int(show)
        self.statusBar().showMessage(f'{visible} quick action(s) available' if q else 'Quick actions ready', 1500)

    def work(self, p, l):
        active_count = len([t for t in self.tasks if not t.get('done')])
        done_count = len([t for t in self.tasks if t.get('done')])
        l.addLayout(self.cards([
            ('ACTIVE TASKS', 'Tracked in this session', str(active_count)),
            ('COMPLETED', 'Finished tasks', str(done_count)),
            ('WORKSPACE', 'Task engine', 'READY')
        ]))

        # Task manager card
        task_box = QFrame()
        task_box.setObjectName('SettingsCard')
        tl = QVBoxLayout(task_box)
        tl.setContentsMargins(18, 16, 18, 16)
        tl.setSpacing(12)

        top_row = QHBoxLayout()
        title = QLabel('TASK TRACKER & CONTINUITY')
        title.setObjectName('SectionSmall')
        top_row.addWidget(title)
        top_row.addStretch()

        btn_clear = QPushButton('Clear Completed')
        btn_clear.clicked.connect(self.clear_completed_tasks)
        top_row.addWidget(btn_clear)
        tl.addLayout(top_row)

        # Input to add task
        add_row = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText('Enter a new task title and press Enter…')
        self.task_input.returnPressed.connect(self._add_task_from_input)
        add_row.addWidget(self.task_input, 1)

        btn_add = QPushButton('Add Task')
        btn_add.setObjectName('SuggestionButton')
        btn_add.clicked.connect(self._add_task_from_input)
        add_row.addWidget(btn_add)
        tl.addLayout(add_row)

        # Tasks list container
        self.tasks_list_layout = QVBoxLayout()
        self.tasks_list_layout.setSpacing(6)
        self.render_tasks()
        tl.addLayout(self.tasks_list_layout)

        l.addWidget(task_box)

        self.feature_row(l, [
            ('WORKDAY SETUP', 'Create workspace folder & summary.', 'Prepare my workspace'),
            ('RECENT FILES', 'Check recent Windows documents.', 'Show recent files'),
            ('FINISH LATEST', 'Mark most recent task as complete.', 'complete my latest task')
        ])

    def _add_task_from_input(self):
        text = self.task_input.text().strip()
        if text:
            self.task_input.clear()
            self.add_task(text)
            self.render_tasks()

    def add_task(self, title):
        self.tasks.append({
            'title': title,
            'done': False,
            'created_at': datetime.now().isoformat(timespec='seconds')
        })
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.render_tasks()

    def clear_completed_tasks(self):
        self.tasks = [t for t in self.tasks if not t.get('done')]
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.render_tasks()
        self.statusBar().showMessage('Completed tasks cleared.', 2000)

    def render_tasks(self):
        if not hasattr(self, 'tasks_list_layout'):
            return
        # Clear existing widgets
        while self.tasks_list_layout.count():
            item = self.tasks_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.tasks:
            empty = QLabel('No tasks yet. Type a task above or say "create task <name>" in chat.')
            empty.setStyleSheet('color: #646B82; font-style: italic; padding: 12px 0;')
            self.tasks_list_layout.addWidget(empty)
            return

        for idx, t in enumerate(self.tasks):
            row = QFrame()
            row.setStyleSheet(f"""
                background: {BG_INPUT};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 8px;
                padding: 6px 10px;
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 4, 6, 4)
            rl.setSpacing(10)

            cb = QCheckBox(t.get('title', 'Untitled Task'))
            cb.setChecked(bool(t.get('done')))
            cb.clicked.connect(lambda checked, i=idx: self._toggle_task(i, checked))
            rl.addWidget(cb, 1)

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet("""
                background: transparent;
                border: 0;
                color: #646B82;
                font-weight: 800;
                padding: 2px 6px;
            """)
            del_btn.clicked.connect(lambda _, i=idx: self._delete_task(i))
            rl.addWidget(del_btn)

            self.tasks_list_layout.addWidget(row)

    def _toggle_task(self, index, checked):
        if 0 <= index < len(self.tasks):
            self.tasks[index]['done'] = checked
            if checked:
                self.tasks[index]['completed_at'] = datetime.now().isoformat(timespec='seconds')
            save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})

    def _delete_task(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
            self.render_tasks()

    def productivity(self, p, l):
        l.addLayout(self.cards([
            ('ACTIVITY', 'Today’s session', 'Active'),
            ('CONTINUITY', 'Context Memory', str(len(self.memory))),
            ('FOCUS', 'Mode', 'Balanced')
        ]))

        self.feature_row(l, [
            ('DIAGNOSE PERFORMANCE', 'Run PC performance analysis.', 'diagnose performance'),
            ('INSPECT RAM', 'Check top memory-consuming applications.', 'which app is using my ram'),
            ('INSPECT PROCESSES', 'List active background processes.', 'show running apps'),
            ('SCREEN CONTEXT', 'Read what is currently open on screen.', 'what is on my screen')
        ])

    def specifications(self, p, l):
        specs = self.get_specifications()
        l.addLayout(self.cards([
            ('OS', specs.get('edition', 'Windows'), specs.get('windows', 'Windows')),
            ('PROCESSOR', 'CPU Model', specs.get('cpu', 'CPU')),
            ('GRAPHICS', 'GPU Adapter', specs.get('gpu', 'GPU')),
            ('MEMORY', 'Installed RAM', specs.get('ram', 'RAM'))
        ]))

        box = QFrame()
        box.setObjectName('SpecCard')
        bl = QVBoxLayout(box)
        bl.setContentsMargins(18, 16, 18, 16)
        bl.setSpacing(10)

        title = QLabel('SYSTEM HARDWARE & PLATFORM PROFILE')
        title.setObjectName('SectionSmall')
        bl.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        fields = [
            ("Operating System", specs.get('edition', 'Windows')),
            ("Kernel / Version", specs.get('windows', 'NT')),
            ("Processor (CPU)", specs.get('cpu', 'Unavailable')),
            ("Graphics (GPU)", specs.get('gpu', 'Unavailable')),
            ("System Memory", specs.get('ram', 'Unavailable')),
            ("Motherboard", specs.get('board', 'Unavailable')),
            ("BIOS Version", specs.get('bios', 'Unavailable')),
            ("Qt Framework", specs.get('pyside', 'PySide6')),
            ("Python Runtime", specs.get('python', 'Python')),
        ]

        for i, (k, v) in enumerate(fields):
            lbl_k = QLabel(k)
            lbl_k.setObjectName('SpecLabel')
            lbl_v = QLabel(v)
            lbl_v.setObjectName('SpecValue')
            lbl_v.setWordWrap(True)
            grid.addWidget(lbl_k, i // 2, (i % 2) * 2)
            grid.addWidget(lbl_v, i // 2, (i % 2) * 2 + 1)

        bl.addLayout(grid)
        l.addWidget(box)

    def get_specifications(self):
        now_ms = time.monotonic()
        if self._spec_cache and now_ms - self._spec_cache_ms < 60.0:
            return self._spec_cache

        info = {
            'cpu': 'Unavailable', 'gpu': 'Unavailable', 'ram': 'Unavailable',
            'windows': platform.platform(), 'edition': 'Windows', 'board': 'Unavailable',
            'bios': 'Unavailable', 'pyside': 'PySide6', 'python': platform.python_version()
        }

        try:
            import psutil
            info['ram'] = f"{psutil.virtual_memory().total / (1024**3):.1f} GB"
        except Exception:
            pass

        if os.name == 'nt':
            def cim(cls, prop):
                try:
                    out = subprocess.check_output(
                        ['powershell', '-NoProfile', '-Command', f"(Get-CimInstance Win32_{cls} | Select-Object -First 1 -ExpandProperty {prop})"],
                        text=True, stderr=subprocess.DEVNULL, timeout=3
                    ).strip()
                    return out or 'Unavailable'
                except Exception:
                    return 'Unavailable'

            info['cpu'] = cim('Processor', 'Name')
            info['gpu'] = cim('VideoController', 'Name')
            info['bios'] = cim('BIOS', 'SMBIOSBIOSVersion')
            info['board'] = cim('BaseBoard', 'Product')
            info['edition'] = cim('OperatingSystem', 'Caption')
            build = cim('OperatingSystem', 'BuildNumber')
            if build != 'Unavailable':
                info['windows'] = f'{platform.version()} • Build {build}'

        self._spec_cache = dict(info)
        self._spec_cache_ms = now_ms
        return info

    def settings_page(self,p,l):
        """Professional, single-column, vertically scrollable settings page."""
        scroll = QScrollArea()
        scroll.setObjectName('SettingsScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        host = QWidget()
        host.setObjectName('SettingsHost')
        scroll.setWidget(host)
        l.addWidget(scroll, 1)

        root = QVBoxLayout(host)
        root.setContentsMargins(2, 0, 12, 20)
        root.setSpacing(16)

        def card(title, subtitle=''):
            box = QFrame()
            box.setObjectName('SettingsCard')
            v = QVBoxLayout(box)
            v.setContentsMargins(18, 18, 18, 18)
            v.setSpacing(12)
            h = QLabel(title)
            h.setObjectName('SettingsSectionTitle')
            h.setWordWrap(True)
            v.addWidget(h)
            if subtitle:
                q = QLabel(subtitle)
                q.setObjectName('SettingsDescription')
                q.setWordWrap(True)
                q.setTextFormat(Qt.TextFormat.PlainText)
                v.addWidget(q)
            root.addWidget(box)
            return v

        def row(parent, title, description, control=None, buttons=None):
            r = QFrame()
            r.setObjectName('SettingsRow')
            rv = QVBoxLayout(r)
            rv.setContentsMargins(14, 13, 14, 13)
            rv.setSpacing(8)
            a = QLabel(title)
            a.setObjectName('SettingsRowTitle')
            a.setWordWrap(True)
            rv.addWidget(a)
            b = QLabel(description)
            b.setObjectName('SettingsRowDescription')
            b.setWordWrap(True)
            b.setTextFormat(Qt.TextFormat.PlainText)
            rv.addWidget(b)
            if control is not None:
                control.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                rv.addWidget(control)
            if buttons:
                br = QHBoxLayout()
                br.setSpacing(8)
                for btn in buttons:
                    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    br.addWidget(btn)
                rv.addLayout(br)
            parent.addWidget(r)
            return r

        def button(text, slot):
            b = QPushButton(text)
            b.setObjectName('Action')
            b.setMinimumHeight(42)
            b.clicked.connect(slot)
            return b

        # Identity
        v = card('ASSISTANT IDENTITY', 'Your assistant name is limited to 6 letters and is updated throughout the visible interface.')
        self.name_edit = QLineEdit(self.assistant_name)
        self.name_edit.setObjectName('SettingInput')
        self.name_edit.setMaxLength(6)
        self.name_edit.setMinimumHeight(42)
        self.name_edit.setPlaceholderText('1–6 letters only')
        save_name = button('Save name everywhere', self.save_assistant_name)
        row(v, 'Assistant name', 'Use letters A–Z only. Example: VEXORA, NOVA, ORBIT.', self.name_edit, [save_name])

        self.start_page_combo = QComboBox()
        for label, data in [('Overview', 'Overview'), ('Ask VEXORA', 'Ask VEXORA'), ('My Work', 'My Work'), ('Productivity', 'Productivity')]:
            self.start_page_combo.addItem(label, data)
        self.start_page_combo.setCurrentIndex(max(0, self.start_page_combo.findData(self.settings.get('start_page', 'Overview'))))
        self.start_page_combo.setMinimumHeight(42)
        self.start_page_combo.currentIndexChanged.connect(lambda _: self.set_start_page())
        row(v, 'Start page', 'Choose where the application opens.', self.start_page_combo)

        # AI Engine
        v = card('AI ENGINE', 'The selected provider/model is the actual backend used for general chat. VEXORA does not fake model responses.')
        self.provider_combo = QComboBox()
        for label, data in [('Offline fallback', 'offline'), ('Ollama • local', 'ollama'), ('Gemini API', 'gemini'), ('OpenAI API', 'openai')]:
            self.provider_combo.addItem(label, data)
        self.provider_combo.setCurrentIndex(max(0, self.provider_combo.findData(self.settings.get('model_provider', 'offline'))))
        self.provider_combo.setMinimumHeight(42)
        row(v, 'Provider', 'Select the service that will generate your answers.', self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(DEFAULT_MODELS + GEMINI_FREE_MODELS + OPENAI_MODELS)
        self.model_combo.setCurrentText(self.settings.get('model_name', 'llama3.2'))
        self.model_combo.setMinimumHeight(42)
        refresh = button('Refresh Ollama models', self.refresh_models)
        row(v, 'Model ID', 'This exact model ID is sent to the selected provider.', self.model_combo, [refresh])

        self.host_edit = QLineEdit(self.settings.get('ollama_host', 'http://127.0.0.1:11434'))
        self.host_edit.setObjectName('SettingInput')
        self.host_edit.setMinimumHeight(42)
        row(v, 'Ollama host', 'Only used for local Ollama requests.', self.host_edit)

        self.gemini_key_edit = QLineEdit(self.settings.get('gemini_api_key', ''))
        self.gemini_key_edit.setObjectName('SettingInput')
        self.gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_edit.setMinimumHeight(42)
        self.gemini_key_edit.setPlaceholderText('GEMINI_API_KEY')
        row(v, 'Gemini API key', 'Optional. Keys are kept out of the saved workspace file.', self.gemini_key_edit)

        self.openai_key_edit = QLineEdit(self.settings.get('openai_api_key', ''))
        self.openai_key_edit.setObjectName('SettingInput')
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_edit.setMinimumHeight(42)
        self.openai_key_edit.setPlaceholderText('OPENAI_API_KEY')
        row(v, 'OpenAI API key', 'Optional. API usage is separate from a ChatGPT subscription.', self.openai_key_edit)

        save_model = button('Save AI configuration', self.save_model_settings)
        test_model = button('Test the selected model (Async)', self.test_model_connection)
        row(v, 'Connection', 'Save first, then send a real verification request to remote providers without freezing.', None, [save_model, test_model])

        self.model_status = QLabel('Active: ' + self.backend_label())
        self.model_status.setObjectName('SettingsStatusText')
        self.model_status.setWordWrap(True)
        v.addWidget(self.model_status)

        # Windows Quick Settings
        v = card('WINDOWS QUICK SETTINGS', 'Open common Windows Settings pages directly from VEXORA.')
        quick = [
            ('Windows Settings', '__open_settings__'), ('Display', '__settings_display__'), ('Network & Internet', '__settings_network__'),
            ('Bluetooth & devices', '__settings_bluetooth__'), ('Apps', '__settings_apps__'), ('Personalization', '__settings_personalization__'),
            ('Accounts', '__settings_accounts__'), ('Windows Update', '__settings_update__'), ('Privacy & security', '__settings_privacy__'),
            ('Gaming', '__settings_gaming__'), ('Storage', '__settings_storage__'), ('Sound', '__settings_sound__'), ('Power & battery', '__settings_power__')
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for i, (label, cmd) in enumerate(quick):
            b = button(label, lambda _, x=cmd: self._feature_command(x))
            grid.addWidget(b, i // 2, i % 2)
        v.addLayout(grid)

        # Interface & Performance
        v = card('INTERFACE & PERFORMANCE', 'Keep the desktop responsive and control visual behavior.')
        controls = [
            ('Fast replies', 'Shorter response animation.', 'fast_replies', True),
            ('Tab animations', 'Animate navigation transitions.', 'animations', True),
            ('Reduce motion', 'Use simpler transitions.', 'reduce_motion', False),
            ('Auto-scroll chat', 'Keep the newest answer visible.', 'auto_scroll', True),
            ('Interaction feedback', 'Use lightweight feedback on important actions.', 'feedback_enabled', True),
            ('Focus mode', 'Keep productivity suggestions minimal.', 'focus_mode', False)
        ]
        for title, desc, k, default in controls:
            cb = QCheckBox(title)
            cb.setChecked(self.settings.get(k, default))
            cb.clicked.connect(lambda checked, key_name=k: self.set_setting(key_name, checked))
            row(v, title, desc, cb)

        # Privacy & Safety
        v = card('PRIVACY, SAFETY & COMPUTER ACCESS', 'Control what context VEXORA may use. Protected actions remain approval-gated.')
        safety_controls = [
            ('Local-first mode', 'Prefer local tools and local providers when available.', 'local_only', True),
            ('Online knowledge', 'Allow public web knowledge fallback when enabled.', 'online_knowledge', True),
            ('Use local AI', 'Allow the configured Ollama model for chat.', 'use_local_model', True),
            ('Action confirmation', 'Require approval before protected computer actions.', 'require_action_confirmation', True),
            ('Screen context', 'Allow screen/active-window inspection when requested.', 'screen_context', True),
            ('OCR', 'Enable optional OCR for visible screen text.', 'ocr_enabled', False),
            ('Everyday mode', 'Prioritize practical computer/work actions.', 'everyday_mode', True)
        ]
        for title, desc, k, default in safety_controls:
            cb = QCheckBox(title)
            cb.setChecked(self.settings.get(k, default))
            cb.clicked.connect(lambda checked, key_name=k: self.set_setting(key_name, checked))
            row(v, title, desc, cb)

        # Workspace and memory
        v = card('WORKSPACE & MEMORY', 'Useful maintenance controls without exposing low-level internals.')
        row(v, 'Workspace', 'Open the local workspace folder used for tasks and data.', None, [button('Open workspace', lambda: self._feature_command('Prepare my workspace'))])
        row(v, 'Saved conversation memory', 'Remove saved contextual chat memory while keeping tasks.', None, [button('Clear chat memory', self.clear_local_memory)])
        row(v, 'Preferences', 'Restore interface and AI preference defaults.', None, [button('Reset preferences', self.reset_preferences)])

        # Diagnostics
        v = card('DIAGNOSTICS', 'Jump directly to VEXORA diagnostics and hardware information.')
        row(v, 'PC health', 'CPU, RAM, storage and system health snapshot.', None, [button('Run PC health', lambda: self._feature_command('How is my PC?'))])
        row(v, 'System specifications', 'Hardware, Windows, BIOS, motherboard and runtime information.', None, [button('Open system specifications', lambda: self.navigate('System Specifications'))])
        row(v, 'Vision', 'Capture or inspect the current screen from Ask VEXORA.', None, [button('Open screen tools', lambda: self.navigate('Ask VEXORA'))])

        foot = QLabel(f'{self.assistant_name} v5.8 • Settings are vertically scrollable • No unrestricted shell access • Protected actions require approval.')
        foot.setObjectName('SettingsFooter')
        foot.setWordWrap(True)
        root.addWidget(foot)

    def set_start_page(self):
        value = self.start_page_combo.currentData() if hasattr(self, 'start_page_combo') else 'Overview'
        self.settings['start_page'] = value
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.statusBar().showMessage('Start page saved • ' + str(value), 2000)

    def clear_local_memory(self):
        self.memory = []
        try:
            data = load_store()
            data['memory'] = []
            save_store(data)
        except Exception:
            pass
        self._feedback()
        self.statusBar().showMessage('Local chat memory cleared.', 2500)

    def reset_preferences(self):
        defaults = {
            'animations': True, 'fast_replies': True, 'local_only': True, 'auto_scroll': True,
            'focus_mode': False, 'online_knowledge': True, 'use_local_model': True, 'everyday_mode': True,
            'require_action_confirmation': True, 'ocr_enabled': False, 'screen_context': True,
            'feedback_enabled': True, 'reduce_motion': False, 'start_page': 'Overview'
        }
        self.settings.update(defaults)
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self._feedback()
        self.statusBar().showMessage('Preferences reset to safe defaults. Reopen Settings to refresh controls.', 3000)

    def backend_label(self):
        provider = self.settings.get('model_provider', 'offline')
        if provider == 'offline':
            return 'Offline fallback'
        if provider == 'ollama':
            return f'Ollama • {self.settings.get("model_name", "llama3.2")}'
        if provider == 'gemini':
            return f'Gemini • {self.settings.get("model_name", "gemini-3.8-flash")}'
        if provider == 'openai':
            return f'OpenAI • {self.settings.get("model_name", "gpt-5.6-luna")}'
        return provider

    def save_assistant_name(self):
        raw = self.name_edit.text().strip()
        name = raw if re.fullmatch(r"[A-Za-z]{1,6}", raw) else self.assistant_name
        if not name:
            name = 'VEXORA'
        old_name = self.assistant_name
        self.assistant_name = name
        self.settings['assistant_name'] = name
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self._refresh_identity_text(old_name)
        self._feedback()
        self.statusBar().showMessage(f'Assistant name changed to {name} across the interface.', 3000)

    def _refresh_identity_text(self, old_name='VEXORA'):
        for w in self.findChildren(QWidget):
            if isinstance(w, (QLabel, QPushButton, QLineEdit, QPlainTextEdit)):
                try:
                    if isinstance(w, QLabel):
                        w.setText(w.text().replace(old_name, self.assistant_name).replace('VEXORA', self.assistant_name))
                    elif isinstance(w, QPushButton):
                        w.setText(w.text().replace(old_name, self.assistant_name).replace('VEXORA', self.assistant_name))
                    elif isinstance(w, (QLineEdit, QPlainTextEdit)):
                        if w.placeholderText():
                            w.setPlaceholderText(w.placeholderText().replace(old_name, self.assistant_name).replace('VEXORA', self.assistant_name))
                except Exception:
                    pass
        self.setWindowTitle(f'{self.assistant_name} v5.8 Professional — Your AI for the entire computer')
        if hasattr(self, 'brand_label'):
            self.brand_label.setText(self.assistant_name)
        if hasattr(self, 'name_edit'):
            self.name_edit.setText(self.assistant_name)

    def refresh_models(self):
        lm = LocalModel('ollama', self.settings.get('model_name', 'llama3.2'), self.host_edit.text().strip() or None)
        models = lm.list_models()
        if models:
            current = self.model_combo.currentText().strip()
            self.model_combo.clear()
            self.model_combo.addItems(models)
            self.model_combo.setCurrentText(current if current else models[0])
            self.model_status.setText(f'Found {len(models)} installed Ollama model(s).')
        else:
            self.model_status.setText('No Ollama models detected. Install/start Ollama and click Refresh models.')

    def save_model_settings(self):
        provider = self.provider_combo.currentData() or 'offline'
        model = self.model_combo.currentText().strip() or 'llama3.2'
        if provider == 'gemini' and model not in GEMINI_FREE_MODELS:
            model = 'gemini-3.8-flash'
        if provider == 'openai' and model not in OPENAI_MODELS:
            model = 'gpt-5.6-luna'
        self.settings['model_provider'] = provider
        self.settings['model_name'] = model
        self.settings['ollama_host'] = self.host_edit.text().strip() or 'http://127.0.0.1:11434'
        self.settings['gemini_api_key'] = self.gemini_key_edit.text().strip()
        self.settings['openai_api_key'] = self.openai_key_edit.text().strip()
        if self.settings['gemini_api_key']:
            os.environ['GEMINI_API_KEY'] = self.settings['gemini_api_key']
        if self.settings['openai_api_key']:
            os.environ['OPENAI_API_KEY'] = self.settings['openai_api_key']
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.model_combo.setCurrentText(model)
        self.model_status.setText('Active model: ' + self.backend_label() + ' • live requests use this exact model ID.')
        for session in self.sessions.values():
            combo = session.get('model_combo')
            if combo:
                self._populate_model_selector(combo)
        self._feedback()
        self.statusBar().showMessage('AI model saved • ' + self.backend_label(), 2500)

    def test_model_connection(self):
        """Asynchronous, non-blocking model connection testing."""
        provider = self.provider_combo.currentData() or 'offline'
        model = self.model_combo.currentText().strip() or 'llama3.2'
        host = self.host_edit.text().strip() or 'http://127.0.0.1:11434'

        if provider in ('gemini', 'openai'):
            key = self.gemini_key_edit.text().strip() if provider == 'gemini' else self.openai_key_edit.text().strip()
            if not key:
                self.model_status.setText(f'✕ {provider.title()} API key missing. Add the key first.')
                return

        self.model_status.setText(f'Testing connection to {provider.title()} ({model}) in background…')
        ctx = {
            'model_provider': provider,
            'model_name': model,
            'gemini_api_key': self.gemini_key_edit.text().strip(),
            'openai_api_key': self.openai_key_edit.text().strip(),
            'assistant_name': self.assistant_name
        }
        worker = ModelTestWorker(provider, model, ctx, host)
        worker.signals.result.connect(self._on_model_test_result)
        self.thread_pool.start(worker)

    def _on_model_test_result(self, ok: bool, message: str):
        self.model_status.setText(message)
        self.statusBar().showMessage(message, 3500)

    def set_setting(self, key, value, button=None):
        self.settings[key] = bool(value)
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        if button:
            button.setText('ON' if value else 'OFF')
        if key == 'fast_replies' and self.settings[key]:
            self.typing.setInterval(24)
        elif key == 'fast_replies':
            self.typing.setInterval(36)

    def feature_row(self, l, items):
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        columns = 4 if len(items) <= 4 else 3
        for i, (title, text, cmd) in enumerate(items):
            c = QFrame()
            c.setObjectName('FeatureCard')
            c.setMinimumHeight(105)
            v = QVBoxLayout(c)
            v.setContentsMargins(14, 12, 14, 12)
            a = QLabel(title.replace('VEXORA', self.assistant_name))
            a.setObjectName('CardTitle')
            b = QLabel(text)
            b.setWordWrap(True)
            b.setObjectName('FeatureText')
            z = QPushButton('Open Action')
            z.setObjectName('Action')
            z.setMinimumHeight(34)
            z.clicked.connect(lambda _, x=cmd: self._feature_command(x))
            v.addWidget(a)
            v.addWidget(b)
            v.addStretch()
            v.addWidget(z)
            grid.addWidget(c, i // columns, i % columns)
        l.addLayout(grid)

    def navigate(self, key):
        self.current_page = key
        for b, (_, k) in zip(self.nav, self.NAV):
            b.setObjectName('NavActive' if k == key else 'Nav')
            b.style().unpolish(b)
            b.style().polish(b)
            b.update()
        self.stack.setCurrentWidget(self.pages[key])
        if hasattr(self.pages[key], 'battery'):
            self.pages[key].battery.set_state(*self.power())
        self.statusBar().showMessage(f'{key} • ready', 1800)

        if self.settings.get('animations', True):
            self._transition_timer = QTimer(self)
            self._transition_timer.setSingleShot(True)
            self._transition_timer.timeout.connect(lambda: None)
            self._transition_timer.start(140)

        if key == 'Ask VEXORA' and key in self.sessions:
            self.sessions[key]['input'].setFocus()

    def power(self):
        s = self._snapshot_cached()
        return s.battery, s.charging

    def _snapshot_cached(self):
        now = time.monotonic()
        if self._health_cache is None or now - self._health_cache_ms > 1.0:
            self._health_cache = self.health.snapshot()
            self._health_cache_ms = now
        return self._health_cache

    def refresh(self):
        s = self._snapshot_cached()
        p = self.pages.get(self.current_page)
        if p is not None and hasattr(p, 'battery'):
            p.battery.set_state(s.battery, s.charging)
        overview = self.pages.get('Overview')
        if overview is not None:
            cards = overview.findChildren(QFrame, 'MetricCard')
            if len(cards) >= 5:
                # Update first 3 metric cards and backend
                if hasattr(cards[0], 'set_data'):
                    cards[0].set_data(f'{s.cpu:.0f}%', 'Live processor load', s.cpu)
                    cards[1].set_data(f'{s.ram:.0f}%', 'RAM in use', s.ram)
                    cards[2].set_data(f'{s.disk:.0f}%', 'Primary disk load', s.disk)
                    cards[4].set_data(self.backend_label(), 'Active AI provider', 100)
                else:
                    cards[0].findChild(QLabel, 'CardValue').setText(f'{s.cpu:.0f}%')
                    cards[1].findChild(QLabel, 'CardValue').setText(f'{s.ram:.0f}%')
                    cards[2].findChild(QLabel, 'CardValue').setText(f'{s.disk:.0f}%')
                    cards[4].findChild(QLabel, 'CardValue').setText(self.backend_label())

    def send(self, key):
        session = self.sessions.get(key)
        if not session:
            return
        text = session['input'].toPlainText().strip()
        session['input'].clear()
        if text:
            self.command(key, text, True)

    def command(self, key, text, show=True):
        if key not in self.sessions:
            return self._feature_command(text)

        if text=='__capabilities__':
            if show:
                self.add(key, 'user', f'What can {self.assistant_name} do?', True)
            self.add(key, 'ai', self.capabilities_text(), True)
            return

        if text == '__capture_screen__':
            if show:
                self.add(key, 'user', 'Capture my screen', True)
            r = capture_screen()
            self.add(key, 'ai', (f'✓ SEE: Screenshot captured successfully.\n\nSaved to: {r["path"]}' if r['ok'] else '✕ SEE: ' + r['error']), True)
            return

        if text == '__agent_capture__':
            if show:
                self.add(key, 'user', 'Inspect my screen', True)
            shot = see_screenshot()
            if not shot.get('ok'):
                self.add(key, 'ai', '✕ Screen capture unavailable: ' + shot.get('error', 'unknown error'), True)
                return
            obs = observe_image(shot['path'], ocr=False)
            msg = (
                f'✓ Visual observation recorded.\n\nResolution: {obs.width} × {obs.height}\n'
                f'Fingerprint: {obs.fingerprint[:16]}…\n'
                f'OCR backend: {"available" if obs.ocr_available else "optional / not active"}'
            ) if obs.ok else ('✕ Visual observation failed: ' + obs.error)
            self.add(key, 'ai', msg, True)
            return

        if text == '__agent_ocr__':
            if show:
                self.add(key, 'user', 'Read the text on my screen', True)
            shot = see_screenshot()
            if not shot.get('ok'):
                self.add(key, 'ai', '✕ Screen capture unavailable: ' + shot.get('error', 'unknown error'), True)
                return
            obs = observe_image(shot['path'], ocr=True)
            if obs.ok and obs.text_regions:
                text_out = '\n'.join(r.text for r in obs.text_regions)
                self.add(key, 'ai', 'Screen text detected:\n\n' + text_out, True)
            elif obs.ok:
                self.add(key, 'ai', 'No OCR text was detected. The visual observation itself succeeded.', True)
            else:
                self.add(key, 'ai', 'OCR observation failed safely: ' + obs.error, True)
            return

        if text.startswith('__settings_') or text == '__open_settings__':
            if show:
                self.add(key, 'user', text.replace('_', ' ').strip(), True)
            mapping = {
                '__open_settings__': None,
                '__settings_display__': 'display',
                '__settings_network__': 'network',
                '__settings_bluetooth__': 'bluetooth',
                '__settings_apps__': 'apps',
                '__settings_personalization__': 'personalization',
                '__settings_accounts__': 'accounts',
                '__settings_update__': 'update',
                '__settings_privacy__': 'privacy',
                '__settings_gaming__': 'gaming',
                '__settings_storage__': 'storage',
                '__settings_sound__': 'sound',
                '__settings_power__': 'power'
            }
            self.add(key, 'ai', open_windows_settings_page(mapping.get(text)), True)
            return

        if text.strip().lower() in ('prepare my workspace', 'set up my workspace', 'start my workday', 'workday setup'):
            if show:
                self.add(key, 'user', text, True)
            r = open_workspace_folder()
            summary = workday_summary(self.tasks)
            msg = (f'✓ Workspace ready at: {r["path"]}' if r.get('ok') else f'✕ Could not create workspace: {r.get("error","unknown error")}')
            self.add(key, 'ai', msg + '\n\n' + summary, True)
            return

        if text.strip().lower() in ('create workspace folder', 'create a workspace folder', 'create a folder named vexora_workspace on desktop'):
            if show:
                self.add(key, 'user', text, True)
            r = open_workspace_folder()
            self.add(key, 'ai', (f'✓ Workspace ready at: {r["path"]}' if r.get('ok') else ('✕ Could not create workspace: ' + r.get('error', 'unknown error'))), True)
            return

        task_match = re.match(r'(?i)^create (?:a )?task(?: to|:)?\s*(.+)$', text.strip())
        if task_match:
            title = task_match.group(1).strip()
            if show:
                self.add(key, 'user', text, True)
            self.add_task(title)
            self.add(key, 'ai', f'✓ Task created: {title}', True)
            return

        if re.match(r'(?i)^(complete|finish) (?:my )?(latest|last) task$', text.strip()):
            if show:
                self.add(key, 'user', text, True)
            for t in reversed(self.tasks):
                if not t.get('done'):
                    t['done'] = True
                    t['completed_at'] = datetime.now().isoformat(timespec='seconds')
                    save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
                    self.render_tasks()
                    self.add(key, 'ai', f'✓ Completed task: {t["title"]}', True)
                    return
            self.add(key, 'ai', 'There are no unfinished tasks to complete.', True)
            return

        if show:
            self.add(key, 'user', text)
        self.current_query = text

        if text.strip().lower() in ('capture screen', 'take a screenshot', 'screenshot', 'capture my screen'):
            r = see_screenshot()
            self.add(key, 'ai', ('✓ Screenshot captured: ' + r['path']) if r.get('ok') else ('✕ Screenshot unavailable: ' + r.get('error', 'unknown error')), True)
            return

        low = text.strip().lower()
        if low in ('read the text on my screen', 'ocr my screen', 'what text is on my screen'):
            shot = see_screenshot()
            if not shot.get('ok'):
                self.add(key, 'ai', '✕ Screenshot unavailable: ' + shot.get('error', 'unknown error'), True)
                return
            ocr = ocr_image(shot['path'])
            if ocr.get('ok') and ocr.get('text'):
                self.add(key, 'ai', 'Screen text detected:\n\n' + ocr['text'], True)
            else:
                self.add(key, 'ai', 'OCR is not ready. Install the optional pytesseract package and a Tesseract OCR engine, then enable OCR in Settings.', True)
            return

        if low.startswith('plan opening calculator'):
            p = build_agent_plan('Open calculator')
            self.add(key, 'ai', 'Agent plan:\n\n1. Open Calculator (protected action)\n\nApproval is required before execution.', True)
            return

        res = handle_result(text)
        if res.requires_confirmation:
            self.add(key, 'ai', 'Permission required before this protected action. No system change has been made.', True)
            return

        general = res.plan is None or res.plan.get('tool') is None or res.plan.get('intent') in ('General request', 'Explain capabilities')
        if not general:
            action = (res.plan or {}).get('action') if res.plan else None
            if res.plan and res.plan.get('tool') == 'screen_inspect':
                self.add(key, 'ai', res.text, True)
                return
            if res.plan and res.plan.get('tool') == 'performance_diagnosis':
                self.add(key, 'ai', res.text, True)
                return
            if res.plan and res.plan.get('tool') == 'everyday_workflow':
                self.add(key, 'ai', build_workflow(self.tasks, recent_files(3)), True)
                return
            if res.plan and res.plan.get('tool') == 'safe_app_launcher':
                action = (res.plan or {}).get('action') or 'unknown'
                approved = True
                if self.settings.get('require_action_confirmation', True):
                    # Use our modern Fluent PermissionDialog!
                    dlg = PermissionDialog(self, action.title(), res.text, risk_level="moderate")
                    result = dlg.exec_() if hasattr(dlg, 'exec_') else dlg.exec()
                    approved = (result == QDialog.DialogCode.Accepted if hasattr(QDialog, 'DialogCode') else result == 1)

                if not approved:
                    audit_record('action_denied', action=action)
                    self.add(key, 'ai', 'Action cancelled. No computer change was made.', True)
                    return

                r = execute_action(action, approved=True)
                audit_record('action_executed', action=action, ok=r.ok, verified=r.verified)
                self.add(key, 'ai', res.text + '\n\n' + (('✓ ' + r.message) if r.ok else ('✕ ' + r.message)), True)
                return

            if res.plan and res.plan.get('tool') == 'windows_settings':
                self.add(key, 'ai', open_windows_settings(), True)
                return
            if res.plan and res.plan.get('tool') == 'workday_setup':
                r = open_workspace_folder()
                self.add(key, 'ai', (f'✓ Workspace ready at: {r["path"]}' if r.get('ok') else f'✕ {r.get("error","unknown error")}') + '\n\n' + workday_summary(self.tasks), True)
                return
            if res.plan and res.plan.get('tool') == 'workday_plan':
                self.add(key, 'ai', workday_summary(self.tasks), True)
                return
            if res.plan and res.plan.get('tool') is not None:
                self.add(key, 'ai', f"{res.plan['intent']} • confidence {res.plan.get('confidence',0):.0%}\n\n{res.text}", True)
            else:
                self.add(key, 'ai', res.text, True)
            return

        self.request_id += 1
        rid = self.request_id
        session = self.sessions[key]
        session['pending_id'] = rid
        self.last_request[rid] = (key, text)
        session['stop'].setVisible(True)
        session['typing'].setVisible(True)

        context = {
            'tasks': self.tasks,
            'page': key,
            'local_only': self.settings.get('local_only', True),
            'online_knowledge': self.settings.get('online_knowledge', True),
            'use_local_model': self.settings.get('use_local_model', True),
            'model_provider': self.settings.get('model_provider', 'offline'),
            'model_name': self.settings.get('model_name', 'llama3.2'),
            'ollama_host': self.settings.get('ollama_host', 'http://127.0.0.1:11434'),
            'gemini_api_key': self.settings.get('gemini_api_key', ''),
            'openai_api_key': self.settings.get('openai_api_key', ''),
            'assistant_name': self.assistant_name
        }
        worker = ChatWorker(rid, key, text, list(session.get('history', [])), context)
        worker.signals.finished.connect(self.on_chat_finished)
        self.thread_pool.start(worker)

    def on_chat_finished(self, rid, key, query, reply):
        if key not in self.sessions:
            return
        session = self.sessions[key]
        if session.get('pending_id') != rid:
            return
        session['pending_id'] = None
        session['typing'].setVisible(False)
        session['stop'].setVisible(False)
        session.setdefault('history', []).append({'user': query, 'assistant': reply})
        session['history'] = session['history'][-12:]
        self.current_query = query
        try:
            remember_store(query, reply)
        except Exception:
            pass
        self.add(key, 'ai', reply, True)

    def _feature_command(self, text):
        self.navigate('Ask VEXORA')
        self.command('Ask VEXORA', text, True)

    def add(self, key, role, text, animate=True):
        ss = self.sessions[key]
        m = Message(role, '' if animate else text, self.copy, self.regenerate, self.assistant_name, key)
        m.page_key = key
        ss['chat'].insertWidget(ss['chat'].count() - 1, m)
        self.scroll(key)
        if animate:
            self.queue.append([key, m, text, 0])
            ss['stop'].setVisible(True)
            ss['typing'].setVisible(True)
            if not self.typing.isActive():
                self.typing.start(24 if self.settings.get('fast_replies', True) else 34)

    def scroll(self, key):
        if not self.settings.get('auto_scroll', True):
            return
        QTimer.singleShot(8, lambda: self.sessions[key]['scroll'].verticalScrollBar().setValue(
            self.sessions[key]['scroll'].verticalScrollBar().maximum()
        ))

    def type_next(self):
        if not self.queue:
            self.typing.stop()
            return
        key, m, text, i = self.queue[0]
        step = 5 if len(text) > 700 else (3 if len(text) > 180 else 2)
        n = min(len(text), i + step)
        m.set_text(text[:n])
        self.queue[0][3] = n
        self.scroll(key)
        if n >= len(text):
            self.queue.pop(0)
            self.sessions[key]['typing'].setVisible(bool(self.queue))
            self.sessions[key]['stop'].setVisible(bool(self.queue))

    def stop(self):
        self.request_id += 1
        for key, m, text, i in self.queue:
            m.set_text(text)
        self.queue.clear()
        self.typing.stop()
        for session in self.sessions.values():
            session['pending_id'] = None
            session['stop'].setVisible(False)
            session['typing'].setVisible(False)

    def copy(self, m):
        QApplication.clipboard().setText(m.raw_text if hasattr(m, 'raw_text') else m.body.text())
        self.statusBar().showMessage('Message text copied to clipboard.', 2000)

    def regenerate(self, m):
        page_key = getattr(m, 'page_key', self.current_page)
        session = self.sessions.get(page_key)
        if session and session.get('history'):
            q = session['history'][-1].get('user', '')
            if q:
                self.command(page_key, q, False)

    def style_ui(self):
        self.setStyleSheet(get_stylesheet(self.assistant_name))
