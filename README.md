# 🖥️ Prompt OS

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat)
![Stars](https://img.shields.io/github/stars/thomastschinkel/prompt-os?style=flat&color=yellow)

**Prompt OS** is a powerful, desktop-based AI agent built in Python. Unlike a simple chatbot, it acts as a true system agent — it can execute terminal commands, manage your files, run code, search the web, and understand voice commands, all from a sleek local GUI.

> "What processes are using the most memory?" → it runs the command and tells you.
> "Rename all images in my Downloads folder" → it writes and runs the script.

---

![Prompt OS GUI](assets/GUI.png)

---

## ✨ Why Prompt OS?

Most AI assistants just *talk*. Prompt OS *acts*. It runs iteratively — thinking, using tools, reading outputs, and refining — until your task is actually done. No copy-pasting commands, no manual steps.

---

## 🚀 Features

- **Local System Control** — Executes terminal commands (`CMD`), manages files (`FILE_HANDLER`), and runs Python snippets (`EXEC_PY`) autonomously.
- **Voice Interface** — Built-in microphone recording with fast, accurate transcription via Groq's Whisper model.
- **Multi-Provider LLM Support** — Switch between GitHubAI, Groq, OpenRouter, and Unclose (free/local) right from the GUI.
- **Web Search** — The agent autonomously queries DuckDuckGo (`SEARCH_WEB`) for real-time information when needed.
- **Persistent Memory** — Stores long-term preferences and context in `config/memory.txt`, injected automatically into every session.
- **Modern Dark UI** — Sleek, responsive desktop interface built with `customtkinter`.

---

## ⚙️ Prerequisites

- Python 3.10+
- An active internet connection for API services
- A microphone (for voice features)
- API keys for one or more supported LLM providers

---

## 🛠️ Installation

**1. Clone the repository:**
```bash
git clone https://github.com/thomastschinkel/prompt-os.git
cd prompt-os
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

> **Note:** For `pyaudio` on macOS/Linux, you may need PortAudio installed first:
> - macOS: `brew install portaudio`
> - Ubuntu/Debian: `sudo apt-get install portaudio19-dev`

**3. Configure API keys:**

Create or edit `config/keys.json`:
```json
{
    "GROQ_API_KEY": "your_groq_key_here",
    "GITHUB_TOKEN": "your_github_ai_token_here",
    "OPENROUTE_API_KEY": "your_openrouter_key_here"
}
```

> A Groq API key is only required for voice transcription. For text-only use, the built-in **Unclose** provider works for free with no key needed.

---

## 💡 Usage

```bash
python main.py
```

| Step | Action |
|---|---|
| **1. Pick a model** | Use the toggle at the top to select your LLM provider |
| **2. Type a request** | e.g. *"What's eating my CPU right now?"* or *"Create a script to organize my Desktop"* |
| **3. Or use voice** | Click ⏺ to start recording, click ⏹ to stop — it transcribes automatically |
| **4. Watch it work** | The agent thinks iteratively, uses tools, and streams updates in real time |

---

## 📁 Project Structure

```
prompt-os/
├── main.py               # Entry point, UI layer, and tool execution loop
├── requirements.txt      # Python dependencies
├── assets/               # Images and static UI assets
├── config/
│   ├── keys.json         # API key configuration
│   ├── memory.txt        # Persistent long-term memory for the AI
│   └── prompt.txt        # System instructions defining agent behavior
└── src/
    ├── ai.py             # LLM engine, conversation history, API integrations
    └── utils.py          # Web search, audio recording, terminal output helpers
```

---

## 🤖 Supported Providers

| Provider | Model | Free? | Requires Key? |
|---|---|---|---|
| **GitHubAI** | GPT-4o Mini | ✅ (with GitHub account) | Yes |
| **Groq** | LLaMA 3.3 70B | ✅ (free tier) | Yes |
| **OpenRouter** | Qwen 3.6+ | ✅ (free tier) | Yes |
| **Unclose** | DeepSeek R1 14B | ✅ Completely free | No |

---

## 📜 License

Distributed under the [MIT License](LICENSE).

---

## 🙌 Contributing

Contributions, issues, and feature requests are welcome! Feel free to open an issue or submit a pull request.

If you find this project useful, consider giving it a ⭐ — it helps a lot!
