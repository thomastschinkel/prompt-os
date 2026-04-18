import traceback
import tkinter as tk
from PIL import Image, ImageTk
import subprocess
from src.ai import LLM
import threading
from io import StringIO
import sys
from src.utils import search_web, resource_path, decode_output, get_config_path
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk
import json
import os
import asyncio
import re
import tkinter.font as tkfont

stop_event = threading.Event()

SETTINGS_PATH = get_config_path("settings.json")


def load_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
                if "enabled_tools" not in settings:
                    settings["enabled_tools"] = ["BASH", "POWERSHELL", "FILE_HANDLER", "EXEC_PY", "SEARCH_WEB", "READ_FILE",
                                                 "USE_BROWSER", "CLIPBOARD_MANAGER", "INTERPRET_SCREENSHOT", "GLOB", "GREP"]
                return settings
    except Exception:
        pass
    return {
        "provider": "GitHubAI",
        "model": "openai/gpt-4o-mini",
        "mode": "FAST",
        "ollama_base_url": "http://localhost:11434/v1",
        "lmstudio_base_url": "http://localhost:1234/v1",
        "enabled_tools": ["BASH", "POWERSHELL", "FILE_HANDLER", "EXEC_PY", "SEARCH_WEB", "READ_FILE", "USE_BROWSER",
                          "CLIPBOARD_MANAGER", "INTERPRET_SCREENSHOT", "GLOB", "GREP"]
    }


def save_settings(provider, model, mode, enabled_tools=None):
    try:
        current = load_settings()
        settings = dict(current)
        settings["provider"] = provider
        settings["model"] = model
        settings["mode"] = mode
        settings["enabled_tools"] = enabled_tools if enabled_tools is not None else current.get("enabled_tools", [])
        settings.setdefault("ollama_base_url", "http://localhost:11434/v1")
        settings.setdefault("lmstudio_base_url", "http://localhost:1234/v1")
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass


def update_status(text):
    root.after(0, lambda: status_label.configure(text=text))


def insert_inline_markdown(text_widget, line):
    pattern = r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)"
    parts = re.split(pattern, line)

    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            text_widget.insert(tk.END, part[1:-1], ("md_inline_code",))
        elif part.startswith("**") and part.endswith("**") and len(part) >= 4:
            text_widget.insert(tk.END, part[2:-2], ("md_bold",))
        elif part.startswith("*") and part.endswith("*") and len(part) >= 2:
            text_widget.insert(tk.END, part[1:-1], ("md_italic",))
        else:
            text_widget.insert(tk.END, part)


def render_markdown_to_textbox(text_widget, text):
    in_code_block = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            text_widget.insert(tk.END, f"{raw_line}\n", ("md_code_block",))
            continue

        if stripped.startswith("### "):
            text_widget.insert(tk.END, stripped[4:] + "\n", ("md_h3",))
            continue
        if stripped.startswith("## "):
            text_widget.insert(tk.END, stripped[3:] + "\n", ("md_h2",))
            continue
        if stripped.startswith("# "):
            text_widget.insert(tk.END, stripped[2:] + "\n", ("md_h1",))
            continue

        if re.match(r"^[-*+]\s+", stripped):
            text_widget.insert(tk.END, "• ", ("md_list",))
            insert_inline_markdown(text_widget, re.sub(r"^[-*+]\s+", "", stripped))
            text_widget.insert(tk.END, "\n")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            insert_inline_markdown(text_widget, stripped)
            text_widget.insert(tk.END, "\n")
            continue

        if stripped.startswith("> "):
            text_widget.insert(tk.END, "| ", ("md_quote",))
            insert_inline_markdown(text_widget, stripped[2:])
            text_widget.insert(tk.END, "\n")
            continue

        insert_inline_markdown(text_widget, raw_line)
        text_widget.insert(tk.END, "\n")


