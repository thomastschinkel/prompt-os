import tkinter as tk
from PIL import Image, ImageTk
import subprocess
from src.ai import LLM
import threading
from io import StringIO
from src.utils import search_web, resource_path, decode_output

def handle_task():
    user_input = text_input.get()
    ai_answer_box.config(text="Thinking...", fg="gray")
    send_button.config(state="disabled")
    llm = LLM(model_provider="Groq")
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

        root.after(0, lambda r=response: ai_answer_box.config(text=r["response"]))
    root.after(0, lambda r=response: ai_answer_box.config(text=r["response"], fg="black"))
    root.after(0, lambda: send_button.config(state="normal"))

def thread_handle_task():
    threading.Thread(target=handle_task, daemon=True).start()

root = tk.Tk()
root.title("Prompt OS")
root.geometry("500x500")

title = tk.Label(root, text="Prompt OS", font=("Arial", 24, "bold"))
title.pack(pady=20, side="top")

input_frame = tk.Frame(root)
input_frame.pack(pady=10, side="top")

record_btn_pil = Image.open(resource_path("..", "assets", "Basic_red_dot.png"))
record_btn_pil = record_btn_pil.resize((32, 32))
record_button_image = ImageTk.PhotoImage(record_btn_pil)
record_button = tk.Button(input_frame, image=record_button_image, borderwidth=0)
record_button.pack(pady=10, side="left", padx=15)

text_input = tk.Entry(input_frame, font=("Arial", 14), width=30, justify="center")
text_input.pack(pady=10, side="left")

send_button = tk.Button(input_frame, text="Send", font=("Arial", 14), command=thread_handle_task)
send_button.pack(pady=10, side="left", padx=20)

ai_answer_box = tk.Label(root, text="", font=("Arial", 14), bg="lightgray", fg="black", height=6, width=40, relief="sunken", bd=2, anchor="nw", justify="left", wraplength=400)
ai_answer_box.pack(pady=20, side="top")

root.mainloop()