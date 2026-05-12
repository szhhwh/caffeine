import ctypes
import sys
import threading

from caffeine.tray import TrayApp


def _enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    if sys.platform != "win32":
        print("Caffeine only supports Windows.", file=sys.stderr)
        sys.exit(1)

    _enable_dpi_awareness()
    _acquire_lock()

    app = TrayApp()
    app.run()


def _acquire_lock() -> threading.Lock:
    lock = threading.Lock()

    if not lock.acquire(blocking=False):
        print("Caffeine is already running.", file=sys.stderr)
        sys.exit(0)

    return lock


if __name__ == "__main__":
    main()