def configure_markdown_tags(text_widget):
    internal_text = text_widget._textbox
    base_font = tkfont.Font(font=internal_text.cget("font"))
    base_family = base_font.actual("family")
    base_size = base_font.actual("size")
    size_offset = -1 if base_size < 0 else 1

    text_widget._md_fonts = {
        "h1": tkfont.Font(family=base_family, size=base_size + (4 * size_offset), weight="bold"),
        "h2": tkfont.Font(family=base_family, size=base_size + (2 * size_offset), weight="bold"),
        "h3": tkfont.Font(family=base_family, size=base_size + (1 * size_offset), weight="bold"),
        "bold": tkfont.Font(family=base_family, size=base_size, weight="bold"),
        "italic": tkfont.Font(family=base_family, size=base_size, slant="italic"),
        "inline_code": tkfont.Font(family="Consolas", size=base_size),
        "code_block": tkfont.Font(family="Consolas", size=base_size - (1 * size_offset))
    }

    internal_text.tag_config("md_h1", foreground="#ffffff", spacing1=10, spacing3=8, font=text_widget._md_fonts["h1"])
    internal_text.tag_config("md_h2", foreground="#ffffff", spacing1=8, spacing3=6, font=text_widget._md_fonts["h2"])
    internal_text.tag_config("md_h3", foreground="#ffffff", spacing1=6, spacing3=4, font=text_widget._md_fonts["h3"])
    internal_text.tag_config("md_bold", foreground="#ffffff", font=text_widget._md_fonts["bold"])
    internal_text.tag_config("md_italic", foreground="#e0e0e0", font=text_widget._md_fonts["italic"])
    internal_text.tag_config("md_inline_code", background="#2a2a3a", foreground="#f6d365",
                             font=text_widget._md_fonts["inline_code"])
    internal_text.tag_config("md_code_block", background="#1a1a28", foreground="#c9f0ff", lmargin1=10, lmargin2=10,
                             font=text_widget._md_fonts["code_block"])
    internal_text.tag_config("md_list", foreground="#e0e0e0")
    internal_text.tag_config("md_quote", foreground="#a9a9c5", lmargin1=10, lmargin2=10)


