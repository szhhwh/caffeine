from pathlib import Path

import pystray

from caffeine import autostart, core
from caffeine.config import Config
from caffeine.icon import create_icon
from caffeine.timer import Timer


class TrayApp:
    INFINITE = "infinite"
    TIMED_30 = "timed_30"
    TIMED_60 = "timed_60"
    TIMED_120 = "timed_120"
    SYSTEM_ONLY = "system_only"

    _TIMED_MODES = {
        TIMED_30: 30,
        TIMED_60: 60,
        TIMED_120: 120,
    }

    _TIMED_LABELS = {
        TIMED_30: "30 \u5206\u949f",
        TIMED_60: "1 \u5c0f\u65f6",
        TIMED_120: "2 \u5c0f\u65f6",
    }

    _ALL_MODES = (INFINITE, SYSTEM_ONLY, TIMED_30, TIMED_60, TIMED_120)

    def __init__(self, config_path: Path | None = None) -> None:
        self._active = False
        self._mode: str | None = None
        self._timer = Timer(
            on_expire=self._on_timer_expire, on_tick=self._on_timer_tick
        )
        self._config = Config(config_path)
        self._load_last_mode()
        self._tray = pystray.Icon(
            name="Caffeine",
            icon=create_icon(active=False),
            title="Caffeine - \u672a\u6fc0\u6d3b",
            menu=self._build_menu(),
        )

    def _load_last_mode(self) -> None:
        saved = self._config.load()
        mode = saved.get("mode")
        self._last_mode: str | None = mode if mode in self._ALL_MODES else None
        self._last_remaining: int | None = self._valid_remaining(saved.get("remaining"))

    @staticmethod
    def _valid_remaining(value: object) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        return value

    def run(self) -> None:
        self._tray.run()

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                "\u5f00\u542f/\u5173\u95ed",
                self._on_left_click,
                default=True,
                visible=False,
            ),
            pystray.MenuItem(
                "\u221e \u65e0\u9650\u6a21\u5f0f",
                self._toggle_infinite,
                checked=lambda _: self._mode == self.INFINITE,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "\u25b6 \u5b9a\u65f6\u6a21\u5f0f",
                pystray.Menu(
                    *[
                        pystray.MenuItem(
                            self._TIMED_LABELS[key],
                            lambda _, k=key: self._activate_timed(k),
                            checked=lambda _, k=key: self._mode == k,
                        )
                        for key in self._TIMED_MODES
                    ]
                ),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "\u5141\u8bb8\u7184\u5c4f",
                self._toggle_system_only,
                checked=lambda _: self._mode == self.SYSTEM_ONLY,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "\u5f00\u673a\u81ea\u542f\u52a8",
                self._toggle_autostart,
                checked=lambda _: autostart.is_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("\u9000\u51fa", self._quit),
        )

    def _on_left_click(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self._active:
            self._deactivate()
        else:
            self._activate_last_mode()

    def _activate_last_mode(self) -> None:
        mode = self._last_mode or self.INFINITE
        self._last_mode = mode
        if mode in self._TIMED_MODES:
            self._mode = mode
            self._last_remaining = self._resume_seconds(mode)
            self._activate()
            self._timer.resume(self._last_remaining)
        elif mode == self.SYSTEM_ONLY:
            self._cancel_timer()
            self._mode = self.SYSTEM_ONLY
            self._last_remaining = None
            self._activate_system_only()
        else:
            self._cancel_timer()
            self._mode = self.INFINITE
            self._last_remaining = None
            self._activate()

    def _resume_seconds(self, mode: str) -> int:
        full = self._TIMED_MODES[mode] * 60
        remaining = self._last_remaining
        if remaining is not None and 0 < remaining < full:
            return remaining
        return full

    def _toggle_infinite(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self._mode == self.INFINITE:
            self._deactivate()
        else:
            self._cancel_timer()
            self._mode = self.INFINITE
            self._last_mode = self.INFINITE
            self._last_remaining = None
            self._activate()

    def _toggle_system_only(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self._mode == self.SYSTEM_ONLY:
            self._deactivate()
        else:
            self._cancel_timer()
            self._mode = self.SYSTEM_ONLY
            self._last_mode = self.SYSTEM_ONLY
            self._last_remaining = None
            self._activate_system_only()

    def _activate_timed(self, mode: str) -> None:
        self._cancel_timer()
        self._mode = mode
        self._last_mode = mode
        self._last_remaining = self._TIMED_MODES[mode] * 60
        self._activate()
        self._timer.start(self._TIMED_MODES[mode])

    def _activate(self) -> None:
        self._active = True
        core.keep_awake()
        self._update_icon()
        self._persist()

    def _activate_system_only(self) -> None:
        self._active = True
        core.keep_system_awake()
        self._update_icon()
        self._persist()

    def _deactivate(self) -> None:
        self._active = False
        if self._mode in self._TIMED_MODES and self._timer.is_running:
            self._last_remaining = self._timer.remaining
        self._mode = None
        self._cancel_timer()
        core.allow_sleep()
        self._update_icon()
        self._persist()

    def _cancel_timer(self) -> None:
        self._timer.cancel()

    def _on_timer_expire(self) -> None:
        self._active = False
        self._mode = None
        self._last_remaining = 0
        core.allow_sleep()
        self._update_icon()
        self._persist()

    def _on_timer_tick(self, remaining: int) -> None:
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            self._tray.title = f"Caffeine - \u5269\u4f59 {mins:02d}:{secs:02d}"
        else:
            self._tray.title = "Caffeine - \u672a\u6fc0\u6d3b"

    def _toggle_autostart(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if autostart.is_enabled():
            autostart.disable()
        else:
            autostart.enable()

    def _update_icon(self) -> None:
        self._tray.icon = create_icon(active=self._active)
        self._tray.title = (
            "Caffeine - \u6d3b\u8dc3\u4e2d"
            if self._active
            else "Caffeine - \u672a\u6fc0\u6d3b"
        )

    def _persist(self) -> None:
        self._config.save(self._last_mode, self._last_remaining)

    def _quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._deactivate()
        icon.stop()
