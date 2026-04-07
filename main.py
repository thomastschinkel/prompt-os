import tkinter as tk
from PIL import Image, ImageTk
import subprocess
from src.ai import LLM
import threading
from io import StringIO
import sys
from src.utils import search_web, resource_path, decode_output, listen
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk
from bs4 import BeautifulSoup

is_recording = False
recording_stop_event = threading.Event()

def update_status(text):
    root.after(0, lambda: status_label.configure(text=text))

def listen_and_update_input():
    global is_recording, recording_stop_event

    if is_recording:
        recording_stop_event.set()
        is_recording = False
        record_button.configure(fg_color="#3a1a1a", text="⏺")
        return

    is_recording = True
    recording_stop_event.clear()
    record_button.configure(fg_color="#7a1a1a", text="⏹")
    text_input.configure(state="disabled", text_color="gray")

    def task():
        global is_recording
        root.after(0, lambda: text_input.configure(state="normal"))
        root.after(0, lambda: text_input.delete(0, tk.END))
        root.after(0, lambda: text_input.insert(0, "Listening..."))
        root.after(0, lambda: text_input.configure(state="disabled"))
        try:
            transcript = listen(stop_event=recording_stop_event)
            root.after(0, lambda: text_input.configure(state="normal", text_color="#e0e0e0"))
            root.after(0, lambda: text_input.delete(0, tk.END))
            root.after(0, lambda: text_input.insert(0, transcript))
        except Exception as e:
            root.after(0, lambda: text_input.configure(state="normal", text_color="#e0e0e0"))
            root.after(0, lambda: text_input.delete(0, tk.END))
            root.after(0, lambda err=e: text_input.insert(0, f"Error: {err}"))
        finally:
            is_recording = False
            root.after(0, lambda: record_button.configure(fg_color="#3a1a1a", text="⏺"))
            root.after(0, lambda: text_input.configure(state="normal", text_color="#e0e0e0"))

    threading.Thread(target=task, daemon=True).start()

def update_answer_box(text, color="#e0e0e0"):
    ai_answer_box.configure(state="normal")
    ai_answer_box.delete("1.0", tk.END)
    ai_answer_box.insert(tk.END, text)
    ai_answer_box.configure(text_color=color)
    ai_answer_box.configure(state="disabled")
    ai_answer_box.see(tk.END)