def get_image_description(img_str, provider, model, keys):
    from openai import OpenAI
    client = None
    fallback_model = model
    settings = load_settings()

    if provider == "Groq":
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=keys.get("GROQ_API_KEY", ""))
        fallback_model = "meta-llama/llama-4-scout-17b-16e-instruct"
    elif provider == "GitHubAI":
        client = OpenAI(base_url="https://models.github.ai/inference", api_key=keys.get("GITHUB_TOKEN", ""))
        fallback_model = "Phi-4-multimodal-instruct"
    elif provider == "OpenRoute":
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=keys.get("OPENROUTE_API_KEY", ""))
        fallback_model = "gemma-4-31b-it"
    elif provider == "Unclose":
        client = OpenAI(base_url="https://qwen-vl.ai.unturf.com/v1/", api_key="is_free")
        fallback_model = model
    elif provider == "OpenAI":
        client = OpenAI(api_key=keys.get("OPENAI_API_KEY", ""))
        fallback_model = "gpt-4.1"
    elif provider == "Anthropic":
        client = OpenAI(base_url="https://api.anthropic.com/v1/", api_key=keys.get("ANTHROPIC_API_KEY", ""))
        fallback_model = "claude-haiku-4-5"
    elif provider == "Google":
        client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                        api_key=keys.get("GOOGLE_API_KEY", ""))
        fallback_model = model
    elif provider == "Ollama":
        client = OpenAI(base_url=settings.get("ollama_base_url", "http://localhost:11434/v1"),
                        api_key=keys.get("OLLAMA_API_KEY", "ollama"))
        fallback_model = model
    elif provider == "LMStudio":
        client = OpenAI(base_url=settings.get("lmstudio_base_url", "http://localhost:1234/v1"),
                        api_key=keys.get("LMSTUDIO_API_KEY", "lm-studio"))
        fallback_model = model

    if not client:
        return "Error: Unknown provider for image interpretation."

    messages = [{
        "role": "user",
        "content": [
            {"type": "text",
             "text": "Describe this image in extreme detail. Identify objects, colors, text, and overall composition."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
        ]
    }]
    try:
        res = client.chat.completions.create(model=model, messages=messages)
        return res.choices[0].message.content
    except Exception:
        try:
            res = client.chat.completions.create(model=fallback_model, messages=messages)
            return res.choices[0].message.content
        except Exception as e:
            return f"Error describing image (both models failed): {e}"


def update_answer_box(text, color="#e0e0e0", done_event=None):
    def _update():
        ai_answer_box.configure(state="normal")
        ai_answer_box.delete("1.0", tk.END)
        render_markdown_to_textbox(ai_answer_box, text)
        ai_answer_box.configure(text_color=color, state="disabled")
        if done_event:
            done_event.set()

    root.after(0, _update)


def stop_task():
    if send_button.cget("state") == "disabled":
        stop_event.set()
        update_status("Stopped")
        send_button.configure(state="normal")
        stop_button.configure(fg_color="#3a3a55", hover_color="#4a4a65")
        update_answer_box("Task aborted by user", "#ff5555")


def handle_task():
    user_input = text_input.get()
    if not user_input.strip():
        return

    current_stop_event = threading.Event()
    global stop_event
    stop_event = current_stop_event

    provider = provider_var.get()
    model = model_var.get()
    mode = mode_var.get()

    event = threading.Event()
    update_answer_box("Thinking...", "#888888", event)
    event.wait()

    send_button.configure(state="disabled")
    root.after(0, lambda: stop_button.configure(fg_color="#c42b2b", hover_color="#a82525"))

    llm = LLM(provider=provider, model_name=model, mode=mode, stop_event=current_stop_event)
    settings = load_settings()
    enabled_tools = settings.get("enabled_tools", [])
    disabled_tools = [t for t in
                      ["BASH", "POWERSHELL", "FILE_HANDLER", "EXEC_PY", "SEARCH_WEB", "READ_FILE", "USE_BROWSER", "CLIPBOARD_MANAGER",
                       "INTERPRET_SCREENSHOT", "GLOB", "GREP"] if t not in enabled_tools]

    aborted = False

    def on_finish():
        root.after(0, lambda: send_button.configure(state="normal"))
        root.after(0, lambda: stop_button.configure(fg_color="#3a3a55", hover_color="#4a4a65"))

    response = llm.generate_response(user_input, status_callback=update_status)

    if current_stop_event.is_set():
        on_finish()
        return

    while response.get("status", "y") != "y":
        if current_stop_event.is_set():
            break

        event.clear()
        update_answer_box(response.get("response", ""), "#888888", event)
        event.wait()

        tool = response.get("tool", "")
        update_status(f"Running Tool: {tool}")

        if tool and tool != "ANSWER" and tool not in enabled_tools:
            output = f"Error: Tool '{tool}' is disabled by the administrator. DO NOT try to use this tool again in this conversation. If you have no other enabled tools to fulfill the request, inform the user and finish."
        # Tool execution check
        elif tool == "BASH":
            try:
                creation_flags = 0
                if os.name == 'nt':
                     creation_flags = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(["bash", "-c", response.get("input", "")], capture_output=True, text=False,
                                        timeout=None, creationflags=creation_flags)
                stdout = decode_output(result.stdout or b"")
                stderr = decode_output(result.stderr or b"")
                output = f"{stdout} | {stderr}".strip()
            except Exception as e:
                output = f"Error: {e}"

        elif tool == "POWERSHELL":
            try:
                creation_flags = 0
                if os.name == 'nt':
                     creation_flags = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(["powershell.exe", "-Command", response.get("input", "")], capture_output=True, text=False,
                                        timeout=None, creationflags=creation_flags)
                stdout = decode_output(result.stdout or b"")
                stderr = decode_output(result.stderr or b"")
                output = f"{stdout} | {stderr}".strip()
            except Exception as e:
                output = f"Error: {e}"

        elif tool == "FILE_HANDLER":
            path = response.get("path", "").strip('"')
            if response.get("mode", "r") != "r":
                try:
                    with open(path, response["mode"], encoding="utf-8") as f:
                        f.write(response["content"])
                    output = f"File written to {path} with mode {response['mode']}"
                except Exception:
                    output = f"Error writing to file {path} with mode {response.get('mode')}"
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    output = f"Content of {path}: {content} with mode {response['mode']}"
                except Exception as e:
                    output = f"Error reading file {path}: {str(e)}"

        elif tool == "EXEC_PY":
            try:
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = StringIO(), StringIO()
                exec(response.get("code", ""), {})
                out = f"STDOUT: {sys.stdout.getvalue()}\nSTDERR: {sys.stderr.getvalue()}"
            except Exception as e:
                out = f"ERROR: {str(e)}"
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            output = out.strip() or "Executed (no output)"

        elif tool == "SEARCH_WEB":
            output = search_web(response.get("input", ""), max_results=response.get("max_results", 3))

        elif tool == "READ_FILE":
            path = response.get("path", "").strip('"')
            if not os.path.exists(path):
                output = f"Error: File not found at {path}"
            else:
                ext = path.lower().split('.')[-1]
                try:
                    if ext == "pdf":
                        import fitz
                        with fitz.open(path) as doc:
                            output = "\n".join(page.get_text() for page in doc)
                    elif ext == "docx":
                        import docx
                        output = "\n".join(p.text for p in docx.Document(path).paragraphs)
                    elif ext in ["png", "jpg", "jpeg", "webp", "bmp"]:
                        import base64
                        with open(path, "rb") as f:
                            img_str = base64.b64encode(f.read()).decode("utf-8")
                        try:
                            with open(get_config_path("keys.json"), "r", encoding="utf-8") as f:
                                keys = json.load(f)
                        except:
                            keys = {}
                        output = get_image_description(img_str, provider, model, keys)
                    elif ext == "pptx":
                        import pptx
                        prs = pptx.Presentation(path)
                        txt = []
                        for slide in prs.slides:
                            for shape in slide.shapes:
                                if hasattr(shape, "text"): txt.append(shape.text)
                        output = "\n".join(txt)
                    elif ext in ["xlsx", "xls"]:
                        import pandas as pd
                        output = pd.read_excel(path).to_markdown()
                    elif ext == "csv":
                        import pandas as pd
                        output = pd.read_csv(path).to_markdown()
                    elif ext in ["html", "htm"]:
                        from bs4 import BeautifulSoup
                        with open(path, "r", encoding="utf-8") as f:
                            soup = BeautifulSoup(f.read(), "lxml")
                        for s in soup(["script", "style"]): s.decompose()
                        output = "\n".join(l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip())
                    else:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            output = f.read()
                except Exception as e:
                    output = f"Error reading {path}: {e}"

        elif tool == "USE_BROWSER":
            try:
                from src.ai import run_browser_task
                output = asyncio.run(
                    run_browser_task(task=response.get("input", ""), provider=provider, model_name=model))
            except ImportError as e:
                output = f"Error: Browser tool dependencies missing in this build. Details: {e}"
            except Exception as e:
                import traceback
                output = f"Error using browser: {str(e)}\n{traceback.format_exc()}"

        elif tool == "CLIPBOARD_MANAGER":
            import pyperclip
            if response.get("action") == "read":
                try:
                    text = pyperclip.paste()
                    output = f"Clipboard content (read success): {text}"
                except Exception as e:
                    output = f"Error reading clipboard: {e}"
            elif response.get("action") == "write":
                try:
                    content_to_write = response.get("content", "")
                    pyperclip.copy(content_to_write)
                    verification = pyperclip.paste()
                    if verification == content_to_write:
                        output = f"Content successfully written and verified in clipboard: {content_to_write}"
                    else:
                        output = f"Warning: Written content did not match verification! Clipboard currently contains: {verification}"
                except Exception as e:
                    output = f"Error writing to clipboard: {e}"

        elif tool == "INTERPRET_SCREENSHOT":
            try:
                import base64
                from io import BytesIO
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                buffered = BytesIO()
                screenshot.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                try:
                    with open(get_config_path("keys.json"), "r", encoding="utf-8") as f:
                        keys = json.load(f)
                except:
                    keys = {}

                output = get_image_description(img_str, provider, model, keys)
            except Exception as e:
                output = f"Error taking screenshot: {e}"

        elif tool == "GLOB":
            import glob
            pattern = response.get("pattern", "")
            if not pattern:
                output = "Error: No pattern provided."
            else:
                try:
                    matches = glob.glob(pattern, recursive=True)
                    if matches:
                        output = "Matches found:\n" + "\n".join(matches)
                    else:
                        output = f"No files matched the pattern: {pattern}"
                except Exception as e:
                    output = f"Error performing glob search: {e}"

        elif tool == "GREP":
            pattern = response.get("pattern", "")
            path = response.get("path", "")
            if not pattern or not path:
                output = "Error: Missing pattern or path."
            else:
                try:
                    results = []
                    if os.path.isfile(path):
                        files_to_check = [path]
                    elif os.path.isdir(path):
                        files_to_check = []
                        for root_dir, _, files in os.walk(path):
                            for f in files:
                                files_to_check.append(os.path.join(root_dir, f))
                    else:
                        files_to_check = []
                    
                    compiled = re.compile(pattern)
                    for fpath in files_to_check:
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                for i, line in enumerate(f, 1):
                                    if compiled.search(line):
                                        results.append(f"{fpath}:{i}:{line.strip()}")
                        except:
                            pass
                    
                    if results:
                        output = "Matches found:\n" + "\n".join(results[:100])
                        if len(results) > 100:
                            output += f"\n... and {len(results)-100} more matches."
                    else:
                        if not files_to_check:
                            output = f"Error: Path not found or invalid: {path}"
                        else:
                            output = "No matches found."
                except Exception as e:
                    output = f"Error performing grep search: {e}"

        else:
            output = f"Unknown tool: {tool}"

        if current_stop_event.is_set():
            break

        response = llm.generate_response(user_input, validate_response=True, output=output,
                                         status_callback=update_status)

        if current_stop_event.is_set():
            aborted = True
            break

    event.clear()

    def _final_update():
        if current_stop_event.is_set() or aborted:
            ai_answer_box.configure(state="normal")
            ai_answer_box.delete("1.0", tk.END)
            render_markdown_to_textbox(ai_answer_box, "[Task stopped by user]")
            ai_answer_box.configure(text_color="#ff5555", state="disabled")
        else:
            ai_answer_box.configure(state="normal")
            ai_answer_box.delete("1.0", tk.END)
            render_markdown_to_textbox(ai_answer_box, response.get("response", ""))
            ai_answer_box.configure(text_color="#e0e0e0", state="disabled")
        event.set()

    root.after(0, _final_update)
    event.wait()

    on_finish()

    if not current_stop_event.is_set():
        with open(get_config_path("memory.txt"), "a", encoding="utf-8") as mem_file:
            memory_content = response.get("memory")
            if memory_content:
                mem_file.write(f"{memory_content}\n")


def thread_handle_task():
    threading.Thread(target=handle_task, daemon=True).start()


def open_settings():
    settings_win = ctk.CTkToplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("450x480")
    settings_win.transient(root)

    current_settings = load_settings()
    enabled_tools_vars = {}

    all_tools = ["BASH", "POWERSHELL", "FILE_HANDLER", "EXEC_PY", "SEARCH_WEB", "READ_FILE", "USE_BROWSER", "CLIPBOARD_MANAGER",
                 "INTERPRET_SCREENSHOT", "GLOB", "GREP"]

    def on_settings_change(*args):
        active_tools = [t for t in all_tools if enabled_tools_vars[t].get()]
        save_settings(provider_var.get(), model_var.get(), mode_var.get(), active_tools)

    def on_model_change(choice):
        model_entry.delete(0, tk.END)
        model_entry.insert(0, choice)
        on_settings_change()

    def on_model_entry_change(event=None):
        model_var.set(model_entry.get())
        on_settings_change()

    keys_path = resource_path("..", "config", "keys.json")

    provider_to_key_name = {
        "GitHubAI": "GITHUB_TOKEN",
        "Groq": "GROQ_API_KEY",
        "OpenRoute": "OPENROUTE_API_KEY",
        "Unclose": "UNCLOSE_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Google": "GOOGLE_API_KEY",
        "Ollama": "OLLAMA_API_KEY",
        "LMStudio": "LMSTUDIO_API_KEY"
    }

    def load_keys():
        abs_keys_path = get_config_path("keys.json")
        try:
            with open(abs_keys_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_key(event=None):
        provider = provider_var.get()
        key_name = provider_to_key_name.get(provider)
        if key_name:
            keys = load_keys()
            keys[key_name] = api_key_entry.get()
            abs_keys_path = get_config_path("keys.json")
            with open(abs_keys_path, "w", encoding="utf-8") as f:
                json.dump(keys, f, indent=4)
            if event is None:
                update_status("Settings saved")
                settings_win.destroy()
        on_settings_change()

    def toggle_password():
        if api_key_entry.cget("show") == "*":
            api_key_entry.configure(show="")
            eye_button.configure(text="👁")
        else:
            api_key_entry.configure(show="*")
            eye_button.configure(text="🔒")

    def update_models(provider):
        models = {
            "GitHubAI": ["openai/gpt-4o", "microsoft/phi-4", "meta/llama-3.3-70b-instruct", "deepseek/deepseek-r1",
                         "openai/gpt-4o-mini", "meta/llama-4-maverick-17b-128e-instruct-fp8"],
            "Groq": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "groq/compound", "qwen/qwen3-32b",
                     "meta-llama/llama-4-scout-17b-16e-instruct", "groq/compound-mini", "openai/gpt-oss-20b",
                     "llama-3.1-8b-instant", "openai/gpt-oss-safeguard-20b"],
            "OpenRoute": ["xiaomi/mimo-v2-pro", "anthropic/claude-4.6-sonnet", "minimax/minimax-m2.7",
                          "deepseek/deepseek-v3.2", "qwen/qwen3.6-plus:free", "anthropic/claude-4.6-opus",
                          "openai/gpt-5.4", "google/gemini-3.1-pro-preview", "moonshotai/kimi-k2.5",
                          "google/gemini-3.1-flash-lite-preview", "nousresearch/hermes-3-llama-3.1-405b:free",
                          "qwen/qwen3-coder:free", "google/gemma-3-27b-it:free", "openrouter/free",
                          "nvidia/nemotron-3-super-120b-a12b:free", "openai/gpt-oss-120b:free"],
            "Unclose": ["qwen3-vl:8b", "gpt-oss:latest", "deepseek-r1:14b-qwen-distill-q8_0"],
            "Anthropic": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-opus-4-5", "claude-sonnet-4-5",
                          "claude-haiku-4-5", "claude-opus-4", "claude-sonnet-4", "claude-opus-4-5-20251101",
                          "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"],
            "OpenAI": ["gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5-mini", "gpt-5", "gpt-5-nano",
                       "gpt-5.3-chat-latest", "gpt-4.1", "gpt-4o-mini"],
            "Google": ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview",
                       "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemma-4-31b-it",
                       "gemini-flash-latest"],
            "Ollama": ["llama3.1", "deepseek-r1", "llama3.2", "gemma3", "mistral", "qwen2.5", "qwen3", "llama3", "gemma2", "deepseek-r1:8b", "phi4"],
            "LMStudio": ["local-model", "qwen3-8b", "llama-3.1-8b", "mistral-7b-instruct", "gpt-oss-20b", "deepseek-r1-0528-qwen3-8b", "qwen3.5", "gemma4", "llama4", "mistral-small-3", "phi-4-mini", "lfm2-24b", "nemotron-3-super", "qwen3-coder"]
        }
        model_list = models.get(provider, ["default-model"])
        model_menu.configure(values=model_list)

        current_settings = load_settings()
        selected_model = ""
        if provider == current_settings.get("provider"):
            selected_model = current_settings.get("model")
        elif model_list:
            selected_model = model_list[0]
        
        if selected_model:
            model_var.set(selected_model)
            model_entry.delete(0, tk.END)
            model_entry.insert(0, selected_model)

        on_settings_change()

        keys = load_keys()
        key_name = provider_to_key_name.get(provider)
        api_key_entry.delete(0, tk.END)
        if key_name and key_name in keys:
            api_key_entry.insert(0, keys[key_name])

    # Left Column (Core Settings)
    main_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    left_col = ctk.CTkFrame(main_frame, fg_color="transparent")
    left_col.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(left_col, text="Provider:").pack(pady=(10, 0))
    provider_menu = ctk.CTkOptionMenu(left_col, variable=provider_var,
                                      values=["GitHubAI", "Groq", "OpenRoute", "Unclose", "Anthropic", "OpenAI",
                                              "Google", "Ollama", "LMStudio"], command=update_models)
    provider_menu.pack(pady=5)

    ctk.CTkLabel(left_col, text="Model:").pack(pady=(10, 0))
    model_menu = ctk.CTkOptionMenu(left_col, variable=model_var, values=[], command=on_model_change)
    model_menu.pack(pady=5)

    ctk.CTkLabel(left_col, text="Custom Model ID:").pack(pady=(5, 0))
    model_entry = ctk.CTkEntry(left_col, width=140)
    model_entry.pack(pady=5)
    model_entry.bind("<KeyRelease>", on_model_entry_change)

    ctk.CTkLabel(left_col, text="API Key:").pack(pady=(10, 0))
    key_frame = ctk.CTkFrame(left_col, fg_color="transparent")
    key_frame.pack(pady=5)

    api_key_entry = ctk.CTkEntry(key_frame, show="*", width=140)
    api_key_entry.pack(side="left")
    api_key_entry.bind("<KeyRelease>", save_key)

    eye_button = ctk.CTkButton(key_frame, text="🔒", width=30, command=toggle_password)
    eye_button.pack(side="left", padx=5)

    # Right Column (Tool Permissions)
    right_col = ctk.CTkFrame(main_frame, fg_color="#2a2a3a", corner_radius=10)
    right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

    ctk.CTkLabel(right_col, text="Tool Permissions", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))

    scroll_frame = ctk.CTkScrollableFrame(right_col, fg_color="transparent", width=180, height=200)
    scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    enabled_tools = current_settings.get("enabled_tools", all_tools)
    for tool_name in all_tools:
        var = tk.BooleanVar(value=(tool_name in enabled_tools))
        enabled_tools_vars[tool_name] = var
        cb = ctk.CTkCheckBox(scroll_frame, text=tool_name, variable=var, command=on_settings_change,
                             font=ctk.CTkFont(size=11))
        cb.pack(anchor="w", pady=2)

    save_button = ctk.CTkButton(settings_win, text="Close", command=settings_win.destroy)
    save_button.pack(pady=10)

    update_models(provider_var.get())


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Prompt OS")
root.geometry("500x500")
root.resizable(False, False)

