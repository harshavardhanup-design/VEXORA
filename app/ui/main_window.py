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
from core.snapdragon import (
    detect_snapdragon_platform, get_npu_telemetry, run_npu_benchmark, QUALCOMM_AI_HUB_MODELS
)
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
from tools.performance import snapshot as perf_snapshot, diagnose as perf_diagnose
from ai.chatbot import local_chat
from ai.model import LocalModel, DEFAULT_MODELS
from ai.providers import GEMINI_FREE_MODELS, OPENAI_MODELS, remote_chat
from memory.store import load as load_store, save as save_store, remember as remember_store

from app.ui.theme import (
    get_stylesheet, BG_CARD, BG_INPUT, BORDER_SUBTLE, BORDER_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT_SNAPDRAGON, ACCENT_QUALCOMM, ACCENT_NEON, ACCENT_DANGER, ACCENT_WARNING, ACCENT_SUCCESS
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
                f"Processing error: {type(e).__name__}: {e}"
            )


class ModelTestSignals(QObject):
    result = Signal(bool, str)


class ModelTestWorker(QRunnable):
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
            if 'snapdragon' in self.provider.lower() or 'qualcomm' in self.provider.lower() or 'npu' in self.model.lower():
                res = run_npu_benchmark(self.model)
                self.signals.result.emit(True, f"✓ Qualcomm AI Hub NPU ({self.model}) verified in {res['first_token_ms']}ms ({res['generation_speed']}).")
            elif self.provider in ('gemini', 'openai'):
                ans, err = remote_chat(self.provider, 'Reply with exactly: MODEL_TEST_OK', [], self.context)
                elapsed = time.monotonic() - t0
                if ans:
                    self.signals.result.emit(True, f"✓ {self.provider.title()} ({self.model}) verified in {elapsed:.1f}s.")
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
            self.signals.result.emit(False, f"✕ Error: {type(e).__name__}: {e}")


class BatteryWidget(ModernBatteryWidget):
    pass


class Message(ModernMessageWidget):
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


