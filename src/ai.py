import platform
import json
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

            system_content = f"""Those are the system instructions, you have to follow what's inside here: {system_instructions}
            System information: OS: {platform.system()} | Arch: {platform.machine()} | Host-Name: {platform.node()} | CWD: {os.getcwd()} | User: {getpass.getuser()} | Local-IP: {socket.gethostbyname(platform.node())}
            Permanently saved memory: {memory}
            CRITICAL: You must ALWAYS respond with exactly one raw JSON object matching the required schema. No markdown, no text outside the JSON, no extra keys."""

            self.history.append({"role": "system", "content": system_content})
            self.history.append({"role": "user",
                                 "content": f"This is the initial message from the user, you have to strictly follow this: {user_prompt}"})

        if validate_response and output is not None:
            self.history.append({"role": "user", "content": f"Command output: {output}"})

        client = None
        extra_kwargs = {}
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
        elif self.provider == "Google":
            client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=self.keys.get("GOOGLE_API_KEY"))
            extra_kwargs["response_format"] = {"type": "json_object"}

        if not client:
             return {"tool": "CMD", "input": "", "response": "Invalid Provider", "status": "y"}

        try:
            completions = client.chat.completions.create(
                messages=[
                    *self.history
                ],
                model=self.model_name,
                **extra_kwargs
            )
            raw = completions.choices[0].message.content
            print(raw)
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


from browser_use import Agent, ChatOpenAI, ChatAnthropic, ChatGoogle
from browser_use.llm import ChatGroq
import asyncio

def get_llm(provider: str, model_name: str):
    with open(KEYS_PATH, "r", encoding="utf-8") as f:
        keys = json.load(f)

    if provider == "Google":
        os.environ["GOOGLE_API_KEY"] = keys.get("GOOGLE_API_KEY", "")
        return ChatGoogle(model=model_name)

    if provider == "Anthropic":
        os.environ["ANTHROPIC_API_KEY"] = keys.get("ANTHROPIC_API_KEY", "")
        return ChatAnthropic(model=model_name)

    if provider == "Groq":
        os.environ["GROQ_API_KEY"] = keys.get("GROQ_API_KEY", "")
        return ChatGroq(model=model_name)

    openai_compat = {
        "OpenAI":    ("https://api.openai.com/v1",            keys.get("OPENAI_API_KEY")),
        "GitHubAI":  ("https://models.github.ai/inference",   keys.get("GITHUB_TOKEN")),
        "OpenRoute": ("https://openrouter.ai/api/v1",         keys.get("OPENROUTE_API_KEY")),
        "Unclose":   ("https://qwen-vl.ai.unturf.com/v1/",   "is_free"),
    }

    if provider not in openai_compat:
        raise ValueError(f"Unknown provider: '{provider}'. Choose from: Google, Anthropic, Groq, {list(openai_compat)}")

    base_url, api_key = openai_compat[provider]
    return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, max_retries=2)


async def run_browser_task(task: str, provider: str, model_name: str) -> str:
    llm    = get_llm(provider, model_name)
    agent  = Agent(task=task, llm=llm)
    result = await agent.run()
    if result.is_done():
        return result.final_result()
    else:
        return f"Task did not complete successfully, try another approach.\n\nError:\n{result.errors()}"


if __name__ == "__main__":
    task       = "Search for the latest news on AI advancements and summarize the key points."
    provider   = "Google"
    model_name = "gemini-2.5-flash-lite"

    result = asyncio.run(run_browser_task(task, provider, model_name))
    print(result)
