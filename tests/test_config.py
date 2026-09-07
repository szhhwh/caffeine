from pathlib import Path

from caffeine.config import Config, default_path


def test_load_missing_file_returns_empty(tmp_path):
    assert Config(tmp_path / "missing.json").load() == {}


def test_save_and_load_roundtrip(tmp_path):
    config = Config(tmp_path / "nested" / "config.json")
    config.save("timed_30", 1234)
    assert config.load() == {"mode": "timed_30", "remaining": 1234}


def test_save_none_values_roundtrip(tmp_path):
    config = Config(tmp_path / "config.json")
    config.save(None, None)
    assert config.load() == {"mode": None, "remaining": None}


def test_load_invalid_json_returns_empty(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    assert Config(path).load() == {}


def test_load_non_dict_returns_empty(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert Config(path).load() == {}


def test_save_swallows_unwritable_path(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    Config(blocker / "config.json").save("infinite", None)


def test_default_path_uses_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_path() == tmp_path / "Caffeine" / "config.json"


def test_default_path_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    assert default_path() == Path.home() / ".config" / "caffeine" / "config.json"
