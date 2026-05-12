import subprocess
import sys
from pathlib import Path

from caffeine.icon import create_ico

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
MAIN = ROOT / "main.py"
ICON_DIR = ROOT / "assets"


def build() -> None:
    DIST.mkdir(exist_ok=True)
    ICON_DIR.mkdir(exist_ok=True)

    ico_path = ICON_DIR / "app.ico"
    if not ico_path.exists():
        print("Generating app.ico ...")
        create_ico(ico_path)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=Caffeine",
        "--icon=" + str(ico_path),
        "--distpath",
        str(DIST),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT),
        str(MAIN),
    ]

    print("Building Caffeine.exe ...")
    subprocess.run(cmd, check=True)
    print(f"Done: {DIST / 'Caffeine.exe'}")


if __name__ == "__main__":
    build()
