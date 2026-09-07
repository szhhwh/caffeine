import threading

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
