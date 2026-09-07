import ctypes
import os
import sys
import types
from unittest import mock

import pytest

os.environ["PYSTRAY_BACKEND"] = "dummy"

if sys.platform != "win32":

    def _fake_winreg() -> types.ModuleType:
        module = types.ModuleType("winreg")
        module.HKEY_CURRENT_USER = mock.MagicMock()
        module.KEY_READ = 0x20019
        module.KEY_WRITE = 0x20006
        module.REG_SZ = 1
        module.OpenKey = mock.MagicMock(side_effect=FileNotFoundError)
        module.QueryValueEx = mock.MagicMock()
        module.SetValueEx = mock.MagicMock()
        module.DeleteValue = mock.MagicMock()
        module.CloseKey = mock.MagicMock()
        return module

    sys.modules.setdefault("winreg", _fake_winreg())

    if not hasattr(ctypes, "windll"):
        ctypes.windll = mock.MagicMock()

    _real_platform = sys.platform
    sys.platform = "win32"
    try:
        import caffeine.tray  # noqa: F401
    finally:
        sys.platform = _real_platform

from caffeine import core  # noqa: E402


@pytest.fixture
def awake(monkeypatch):
    calls: list[str] = []
    for name in ("keep_awake", "keep_system_awake", "allow_sleep"):
        monkeypatch.setattr(core, name, lambda n=name: calls.append(n))
    return calls
