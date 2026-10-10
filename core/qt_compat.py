"""Qt compatibility bridge for VEXORA.

Windows 10/11: PySide6.
Windows 8/8.1 legacy: PySide2 (Python 3.8 recommended).
"""
try:
    from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRunnable, QThreadPool, QPropertyAnimation, QEasingCurve, QAbstractAnimation
    from PySide6.QtGui import QColor, QPainter, QPen, QKeyEvent, QShortcut, QAction, QKeySequence, QGuiApplication, QPixmap, QIcon
    from PySide6.QtWidgets import *
    QT_API = "PySide6"
except ImportError:
    from PySide2.QtCore import Qt as _Qt, QTimer, Signal, QObject, QRunnable, QThreadPool, QPropertyAnimation, QEasingCurve, QAbstractAnimation
    from PySide2.QtGui import QColor, QPainter, QPen, QKeyEvent, QKeySequence, QGuiApplication, QPixmap, QIcon
    from PySide2.QtWidgets import *
    try:
        from PySide2.QtWidgets import QShortcut, QAction
    except ImportError:
        from PySide2.QtGui import QShortcut, QAction
    QT_API = "PySide2"

    class _Key:
        Key_Return = _Qt.Key_Return

    class _KeyboardModifier:
        ShiftModifier = _Qt.ShiftModifier

    class _BrushStyle:
        NoBrush = _Qt.NoBrush

    class _PenStyle:
        NoPen = _Qt.NoPen

    class _TextInteractionFlag:
        TextSelectableByMouse = _Qt.TextSelectableByMouse

    class _ScrollBarPolicy:
        ScrollBarAlwaysOff = _Qt.ScrollBarAlwaysOff
        ScrollBarAsNeeded = _Qt.ScrollBarAsNeeded

    class _QtCompat:
        Key = _Key
        KeyboardModifier = _KeyboardModifier
        BrushStyle = _BrushStyle
        PenStyle = _PenStyle
        TextInteractionFlag = _TextInteractionFlag
        ScrollBarPolicy = _ScrollBarPolicy

    Qt = _QtCompat

    class _RenderHint:
        Antialiasing = QPainter.Antialiasing
    QPainter.RenderHint = _RenderHint
