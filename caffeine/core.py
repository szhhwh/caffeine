import ctypes
import queue
import sys
import threading

if sys.platform != "win32":
    raise RuntimeError("Caffeine only supports Windows")

_kernel32 = ctypes.windll.kernel32

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_AWAKE_FLAGS = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
_SYSTEM_ONLY_FLAGS = ES_CONTINUOUS | ES_SYSTEM_REQUIRED


class _Request:
    def __init__(self, flags: int) -> None:
        self.flags = flags
        self.done = threading.Event()
        self.error: BaseException | None = None


_requests: queue.Queue[_Request] = queue.Queue()
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()


def _apply_state(flags: int) -> None:
    _kernel32.SetThreadExecutionState(flags)


def _worker_loop() -> None:
    while True:
        request = _requests.get()
        try:
            _apply_state(request.flags)
        except BaseException as exc:
            request.error = exc
        finally:
            request.done.set()


def _submit(flags: int) -> None:
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = threading.Thread(
                target=_worker_loop, name="caffeine-execution-state", daemon=True
            )
            _worker.start()
    request = _Request(flags)
    _requests.put(request)
    request.done.wait()
    if request.error is not None:
        raise request.error


def keep_awake() -> None:
    _submit(_AWAKE_FLAGS)


def keep_system_awake() -> None:
    _submit(_SYSTEM_ONLY_FLAGS)


def allow_sleep() -> None:
    _submit(ES_CONTINUOUS)
