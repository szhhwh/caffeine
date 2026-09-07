import os
import re
from pathlib import Path

_VERSION_PATTERN = re.compile(r'#define MyAppVersion "[^"]*"')


def inject_version(path: Path, version: str) -> None:
    content = path.read_text(encoding="utf-8")
    content, count = _VERSION_PATTERN.subn(f'#define MyAppVersion "{version}"', content)
    if count != 1:
        raise ValueError(
            f"expected exactly one MyAppVersion define in {path}, found {count}"
        )
    path.write_text(content, encoding="utf-8")
    print(f"Injected version: {version}")


if __name__ == "__main__":
    version = os.environ["VERSION"]
    inject_version(Path("installer.iss"), version)
