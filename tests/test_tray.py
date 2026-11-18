import json
from unittest import mock

import pystray
import pytest

from caffeine.tray import TrayApp

FULL_30 = 30 * 60
FULL_60 = 60 * 60


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "config.json"


@pytest.fixture
def app(config_path, awake):
    application = TrayApp(config_path)
    try:
        yield application
    finally:
        application._timer.cancel()


def click(instance: TrayApp) -> None:
    instance._on_left_click(None, None)


def test_left_click_uses_infinite_by_default(app, awake):
    click(app)
    assert app._active
    assert app._mode == TrayApp.INFINITE
    assert app._last_mode == TrayApp.INFINITE
    assert awake == ["keep_awake"]

    click(app)
    assert not app._active
    assert app._mode is None
    assert app._last_mode == TrayApp.INFINITE
    assert awake == ["keep_awake", "allow_sleep"]


def test_left_click_persists_mode_to_config(app, config_path):
    click(app)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data == {"mode": "infinite", "remaining": None}


def test_left_click_resumes_timed_remaining(app):
    app._activate_timed(TrayApp.TIMED_30)
    assert app._active

    click(app)
    assert not app._active
    assert app._last_mode == TrayApp.TIMED_30
    assert 0 < app._last_remaining <= FULL_30

    click(app)
    assert app._active
    assert app._mode == TrayApp.TIMED_30
    assert app._timer.is_running
    assert 0 < app._timer.remaining <= app._last_remaining


def test_timed_mode_survives_restart(config_path, awake):
    first = TrayApp(config_path)
    first._activate_timed(TrayApp.TIMED_60)
    first._on_left_click(None, None)
    first._timer.cancel()

    second = TrayApp(config_path)
    try:
        assert second._last_mode == TrayApp.TIMED_60
        assert FULL_60 - 2 <= second._last_remaining <= FULL_60

        second._on_left_click(None, None)
        assert second._active
        assert second._mode == TrayApp.TIMED_60
        assert second._timer.is_running
        assert FULL_60 - 2 <= second._timer.remaining <= FULL_60
    finally:
        second._timer.cancel()


def test_expired_timed_mode_restores_full_duration(config_path):
    config_path.write_text(
        json.dumps({"mode": "timed_30", "remaining": 0}), encoding="utf-8"
    )
    app = TrayApp(config_path)
    try:
        app._on_left_click(None, None)
        assert app._active
        assert app._mode == TrayApp.TIMED_30
        assert FULL_30 - 2 <= app._timer.remaining <= FULL_30
    finally:
        app._timer.cancel()


def test_stale_remaining_is_clamped_to_full_duration(config_path):
    config_path.write_text(
        json.dumps({"mode": "timed_30", "remaining": 999999}),
        encoding="utf-8",
    )
    app = TrayApp(config_path)
    try:
        app._on_left_click(None, None)
        assert app._timer.remaining <= FULL_30
    finally:
        app._timer.cancel()


def test_invalid_config_falls_back_to_infinite(config_path):
    config_path.write_text(
        json.dumps({"mode": "bogus", "remaining": "soon"}), encoding="utf-8"
    )
    app = TrayApp(config_path)
    assert app._last_mode is None
    assert app._last_remaining is None


def test_corrupt_config_is_ignored(config_path):
    config_path.write_text("{ broken", encoding="utf-8")
    app = TrayApp(config_path)
    assert app._last_mode is None


def test_system_only_mode_is_restored(app, awake):
    app._toggle_system_only(None, None)
    assert app._active

    click(app)
    assert not app._active
    assert app._last_mode == TrayApp.SYSTEM_ONLY

    click(app)
    assert app._active
    assert app._mode == TrayApp.SYSTEM_ONLY
    assert awake == [
        "keep_system_awake",
        "allow_sleep",
        "keep_system_awake",
    ]


def test_timer_expire_resets_remaining_for_next_restore(app):
    app._activate_timed(TrayApp.TIMED_30)
    app._on_timer_expire()
    assert not app._active
    assert app._last_mode == TrayApp.TIMED_30
    assert app._last_remaining == 0

    click(app)
    assert app._active
    assert FULL_30 - 2 <= app._timer.remaining <= FULL_30


def test_menu_has_hidden_default_toggle(app):
    menu = app._build_menu()
    (default_item,) = [item for item in menu.items if item.default]
    assert not default_item.visible


def test_hidden_toggle_not_in_visible_menu(app):
    menu = app._build_menu()
    visible = [item.text for item in menu]
    assert "开启/关闭" not in visible
    assert visible[0] == "∞ 无限模式"


def test_menu_default_action_toggles(app, awake):
    app._build_menu()(None)
    assert app._active
    assert awake == ["keep_awake"]


def test_lid_option_is_in_same_group_as_system_only(app):
    items = list(app._build_menu().items)
    index = next(i for i, item in enumerate(items) if item.text == "允许熄屏")
    assert items[index + 1].text == "阻止关盖睡眠"
    assert items[index + 2].text == pystray.Menu.SEPARATOR.text


