import ctypes
import sys
import types
from unittest import mock

import pytest

import main


class FakeKernel32:
    def __init__(self, handle=1) -> None:
        self._handle = handle
        self.mutex_names: list[str | None] = []

    def CreateMutexW(self, attrs, initial, name):
        self.mutex_names.append(name)
        return self._handle


def _patch_winDll(monkeypatch, kernel32: FakeKernel32) -> dict:
    recorded: dict = {}

    def fake_windll(name, use_last_error=False):
        recorded["name"] = name
        recorded["use_last_error"] = use_last_error
        return kernel32

    monkeypatch.setattr(ctypes, "WinDLL", fake_windll, raising=False)
    return recorded


def test_singleton_check_uses_last_error_safe_dll(monkeypatch):
    kernel32 = FakeKernel32(handle=1)
    recorded = _patch_winDll(monkeypatch, kernel32)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 0, raising=False)

    main._acquire_singleton()

    assert recorded["name"] == "kernel32"
    assert recorded["use_last_error"] is True
    assert kernel32.mutex_names == [main._MUTEX_NAME]


def test_singleton_exits_when_already_running(monkeypatch, capsys):
    _patch_winDll(monkeypatch, FakeKernel32(handle=1))
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 183, raising=False)

    with pytest.raises(SystemExit) as exc:
        main._acquire_singleton()

    assert exc.value.code == 0
    assert "already running" in capsys.readouterr().err


def test_singleton_exits_on_null_mutex(monkeypatch, capsys):
    _patch_winDll(monkeypatch, FakeKernel32(handle=0))
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 0, raising=False)

    with pytest.raises(SystemExit) as exc:
        main._acquire_singleton()

    assert exc.value.code == 1
    assert "Failed to create mutex" in capsys.readouterr().err


def test_dpi_awareness_prefers_per_monitor(monkeypatch):
    shcore = mock.MagicMock()
    user32 = mock.MagicMock()
    windll = types.SimpleNamespace(shcore=shcore, user32=user32)
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)

    main._enable_dpi_awareness()

    shcore.SetProcessDpiAwareness.assert_called_once_with(2)
    user32.SetProcessDPIAware.assert_not_called()


def test_dpi_awareness_falls_back_to_user32(monkeypatch):
    shcore = mock.MagicMock()
    shcore.SetProcessDpiAwareness.side_effect = OSError
    user32 = mock.MagicMock()
    windll = types.SimpleNamespace(shcore=shcore, user32=user32)
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)

    main._enable_dpi_awareness()

    user32.SetProcessDPIAware.assert_called_once()


def test_dpi_awareness_tolerates_total_failure(monkeypatch):
    shcore = mock.MagicMock()
    shcore.SetProcessDpiAwareness.side_effect = AttributeError
    user32 = mock.MagicMock()
    user32.SetProcessDPIAware.side_effect = OSError
    windll = types.SimpleNamespace(shcore=shcore, user32=user32)
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)

    main._enable_dpi_awareness()


def test_main_rejects_non_windows(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1
    assert "only supports Windows" in capsys.readouterr().err


def test_main_initializes_then_runs_app(monkeypatch):
    order: list[str] = []
    app = mock.MagicMock()
    app.run.side_effect = lambda: order.append("run")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(main, "TrayApp", mock.MagicMock(return_value=app))
    monkeypatch.setattr(main, "_enable_dpi_awareness", lambda: order.append("dpi"))
    monkeypatch.setattr(main, "_acquire_singleton", lambda: order.append("mutex"))

    main.main()

    assert order == ["dpi", "mutex", "run"]
