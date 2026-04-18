import platform
import json
import os
import getpass
import socket
from pathlib import Path
import re
from src.utils import get_config_path

PROMPT_PATH = get_config_path("prompt.txt")
KEYS_PATH = get_config_path("keys.json")
MEMORY_PATH = get_config_path("memory.txt")


def load_runtime_settings():
    try:
        with open(get_config_path("settings.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_base_url_for_provider(provider, settings):
    if provider == "Ollama":
        return settings.get("ollama_base_url", "http://localhost:11434/v1")
    if provider == "LMStudio":
        return settings.get("lmstudio_base_url", "http://localhost:1234/v1")
    return None


class LLM():
    def __init__(self, provider, model_name, mode="FAST", stop_event=None):
        self.provider = provider
        self.model_name = model_name
        self.mode = mode
        self.history = []
        self.stop_event = stop_event

        with open(KEYS_PATH, 'r', encoding='utf-8') as keys_file:
            self.keys = json.load(keys_file)

    def generate_response(self, user_prompt, validate_response=False, output=None, status_callback=None):
        from openai import OpenAI
        runtime_settings = load_runtime_settings()
        if not self.history:
            with open(MEMORY_PATH, 'r', encoding='utf-8') as mem_file:
                memory = mem_file.read().strip()

            with open(PROMPT_PATH, 'r', encoding='utf-8') as file:
                system_instructions = file.read()

            try:
                with open(get_config_path("settings.json"), "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    enabled_tools = settings.get("enabled_tools", [])
            except:
                enabled_tools = ["BASH", "POWERSHELL", "FILE_HANDLER", "EXEC_PY", "SEARCH_WEB", "READ_FILE", "USE_BROWSER",
                                 "CLIPBOARD_MANAGER", "INTERPRET_SCREENSHOT", "GLOB", "GREP"]

            all_tools = {
                "BASH": r"BASH \(Executes shell commands.*?:.*?{.*?}\n\n",
                "POWERSHELL": r"POWERSHELL \(Executes PowerShell commands.*?:.*?{.*?}\n\n",
                "INTERPRET_SCREENSHOT": r"INTERPRET_SCREENSHOT \(Capture and describe.*?:.*?{.*?}\n\n",
                "FILE_HANDLER": r"FILE_HANDLER \(Safe file reading.*?:.*?{.*?}\n\n",
                "EXEC_PY": r"EXEC_PY \(Complex logic.*?:.*?{.*?}\n\n",
                "SEARCH_WEB": r"SEARCH_WEB \(Live external data.*?:.*?{.*?}\n\n",
                "READ_FILE": r"READ_FILE \(Natively parse PDF.*?:.*?{.*?}\n\n(When `READ_FILE` is used to read an image file.*?reasoning about image contents\.\n\n)?",
                "USE_BROWSER": r"USE_BROWSER \(Live multi-step web interactions.*?:.*?{.*?}\n\n",
                "CLIPBOARD_MANAGER": r"CLIPBOARD_MANAGER \(Read from or write to the system clipboard.*?:.*?{.*?}\n\n",
                "GLOB": r"GLOB \(Finds files by pattern matching.*?:.*?{.*?}\n\n",
                "GREP": r"GREP \(Searches for patterns in file contents.*?:.*?{.*?}\n\n"
            }

            filtered_instructions = system_instructions
            for tool_name, pattern in all_tools.items():
                if tool_name not in enabled_tools:
                    filtered_instructions = re.sub(pattern, f"{tool_name} is DISABLED and unavailable.\n\n",
                                                   filtered_instructions, flags=re.DOTALL)

            system_content = f"""{filtered_instructions} {self.mode}
            System information: OS: {platform.system()} | Arch: {platform.machine()} | Host-Name: {platform.node()} | CWD: {os.getcwd()} | User: {getpass.getuser()} | Local-IP: {socket.gethostbyname(platform.node())}
            Permanently saved memory: {memory}
            AVAILABLE TOOLS: {", ".join(enabled_tools)}
            CRITICAL: If you need a tool that is not in the AVAILABLE TOOLS list, you MUST NOT try to use it. Inform the user that the required capability is disabled and provide the best possible answer with the remaining information.
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
            client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                            api_key=self.keys.get("GOOGLE_API_KEY"))
            extra_kwargs["response_format"] = {"type": "json_object"}
        elif self.provider == "Ollama":
            client = OpenAI(base_url=get_base_url_for_provider("Ollama", runtime_settings),
                            api_key=self.keys.get("OLLAMA_API_KEY") or "ollama")
        elif self.provider == "LMStudio":
            client = OpenAI(base_url=get_base_url_for_provider("LMStudio", runtime_settings),
                            api_key=self.keys.get("LMSTUDIO_API_KEY") or "lm-studio")

        if not client:
            return {"tool": "CMD", "input": "", "response": "Invalid Provider", "status": "y"}

        retry_messages = []
        for attempt in range(3):
            if self.stop_event and self.stop_event.is_set():
                return {"tool": "CMD", "input": "", "response": "Task stopped by user", "status": "y"}

            try:
                completions = client.chat.completions.create(
                    messages=[
                        *self.history,
                        *retry_messages
                    ],
                    model=self.model_name,
                    **extra_kwargs
                )
                raw = completions.choices[0].message.content
                print(raw)
                raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            except Exception as e:
                if status_callback:
                    status_callback(f"API Error, retrying {attempt + 1}/3")
                if attempt < 2:
                    retry_messages.append(
                        {"role": "user", "content": f"API request failed with error: {e}. Please try again."})
                    continue
                else:
                    return {"tool": "CMD", "input": "", "response": f"Error with API after 3 retries\n{e}",
                            "status": "y"}
            try:
                start_index = raw.find('{')
                end_index = raw.rfind('}')

                if start_index != -1 and end_index != -1 and end_index >= start_index:
                    json_str = raw[start_index:end_index + 1]
                else:
                    raise ValueError("No valid JSON found in the response")

                parsed = json.loads(json_str)
                # Success: append the actual completion (as it was received) to the history
                self.history.append({"role": "assistant", "content": raw})
                return parsed
            except Exception as e:
                if status_callback:
                    status_callback(f"JSON Parsing Error, retrying {attempt + 1}/3")
                if attempt < 2:
                    # Keep track of the failure so the LLM knows what happened
                    retry_messages.append({"role": "assistant", "content": raw})
                    retry_messages.append({"role": "user",
                                           "content": f"JSON parsing failed with error: {e}. Please respond with exactly ONE valid, properly formatted JSON object."})
                    continue
                else:
                    return {"tool": "CMD", "input": "", "response": f"Error with JSON parsing after 3 retries\n{e}",
                            "status": "y"}


def get_llm(provider: str, model_name: str):
    from browser_use.llm import ChatGoogle, ChatAnthropic, ChatGroq, ChatOpenAI
    settings = load_runtime_settings()
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
        "OpenAI": ("https://api.openai.com/v1", keys.get("OPENAI_API_KEY")),
        "GitHubAI": ("https://models.github.ai/inference", keys.get("GITHUB_TOKEN")),
        "OpenRoute": ("https://openrouter.ai/api/v1", keys.get("OPENROUTE_API_KEY")),
        "Unclose": ("https://qwen-vl.ai.unturf.com/v1/", "is_free"),
        "Ollama": (get_base_url_for_provider("Ollama", settings), keys.get("OLLAMA_API_KEY") or "ollama"),
        "LMStudio": (get_base_url_for_provider("LMStudio", settings), keys.get("LMSTUDIO_API_KEY") or "lm-studio"),
    }

    if provider not in openai_compat:
        raise ValueError(f"Unknown provider: '{provider}'. Choose from: Google, Anthropic, Groq, {list(openai_compat)}")

    base_url, api_key = openai_compat[provider]
    return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, max_retries=2)


async def run_browser_task(task: str, provider: str, model_name: str) -> str:
    from browser_use import Agent
    llm = get_llm(provider, model_name)
    agent = Agent(task=task, llm=llm, max_retries=2, use_vision=False)
    result = await agent.run()
    if result.is_done():
        return result.final_result()
    else:
        return f"Task did not complete successfully.\n\nError:\n{result.errors()}"