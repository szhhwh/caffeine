import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "inject_version.py"

SAMPLE = """#define MyAppName "Caffeine"
#define MyAppVersion "0.0.0"
#define MyAppExeName "Caffeine.exe"

[Setup]
AppVersion={#MyAppVersion}
OutputBaseFilename=Caffeine_Setup_{#MyAppVersion}_x64
"""


def load_script():
    spec = importlib.util.spec_from_file_location("inject_version", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["inject_version"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def inject_version():
    return load_script().inject_version


def test_inject_replaces_placeholder(tmp_path, inject_version):
    iss = tmp_path / "installer.iss"
    iss.write_text(SAMPLE, encoding="utf-8")
    inject_version(iss, "1.2.0")
    content = iss.read_text(encoding="utf-8")
    assert '#define MyAppVersion "1.2.0"' in content
    assert "Caffeine_Setup_{#MyAppVersion}_x64" in content


def test_inject_replaces_any_existing_version(tmp_path, inject_version):
    iss = tmp_path / "installer.iss"
    iss.write_text(SAMPLE.replace("0.0.0", "9.9.9"), encoding="utf-8")
    inject_version(iss, "1.2.0")
    assert '#define MyAppVersion "1.2.0"' in iss.read_text(encoding="utf-8")


def test_inject_fails_without_define(tmp_path, inject_version):
    iss = tmp_path / "installer.iss"
    iss.write_text('#define MyAppName "Caffeine"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="found 0"):
        inject_version(iss, "1.2.0")
