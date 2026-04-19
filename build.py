import os
import subprocess
import shutil
import sys
import json

def build():
    config_dir = 'config'
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    keys_path = os.path.join(config_dir, 'keys.json')
    fresh_keys = {
        "GOOGLE_API_KEY": "",
        "GROQ_API_KEY": "",
        "UNCLOSE_API_KEY": "",
        "OPENROUTE_API_KEY": "",
        "GITHUB_TOKEN": "",
        "ANTHROPIC_API_KEY": "",
        "OPENAI_API_KEY": "",
        "OLLAMA_API_KEY": "",
        "LMSTUDIO_API_KEY": ""
    }
    with open(keys_path, 'w', encoding='utf-8') as f:
        json.dump(fresh_keys, f, indent=4)

    memory_path = os.path.join(config_dir, 'memory.txt')
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write("")

    chats_dir = os.path.join(config_dir, 'chats')
    os.makedirs(chats_dir, exist_ok=True)

    settings_path = os.path.join(config_dir, 'settings.json')
    fresh_settings = {
        "provider": "GitHubAI",
        "model": "openai/gpt-4o-mini",
        "mode": "FAST",
        "ollama_base_url": "http://localhost:11434/v1",
        "lmstudio_base_url": "http://localhost:1234/v1",
        "enabled_tools": ["BASH", "POWERSHELL", "FILE_HANDLER", "EXEC_PY", "SEARCH_WEB", "READ_FILE", "USE_BROWSER",
                          "CLIPBOARD_MANAGER", "INTERPRET_SCREENSHOT", "GLOB", "GREP"]
    }
    with open(settings_path, 'w', encoding='utf-8') as f:
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
