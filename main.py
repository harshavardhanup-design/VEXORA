"""VEXORA entry point."""
import sys

from core.logging_setup import configure, get_logger


def _install_excepthook():
    log = get_logger('main')

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.critical('uncaught exception', exc_info=(exc_type, exc, tb))  # crashes are no longer silent

    sys.excepthook = hook


def main():
    configure()
    _install_excepthook()
    # Qt imports happen after logging so import-time failures are recorded too.
    from core.qt_compat import QApplication
    from core.windows11 import configure_process
    from app.ui.main_window import MainWindow

    configure_process()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