def test_lid_mode_toggles_and_restores_settings(app, awake, mock_lid_settings):
    mock_lid_settings.reset_mock()
    app._toggle_block_lid_sleep(None, None)
    assert app._active
    assert app._mode == TrayApp.BLOCK_LID_SLEEP
    assert awake == ["keep_system_awake"]
    mock_lid_settings.enable.assert_called_once()
    assert not app._timer.is_running

    app._toggle_block_lid_sleep(None, None)
    assert not app._active
    assert app._mode is None
    assert awake == ["keep_system_awake", "allow_sleep"]
    mock_lid_settings.restore.assert_called_once()


def test_lid_mode_remembers_last_mode(app, awake, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    click(app)
    click(app)
    assert app._active
    assert app._mode == TrayApp.BLOCK_LID_SLEEP
    assert mock_lid_settings.enable.call_count == 2
    assert awake == ["keep_system_awake", "allow_sleep", "keep_system_awake"]


def test_lid_mode_survives_restart(app, config_path, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    click(app)
    restarted = TrayApp(config_path)
    assert not restarted._active
    assert restarted._last_mode == TrayApp.BLOCK_LID_SLEEP
    click(restarted)
    assert restarted._mode == TrayApp.BLOCK_LID_SLEEP


def test_startup_recovers_lid_settings(app, mock_lid_settings):
    icon = mock.Mock()
    app._on_tray_ready(icon)
    assert icon.visible
    mock_lid_settings.restore.assert_called_once()


def test_startup_restore_failure_is_reported_after_tray_is_visible(
    app, mock_lid_settings
):
    mock_lid_settings.restore.side_effect = OSError("denied")
    app._tray.notify = mock.Mock()
    icon = mock.Mock()
    app._on_tray_ready(icon)
    assert icon.visible
    app._tray.notify.assert_called_once()
    assert not app._active


@pytest.mark.parametrize(
    "mode",
    [
        TrayApp.INFINITE,
        TrayApp.SYSTEM_ONLY,
        TrayApp.TIMED_30,
    ],
)
def test_switching_from_lid_mode_restores_settings(app, mock_lid_settings, mode):
    app._toggle_block_lid_sleep(None, None)
    mock_lid_settings.reset_mock()
    if mode == TrayApp.INFINITE:
        app._toggle_infinite(None, None)
    elif mode == TrayApp.SYSTEM_ONLY:
        app._toggle_system_only(None, None)
    else:
        app._activate_timed(mode)
    assert app._active
    assert app._mode == mode
    mock_lid_settings.restore.assert_called_once()


def test_switching_from_timer_to_lid_mode_cancels_timer(app):
    app._activate_timed(TrayApp.TIMED_30)
    app._toggle_block_lid_sleep(None, None)
    assert not app._timer.is_running
    assert app._mode == TrayApp.BLOCK_LID_SLEEP
    assert app._last_remaining is None


def test_lid_enable_failure_preserves_current_mode(app, awake, mock_lid_settings):
    app._toggle_infinite(None, None)
    mock_lid_settings.enable.side_effect = OSError("denied")
    app._tray.notify = mock.Mock()
    app._toggle_block_lid_sleep(None, None)
    assert app._mode == TrayApp.INFINITE
    assert app._last_mode == TrayApp.INFINITE
    assert app._active
    assert awake == ["keep_awake"]
    app._tray.notify.assert_called_once()


def test_lid_restore_failure_does_not_deactivate(app, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    mock_lid_settings.restore.side_effect = OSError("denied")
    app._tray.notify = mock.Mock()
    click(app)
    assert app._active
    assert app._mode == TrayApp.BLOCK_LID_SLEEP
    app._tray.notify.assert_called_once()


def test_lid_restore_failure_does_not_switch_modes(app, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    mock_lid_settings.restore.side_effect = OSError("denied")
    app._tray.notify = mock.Mock()
    app._toggle_infinite(None, None)
    assert app._mode == TrayApp.BLOCK_LID_SLEEP
    app._tray.notify.assert_called_once()


def test_quit_restores_lid_settings_before_stopping(app, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    mock_lid_settings.reset_mock()
    icon = mock.Mock()
    app._quit(icon, None)
    mock_lid_settings.restore.assert_called_once()
    icon.stop.assert_called_once()
    assert not app._active


def test_quit_is_aborted_if_restore_fails(app, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    mock_lid_settings.restore.side_effect = OSError("denied")
    app._tray.notify = mock.Mock()
    icon = mock.Mock()
    app._quit(icon, None)
    icon.stop.assert_not_called()
    assert app._active


def test_run_cleans_up_on_unexpected_exit(app, mock_lid_settings):
    app._toggle_block_lid_sleep(None, None)
    mock_lid_settings.reset_mock()
    app._tray.run = mock.Mock(side_effect=RuntimeError("tray error"))
    with pytest.raises(RuntimeError, match="tray error"):
        app.run()
    mock_lid_settings.restore.assert_called_once()
    assert not app._active
