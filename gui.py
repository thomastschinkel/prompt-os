import tkinter as tk
from PIL import Image, ImageTk
import subprocess
from ai import LLM
import threading

def handle_task():
    user_input = text_input.get()
    ai_answer_box.config(text="Thinking...", fg="gray")
    llm = LLM(model_provider="Groq")
    response = llm.generate_response(user_input)

    if response["tool"] == "CMD":
        while response["status"] != "y":
            result = subprocess.run(response["input"], shell=True, capture_output=True, text=True)
            output = f"{result.stdout} | {result.stderr}"
            response = llm.generate_response(user_input, validate_response=True, output=output)
            ai_answer_box.config(text=response["response"])

    ai_answer_box.config(fg="black")

def thread_handle_task():
    threading.Thread(target=handle_task).start()

root = tk.Tk()
root.title("Prompt OS")
root.geometry("500x500")

title = tk.Label(root, text="Prompt OS", font=("Arial", 24, "bold"))
title.pack(pady=20, side="top")

input_frame = tk.Frame(root)
input_frame.pack(pady=10, side="top")

record_btn_pil = Image.open("assets/Basic_red_dot.png")
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