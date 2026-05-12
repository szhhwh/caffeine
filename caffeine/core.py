import ctypes
import sys

if sys.platform != "win32":
    raise RuntimeError("Caffeine only supports Windows")

_kernel32 = ctypes.windll.kernel32

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_AWAKE_FLAGS = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED


def keep_awake() -> None:
    _kernel32.SetThreadExecutionState(_AWAKE_FLAGS)


def allow_sleep() -> None:
    _kernel32.SetThreadExecutionState(ES_CONTINUOUS)
