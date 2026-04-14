import os
import subprocess
import shutil
import sys
import json

def build():
    config_dir = 'config'

    keys_path = os.path.join(config_dir, 'keys.json')
    fresh_keys = {
        "GOOGLE_API_KEY": "",
        "GROQ_API_KEY": "",
        "UNCLOSE_API_KEY": "",
        "OPENROUTE_API_KEY": "",
        "GITHUB_TOKEN": ""
    }
    with open(keys_path, 'w') as f:
        json.dump(fresh_keys, f, indent=4)

    memory_path = os.path.join(config_dir, 'memory.txt')
    with open(memory_path, 'w') as f:
        f.write("")

    settings_path = os.path.join(config_dir, 'settings.json')
    fresh_settings = {
        "provider": "GitHubAI",
        "model": "openai/gpt-4o",
        "mode": "FAST"
    }
    with open(settings_path, 'w') as f:
        json.dump(fresh_settings, f, indent=4)

    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    try:
        os.remove('main.spec')
    except OSError:
        pass

    print("Starting build process...")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--windows-disable-console",
        f"--windows-icon-from-ico={os.path.abspath('assets/logo.ico')}",
        "--enable-plugin=tk-inter",
        "--include-data-dir=assets=assets",
        "--include-data-dir=config=config",
        "--output-dir=dist",
        "--remove-output",
        "--no-pyi-file",
        "--onefile-tempdir-spec={CACHE_DIR}/PromptOS",
        "--onefile-no-compression",
        "main.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("Build complete. Executable is located in the 'dist' folder.")

if __name__ == "__main__":
    build()
