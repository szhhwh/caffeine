import threading
import time

from caffeine.timer import Timer


def _make_timer() -> tuple[Timer, threading.Event, list[int]]:
    expired = threading.Event()
    ticks: list[int] = []
    timer = Timer(on_expire=expired.set, on_tick=ticks.append)
    return timer, expired, ticks


def test_start_sets_remaining():
    timer, _, _ = _make_timer()
    timer.start(30)
    try:
        assert timer.is_running
        assert timer.remaining == 1800
    finally:
        timer.cancel()


def test_cancel_stops_timer():
    timer, expired, _ = _make_timer()
    timer.start(30)
    timer.cancel()
    assert not timer.is_running
    assert timer.remaining == 0
    assert not expired.is_set()


def test_cancel_before_start_is_noop():
    timer, _, _ = _make_timer()
    timer.cancel()
    assert not timer.is_running
    assert timer.remaining == 0


def test_resume_counts_down_saved_seconds():
    timer, expired, ticks = _make_timer()
    timer.resume(2)
    assert expired.wait(timeout=5)
    assert not timer.is_running
    assert timer.remaining == 0
    assert ticks == [2, 1, 0]


def test_resume_zero_expires_immediately():
    timer, expired, ticks = _make_timer()
    timer.resume(0)
    assert expired.wait(timeout=5)
    assert ticks == [0]
    assert not timer.is_running


def test_restart_replaces_previous_countdown():
    timer, _, _ = _make_timer()
    timer.start(120)
    timer.resume(3)
    try:
        assert timer.remaining == 3
    finally:
        timer.cancel()


def test_cancel_clears_thread_references():
    timer, _, _ = _make_timer()
    timer.start(5)
    timer.cancel()
    assert timer._thread is None
    assert timer._stop_event is None


def test_each_run_uses_its_own_stop_event():
    timer, expired, _ = _make_timer()
    timer.resume(1)
    first = timer._stop_event
    timer.cancel()
    assert first is not None
    assert first.is_set()

    timer.resume(1)
    assert timer._stop_event is not first
    assert timer._stop_event is not None
    assert not timer._stop_event.is_set()

    assert expired.wait(timeout=5)
    timer.cancel()


def test_cancel_with_blocked_tick_does_not_resurrect_old_thread():
    release = threading.Event()
    first_tick = threading.Event()
    expire_calls: list[int] = []

    def on_tick(remaining: int) -> None:
        if not first_tick.is_set():
            first_tick.set()
            release.wait(timeout=10)

    timer = Timer(on_expire=lambda: expire_calls.append(1), on_tick=on_tick)
    timer.resume(2)
    assert first_tick.wait(timeout=5)

    timer.cancel()
    timer.resume(1)

    release.set()

    assert timer.is_running
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not expire_calls:
        time.sleep(0.02)

    assert expire_calls == [1]
    assert timer.remaining == 0
