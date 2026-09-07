import threading
from collections.abc import Callable


class Timer:
    def __init__(self, on_expire: Callable[[], None], on_tick: Callable[[int], None]):
        self._on_expire = on_expire
        self._on_tick = on_tick
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._remaining: int = 0

    @property
    def remaining(self) -> int:
        return self._remaining

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, minutes: int) -> None:
        self._start_seconds(minutes * 60)

    def resume(self, seconds: int) -> None:
        self._start_seconds(seconds)

    def _start_seconds(self, seconds: int) -> None:
        self.cancel()
        self._stop_event.clear()
        self._remaining = max(0, seconds)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        if self.is_running:
            self._stop_event.set()
            if self._thread is not None:
                self._thread.join(timeout=2)
        self._remaining = 0
        self._thread = None

    def _run(self) -> None:
        while self._remaining > 0 and not self._stop_event.is_set():
            self._on_tick(self._remaining)
            if self._stop_event.wait(timeout=1.0):
                break
            self._remaining -= 1

        if self._remaining <= 0 and not self._stop_event.is_set():
            self._on_tick(0)
            self._on_expire()
