import ctypes
import sys
import uuid

from caffeine.tray import TrayApp

_MUTEX_NAME = f"Local\\Caffeine-{uuid.uuid5(uuid.NAMESPACE_DNS, 'caffeine')}"


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
    _acquire_singleton()

    app = TrayApp()
    app.run()


def _acquire_singleton() -> None:
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not mutex:
        print("Failed to create mutex.", file=sys.stderr)
        sys.exit(1)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("Caffeine is already running.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
