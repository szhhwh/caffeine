import sys
import types
from pathlib import Path

import pytest

from caffeine import autostart


class FakeKey:
    def __init__(self) -> None:
        self.closed = False


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.keys: list[FakeKey] = []
        self.open_error: OSError | None = None

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=0x20019,
            KEY_WRITE=0x20006,
            REG_SZ=1,
            OpenKey=self._open_key,
            QueryValueEx=self._query_value_ex,
            SetValueEx=self._set_value_ex,
            DeleteValue=self._delete_value,
            CloseKey=self._close_key,
        )
        monkeypatch.setattr(autostart, "winreg", module)

    def assert_all_keys_closed(self) -> None:
        assert self.keys
        assert all(key.closed for key in self.keys)

    def _open_key(self, root, sub_key, reserved, access) -> FakeKey:
        if self.open_error is not None:
            raise self.open_error
        key = FakeKey()
        self.keys.append(key)
        return key

    def _query_value_ex(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], 1

    def _set_value_ex(self, key, name, reserved, value_type, value) -> None:
        self.values[name] = value

    def _delete_value(self, key, name) -> None:
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]

    def _close_key(self, key) -> None:
        key.closed = True


@pytest.fixture
def registry(monkeypatch):
    fake = FakeRegistry()
    fake.install(monkeypatch)
    return fake


def test_is_enabled_false_when_value_missing(registry):
    assert not autostart.is_enabled()
    registry.assert_all_keys_closed()


def test_is_enabled_true_when_value_present(registry):
    registry.values[autostart._APP_NAME] = "something"

    assert autostart.is_enabled()
    registry.assert_all_keys_closed()


def test_is_enabled_false_when_open_key_fails(registry):
    registry.open_error = OSError("denied")

    assert not autostart.is_enabled()


def test_enable_writes_dev_command(registry, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python")
    monkeypatch.setattr(sys, "argv", ["/home/user/caffeine/main.py"])

    autostart.enable()

    assert registry.values[autostart._APP_NAME] == (
        f'"/usr/bin/python" "{Path("/home/user/caffeine/main.py").resolve()}"'
    )
    registry.assert_all_keys_closed()


def test_enable_writes_frozen_executable(registry, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\Caffeine.exe")

    autostart.enable()

    assert registry.values[autostart._APP_NAME] == r"C:\Apps\Caffeine.exe"
    registry.assert_all_keys_closed()


def test_disable_removes_value(registry):
    registry.values[autostart._APP_NAME] = "something"

    autostart.disable()

    assert autostart._APP_NAME not in registry.values
    registry.assert_all_keys_closed()


def test_disable_missing_value_is_noop(registry):
    autostart.disable()

    assert autostart._APP_NAME not in registry.values
    registry.assert_all_keys_closed()


def test_exe_path_frozen_uses_executable(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\Caffeine.exe")

    assert autostart._exe_path() == r"C:\Apps\Caffeine.exe"


def test_exe_path_dev_quotes_interpreter_and_script(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python")
    monkeypatch.setattr(sys, "argv", ["main.py"])

    expected = f'"/usr/bin/python" "{Path("main.py").resolve()}"'
    assert autostart._exe_path() == expected