icon_path = resource_path("assets", "logo.ico")
if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
        img = ImageTk.PhotoImage(Image.open(icon_path))
        root.wm_iconphoto(True, img)
    except Exception:
        pass

initial_settings = load_settings()
provider_var = ctk.StringVar(value=initial_settings.get("provider", "GitHubAI"))
model_var = ctk.StringVar(value=initial_settings.get("model", "openai/gpt-4o-mini"))
mode_var = ctk.StringVar(value=initial_settings.get("mode", "FAST"))

settings_pil = Image.open(resource_path("assets", "settings.png"))
settings_img = ctk.CTkImage(light_image=settings_pil, dark_image=settings_pil, size=(36, 36))
settings_btn = ctk.CTkButton(root, text="", image=settings_img, width=30, height=30, fg_color="transparent",
                             command=open_settings)
settings_btn.place(x=10, y=10)

root.configure(padx=20, pady=10)
root.configure(fg_color="#0f0f1a")

logo_pil = Image.open(resource_path("assets", "logo.png"))
logo_img = ctk.CTkImage(light_image=logo_pil, dark_image=logo_pil, size=(64, 64))
logo_label = ctk.CTkLabel(root, text="", image=logo_img)
logo_label.pack(pady=(10, 0), side="top")

title = ctk.CTkLabel(root, text="Prompt OS", font=ctk.CTkFont(size=22, weight="bold"))
title.pack(pady=20, side="top")

