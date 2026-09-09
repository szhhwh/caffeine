import threading

import pytest

from caffeine import core

AWAKE_FLAGS = core.ES_CONTINUOUS | core.ES_SYSTEM_REQUIRED | core.ES_DISPLAY_REQUIRED
SYSTEM_ONLY_FLAGS = core.ES_CONTINUOUS | core.ES_SYSTEM_REQUIRED


def test_keep_awake_requests_display_and_system(monkeypatch):
    applied: list[int] = []
    monkeypatch.setattr(core, "_apply_state", applied.append)

    core.keep_awake()

    assert applied == [AWAKE_FLAGS]


def test_keep_system_awake_keeps_display_off(monkeypatch):
    applied: list[int] = []
    monkeypatch.setattr(core, "_apply_state", applied.append)

    core.keep_system_awake()

    assert applied == [SYSTEM_ONLY_FLAGS]


def test_allow_sleep_clears_all_requests(monkeypatch):
    applied: list[int] = []
    monkeypatch.setattr(core, "_apply_state", applied.append)

    core.allow_sleep()

    assert applied == [core.ES_CONTINUOUS]


def test_state_changes_run_on_a_single_dedicated_thread(monkeypatch):
    worker_threads: set[int] = set()
    monkeypatch.setattr(
        core, "_apply_state", lambda flags: worker_threads.add(threading.get_ident())
    )

    core.keep_awake()
    core.keep_system_awake()
    core.allow_sleep()

    assert len(worker_threads) == 1
    assert threading.get_ident() not in worker_threads


def test_state_set_from_background_thread_lands_on_same_worker(monkeypatch):
    worker_threads: set[int] = set()
    monkeypatch.setattr(
        core, "_apply_state", lambda flags: worker_threads.add(threading.get_ident())
    )

    core.keep_awake()
    other = threading.Thread(target=core.allow_sleep)
    other.start()
    other.join(timeout=5)

    assert not other.is_alive()
    assert len(worker_threads) == 1


def test_apply_failure_propagates_and_worker_survives(monkeypatch):
    calls: list[int] = []

    def flaky(flags: int) -> None:
        calls.append(threading.get_ident())
        if len(calls) == 1:
            raise RuntimeError("boom")

    monkeypatch.setattr(core, "_apply_state", flaky)

    with pytest.raises(RuntimeError, match="boom"):
        core.allow_sleep()

    core.keep_awake()
    assert len(calls) == 2
    assert calls[0] == calls[1]
