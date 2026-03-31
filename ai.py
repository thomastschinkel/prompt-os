import platform
import json
from groq import Groq
import os
import getpass
import socket

class LLM():
    def __init__(self, model_provider):
        self.model_provider = model_provider
        self.history = []

    def generate_response(self, user_prompt, validate_response=False, output=None):
        with open('prompt.txt', 'r') as file:
            system_instructions = file.read()

        if not self.history:
            user_message = f"{user_prompt}"
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "system", "content": f"System information from the user: OS: {platform.system()} | Arch: {platform.machine()} | Host-Name: {platform.node()} | CWD: {os.getcwd()} | User: {getpass.getuser()} | Local-IP: {socket.gethostbyname(platform.node())}"})

        if validate_response and output is not None:
            self.history.append({"role": "user", "content": f"Command output: {output}"})

        if self.model_provider == "Groq":
            client = Groq(api_key="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")

            try:
                completions = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instructions},
                        *self.history
                    ],
                    model="llama-3.3-70b-versatile",
                )
                raw = completions.choices[0].message.content
            except Exception:
                return {"tool": "CMD",
                        "input": "",
                        "response": "Error with Groq - API",
                        "status": "y"}
            print(raw)
            self.history.append({"role": "assistant", "content": raw})
            return json.loads(raw)

        return "Unbekannt"