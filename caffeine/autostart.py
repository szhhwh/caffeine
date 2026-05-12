import sys
import winreg
from pathlib import Path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "Caffeine"


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(sys.argv[0]).resolve())


def is_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def enable() -> None:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_path())
    winreg.CloseKey(key)


def disable() -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
    except (FileNotFoundError, OSError):
        pass