def handle_task():
    user_input = text_input.get()
    provider = provider_var.get()
    model = model_var.get()
    root.after(0, lambda: update_answer_box("Thinking...", "#888888"))
    send_button.configure(state="disabled")
    llm = LLM(provider=provider, model_name=model)
    response = llm.generate_response(user_input)

    while response["status"] != "y":
        update_status(f"Using tool: {response['tool']}...")
        if response["tool"] == "CMD":
            result = subprocess.run(response["input"], shell=True, capture_output=True, text=False)
            stdout = decode_output(result.stdout or b"")
            stderr = decode_output(result.stderr or b"")
            output = f"{stdout} | {stderr}".strip()

        elif response["tool"] == "FILE_HANDLER":
            if response["mode"] != "r":
                try:
                    with open(response["path"], response["mode"], encoding="utf-8") as f:
                        f.write(response["content"])
                    output = f"File written to {response["path"]} with mode {response["mode"]}"
                except Exception:
                    output = f"Error writing to file {response["path"]} with mode {response["mode"]}"
            else:
                try:
                    with open(response["path"], response["mode"], encoding="utf-8") as f:
                        content = f.read()
                    output = f"Content of {response["path"]}: {content} with mode {response["mode"]}"
                except Exception:
                    output = f"Error reading file {response["path"]} with mode {response["mode"]}"

        elif response["tool"] == "EXEC_PY":
            try:
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = StringIO(), StringIO()
                exec(response["code"], {})
                out = sys.stdout.getvalue()
            except Exception as e:
                out = f"ERROR: {str(e)}"
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            output = out.strip() or "Executed (no output)"

        elif response["tool"] == "SEARCH_WEB":
            output = search_web(response["input"], max_results=response["max_results"])

        elif response["tool"] == "READ_EFF_HTML":
            with open(response["path"], "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "lxml")
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            clean_text = soup.get_text(separator="\n")
            lines = (line.strip() for line in clean_text.splitlines())
            output = "\n".join(line for line in lines if line)

        else:
            output = f"Unknown tool: {response['tool']}"

        response = llm.generate_response(user_input, validate_response=True, output=output)

        root.after(0, lambda r=response: update_answer_box(r["response"], "#888888"))
    root.after(0, lambda r=response: update_answer_box(r["response"], "#e0e0e0"))
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
    settings_win.geometry("300x200")
    settings_win.transient(root)
    
    def update_models(provider):
        models = {
            "GitHubAI": ["openai/gpt-4o", "microsoft/phi-4", "meta/llama-3.3-70b-instruct", "deepseek/deepseek-r1", "openai/gpt-4o-mini", "meta/llama-4-maverick-17b-128e-instruct-fp8"],
            "Groq": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "groq/compound", "qwen/qwen3-32b", "meta-llama/llama-4-scout-17b-16e-instruct", "groq/compound-mini", "openai/gpt-oss-20b", "llama-3.1-8b-instant", "openai/gpt-oss-safeguard-20b"],
            "OpenRoute": ["xiaomi/mimo-v2-pro", "anthropic/claude-4.6-sonnet", "minimax/minimax-m2.7", "deepseek/deepseek-v3.2", "qwen/qwen3.6-plus:free", "anthropic/claude-4.6-opus", "openai/gpt-5.4", "google/gemini-3.1-pro-preview", "moonshotai/kimi-k2.5", "google/gemini-3.1-flash-lite-preview", "qwen/qwen3.6-plus:free", "stepfun/step-3.5-flash:free", "openrouter/free"],
            "Unclose": ["qwen3-vl:8b", "gpt-oss:latest", "deepseek-r1:14b-qwen-distill-q8_0"]
        }
        model_list = models.get(provider, ["default-model"])
        model_menu.configure(values=model_list)
        if model_var.get() not in model_list:
            model_var.set(model_list[0])

    ctk.CTkLabel(settings_win, text="Provider:").pack(pady=(10, 0))
    provider_menu = ctk.CTkOptionMenu(settings_win, variable=provider_var, values=["GitHubAI", "Groq", "OpenRoute", "Unclose"], command=update_models)
    provider_menu.pack(pady=5)
    
    ctk.CTkLabel(settings_win, text="Model:").pack(pady=(10, 0))
    model_menu = ctk.CTkOptionMenu(settings_win, variable=model_var, values=[])
    model_menu.pack(pady=5)
    
    update_models(provider_var.get())

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Prompt OS")
root.geometry("500x500")

settings_pil = Image.open(resource_path("..", "assets", "settings.png"))
settings_img = ctk.CTkImage(light_image=settings_pil, dark_image=settings_pil, size=(36, 36))
settings_btn = ctk.CTkButton(root, text="", image=settings_img, width=30, height=30, fg_color="transparent", command=open_settings)
settings_btn.place(x=10, y=10)

root.configure(padx=20, pady=10)
root.configure(fg_color="#0f0f1a")

title = ctk.CTkLabel(root, text="Prompt OS", font=ctk.CTkFont(size=22, weight="bold"))
title.pack(pady=20, side="top")

provider_var = ctk.StringVar(value="GitHubAI")
model_var = ctk.StringVar(value="openai/gpt-4o-mini")

input_frame = ctk.CTkFrame(root, fg_color="transparent")
input_frame.pack(pady=10, side="top")

record_btn_pil = Image.open(resource_path("..", "assets", "Basic_red_dot.png"))
record_button_image = ctk.CTkImage(light_image=record_btn_pil, dark_image=record_btn_pil, size=(32, 32))
record_button = ctk.CTkButton(
    input_frame, text="⏺", width=40, height=36,
    fg_color="#3a1a1a", hover_color="#5a2020",
    text_color="#E24B4A", corner_radius=8,
    command=listen_and_update_input
)
record_button.pack(side="left", padx=15)

text_input = ctk.CTkEntry(input_frame, font=("Arial", 14), width=240, placeholder_text="Ask anything...")
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
ai_answer_box.configure(state="disabled")


root.mainloop()