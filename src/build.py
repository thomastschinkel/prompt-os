import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
entry = project_root / "main.py"
icon = project_root / "assets" / "Basic_red_dot.png"
name = project_root.name

command = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--windowed",
    "--name",
    name,
    "--noconfirm",
    str(entry),
]

if icon.exists():
    command.extend(["--icon", str(icon)])

subprocess.run(command, check=True)
print(f"Done: {project_root / 'dist' / (name + '.exe')}")

