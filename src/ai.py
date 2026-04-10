import platform
import json
from groq import Groq
from openai import OpenAI
import os
import getpass
import socket
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = PROJECT_ROOT / "config" / "prompt.txt"
KEYS_PATH = PROJECT_ROOT / "config" / "keys.json"
MEMORY_PATH = PROJECT_ROOT / "config" / "memory.txt"

class LLM():
    def __init__(self, provider, model_name):
        self.provider = provider
        self.model_name = model_name
        self.history = []

        with open(KEYS_PATH, 'r', encoding='utf-8') as keys_file:
            self.keys = json.load(keys_file)

    def generate_response(self, user_prompt, validate_response=False, output=None):
        if not self.history:
            with open(MEMORY_PATH, 'r', encoding='utf-8') as mem_file:
                memory = mem_file.read().strip()

            with open(PROMPT_PATH, 'r', encoding='utf-8') as file:
                system_instructions = file.read()

            user_message = f"This is the initial message from the user, you have to strictly follow this: {user_prompt}"
            self.history.append({"role": "system", "content": f"Those are the system instructions, you have to follow what's inside here: {system_instructions}"})
            self.history.append({"role": "system", "content": f"Here are some system information from the user: OS: {platform.system()} | Arch: {platform.machine()} | Host-Name: {platform.node()} | CWD: {os.getcwd()} | User: {getpass.getuser()} | Local-IP: {socket.gethostbyname(platform.node())}"})
            self.history.append({"role": "system", "content": f"Here is your permanently saved memory from past conversations with the user: {memory}"})
            self.history.append({"role": "user", "content": user_message})

        if validate_response and output is not None:
            self.history.append({"role": "user", "content": f"Command output: {output}"})

        client = None
        if self.provider == "Groq":
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=self.keys.get("GROQ_API_KEY"))
        elif self.provider == "GitHubAI":
            client = OpenAI(base_url="https://models.github.ai/inference", api_key=self.keys.get("GITHUB_TOKEN"))
        elif self.provider == "OpenRoute":
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.keys.get("OPENROUTE_API_KEY"))
        elif self.provider == "Unclose":
            client = OpenAI(base_url="https://qwen-vl.ai.unturf.com/v1/", api_key="is_free")
        elif self.provider == "OpenAI":
            client = OpenAI(api_key=self.keys.get("OPENAI_API_KEY"))
        elif self.provider == "Anthropic":
            client = OpenAI(base_url="https://api.anthropic.com/v1/", api_key=self.keys.get("ANTHROPIC_API_KEY"))
        
        if not client:
             return {"tool": "CMD", "input": "", "response": "Invalid Provider", "status": "y"}

        try:
            completions = client.chat.completions.create(
                messages=[
                    *self.history
                ],
                model=self.model_name,
            )
            raw = completions.choices[0].message.content
            raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        except Exception as e:
            return {"tool": "CMD",
                    "input": "",
                    "response": f"Error with API\n{e}",
                    "status": "y"}
        try:
            json_match = re.search(r'({.*})', raw, re.DOTALL)
            if json_match:
                raw = json_match.group(1)
        
            self.history.append({"role": "assistant", "content": raw})
            return json.loads(raw.replace("`", "").strip())
        except Exception as e:
            return {"tool": "CMD",
                    "input": "",
                    "response": f"Error with JSON parsing\n{e}",
                    "status": "y"}