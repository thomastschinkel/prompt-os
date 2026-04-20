import os, sys, shutil, subprocess, tempfile, tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

INSTALLER_TEMPLATE = """
import os, sys, shutil, subprocess, threading, tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PromptOS Installer")
        self.root.geometry("600x450")
        self.root.configure(bg="#0f0f1a")
        self.root.resizable(False, False)
        
        x = (self.root.winfo_screenwidth() // 2) - 300
        y = (self.root.winfo_screenheight() // 2) - 225
        self.root.geometry(f"+{x}+{y}")

        self.path = tk.StringVar(value=str(Path(os.environ["LOCALAPPDATA"]) / "PromptOS"))
        self.run_after = tk.BooleanVar(value=True)
        self.desktop_sc = tk.BooleanVar(value=True)
        
        self.s = ttk.Style()
        self.s.theme_use('default')
        self.s.configure("TProgressbar", thickness=8, troughcolor='#1a1a24', background='#7fb5ff', borderwidth=0)
        self.s.configure("TCheckbutton", background="#0f0f1a", foreground="#e0e0e0", font=("Segoe UI", 10))
        self.s.map("TCheckbutton", background=[('active', "#0f0f1a")], foreground=[('active', "#7fb5ff")])

        self.draw_main()

    def draw_main(self):
        for w in self.root.winfo_children(): w.destroy()
        
        tk.Label(self.root, text="PROMPT OS", font=("Segoe UI", 28, "bold"), fg="#7fb5ff", bg="#0f0f1a").pack(pady=(30, 10))
        tk.Label(self.root, text="A desktop AI agent that controls your local machine", font=("Segoe UI", 10), fg="#a9a9c5", bg="#0f0f1a").pack()

        p_frame = tk.Frame(self.root, bg="#0f0f1a", pady=30)
        p_frame.pack(fill="x", padx=50)
        
        tk.Label(p_frame, text="Installation Path", font=("Segoe UI", 9, "bold"), fg="#e0e0e0", bg="#0f0f1a").pack(anchor="w")
        e_frame = tk.Frame(p_frame, bg="#1a1a24")
        e_frame.pack(fill="x", pady=5)
        
        self.ent = tk.Entry(e_frame, textvariable=self.path, font=("Segoe UI", 10), bg="#1a1a24", fg="#ffffff", borderwidth=0, highlightthickness=1, highlightbackground="#3a3a4a")
        self.ent.pack(side="left", fill="x", expand=True, padx=5, ipady=5)
        
        tk.Button(e_frame, text="Browse", font=("Segoe UI", 9), bg="#2a2a3a", fg="#ffffff", relief="flat", padx=10, command=self.browse).pack(side="right")

        o_frame = tk.Frame(self.root, bg="#0f0f1a")
        o_frame.pack(fill="x", padx=50)
        
        ttk.Checkbutton(o_frame, text="Launch PromptOS after installation", variable=self.run_after).pack(anchor="w", pady=5)
        ttk.Checkbutton(o_frame, text="Create Desktop shortcut", variable=self.desktop_sc).pack(anchor="w", pady=5)

        self.btn = tk.Button(self.root, text="INSTALL", font=("Segoe UI", 11, "bold"), bg="#1f538d", fg="white", relief="flat", width=20, height=2, command=self.install)
        self.btn.pack(side="bottom", pady=40)

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.path.get())
        if d: self.path.set(str(Path(d) / "PromptOS"))

    def install(self):
        self.btn.config(state="disabled", text="INSTALLING...")
        self.ent.config(state="disabled")
        
        self.pb = ttk.Progressbar(self.root, length=500, mode='determinate')
        self.pb.pack(side="bottom", pady=20)
        
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        try:
            target = Path(self.path.get())
            if target.exists(): shutil.rmtree(target, ignore_errors=True)
            source = Path(sys._MEIPASS) / "app_files"
            if not source.exists(): source = Path(sys._MEIPASS).parent / "app_files"
            
            shutil.copytree(source, target, dirs_exist_ok=True)
            
            exe = target / "PromptOS.exe"
            ico = target / "lib" / "assets" / "logo.ico"
            if not ico.exists(): ico = exe
            
            if self.desktop_sc.get():
                self.sc(str(exe), str(Path(os.environ["USERPROFILE"]) / "Desktop" / "PromptOS.lnk"), str(ico))
            
            self.sc(str(exe), str(Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "PromptOS.lnk"), str(ico))
            
            if self.run_after.get():
                subprocess.Popen([str(exe)], cwd=str(target))
                
            self.root.after(0, self.done)
        except Exception as e:
            self.root.after(0, lambda: self.fail(str(e)))

    def sc(self, t, p, i):
        c = f"$s=(New-Object -COM WScript.Shell).CreateShortcut('{p}');$s.TargetPath='{t}';$s.IconLocation='{i}';$s.Save()"
        subprocess.run(["powershell", "-Command", c], capture_output=True)

    def fail(self, e):
        self.btn.config(state="normal", text="RETRY", command=self.install)
        tk.Label(self.root, text=f"Error: {e[:50]}", fg="#ff5555", bg="#0f0f1a").pack()

    def done(self):
        self.pb.destroy()
        for w in self.root.winfo_children():
            if w != self.btn: w.destroy()
        
        tk.Label(self.root, text="INSTALLATION COMPLETE", font=("Segoe UI", 18, "bold"), fg="#00e676", bg="#0f0f1a").pack(expand=True)
        self.btn.config(state="normal", text="FINISH", command=self.root.destroy, bg="#00e676")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
"""

def run():
    for d in ['build', 'dist']:
        if os.path.exists(d): shutil.rmtree(d)
    
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--clean", "--contents-directory=lib", f"--icon={os.path.abspath('assets/logo.ico')}", "--add-data=assets;assets", "--add-data=config;config", "--name=PromptOS", "main.py"], check=True)

    t = os.path.join(tempfile.gettempdir(), "_s.py")
    with open(t, "w", encoding="utf-8") as f: f.write(INSTALLER_TEMPLATE)
    
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--clean", f"--icon={os.path.abspath('assets/logo.ico')}", f"--add-data={os.path.abspath('dist/PromptOS')};app_files", "--name=PromptOS_Setup", t], check=True)
    
    try: os.remove(t)
    except: pass

if __name__ == "__main__":
    run()
