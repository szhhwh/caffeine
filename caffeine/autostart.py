import sys
import winreg
from pathlib import Path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "Caffeine"


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" "{Path(sys.argv[0]).resolve()}"'


def is_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
    except (FileNotFoundError, OSError):
        return False
    try:
        winreg.QueryValueEx(key, _APP_NAME)
        return True
    except (FileNotFoundError, OSError):
        return False
    finally:
        winreg.CloseKey(key)


def enable() -> None:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE)
    try:
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_path())
    finally:
        winreg.CloseKey(key)


def disable() -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE)
    except (FileNotFoundError, OSError):
        return
    try:
        winreg.DeleteValue(key, _APP_NAME)
    except (FileNotFoundError, OSError):
        pass
    finally:
        winreg.CloseKey(key)
