# Prompt OS

Prompt OS is a powerful, desktop-based AI assistant built in Python. Designed as a hands-on system agent rather than a simple chatbot, Prompt OS can directly interact with your local machine, execute commands, read and write files, perform web searches, and even understand voice commands.

## ✨ Features

- **Local System Control**: The AI is prompted as a system agent that can execute terminal commands (`CMD`), manage files (`FILE_HANDLER`), and safely run Python code snippets (`EXEC_PY`) to autonomously complete tasks on your machine.
- **Voice Interface**: Built-in voice recording capability with fast, accurate speech-to-text transcription powered by Groq's Whisper model.
- **Multi-Provider Support**: Seamlessly switch between different LLM providers (GitHubAI, Groq, OpenRoute, Unclose) right from the GUI.
- **Web Search Integration**: The agent can autonomously run DuckDuckGo searches (`SEARCH_WEB`) to pull precise real-time information when local context is insufficient.
- **Persistent Memory**: The assistant automatically stores and dynamically injects long-term memory (`config/memory.txt`) to remember user preferences and past interactions across sessions.
- **Modern GUI**: A sleek, dark-themed responsive desktop interface cleanly built with `customtkinter`.

## ⚙️ Prerequisites

- **Python 3.10+**
- An active internet connection for API services.
- Operating System with a native microphone (for voice features). *(Note: Command outputs format gracefully for Windows CMD/PowerShell, but the core tools are OS-agnostic).*
- API Keys for one or more of the integrated AI providers.

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/thomastschinkel/prompt-os.git
   cd prompt-os
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: For `pyaudio`, you may need system-level audio dependencies like PortAudio if you are running on macOS/Linux. On Windows, the binary wheel is usually provided via pip).*

3. **Configure API Keys:**
   Look for `config/keys.json` in your project folder, and add your API credentials:
   ```json
   {
       "GROQ_API_KEY": "your_groq_key_here",
       "GITHUB_TOKEN": "your_github_ai_token_here",
       "OPENROUTE_API_KEY": "your_openrouter_key_here"
   }
   ```
   *Note: A [Groq API key](https://console.groq.com/) is specifically required for the voice control / transcription features. If you just want to use the text-based interface, you don't necessarily need to pass API keys if you use the built-in free provider (Unclose).*

## 💡 Usage

Start the application by running the main execution file:
```bash
python main.py
```

### Getting Started:
1. **Choose a Model**: Use the toggle at the top to select your preferred LLM provider.
2. **Text Input**: Type your request (e.g., *"What processes are using the most memory right now?"*, *"Write a python script that renames all images in my Downloads folder"*, or *"Search the web for the latest Python version"*).
3. **Voice Input**: Click the red record button (⏺) to start speaking into your microphone. Click it again to stop, and it will immediately transcribe the request into the prompt bar.
4. **Sit Back**: The AI will think iteratively, updating you in real-time as it uses tools, reads system outputs, and solves the task!

## 📁 Project Structure

```text
Prompt OS/
├── main.py             # Main entry point and UI layer; handles the tool execution loop
├── requirements.txt    # Python dependencies
├── assets/             # Images and static assets for the UI
├── config/
│   ├── keys.json       # API keys configuration
│   ├── memory.txt      # Long-term memory persistence for the AI
│   └── prompt.txt      # Strict system instructions defining AI behavior
└── src/
    ├── ai.py           # LLM engine, history management, and API integrations
    └── utils.py        # Helper utilities for web search, audio recording, and terminal decoding
```

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---
