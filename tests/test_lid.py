import ctypes
import json
from unittest import mock

import pytest

from caffeine import lid

SCHEME = "381b4222-f694-41f0-9685-ff5bb260df2e"
OTHER_SCHEME = "a1841308-3541-4fab-bc81-f71556f20b4a"


@pytest.fixture
def power(monkeypatch):
    state = {"scheme": SCHEME, "AC": 1, "DC": 2}
    writes = []
    applied = []

    def read(scheme, source):
        assert scheme == SCHEME
        return state[source]

    def write(scheme, source, value):
        assert scheme == SCHEME
        writes.append((source, value))
        state[source] = value

    monkeypatch.setattr(lid, "_active_scheme", lambda: state["scheme"])
    monkeypatch.setattr(lid, "_read_action", read)
    monkeypatch.setattr(lid, "_write_action", write)
    monkeypatch.setattr(lid, "_apply", applied.append)
    return state, writes, applied


@pytest.fixture
def blocker(tmp_path):
    return lid.LidSleepBlocker(tmp_path / "backup.json")


def test_guid_uses_windows_layout():
    assert ctypes.sizeof(lid._GUID) == 16
    assert bytes(lid._guid(SCHEME)).hex() == "22421b3894f6f0419685ff5bb260df2e"


def test_check_reports_nonzero_status():
    lid._check(0)
    with pytest.raises(OSError, match="5"):
        lid._check(5)


def test_enable_disables_lid_sleep_on_ac_and_battery(blocker, power):
    state, writes, applied = power
    blocker.enable()

    assert state["AC"] == state["DC"] == 0
    assert writes == [("AC", 0), ("DC", 0)]
    assert applied == [SCHEME]
    assert json.loads(blocker._backup_path.read_text()) == {
        "scheme": SCHEME,
        "ac": 1,
        "dc": 2,
    }


def test_repeated_enable_keeps_original_settings(blocker, power):
    blocker.enable()
    blocker.enable()
    blocker.restore()

    state, writes, _ = power
    assert state["AC"] == 1
    assert state["DC"] == 2
    assert writes == [("AC", 0), ("DC", 0), ("AC", 1), ("DC", 2)]
    assert not blocker._backup_path.exists()


def test_restore_without_backup_does_not_access_power_settings(blocker, power):
    blocker.restore()
    _, writes, applied = power
    assert writes == applied == []


def test_restart_recovers_original_settings(blocker, power):
    blocker.enable()
    restarted = lid.LidSleepBlocker(blocker._backup_path)
    restarted.restore()

    state, _, _ = power
    assert state["AC"] == 1
    assert state["DC"] == 2
    assert not blocker._backup_path.exists()


def test_enable_recovers_interrupted_session_before_saving(blocker, power):
    blocker.enable()
    restarted = lid.LidSleepBlocker(blocker._backup_path)
    restarted.enable()
    restarted.restore()

    state, _, _ = power
    assert state["AC"] == 1
    assert state["DC"] == 2


def test_restore_preserves_manual_changes(blocker, power):
    state, _, _ = power
    blocker.enable()
    state["AC"] = 3
    blocker.restore()

    assert state["AC"] == 3
    assert state["DC"] == 2


def test_read_failure_does_not_change_settings(blocker, power, monkeypatch):
    monkeypatch.setattr(lid, "_read_action", mock.Mock(side_effect=OSError("read")))
    with pytest.raises(OSError, match="read"):
        blocker.enable()

    _, writes, applied = power
    assert writes == applied == []
    assert not blocker._backup_path.exists()


def test_backup_failure_does_not_change_settings(blocker, power):
    blocker._backup_path.mkdir()
    with pytest.raises(OSError):
        blocker.enable()

    _, writes, applied = power
    assert writes == applied == []


def test_partial_write_failure_rolls_back(blocker, power, monkeypatch):
    write = lid._write_action

    def fail_dc(scheme, source, value):
        if source == "DC" and value == 0:
            raise OSError("write")
        write(scheme, source, value)

    monkeypatch.setattr(lid, "_write_action", fail_dc)
    with pytest.raises(OSError, match="write"):
        blocker.enable()

    state, _, _ = power
    assert state["AC"] == 1
    assert state["DC"] == 2
    assert not blocker._backup_path.exists()


def test_apply_failure_rolls_back(blocker, power, monkeypatch):
    apply = mock.Mock(side_effect=[OSError("apply"), None])
    monkeypatch.setattr(lid, "_apply", apply)
    with pytest.raises(OSError, match="apply"):
        blocker.enable()

    state, _, _ = power
    assert state["AC"] == 1
    assert state["DC"] == 2
    assert not blocker._backup_path.exists()


def test_failed_enable_can_be_retried_after_failed_rollback(
    blocker, power, monkeypatch
):
    with monkeypatch.context() as patch:
        patch.setattr(lid, "_apply", mock.Mock(side_effect=OSError("apply")))
        with pytest.raises(OSError):
            blocker.enable()
    assert blocker._backup_path.exists()
    blocker.enable()
    state, _, _ = power
    assert state["AC"] == state["DC"] == 0
    blocker.restore()
    assert state["AC"] == 1
    assert state["DC"] == 2


def test_failed_restore_retains_backup_for_retry(blocker, power, monkeypatch):
    blocker.enable()
    with monkeypatch.context() as patch:
        patch.setattr(lid, "_apply", mock.Mock(side_effect=OSError("restore")))
        with pytest.raises(OSError, match="restore"):
            blocker.restore()

    assert blocker._backup_path.exists()
    blocker.restore()
    assert not blocker._backup_path.exists()
    state, _, _ = power
    assert state["AC"] == 1
    assert state["DC"] == 2


@pytest.mark.parametrize(
    "data",
    [
        "{ broken",
        "[]",
        "null",
        "{}",
        json.dumps({"scheme": "bad", "ac": 1, "dc": 2}),
        json.dumps({"scheme": SCHEME, "ac": True, "dc": 2}),
        json.dumps({"scheme": SCHEME, "ac": 1, "dc": 4}),
    ],
)
def test_invalid_backup_is_reported_without_writing(blocker, power, data):
    blocker._backup_path.write_text(data, encoding="utf-8")
    with pytest.raises(OSError, match="Invalid lid settings backup"):
        blocker.restore()
    _, writes, _ = power
    assert writes == []


def test_apply_does_not_switch_to_previous_plan(monkeypatch):
    monkeypatch.setattr(lid, "_active_scheme", lambda: OTHER_SCHEME)
    api = mock.Mock()
    monkeypatch.setattr(lid, "_power", api)

    lid._apply(SCHEME)
    api.PowerSetActiveScheme.assert_not_called()


def test_apply_reactivates_current_plan(monkeypatch):
    monkeypatch.setattr(lid, "_active_scheme", lambda: SCHEME)
    api = mock.Mock()
    api.PowerSetActiveScheme.return_value = 0
    monkeypatch.setattr(lid, "_power", api)

    lid._apply(SCHEME)
    api.PowerSetActiveScheme.assert_called_once()