mode_selection = ctk.CTkSegmentedButton(root, values=["FAST", "THINKING", "PRO"], variable=mode_var,
                                        command=lambda m: save_settings(provider_var.get(), model_var.get(), m))
mode_selection.pack(pady=5)

input_frame = ctk.CTkFrame(root, fg_color="transparent")
input_frame.pack(pady=10, side="top")

stop_button = ctk.CTkButton(input_frame, text="Stop", width=80, fg_color="#3a3a55", hover_color="#4a4a65",
                            command=stop_task)
stop_button.pack(side="left")

text_input = ctk.CTkEntry(input_frame, font=("Arial", 14), width=240, placeholder_text="Ask anything...")
text_input.pack(side="left", padx=10)

send_button = ctk.CTkButton(input_frame, text="Send", width=80, command=thread_handle_task)
send_button.pack(side="left")

status_label = ctk.CTkLabel(
    root,
    text="Ready",
    font=ctk.CTkFont(size=12, slant="italic"),
    text_color="#888888"
)
status_label.pack(pady=5)

separator = ctk.CTkFrame(root, height=1, fg_color="#2a2a40")
separator.pack(fill="x", padx=20, pady=(0, 12))

ai_answer_box = ctk.CTkTextbox(
    root, font=ctk.CTkFont(size=13),
    height=220, width=420,
    corner_radius=12,
    fg_color="#1e1e2e",
    border_color="#3a3a55",
    border_width=1,
    text_color="#e0e0e0"
)
ai_answer_box.pack(pady=(0, 20), padx=20)
configure_markdown_tags(ai_answer_box)
ai_answer_box.configure(state="disabled")

root.mainloop()








