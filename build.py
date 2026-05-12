import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
MAIN = ROOT / "main.py"
ICON_DIR = ROOT / "assets"


def build() -> None:
    DIST.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=Caffeine",
        "--distpath",
        str(DIST),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT),
        str(MAIN),
    ]

    icon_path = ICON_DIR / "app.ico"
    if icon_path.exists():
        cmd.insert(-1, f"--icon={icon_path}")

    print("Building Caffeine.exe ...")
    subprocess.run(cmd, check=True)
    print(f"Done: {DIST / 'Caffeine.exe'}")


if __name__ == "__main__":
    build()