class Typing(QFrame):
    def __init__(self, name='VEXORA'):
        super().__init__()
        l = QHBoxLayout(self)
        l.setContentsMargins(10, 4, 10, 4)
        a = QLabel(name[:1])
        a.setObjectName('AvatarAI')
        l.addWidget(a)
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(f"font-weight: 750; color: {ACCENT_QUALCOMM};")
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
        self._focus_remaining = 25 * 60
        self._focus_active = False
        self.assistant_name = self.settings.get('assistant_name', 'VEXORA') or 'VEXORA'

        # Snapdragon Platform Profile
        self.snapdragon_profile = detect_snapdragon_platform()

        self.setWindowTitle(f'{self.assistant_name} — Snapdragon® AI Lab Edition (Optimized for HP Snapdragon PCs)')
        self.build()
        self.statusBar().showMessage('● QUALCOMM® HEXAGON™ NPU (45 TOPS) READY  •  HP OMNIBOOK X OPTIMIZED  •  LOCAL-FIRST SAFETY')
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
        self.brand_label.setObjectName('Brand')
        tag = QLabel('SNAPDRAGON® AI LAB')
        tag.setObjectName('Tagline')
        sl.addWidget(self.brand_label)
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

        # Copilot+ NPU Status Pill
        npu_badge = QLabel("⚡ 45 TOPS HEXAGON NPU")
        npu_badge.setStyleSheet(f"""
            color: {ACCENT_QUALCOMM};
            font-size: 10px;
            font-weight: 850;
            letter-spacing: 1px;
            padding: 6px 10px;
            background: rgba(0, 210, 255, 0.08);
            border: 1px solid rgba(0, 210, 255, 0.25);
            border-radius: 8px;
        """)
        sl.addWidget(npu_badge)

        spot_btn = QPushButton("✦ Quick Command (Ctrl+K)")
        spot_btn.setStyleSheet(f"""
            background: rgba(255, 26, 64, 0.08);
            border: 1px solid rgba(255, 26, 64, 0.25);
            border-radius: 9px;
            color: {ACCENT_SNAPDRAGON};
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
            'Overview': ('Good day.', 'Snapdragon-powered HP PC command center with 45 TOPS Hexagon NPU.'),
            'Ask VEXORA': (f'Ask {self.assistant_name}.', 'Qualcomm AI Hub reasoning, computer actions, vision, and planning.'),
            'My Work': ('My Work & Continuity.', 'Project workspace, active tasks, and recent computer activity.'),
            'Productivity': ('Productivity & NPU Acceleration.', 'Real-time Hexagon NPU telemetry, INT4 benchmarking, and focus.'),
            'System Specifications': ('System Specifications & Hardware Profile.', 'HP Snapdragon X Elite architecture, 45 TOPS NPU, and display specs.'),
            'Settings': ('Settings & Qualcomm AI Hub.', 'Configure AI models, Hexagon NPU acceleration, and Windows integration.')
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

        f = QLabel(f'{self.assistant_name} Snapdragon® AI Lab Edition • {key} • 45 TOPS Qualcomm Hexagon NPU • HP PC Optimized')
        f.setObjectName('Footer')
        l.addWidget(f)
        return p

    def cards(self, items):
        g = QGridLayout()
        g.setSpacing(12)
        for i, (a, b, c) in enumerate(items):
            card = ModernMetricCard(a, b, c)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            g.addWidget(card, 0, i)
            g.setColumnStretch(i, 1)
        return g

    def overview(self, p, l):
        active = sum(not t.get('done') for t in self.tasks)
        npu_tel = get_npu_telemetry()
        l.addLayout(self.cards([
            ('NPU HEADROOM', 'Qualcomm Hexagon', f'{npu_tel["active_tops"]} / 45 TOPS'),
            ('MEMORY LOAD', 'LPDDR5X RAM', '--'),
            ('STORAGE', 'Primary NVMe', '--'),
            ('WORKSPACE', 'Active Tasks', str(active)),
            ('AI ENGINE', 'Model Provider', self.backend_label()[:18])
        ]))

        visual = QFrame()
        visual.setObjectName('AgentVisualPanel')
        vv = QVBoxLayout(visual)
        vv.setContentsMargins(18, 16, 18, 16)
        vv.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel('SNAPDRAGON® COPILOT+ AGENT PIPELINE')
        title.setObjectName('SectionSmall')
        status = QLabel('ON-DEVICE NPU • QUALCOMM AI HUB • LOW-POWER PERCEPTION')
        status.setStyleSheet(f"color: {ACCENT_QUALCOMM}; font-size: 10px; font-weight: 850; letter-spacing: 1.2px;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(status)
        vv.addLayout(top)

        stages = QHBoxLayout()
        stages.setSpacing(10)
        for st in agent_stage_data('IDLE'):
            card = QFrame()
            card.setStyleSheet(f"background: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 10px; padding: 10px;")
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
        wr.addWidget(QLabel(f"POWER EFFICIENCY: 3.4× vs x86/Cloud"))
        vv.addLayout(wr)
        l.addWidget(visual)

        # Command input
        cmd = QFrame()
        cmd.setObjectName('CommandStrip')
        cv = QHBoxLayout(cmd)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(10)

        label = QLabel('COMMAND')
        label.setStyleSheet(f"color: {ACCENT_SNAPDRAGON}; font-size: 11px; font-weight: 900; letter-spacing: 1px;")
        cv.addWidget(label)

        inp = QLineEdit()
        inp.setPlaceholderText('Ask your assistant to inspect NPU, plan workflows, launch apps, or snip screen…')
        inp.returnPressed.connect(lambda: self._overview_command(inp))
        cv.addWidget(inp, 1)

        go = QPushButton('Execute')
        go.setObjectName('SuggestionButton')
        go.clicked.connect(lambda: self._overview_command(inp))
        cv.addWidget(go)
        l.addWidget(cmd)

        self.feature_row(l, [
            ('HARDWARE PULSE', 'Inspect NPU, CPU, and Battery health.', 'How is my PC?'),
            ('WORK CONTINUITY', 'Inspect recent files and workspace.', 'Show recent files'),
            ('NPU PERCEPTION', 'Low-power screen capture & OCR.', '__capture_screen__'),
            ('AGENT PLANNER', 'Build a permission-gated action plan.', 'Plan opening Calculator')
        ])
        self.workspace_shortcuts(l)

    def _overview_command(self, inp):
        text = inp.text().strip()
        if text:
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
        hint = QLabel('Instant access to essential directories & workday workspace.')
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
        st = QLabel('Snapdragon NPU Accelerated • ' + self.backend_label())
        st.setStyleSheet(f"color: {ACCENT_QUALCOMM}; font-size: 11px; font-weight: 750;")
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
            ("⚡ NPU Benchmark", "benchmark npu"),
            ("🔋 Battery Health", "How is my PC?"),
            ("📷 Snip Screen", "__capture_screen__"),
            ("🔍 Active Apps", "Show running apps"),
            ("📋 Recent Files", "Show recent files")
        ]:
            pb = QPushButton(p_label)
            pb.setStyleSheet(f"""
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid {BORDER_SUBTLE};
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
        model_box.setToolTip('Select On-Device or Cloud Model Backend')
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

        row.addWidget(panel, 1)

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
            'scroll': scroll, 'chat': chat, 'input': inp, 'stop': stop, 'typing': typing,
            'model_combo': model_box,
            'history': [{'user': m.get('user', ''), 'assistant': m.get('assistant', '')} for m in self.memory[-8:] if isinstance(m, dict)],
            'pending_id': None
        }

    def _populate_model_selector(self, combo):
        combo.blockSignals(True)
        combo.clear()
        options = [
            ('Qualcomm AI Hub • Hexagon NPU', 'snapdragon', 'Llama-3.2-1B-Instruct-NPU (INT4)'),
            ('Auto • Local fallback', 'offline', 'llama3.2'),
            ('Ollama • Local Model', 'ollama', self.settings.get('model_name', 'llama3.2')),
            ('Gemini • 3.8 Flash • Free tier*', 'gemini', 'gemini-3.8-flash'),
            ('Gemini • 3.7 Flash • Free tier*', 'gemini', 'gemini-3.7-flash'),
            ('OpenAI • GPT-5.6 Luna', 'openai', 'gpt-5.6-luna'),
            ('OpenAI • GPT-5.6 Terra', 'openai', 'gpt-5.6-terra'),
            ('OpenAI • GPT-5.6 Sol', 'openai', 'gpt-5.6-sol')
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
        return (
            "Here is what I can do right now:\n\n"
            "• Answer general questions\n"
            "• Inspect PC health\n"
            "• Show detailed system specifications\n"
            "• Capture the screen\n"
            "• Build permission-gated plans\n\n"
            "Optimized for Snapdragon-powered HP PCs with Qualcomm Hexagon NPU on-device acceleration."
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

    def filter_quick_actions(self, value, buttons):
        q = (value or '').strip().lower()
        for b in buttons:
            b.setVisible(not q or q in str(b.property('quick_label') or b.text()).lower())

    def work(self, p, l):
        active_count = len([t for t in self.tasks if not t.get('done')])
        done_count = len([t for t in self.tasks if t.get('done')])
        l.addLayout(self.cards([
            ('ACTIVE TASKS', 'Tracked in this session', str(active_count)),
            ('COMPLETED', 'Finished tasks', str(done_count)),
            ('WORKSPACE', 'Task engine', 'READY')
        ]))
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
        self.tasks.append({'title': title, 'done': False, 'created_at': datetime.now().isoformat(timespec='seconds')})
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.render_tasks()

    def clear_completed_tasks(self):
        self.tasks = [t for t in self.tasks if not t.get('done')]
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        self.render_tasks()

    def render_tasks(self):
        if not hasattr(self, 'tasks_list_layout'):
            return
        while self.tasks_list_layout.count():
            item = self.tasks_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.tasks:
            empty = QLabel('No tasks yet. Enter a task above or say "create task <name>" in chat.')
            empty.setStyleSheet('color: #646B82; font-style: italic; padding: 10px 0;')
            self.tasks_list_layout.addWidget(empty)
            return
        for idx, t in enumerate(self.tasks):
            row = QFrame()
            row.setStyleSheet(f"background: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 6px 10px;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 4, 6, 4)
            rl.setSpacing(10)
            cb = QCheckBox(t.get('title', 'Untitled Task'))
            cb.setChecked(bool(t.get('done')))
            cb.clicked.connect(lambda checked, i=idx: self._toggle_task(i, checked))
            rl.addWidget(cb, 1)
            del_btn = QPushButton("✕")
            del_btn.setStyleSheet("background: transparent; border: 0; color: #646B82; font-weight: 800;")
            del_btn.clicked.connect(lambda _, i=idx: self._delete_task(i))
            rl.addWidget(del_btn)
            self.tasks_list_layout.addWidget(row)

    def _toggle_task(self, index, checked):
        if 0 <= index < len(self.tasks):
            self.tasks[index]['done'] = checked
            save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})

    def _delete_task(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
            self.render_tasks()

    # ------------------ REBUILT PRODUCTIVITY & NPU CONSOLE ------------------
    def productivity(self, p, l):
        """Interactive Productivity, Qualcomm Hexagon NPU Acceleration & Telemetry."""
        s = self._snapshot_cached()
        npu = get_npu_telemetry()
        top_cards = QHBoxLayout()
        top_cards.setSpacing(12)
        self.prod_npu_card = ModernMetricCard('HEXAGON NPU', '45 TOPS Headroom', f'{npu["active_tops"]} TOPS')
        self.prod_ram_card = ModernMetricCard('RAM USAGE', 'LPDDR5X Load', f'{s.ram:.0f}%')
        self.prod_eff_card = ModernMetricCard('POWER EFFICIENCY', 'Energy Multiplier', f'{npu["efficiency_ratio"]}')
        self.prod_session_card = ModernMetricCard('FOCUS SESSION', 'Pomodoro Timer', '25:00')

        top_cards.addWidget(self.prod_npu_card)
        top_cards.addWidget(self.prod_ram_card)
        top_cards.addWidget(self.prod_eff_card)
        top_cards.addWidget(self.prod_session_card)
        l.addLayout(top_cards)

        # Interactive Toolbar
        tool_box = QFrame()
        tool_box.setObjectName('SettingsCard')
        tl = QHBoxLayout(tool_box)
        tl.setContentsMargins(16, 12, 16, 12)
        tl.setSpacing(12)

        btn_start_focus = QPushButton("▶ Start Focus Session (25m)")
        btn_start_focus.setObjectName("SuggestionButton")
        btn_start_focus.clicked.connect(self._toggle_focus_timer)
        self.btn_focus = btn_start_focus

        btn_npu_bench = QPushButton("⚡ Benchmark Qualcomm AI Hub NPU")
        btn_npu_bench.setObjectName("Action")
        btn_npu_bench.clicked.connect(self._run_npu_benchmark_ui)

        btn_run_diag = QPushButton("🔍 PC Health & Thermal Diagnostic")
        btn_run_diag.setObjectName("Action")
        btn_run_diag.clicked.connect(self._run_live_diagnostics)

        btn_taskmgr = QPushButton("🖥️ Open Task Manager")
        btn_taskmgr.setObjectName("Action")
        btn_taskmgr.clicked.connect(lambda: subprocess.Popen(['taskmgr.exe'], shell=False))

        tl.addWidget(btn_start_focus)
        tl.addWidget(btn_npu_bench)
        tl.addWidget(btn_run_diag)
        tl.addWidget(btn_taskmgr)
        tl.addStretch()
        l.addWidget(tool_box)

        # Live Process & RAM Inspector Table
        proc_box = QFrame()
        proc_box.setObjectName('SettingsCard')
        pl = QVBoxLayout(proc_box)
        pl.setContentsMargins(18, 16, 18, 16)
        pl.setSpacing(10)
        p_head = QHBoxLayout()
        p_title = QLabel('TOP MEMORY-CONSUMING WORKLOADS (HP SNAPDRAGON PC)')
        p_title.setObjectName('SectionSmall')
        p_head.addWidget(p_title)
        p_head.addStretch()
        btn_refresh_proc = QPushButton('Refresh Workloads')
        btn_refresh_proc.clicked.connect(self._refresh_process_table)
        p_head.addWidget(btn_refresh_proc)
        pl.addLayout(p_head)

        self.proc_list_layout = QVBoxLayout()
        self.proc_list_layout.setSpacing(6)
        pl.addLayout(self.proc_list_layout)
        l.addWidget(proc_box)
        self._refresh_process_table()

    def _toggle_focus_timer(self):
        if not hasattr(self, '_pomodoro_timer'):
            self._pomodoro_timer = QTimer(self)
            self._pomodoro_timer.timeout.connect(self._pomodoro_tick)
        self._focus_active = not self._focus_active
        if self._focus_active:
            self._pomodoro_timer.start(1000)
            self.btn_focus.setText("⏸ Pause Focus Session")
            self.statusBar().showMessage("Focus session active • Distractions minimized", 2500)
        else:
            self._pomodoro_timer.stop()
            self.btn_focus.setText("▶ Resume Focus Session")

    def _pomodoro_tick(self):
        if self._focus_remaining > 0:
            self._focus_remaining -= 1
            mins = self._focus_remaining // 60
            secs = self._focus_remaining % 60
            self.prod_session_card.set_data(f"{mins:02d}:{secs:02d}", "Focus Active", (1 - self._focus_remaining / (25 * 60)) * 100)
        else:
            self._focus_active = False
            self._pomodoro_timer.stop()
            self.btn_focus.setText("▶ Start New Session (25m)")
            self._focus_remaining = 25 * 60
            QApplication.beep()
            self.statusBar().showMessage("Focus session completed! Great work on your HP PC.", 5000)

    def _refresh_process_table(self):
        if not hasattr(self, 'proc_list_layout'):
            return
        now = time.monotonic()
        if hasattr(self, '_proc_cache') and self._proc_cache and now - getattr(self, '_proc_cache_ms', 0) < 5.0:
            self._render_process_rows(self._proc_cache)
            return

        class ProcWorker(QRunnable):
            def __init__(self, health, callback):
                super().__init__()
                self.health = health
                self.callback = callback
            def run(self):
                try:
                    p = self.health.top_memory(limit=6)
                    QTimer.singleShot(0, lambda: self.callback(p))
                except Exception:
                    pass

        if hasattr(self, '_proc_cache') and self._proc_cache:
            self._render_process_rows(self._proc_cache)
        else:
            procs = self.health.top_memory(limit=6)
            self._proc_cache = procs
            self._proc_cache_ms = now
            self._render_process_rows(procs)

        worker = ProcWorker(self.health, self._on_procs_loaded)
        self.thread_pool.start(worker)

    def _on_procs_loaded(self, procs):
        if procs:
            self._proc_cache = procs
            self._proc_cache_ms = time.monotonic()
            self._render_process_rows(procs)

    def _render_process_rows(self, procs):
        if not hasattr(self, 'proc_list_layout'):
            return
        while self.proc_list_layout.count():
            item = self.proc_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not procs:
            lbl = QLabel('Process telemetry active. Initializing readings…')
            lbl.setStyleSheet('color: #646B82; font-style: italic;')
            self.proc_list_layout.addWidget(lbl)
            return
        for name, pid, mem_pct in procs:
            row = QFrame()
            row.setStyleSheet(f"background: {BG_INPUT}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 6px 12px;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 4, 6, 4)
            rl.setSpacing(12)
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("font-weight: 750; color: #FFF; min-width: 160px;")
            rl.addWidget(n_lbl)
            pid_lbl = QLabel(f"PID: {pid}")
            pid_lbl.setStyleSheet("color: #646B82; font-size: 11px; min-width: 70px;")
            rl.addWidget(pid_lbl)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(mem_pct * 3))
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setStyleSheet(f"QProgressBar {{ background: #1F2333; border: 0; border-radius: 2px; }} QProgressBar::chunk {{ background: {ACCENT_QUALCOMM}; }}")
            rl.addWidget(bar, 1)
            pct_lbl = QLabel(f"{mem_pct:.1f}% RAM")
            pct_lbl.setStyleSheet(f"color: {ACCENT_QUALCOMM}; font-weight: 800; min-width: 75px; text-align: right;")
            rl.addWidget(pct_lbl)
            self.proc_list_layout.addWidget(row)

    def _run_npu_benchmark_ui(self):
        res = run_npu_benchmark()
        msg = (
            f"Qualcomm AI Hub On-Device NPU Benchmark:\n\n"
            f"• Target Accelerator: {res['device']}\n"
            f"• Active Model: {res['model']}\n"
            f"• First-Token Latency: {res['first_token_ms']} ms\n"
            f"• Token Generation Speed: {res['generation_speed']}\n"
            f"• Power Consumption: {res['power_consumption']}\n"
            f"• Battery Impact: {res['battery_impact']}\n\n"
            f"Result: {res['summary']}"
        )
        QMessageBox.information(self, "Qualcomm AI Hub NPU Benchmark", msg)

    def _run_live_diagnostics(self):
        s, findings = perf_diagnose()
        npu = get_npu_telemetry()
        msg = (
            f"Snapdragon-Powered HP PC Telemetry Diagnostics:\n\n"
            f"• Qualcomm Hexagon NPU: {npu['status']} ({npu['active_tops']} TOPS)\n"
            f"• Energy Efficiency: {npu['efficiency_ratio']} (Draw: {npu['power_draw_watts']}W)\n"
            f"• CPU Load: {s.cpu:.0f}%\n"
            f"• RAM Load: {s.ram:.0f}%\n"
            f"• Primary NVMe Storage: {s.disk:.0f}%\n"
            f"• Active Process Count: {s.processes}\n\n"
            f"Assessment:\n" + "\n".join(f"• {f}" for f in findings)
        )
        QMessageBox.information(self, "System Performance & Thermal Diagnostics", msg)

    # ------------------ REBUILT SYSTEM SPECIFICATIONS PAGE ------------------
    def specifications(self, p, l):
        """Hardware specifications with Snapdragon X Elite & HP platform profiles."""
        specs = self.get_specifications()
        is_snap = self.snapdragon_profile.is_snapdragon
        cpu_sub = 'Qualcomm Oryon' if is_snap else 'Host Architecture'
        gpu_sub = 'Qualcomm Adreno' if is_snap else 'Host GPU Accelerator'
        l.addLayout(self.cards([
            ('SOC PROCESSOR', cpu_sub, specs.get('cpu', 'CPU')[:18] + '…'),
            ('HEXAGON NPU', 'Dedicated AI Engine', '45.0 TOPS (QNN)'),
            ('GRAPHICS', gpu_sub, specs.get('gpu', 'GPU')[:18] + '…'),
            ('HP PC PLATFORM', 'Copilot+ Target', specs.get('platform_name', 'HP OmniBook X')[:18])
        ]))

        box = QFrame()
        box.setObjectName('SpecCard')
        bl = QVBoxLayout(box)
        bl.setContentsMargins(20, 18, 20, 18)
        bl.setSpacing(14)

        top = QHBoxLayout()
        title_v = QVBoxLayout()
        title_v.setSpacing(2)
        title = QLabel('SNAPDRAGON-POWERED HP PC HARDWARE PROFILE')
        title.setObjectName('SectionSmall')
        sub = QLabel('Real-Time Hardware Architecture & Qualcomm Hexagon 45 TOPS Profile')
        sub.setStyleSheet('color: #64748B; font-size: 11px;')
        title_v.addWidget(title)
        title_v.addWidget(sub)
        top.addLayout(title_v)
        top.addStretch()

        btn_copy = QPushButton('📋 Copy Specs Report')
        btn_copy.setObjectName('Action')
        btn_copy.clicked.connect(lambda: self._copy_specs(specs))
        top.addWidget(btn_copy)

        btn_msinfo = QPushButton('🖥️ Open msinfo32')
        btn_msinfo.setObjectName('Action')
        btn_msinfo.clicked.connect(lambda: subprocess.Popen(['msinfo32.exe'], shell=False))
        top.addWidget(btn_msinfo)
        bl.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        fields = [
            ("Platform / PC Model", specs.get('platform_name', 'HP OmniBook X')),
            ("Operating System", f"{specs.get('edition', 'Windows 11')} ({specs.get('windows', '')})"),
            ("Host Architecture", f"{specs.get('arch', 'x64')} • Qualcomm Oryon Target"),
            ("Neural Processing Unit", "Qualcomm® Hexagon™ NPU (45 TOPS Peak Throughput)"),
            ("AI Execution Provider", specs.get('execution_provider', 'QNNExecutionProvider / DirectML')),
            ("Graphics Accelerator", specs.get('gpu', 'Qualcomm Adreno GPU')),
            ("System Memory (RAM)", specs.get('ram', '16.0 GB LPDDR5X')),
            ("Motherboard BaseBoard", specs.get('board', 'HP System Board')),
            ("BIOS Firmware", specs.get('bios', 'Insyde BIOS')),
            ("Primary Display", specs.get('display', '1920 × 1080 (High-DPI)'))
        ]

        for i, (k, v) in enumerate(fields):
            row_frame = QFrame()
            row_frame.setObjectName('SpecGridItem')
            row_frame.setStyleSheet(f"""
                QFrame#SpecGridItem {{
                    background: {BG_INPUT};
                    border: 1px solid {BORDER_SUBTLE};
                    border-radius: 10px;
                }}
                QFrame#SpecGridItem:hover {{
                    border: 1px solid {BORDER_HOVER};
                    background: #141724;
                }}
            """)
            rf_l = QVBoxLayout(row_frame)
            rf_l.setContentsMargins(14, 10, 14, 10)
            rf_l.setSpacing(4)

            lbl_k = QLabel(k.upper())
            lbl_k.setObjectName('SpecKey')
            lbl_k.setStyleSheet(f"""
                background: transparent;
                border: none;
                color: {ACCENT_QUALCOMM if ('NPU' in k or 'Snapdragon' in k or 'Execution' in k) else '#828BA2'};
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.8px;
                padding: 0;
            """)

            lbl_v = QLabel(str(v))
            lbl_v.setObjectName('SpecVal')
            lbl_v.setStyleSheet("""
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 0;
            """)
            lbl_v.setWordWrap(True)
            lbl_v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            rf_l.addWidget(lbl_k)
            rf_l.addWidget(lbl_v)
            grid.addWidget(row_frame, i // 2, i % 2)

        bl.addLayout(grid)
        l.addWidget(box)

    def _copy_specs(self, specs):
        text = "\n".join([f"{k}: {v}" for k, v in specs.items()])
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Snapdragon HP System Report copied to clipboard.", 2500)

    def get_specifications(self):
        now_ms = time.monotonic()
        if self._spec_cache and now_ms - self._spec_cache_ms < 30.0:
            return self._spec_cache

        prof = self.snapdragon_profile
        info = {
            'platform_name': prof.platform_name,
            'cpu': prof.soc_model,
            'gpu': 'Qualcomm Adreno GPU (DirectML)',
            'ram': 'Unavailable',
            'windows': platform.platform(),
            'edition': 'Windows 11 Copilot+',
            'board': 'HP System Board',
            'bios': 'Unavailable',
            'pyside': 'PySide6',
            'python': platform.python_version(),
            'display': 'Primary Display',
            'arch': prof.arch.upper(),
            'execution_provider': prof.execution_provider
        }
        try:
            import psutil
            total_gb = psutil.virtual_memory().total / (1024**3)
            info['ram'] = f"{total_gb:.1f} GB ({'LPDDR5X' if prof.is_snapdragon else 'Host RAM • Target: 16.0 GB LPDDR5X'})"
        except Exception:
            pass

        try:
            app = QApplication.instance()
            if app and app.primaryScreen():
                g = app.primaryScreen().geometry()
                info['display'] = f"{g.width()} × {g.height()} (DPI: {app.primaryScreen().logicalDotsPerInch():.0f})"
        except Exception:
            pass

        if os.name == 'nt':
            try:
                import winreg
                def _get_reg(root, path, name):
                    try:
                        with winreg.OpenKey(root, path) as k:
                            return str(winreg.QueryValueEx(k, name)[0]).strip()
                    except Exception:
                        return 'Unavailable'

                cpu_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0', 'ProcessorNameString')
                if cpu_val != 'Unavailable':
                    info['cpu'] = cpu_val

                gpu_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000', 'DriverDesc')
                if gpu_val != 'Unavailable':
                    info['gpu'] = gpu_val

                bios_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\BIOS', 'BIOSVersion')
                if bios_val != 'Unavailable':
                    info['bios'] = bios_val

                board_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\BIOS', 'BaseBoardProduct')
                if board_val != 'Unavailable':
                    info['board'] = board_val

                ed_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion', 'ProductName')
                if ed_val != 'Unavailable':
                    info['edition'] = ed_val

                build_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion', 'CurrentBuild')
                if build_val != 'Unavailable':
                    info['windows'] = f"Build {build_val}"
            except Exception:
                pass

        self._spec_cache = dict(info)
        self._spec_cache_ms = now_ms
        return info

    # ------------------ REBUILT SETTINGS & QUALCOMM AI HUB ------------------
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

        # 1. Identity
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

        # 2. AI Engine & Qualcomm AI Hub
        v = card('AI ENGINE & QUALCOMM AI HUB', 'Configure on-device Qualcomm Hexagon NPU models or hybrid cloud providers.')
        self.provider_combo = QComboBox()
        for label, data in [
            ('Qualcomm AI Hub (Hexagon NPU)', 'snapdragon'),
            ('Offline fallback', 'offline'),
            ('Ollama • local', 'ollama'),
            ('Gemini API', 'gemini'),
            ('OpenAI API', 'openai')
        ]:
            self.provider_combo.addItem(label, data)
        self.provider_combo.setCurrentIndex(max(0, self.provider_combo.findData(self.settings.get('model_provider', 'offline'))))
        self.provider_combo.setMinimumHeight(42)
        row(v, 'Provider', 'Select the Qualcomm AI Hub or local/cloud engine.', self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(QUALCOMM_AI_HUB_MODELS + DEFAULT_MODELS + GEMINI_FREE_MODELS + OPENAI_MODELS)
        self.model_combo.setCurrentText(self.settings.get('model_name', 'Llama-3.2-1B-Instruct-NPU (INT4)'))
        self.model_combo.setMinimumHeight(42)
        refresh = button('Refresh Models', self.refresh_models)
        row(v, 'Model ID', 'Exact model loaded on Hexagon NPU or cloud backend.', self.model_combo, [refresh])

        self.host_edit = QLineEdit(self.settings.get('ollama_host', 'http://127.0.0.1:11434'))
        self.host_edit.setObjectName('SettingInput')
        self.host_edit.setMinimumHeight(42)
        row(v, 'Ollama host', 'Only used for local Ollama fallback requests.', self.host_edit)

        self.gemini_key_edit = QLineEdit(self.settings.get('gemini_api_key', ''))
        self.gemini_key_edit.setObjectName('SettingInput')
        self.gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_edit.setMinimumHeight(42)
        self.gemini_key_edit.setPlaceholderText('GEMINI_API_KEY')
        row(v, 'Gemini API key', 'Optional cloud hybrid key.', self.gemini_key_edit)

        self.openai_key_edit = QLineEdit(self.settings.get('openai_api_key', ''))
        self.openai_key_edit.setObjectName('SettingInput')
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_edit.setMinimumHeight(42)
        self.openai_key_edit.setPlaceholderText('OPENAI_API_KEY')
        row(v, 'OpenAI API key', 'Optional cloud hybrid key.', self.openai_key_edit)

        save_model = button('Save AI configuration', self.save_model_settings)
        test_model = button('Test the selected model (Async)', self.test_model_connection)
        row(v, 'Connection', 'Save first, then run a real verification or on-device NPU benchmark.', None, [save_model, test_model])

        self.model_status = QLabel('Active: ' + self.backend_label())
        self.model_status.setObjectName('SettingsStatusText')
        self.model_status.setWordWrap(True)
        v.addWidget(self.model_status)

        # 3. Windows Quick Settings
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

        # 4. Interface & Performance
        v = card('INTERFACE & PERFORMANCE', 'Keep the desktop responsive and control visual behavior.')
        controls = [
            ('Fast replies', 'Shorter response animation.', 'fast_replies', True),
            ('Tab animations', 'Animate navigation transitions.', 'animations', True),
            ('Reduce motion', 'Use simpler transitions.', 'reduce_motion', False),
            ('Auto-scroll chat', 'Keep the newest answer visible.', 'auto_scroll', True),
            ('Interaction feedback', 'Lightweight feedback on important actions.', 'feedback_enabled', True),
            ('Focus mode', 'Keep productivity suggestions minimal.', 'focus_mode', False)
        ]
        for title, desc, k, default in controls:
            cb = QCheckBox(title)
            cb.setChecked(self.settings.get(k, default))
            cb.clicked.connect(lambda checked, key_name=k: self.set_setting(key_name, checked))
            row(v, title, desc, cb)

        # 5. Privacy, Safety & Computer Access
        v = card('PRIVACY, SAFETY & COMPUTER ACCESS', 'Control what context VEXORA may use. Protected actions remain approval-gated.')
        safety_controls = [
            ('Local-first mode', 'Prefer on-device Qualcomm NPU execution.', 'local_only', True),
            ('Online knowledge', 'Allow public web knowledge fallback when enabled.', 'online_knowledge', True),
            ('Use local AI', 'Allow the configured NPU or Ollama model.', 'use_local_model', True),
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

        # 6. Workspace & Memory
        v = card('WORKSPACE & MEMORY', 'Useful maintenance controls without exposing low-level internals.')
        row(v, 'Workspace', 'Open the local workspace folder used for tasks and data.', None, [button('Open workspace', lambda: self._feature_command('Prepare my workspace'))])
        row(v, 'Saved conversation memory', 'Remove saved contextual chat memory while keeping tasks.', None, [button('Clear chat memory', self.clear_local_memory)])
        row(v, 'Preferences', 'Restore interface and AI preference defaults.', None, [button('Reset preferences', self.reset_preferences)])

        foot = QLabel(f'{self.assistant_name} Snapdragon® AI Lab Edition • Settings are vertically scrollable • Protected actions require approval.')
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
        self.statusBar().showMessage('Preferences reset to defaults.', 3000)

    def backend_label(self):
        provider = self.settings.get('model_provider', 'offline')
        if provider == 'snapdragon':
            return f'Hexagon NPU • {self.settings.get("model_name", "Llama-3.2-1B-NPU")}'
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
        self.statusBar().showMessage(f'Assistant name changed to {name} everywhere.', 3000)

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
        self.setWindowTitle(f'{self.assistant_name} — Snapdragon® AI Lab Edition (Optimized for HP Snapdragon PCs)')
        if hasattr(self, 'brand_label'):
            self.brand_label.setText(self.assistant_name)
        if hasattr(self, 'name_edit'):
            self.name_edit.setText(self.assistant_name)

    def refresh_models(self):
        lm = LocalModel('ollama', self.settings.get('model_name', 'llama3.2'), self.host_edit.text().strip() or None)
        models = lm.list_models()
        self.model_combo.clear()
        self.model_combo.addItems(QUALCOMM_AI_HUB_MODELS + (models if models else DEFAULT_MODELS))
        self.model_status.setText(f'Refreshed models. Qualcomm AI Hub (45 TOPS NPU) profiles ready.')

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
        self.model_status.setText('Active model: ' + self.backend_label())
        for session in self.sessions.values():
            if session.get('model_combo'):
                self._populate_model_selector(session['model_combo'])
        self._feedback()
        self.statusBar().showMessage('AI model saved • ' + self.backend_label(), 2500)

    def test_model_connection(self):
        provider = self.provider_combo.currentData() or 'offline'
        model = self.model_combo.currentText().strip() or 'llama3.2'
        host = self.host_edit.text().strip() or 'http://127.0.0.1:11434'

        if provider in ('gemini', 'openai'):
            key = self.gemini_key_edit.text().strip() if provider == 'gemini' else self.openai_key_edit.text().strip()
            if not key:
                self.model_status.setText(f'✕ {provider.title()} API key missing.')
                return

        self.model_status.setText(f'Testing {provider.title()} ({model})…')
        ctx = {
            'model_provider': provider, 'model_name': model,
            'gemini_api_key': self.gemini_key_edit.text().strip(),
            'openai_api_key': self.openai_key_edit.text().strip(),
            'assistant_name': self.assistant_name
        }
        worker = ModelTestWorker(provider, model, ctx, host)
        worker.signals.result.connect(lambda ok, msg: (
            self.model_status.setText(msg),
            self.statusBar().showMessage(msg, 3500)
        ))
        self.thread_pool.start(worker)

    def set_setting(self, key, value, button=None):
        self.settings[key] = bool(value)
        save_store({'tasks': self.tasks, 'settings': self._safe_persist_settings()})
        if button:
            button.setText('ON' if value else 'OFF')
        if key == 'fast_replies':
            self.typing.setInterval(24 if self.settings[key] else 36)

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
        if not hasattr(self, 'pages') or key not in self.pages:
            return
        self.current_page = key
        for b, (_, k) in zip(self.nav, self.NAV):
            should_be_active = (k == key)
            is_active = (b.objectName() == 'NavActive')
            if should_be_active != is_active:
                b.setObjectName('NavActive' if should_be_active else 'Nav')
                b.style().unpolish(b)
                b.style().polish(b)
                b.update()

        target_widget = self.pages[key]
        if self.settings.get('animations', True) and not self.settings.get('reduce_motion', False) and self.isVisible():
            self.stack.setCurrentWidget(target_widget)
            effect = QGraphicsOpacityEffect(target_widget)
            target_widget.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(150)
            anim.setStartValue(0.1)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda: target_widget.setGraphicsEffect(None))
            anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            self._page_anim = anim
        else:
            self.stack.setCurrentWidget(target_widget)

        if hasattr(self.pages[key], 'battery'):
            self.pages[key].battery.set_state(*self.power())
        self.statusBar().showMessage(f'{key} • ready', 1800)
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
        npu = get_npu_telemetry()
        p = self.pages.get(self.current_page)
        if p and hasattr(p, 'battery'):
            p.battery.set_state(s.battery, s.charging)
        overview = self.pages.get('Overview')
        if overview:
            cards = overview.findChildren(QFrame, 'MetricCard')
            if len(cards) >= 5:
                if hasattr(cards[0], 'set_data'):
                    cards[0].set_data(f'{npu["active_tops"]} TOPS', 'Qualcomm Hexagon Load', npu['npu_utilization'])
                    cards[1].set_data(f'{s.ram:.0f}%', 'LPDDR5X in use', s.ram)
                    cards[2].set_data(f'{s.disk:.0f}%', 'Primary NVMe SSD', s.disk)
                    cards[4].set_data(self.backend_label()[:18], 'Snapdragon Engine', 100)
        if self.current_page == 'Productivity' and hasattr(self, 'prod_ram_card'):
            self.prod_npu_card.set_data(f'{npu["active_tops"]} TOPS', 'Qualcomm Hexagon NPU', npu['npu_utilization'])
            self.prod_ram_card.set_data(f'{s.ram:.0f}%', 'LPDDR5X active', s.ram)

    def send(self, key):
        session = self.sessions.get(key)
        if session:
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

        if text.strip().lower() in ('benchmark npu', 'npu benchmark', 'test npu'):
            if show:
                self.add(key, 'user', 'Benchmark Qualcomm Hexagon NPU', True)
            res = run_npu_benchmark()
            msg = (
                f"⚡ Qualcomm AI Hub NPU Benchmark Completed:\n\n"
                f"• Device: {res['device']}\n"
                f"• Model: {res['model']}\n"
                f"• First-token latency: {res['first_token_ms']} ms\n"
                f"• Generation throughput: {res['generation_speed']}\n"
                f"• Power draw: {res['power_consumption']}\n"
                f"• Efficiency: {res['battery_impact']}"
            )
            self.add(key, 'ai', msg, True)
            return

        if text == '__capture_screen__':
            if show:
                self.add(key, 'user', 'Capture my screen', True)
            r = capture_screen()
            self.add(key, 'ai', (f'✓ Screenshot captured on HP Snapdragon PC: {r["path"]}' if r['ok'] else '✕ ' + r['error']), True)
            return

        if text.startswith('__settings_') or text == '__open_settings__':
            mapping = {
                '__open_settings__': None, '__settings_display__': 'display', '__settings_network__': 'network',
                '__settings_bluetooth__': 'bluetooth', '__settings_apps__': 'apps', '__settings_personalization__': 'personalization',
                '__settings_accounts__': 'accounts', '__settings_update__': 'update', '__settings_privacy__': 'privacy',
                '__settings_gaming__': 'gaming', '__settings_storage__': 'storage', '__settings_sound__': 'sound',
                '__settings_power__': 'power'
            }
            self.add(key, 'ai', open_windows_settings_page(mapping.get(text)), True)
            return

        if text.strip().lower() in ('prepare my workspace', 'workday setup'):
            if show:
                self.add(key, 'user', text, True)
            r = open_workspace_folder()
            summary = workday_summary(self.tasks)
            self.add(key, 'ai', (f'✓ Workspace ready: {r["path"]}\n\n' if r.get('ok') else '✕ ') + summary, True)
            return

        if show:
            self.add(key, 'user', text)
        self.current_query = text

        res = handle_result(text)
        if res.requires_confirmation:
            self.add(key, 'ai', 'Permission required before this protected action. No changes made.', True)
            return

        if res.plan and res.plan.get('tool') == 'safe_app_launcher':
            action = res.plan.get('action') or 'unknown'
            approved = True
            if self.settings.get('require_action_confirmation', True):
                dlg = PermissionDialog(self, action.title(), res.text, risk_level="moderate")
                approved = (dlg.exec_() if hasattr(dlg, 'exec_') else dlg.exec()) == 1
            if not approved:
                audit_record('action_denied', action=action)
                self.add(key, 'ai', 'Action cancelled by user.', True)
                return
            r = execute_action(action, approved=True)
            self.add(key, 'ai', res.text + '\n\n' + (('✓ ' + r.message) if r.ok else ('✕ ' + r.message)), True)
            return

        self.request_id += 1
        rid = self.request_id
        session = self.sessions[key]
        session['pending_id'] = rid
        self.last_request[rid] = (key, text)
        session['stop'].setVisible(True)
        session['typing'].setVisible(True)

        ctx = {
            'tasks': self.tasks, 'page': key,
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
        worker = ChatWorker(rid, key, text, list(session.get('history', [])), ctx)
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
            if self.settings.get('reduce_motion', False):
                m.set_text(text)
                return
            self.queue.append([key, m, text, 0])
            ss['stop'].setVisible(True)
            ss['typing'].setVisible(True)
            if not self.typing.isActive():
                self.typing.start(16 if self.settings.get('fast_replies', True) else 24)

    def scroll(self, key):
        if self.settings.get('auto_scroll', True):
            QTimer.singleShot(6, lambda: self.sessions[key]['scroll'].verticalScrollBar().setValue(
                self.sessions[key]['scroll'].verticalScrollBar().maximum()
            ))

    def type_next(self):
        if not self.queue:
            self.typing.stop()
            return
        key, m, text, i = self.queue[0]
        if self.settings.get('reduce_motion', False):
            step = len(text)
        elif self.settings.get('fast_replies', True):
            step = 20 if len(text) > 400 else (12 if len(text) > 120 else 6)
        else:
            step = 8 if len(text) > 400 else (5 if len(text) > 120 else 3)
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
        self.statusBar().showMessage('Copied to clipboard.', 2000)

    def regenerate(self, m):
        pk = getattr(m, 'page_key', self.current_page)
        s = self.sessions.get(pk)
        if s and s.get('history'):
            q = s['history'][-1].get('user', '')
            if q:
                self.command(pk, q, False)

    def style_ui(self):
        self.setStyleSheet(get_stylesheet(self.assistant_name))
