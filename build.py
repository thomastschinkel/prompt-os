import os
import subprocess
import shutil
import sys

def build():
    # Clean previous builds
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            
    try:
        os.remove('main.spec')
    except OSError:
        pass

    print("Starting build process...")
    
    # Run PyInstaller with optimizations for size
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "PromptOS",
        "--add-data", "assets;assets/",
        "--add-data", "config;config/",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PyQt5",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "pytest",
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "pandas",
        "--exclude-module", "tensorflow",
        "main.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("Build complete. Executable is located in the 'dist/PromptOS' folder.")

if __name__ == "__main__":
    build()
