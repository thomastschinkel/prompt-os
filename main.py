import tkinter as tk
from PIL import Image, ImageTk
import subprocess
from src.ai import LLM
import threading
from io import StringIO
import sys
from src.utils import search_web, resource_path, decode_output, listen
from tkinter.scrolledtext import ScrolledText

def listen_and_update_input():
    text_input.delete(0, tk.END)
    text_input.insert(0, "Listening...")
    root.update()
    transcript = listen()
    text_input.delete(0, tk.END)
    text_input.insert(0, transcript)

def update_answer_box(text, color="black"):
    ai_answer_box.config(state="normal")
    ai_answer_box.delete("1.0", tk.END)
    ai_answer_box.insert(tk.END, text)
    ai_answer_box.config(fg=color)
    ai_answer_box.config(state="disabled")
    ai_answer_box.see(tk.END)

def handle_task():
    user_input = text_input.get()
    provider = model_var.get()
    root.after(0, lambda: update_answer_box("Thinking...", "gray"))
    send_button.config(state="disabled")
    llm = LLM(model_provider=provider)
    response = llm.generate_response(user_input)

    while response["status"] != "y":
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

        root.after(0, lambda r=response: update_answer_box(r["response"], "gray"))
    root.after(0, lambda r=response: update_answer_box(r["response"], "black"))
    root.after(0, lambda: send_button.config(state="normal"))

    with open("config/memory.txt", "a", encoding="utf-8") as mem_file:
        mem_file.write(f"{response["memory"]}\n" if response["memory"] else "")

def thread_handle_task():
    threading.Thread(target=handle_task, daemon=True).start()

root = tk.Tk()
root.title("Prompt OS")
root.geometry("500x500")

title = tk.Label(root, text="Prompt OS", font=("Arial", 24, "bold"))
title.pack(pady=20, side="top")

model_var = tk.StringVar(value="OpenAI")
model_switch_frame = tk.Frame(root)
model_switch_frame.pack(pady=5)

tk.Radiobutton(model_switch_frame, text="OpenAI", variable=model_var, value="OpenAI").pack(side="left")
tk.Radiobutton(model_switch_frame, text="Groq", variable=model_var, value="Groq").pack(side="left")

input_frame = tk.Frame(root)
input_frame.pack(pady=10, side="top")

record_btn_pil = Image.open(resource_path("..", "assets", "Basic_red_dot.png"))
record_btn_pil = record_btn_pil.resize((32, 32))
record_button_image = ImageTk.PhotoImage(record_btn_pil)
record_button = tk.Button(input_frame, image=record_button_image, borderwidth=0, command=listen_and_update_input)
record_button.pack(pady=10, side="left", padx=15)

text_input = tk.Entry(input_frame, font=("Arial", 14), width=30, justify="center")
text_input.pack(pady=10, side="left")

send_button = tk.Button(input_frame, text="Send", font=("Arial", 14), command=thread_handle_task)
send_button.pack(pady=10, side="left", padx=20)

ai_answer_box = ScrolledText(
    root,font=("Arial", 14), bg="lightgray", fg="black", height=12, width=36, wrap="word", relief="sunken", bd=2)
ai_answer_box.pack(pady=20, side="top")
ai_answer_box.config(state="disabled")


root.mainloop()