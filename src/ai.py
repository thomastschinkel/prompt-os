import platform
import json
from groq import Groq
from openai import OpenAI
import os
import getpass
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = PROJECT_ROOT / "config" / "prompt.txt"
KEYS_PATH = PROJECT_ROOT / "config" / "keys.json"
MEMORY_PATH = PROJECT_ROOT / "config" / "memory.txt"

class LLM():
    def __init__(self, model_provider):
        self.model_provider = model_provider
        self.history = []

    def generate_response(self, user_prompt, validate_response=False, output=None):
        with open(PROMPT_PATH, 'r', encoding='utf-8') as file:
            system_instructions = file.read()

        with open(MEMORY_PATH, 'r', encoding='utf-8') as mem_file:
            memory = mem_file.read().strip()

        if not self.history:
            user_message = f"This is the initial message from the user, you have to strictly follow this: {user_prompt}"
            self.history.append({"role": "system", "content": f"Those are the system instructions, you have to follow what's inside here: {system_instructions}"})
            self.history.append({"role": "system", "content": f"Here are some system information from the user: OS: {platform.system()} | Arch: {platform.machine()} | Host-Name: {platform.node()} | CWD: {os.getcwd()} | User: {getpass.getuser()} | Local-IP: {socket.gethostbyname(platform.node())}"})
            self.history.append({"role": "system", "content": f"Here is your permanently saved memory from past conversations with the user: {memory}"})
            self.history.append({"role": "user", "content": user_message})

        if validate_response and output is not None:
            self.history.append({"role": "user", "content": f"Command output: {output}"})

        with open(KEYS_PATH, 'r', encoding='utf-8') as keys_file:
            keys = json.load(keys_file)

        model_name = None
        if self.model_provider == "Groq":
            client = Groq(api_key=keys.get("GROQ_API_KEY"))
            model_name = "llama-3.3-70b-versatile"
        elif self.model_provider == "GitHubAI":
            client = OpenAI(base_url="https://models.github.ai/inference", api_key=keys.get("GITHUB_TOKEN"))
            model_name = "openai/gpt-4o-mini"
        elif self.model_provider == "OpenRoute":
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=keys.get("OPENROUTE_API_KEY"))
            model_name = "qwen/qwen3.6-plus:free"
        elif self.model_provider == "Unclose":
            client = OpenAI(base_url="https://qwen-vl.ai.unturf.com/v1/", api_key="is_free")
            model_name = "deepseek-r1:14b-qwen-distill-q8_0"
        try:
            completions = client.chat.completions.create(
                messages=[
                    *self.history
                ],
                model=model_name
            )
            raw = completions.choices[0].message.content
        except Exception as e:
            return {"tool": "CMD",
                    "input": "",
                    "response": f"Error with API\n{e}",
                    "status": "y"}
        print(raw)
        self.history.append({"role": "assistant", "content": raw})
        return json.loads(raw.replace("`", "").strip())