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

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--icon={os.path.abspath('assets/logo.ico')}",
        "--add-data=assets;assets",
        "--add-data=config;config",
        "--name=PromptOS",
        "--clean",
        "main.py"
    ]

    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    build()
