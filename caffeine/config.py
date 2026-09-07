import json
import os
from pathlib import Path


def default_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Caffeine" / "config.json"
    return Path.home() / ".config" / "caffeine" / "config.json"


class Config:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else default_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict:
        try:
            with self._path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, mode: str | None, remaining: int | None) -> None:
        data = {"mode": mode, "remaining": remaining}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass
