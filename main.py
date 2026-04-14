import traceback
import tkinter as tk
from PIL import Image, ImageTk
import subprocess
from src.ai import LLM
import threading
from io import StringIO
import sys
from src.utils import search_web, resource_path, decode_output
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk
import json
import os
import asyncio
import re
import tkinter.font as tkfont


SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json")

def load_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"provider": "GitHubAI", "model": "openai/gpt-4o-mini", "mode": "FAST"}

def save_settings(provider, model, mode):
    try:
        settings = {"provider": provider, "model": model, "mode": mode}
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
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
    internal_text.tag_config("md_inline_code", background="#2a2a3a", foreground="#f6d365", font=text_widget._md_fonts["inline_code"])
    internal_text.tag_config("md_code_block", background="#1a1a28", foreground="#c9f0ff", lmargin1=10, lmargin2=10, font=text_widget._md_fonts["code_block"])
    internal_text.tag_config("md_list", foreground="#e0e0e0")
    internal_text.tag_config("md_quote", foreground="#a9a9c5", lmargin1=10, lmargin2=10)

def update_answer_box(text, color="#e0e0e0", done_event=None):
    def _update():
        ai_answer_box.configure(state="normal")
        ai_answer_box.delete("1.0", tk.END)
        render_markdown_to_textbox(ai_answer_box, text)
        ai_answer_box.configure(text_color=color, state="disabled")
        ai_answer_box.see(tk.END)
        if done_event:
            done_event.set()
    root.after(0, _update)

def handle_task():
    user_input = text_input.get()
    provider = provider_var.get()
    model = model_var.get()
    mode = mode_var.get()
    
    event = threading.Event()
    update_answer_box("Thinking...", "#888888", event)
    event.wait()
    
    send_button.configure(state="disabled")
    llm = LLM(provider=provider, model_name=model, mode=mode)
    response = llm.generate_response(user_input, status_callback=update_status)

    while response.get("status", "y") != "y":
        event.clear()
        update_answer_box(response.get("response", ""), "#888888", event)
        event.wait()

        tool = response.get("tool", "")
        update_status(f"Using tool: {tool}...")
        if tool == "CMD":
            try:
                result = subprocess.run(response.get("input", ""), shell=True, capture_output=True, text=False, timeout=30)
                stdout = decode_output(result.stdout or b"")
                stderr = decode_output(result.stderr or b"")
                output = f"{stdout} | {stderr}".strip()
            except Exception as e:
                output = f"Error: {e}"

        elif tool == "FILE_HANDLER":
            if response.get("mode", "r") != "r":
                try:
                    with open(response["path"], response["mode"], encoding="utf-8") as f:
                        f.write(response["content"])
                    output = f"File written to {response['path']} with mode {response['mode']}"
                except Exception:
                    output = f"Error writing to file {response.get('path')} with mode {response.get('mode')}"
            else:
                try:
                    with open(response["path"], response.get("mode", "r"), encoding="utf-8") as f:
                        content = f.read()
                    output = f"Content of {response['path']}: {content} with mode {response['mode']}"
                except Exception:
                    output = f"Error reading file {response.get('path')} with mode {response.get('mode')}"

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
            from src.ai import run_browser_task
            output = asyncio.run(run_browser_task(task=response.get("input", ""), provider=provider, model_name=model))

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
                
                keys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "keys.json")
                try:
                    with open(keys_path, "r", encoding="utf-8") as f:
                        keys = json.load(f)
                except:
                    keys = {}

                from openai import OpenAI
                client = None
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
                    client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=keys.get("GOOGLE_API_KEY", ""))
                    fallback_model = model
                
                if not client:
                    output = "Error: Unknown provider for image interpretation."
                else:
                    messages = [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this screenshot in extreme detail. Identify windows, applications, text, buttons, and layout."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                        ]
                    }]
                    try:
                        res = client.chat.completions.create(model=model, messages=messages)
                        output = res.choices[0].message.content
                    except Exception:
                        try:
                            res = client.chat.completions.create(model=fallback_model, messages=messages)
                            output = res.choices[0].message.content
                        except Exception as e:
                            output = f"Error describing screenshot (both models failed): {e}"
            except Exception as e:
                output = f"Error taking screenshot: {e}"

        else:
            output = f"Unknown tool: {tool}"

        response = llm.generate_response(user_input, validate_response=True, output=output, status_callback=update_status)


    event.clear()
    update_answer_box(response.get("response", ""), "#e0e0e0", event)
    event.wait()
    
    root.after(0, lambda: send_button.configure(state="normal"))

    with open("config/memory.txt", "a", encoding="utf-8") as mem_file:
        memory_content = response.get("memory")
        if memory_content:
            mem_file.write(f"{memory_content}\n")

def thread_handle_task():
    threading.Thread(target=handle_task, daemon=True).start()

