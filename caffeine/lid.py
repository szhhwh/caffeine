"""Temporarily disable the current power plan's lid-close action."""

import ctypes
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(value: str) -> _GUID:
    return _GUID.from_buffer_copy(UUID(value).bytes_le)


_BUTTONS = _guid("4f971e89-eebd-4455-a8de-9e59040e7347")
_LID_ACTION = _guid("5ca83367-6e45-459f-a27b-476b1d01c936")
_power = ctypes.windll.powrprof
_kernel32 = ctypes.windll.kernel32
_GUID_PTR = ctypes.POINTER(_GUID)

_power.PowerGetActiveScheme.argtypes = [ctypes.c_void_p, ctypes.POINTER(_GUID_PTR)]
_power.PowerGetActiveScheme.restype = ctypes.c_uint32
_power.PowerSetActiveScheme.argtypes = [ctypes.c_void_p, _GUID_PTR]
_power.PowerSetActiveScheme.restype = ctypes.c_uint32
_kernel32.LocalFree.argtypes = [ctypes.c_void_p]
_kernel32.LocalFree.restype = ctypes.c_void_p

for _source in ("AC", "DC"):
    _read = getattr(_power, f"PowerRead{_source}ValueIndex")
    _read.argtypes = [
        ctypes.c_void_p,
        _GUID_PTR,
        _GUID_PTR,
        _GUID_PTR,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    _read.restype = ctypes.c_uint32
    _write = getattr(_power, f"PowerWrite{_source}ValueIndex")
    _write.argtypes = [
        ctypes.c_void_p,
        _GUID_PTR,
        _GUID_PTR,
        _GUID_PTR,
        ctypes.c_uint32,
    ]
    _write.restype = ctypes.c_uint32


def _check(status: int) -> None:
    if status:
        raise OSError(status, f"Windows power settings error: {status}")


def _active_scheme() -> str:
    pointer = _GUID_PTR()
    _check(_power.PowerGetActiveScheme(None, ctypes.byref(pointer)))
    try:
        return str(UUID(bytes_le=bytes(pointer.contents)))
    finally:
        _kernel32.LocalFree(pointer)


def _read_action(scheme: str, source: str) -> int:
    value = ctypes.c_uint32()
    _check(
        getattr(_power, f"PowerRead{source}ValueIndex")(
            None,
            ctypes.byref(_guid(scheme)),
            ctypes.byref(_BUTTONS),
            ctypes.byref(_LID_ACTION),
            ctypes.byref(value),
        )
    )
    return value.value


def _write_action(scheme: str, source: str, value: int) -> None:
    _check(
        getattr(_power, f"PowerWrite{source}ValueIndex")(
            None,
            ctypes.byref(_guid(scheme)),
            ctypes.byref(_BUTTONS),
            ctypes.byref(_LID_ACTION),
            value,
        )
    )


def _apply(scheme: str) -> None:
    # Do not switch back to an old plan if the user has changed plans meanwhile.
    if _active_scheme() == scheme:
        _check(_power.PowerSetActiveScheme(None, ctypes.byref(_guid(scheme))))


@dataclass(frozen=True)
class _Settings:
    scheme: str
    ac: int
    dc: int


class LidSleepBlocker:
    def __init__(self, backup_path: Path) -> None:
        self._backup_path = backup_path
        self._saved: _Settings | None = None
        self._enabled = False

    def enable(self) -> None:
        if self._enabled:
            return
        # Recover a previous interrupted session before taking another snapshot.
        self.restore()
        scheme = _active_scheme()
        saved = _Settings(
            scheme, _read_action(scheme, "AC"), _read_action(scheme, "DC")
        )
        # Persist before making any system changes, so a crash is recoverable.
        self._backup_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._backup_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(saved)), encoding="utf-8")
        temporary.replace(self._backup_path)
        self._saved = saved
        try:
            _write_action(scheme, "AC", 0)
            _write_action(scheme, "DC", 0)
            _apply(scheme)
            self._enabled = True
        except OSError:
            self.restore()
            raise

    def restore(self) -> None:
        saved = self._saved or self._load_backup()
        if saved is None:
            return
        self._saved = saved
        self._enabled = False
        # Only undo our own overrides, preserving subsequent manual changes.
        for source, original in (("AC", saved.ac), ("DC", saved.dc)):
            if _read_action(saved.scheme, source) == 0:
                _write_action(saved.scheme, source, original)
        _apply(saved.scheme)
        self._backup_path.unlink(missing_ok=True)
        self._saved = None

    def _load_backup(self) -> _Settings | None:
        try:
            data = json.loads(self._backup_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except ValueError as exc:
            raise OSError("Invalid lid settings backup") from exc
        try:
            scheme = str(UUID(data["scheme"]))
            ac, dc = data["ac"], data["dc"]
            if any(
                type(value) is not int or value not in range(4) for value in (ac, dc)
            ):
                raise ValueError("Invalid lid action")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise OSError("Invalid lid settings backup") from exc
        return _Settings(scheme, ac, dc)
