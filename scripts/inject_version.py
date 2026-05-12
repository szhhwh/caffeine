import os
from pathlib import Path

def inject_version(path: Path, version: str) -> None:
    content = path.read_text(encoding="utf-8")
    content = content.replace(
        '#define MyAppVersion "1.0.0"',
        f'#define MyAppVersion "{version}"',
    )
    path.write_text(content, encoding="utf-8")
    print(f"Injected version: {version}")

if __name__ == "__main__":
    version = os.environ["VERSION"]
    inject_version(Path("installer.iss"), version)