def open_settings():
    settings_win = ctk.CTkToplevel(root)
    settings_win.title("Settings")
    settings_win.geometry("350x320")
    settings_win.transient(root)

    def on_model_change(choice):
        save_settings(provider_var.get(), choice, mode_var.get())

    keys_path = resource_path("..", "config", "keys.json")
    
    provider_to_key_name = {
        "GitHubAI": "GITHUB_TOKEN",
        "Groq": "GROQ_API_KEY",
        "OpenRoute": "OPENROUTE_API_KEY",
        "Unclose": "UNCLOSE_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Google": "GOOGLE_API_KEY"
    }

    def load_keys():
        abs_keys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "keys.json")
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
            abs_keys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "keys.json")
            os.makedirs(os.path.dirname(abs_keys_path), exist_ok=True)
            with open(abs_keys_path, "w", encoding="utf-8") as f:
                json.dump(keys, f, indent=4)
            if event is None:
                update_status("Settings saved")
                settings_win.destroy()
        save_settings(provider_var.get(), model_var.get(), mode_var.get())

    def toggle_password():
        if api_key_entry.cget("show") == "*":
            api_key_entry.configure(show="")
            eye_button.configure(text="👁")
        else:
            api_key_entry.configure(show="*")
            eye_button.configure(text="🔒")

    def update_models(provider):
        models = {
            "GitHubAI": ["openai/gpt-4o", "microsoft/phi-4", "meta/llama-3.3-70b-instruct", "deepseek/deepseek-r1", "openai/gpt-4o-mini", "meta/llama-4-maverick-17b-128e-instruct-fp8"],
            "Groq": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "groq/compound", "qwen/qwen3-32b", "meta-llama/llama-4-scout-17b-16e-instruct", "groq/compound-mini", "openai/gpt-oss-20b", "llama-3.1-8b-instant", "openai/gpt-oss-safeguard-20b"],
            "OpenRoute": ["xiaomi/mimo-v2-pro", "anthropic/claude-4.6-sonnet", "minimax/minimax-m2.7", "deepseek/deepseek-v3.2", "qwen/qwen3.6-plus:free", "anthropic/claude-4.6-opus", "openai/gpt-5.4", "google/gemini-3.1-pro-preview", "moonshotai/kimi-k2.5", "google/gemini-3.1-flash-lite-preview", "nousresearch/hermes-3-llama-3.1-405b:free", "qwen/qwen3-coder:free", "google/gemma-3-27b-it:free", "openrouter/free", "nvidia/nemotron-3-super-120b-a12b:free", "openai/gpt-oss-120b:free"],
            "Unclose": ["qwen3-vl:8b", "gpt-oss:latest", "deepseek-r1:14b-qwen-distill-q8_0"],
            "Anthropic": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4", "claude-sonnet-4", "claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"],
            "OpenAI": ["gpt-5.4", "gpt-5.4-pro", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5-mini", "gpt-5", "gpt-5-nano", "gpt-5.3-chat-latest", "gpt-4.1", "gpt-4o-mini"],
            "Google": ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        }
        model_list = models.get(provider, ["default-model"])
        model_menu.configure(values=model_list)
        
        current_settings = load_settings()
        if provider == current_settings.get("provider") and current_settings.get("model") in model_list:
            model_var.set(current_settings.get("model"))
        elif model_var.get() not in model_list:
            model_var.set(model_list[0])
            
        save_settings(provider, model_var.get(), mode_var.get())
            
        keys = load_keys()
        key_name = provider_to_key_name.get(provider)
        api_key_entry.delete(0, tk.END)
        if key_name and key_name in keys:
            api_key_entry.insert(0, keys[key_name])

    ctk.CTkLabel(settings_win, text="Provider:").pack(pady=(10, 0))
    provider_menu = ctk.CTkOptionMenu(settings_win, variable=provider_var, values=["GitHubAI", "Groq", "OpenRoute", "Unclose", "Anthropic", "OpenAI", "Google"], command=update_models)
    provider_menu.pack(pady=5)

    ctk.CTkLabel(settings_win, text="Model:").pack(pady=(10, 0))
    model_menu = ctk.CTkOptionMenu(settings_win, variable=model_var, values=[], command=on_model_change)
    model_menu.pack(pady=5)

    ctk.CTkLabel(settings_win, text="API Key:").pack(pady=(10, 0))
    key_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
    key_frame.pack(pady=5)

    api_key_entry = ctk.CTkEntry(key_frame, show="*", width=200)
    api_key_entry.pack(side="left")
    api_key_entry.bind("<KeyRelease>", save_key)

    eye_button = ctk.CTkButton(key_frame, text="🔒", width=30, command=toggle_password)
    eye_button.pack(side="left", padx=5)

    save_button = ctk.CTkButton(settings_win, text="Save", command=lambda: save_key(None))
    save_button.pack(pady=20)
    
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
settings_btn = ctk.CTkButton(root, text="", image=settings_img, width=30, height=30, fg_color="transparent", command=open_settings)
settings_btn.place(x=10, y=10)

root.configure(padx=20, pady=10)
root.configure(fg_color="#0f0f1a")

logo_pil = Image.open(resource_path("assets", "logo.png"))
logo_img = ctk.CTkImage(light_image=logo_pil, dark_image=logo_pil, size=(64, 64))
logo_label = ctk.CTkLabel(root, text="", image=logo_img)
logo_label.pack(pady=(10, 0), side="top")

title = ctk.CTkLabel(root, text="Prompt OS", font=ctk.CTkFont(size=22, weight="bold"))
title.pack(pady=20, side="top")

mode_selection = ctk.CTkSegmentedButton(root, values=["FAST", "THINKING", "PRO"], variable=mode_var, command=lambda m: save_settings(provider_var.get(), model_var.get(), m))
mode_selection.pack(pady=5)

input_frame = ctk.CTkFrame(root, fg_color="transparent")
input_frame.pack(pady=10, side="top")

text_input = ctk.CTkEntry(input_frame, font=("Arial", 14), width=320, placeholder_text="Ask anything...")
text_input.pack(side="left")

send_button = ctk.CTkButton(input_frame, text="Send", width=80, command=thread_handle_task)
send_button.pack(side="left", padx=10)

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