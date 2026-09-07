import json

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
