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
    provider = model_var.get()
    root.after(0, lambda: update_answer_box("Thinking...", "#888888"))
    send_button.configure(state="disabled")
    llm = LLM(model_provider=provider)
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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Prompt OS")
root.geometry("500x500")

root.configure(padx=20, pady=10)
root.configure(fg_color="#0f0f1a")

title = ctk.CTkLabel(root, text="Prompt OS", font=ctk.CTkFont(size=22, weight="bold"))
title.pack(pady=20, side="top")

model_var = ctk.StringVar(value="GitHubAI")
model_switch = ctk.CTkSegmentedButton(root, values=["GitHubAI", "Groq", "OpenRoute", "Unclose"], variable=model_var)
model_switch.pack(pady=8)

input_frame = ctk.CTkFrame(root, fg_color="transparent")
input_frame.pack(pady=10, side="top")

record_btn_pil = Image.open(resource_path("..", "assets", "Basic_red_dot.png"))
record_btn_pil = record_btn_pil.resize((32, 32))
record_button_image = ImageTk.PhotoImage(record_btn_pil)
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