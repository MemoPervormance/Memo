"""
CroixAI — Key Generator (standalone GUI).
Erstellt License Keys und speichert sie lokal in keys.csv.
Kompiliere zu keygen.exe mit: pyinstaller --onefile keygen_gui.py
"""
import csv, secrets, string, datetime, tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

CSV = Path(__file__).parent / "keys.csv"
ALPH = (string.ascii_uppercase + string.digits).translate(str.maketrans("","","O0I1"))

def gen_key():
    return "CROIX-" + "-".join("".join(secrets.choice(ALPH) for _ in range(4)) for _ in range(4))

def generate():
    note  = e_note.get().strip()
    days  = e_days.get().strip()
    count = int(e_count.get().strip() or "1")

    expires = ""
    if days:
        try:
            exp = datetime.datetime.now() + datetime.timedelta(days=int(days))
            expires = exp.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Anzahl Tage.")
            return

    keys = [gen_key() for _ in range(count)]
    now  = datetime.datetime.now().strftime("%Y-%m-%d")

    new_file = not CSV.exists()
    with open(CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["key","note","created","expires","hwid","revoked"])
        for k in keys:
            w.writerow([k, note, now, expires, "", "0"])

    result_text.delete("1.0", tk.END)
    for k in keys:
        result_text.insert(tk.END, k + "\n")

    lbl_status.config(text=f"✓  {count} Key(s) generiert — gespeichert in keys.csv", fg="#00e676")

def copy_keys():
    keys = result_text.get("1.0", tk.END).strip()
    if keys:
        root.clipboard_clear()
        root.clipboard_append(keys)
        lbl_status.config(text="Keys in Zwischenablage kopiert ✓", fg="#00e5ff")

# ── GUI ──────────────────────────────────────────────────
root = tk.Tk()
root.title("CroixAI — Key Generator")
root.configure(bg="#0f0f1a")
root.geometry("520x440")
root.resizable(False, False)

FONT     = ("Segoe UI", 11)
FONT_BIG = ("Segoe UI", 13, "bold")
BG       = "#0f0f1a"
BG2      = "#161624"
FG       = "#e8e8f0"
FG2      = "#9090b0"
ACC      = "#7c4dff"
ACC2     = "#00e5ff"

tk.Label(root, text="CROIXAI  —  KEY GENERATOR", font=("Segoe UI", 16, "bold"),
         bg=BG, fg=ACC2).pack(pady=(18,14))

frame = tk.Frame(root, bg=BG2, padx=20, pady=16, relief="flat")
frame.pack(fill="x", padx=20)

def lrow(parent, text, row):
    tk.Label(parent, text=text, font=FONT, bg=BG2, fg=FG2, anchor="w", width=22).grid(row=row,column=0,sticky="w",pady=5)

def entry(parent, row):
    e = tk.Entry(parent, font=FONT, bg="#1c1c2e", fg=FG, insertbackground=FG2, relief="flat",
                 bd=0, highlightthickness=1, highlightcolor=ACC, highlightbackground="#1e1e30", width=24)
    e.grid(row=row, column=1, sticky="ew", pady=5, padx=(8,0))
    return e

lrow(frame, "Kundenname / Notiz:", 0);  e_note  = entry(frame, 0)
lrow(frame, "Gültig (Tage, leer=∞):", 1); e_days  = entry(frame, 1)
lrow(frame, "Anzahl Keys:", 2);          e_count = entry(frame, 2); e_count.insert(0, "1")
frame.columnconfigure(1, weight=1)

btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=12)

def styled_btn(parent, text, cmd, color=ACC):
    b = tk.Button(parent, text=text, command=cmd, font=FONT_BIG, bg=color,
                  fg="white", relief="flat", padx=16, pady=8, cursor="hand2",
                  activebackground=color, activeforeground="white", bd=0)
    b.pack(side="left", padx=6)
    return b

styled_btn(btn_frame, "⚡ Generieren", generate, ACC)
styled_btn(btn_frame, "📋 Kopieren", copy_keys, "#1c1c2e")

tk.Label(root, text="Generierte Keys:", font=("Segoe UI", 10), bg=BG, fg=FG2).pack(anchor="w", padx=20)

result_text = tk.Text(root, font=("Consolas", 12), bg="#1c1c2e", fg=ACC2,
                       relief="flat", height=6, padx=10, pady=8,
                       insertbackground=FG, wrap="none", state="normal")
result_text.pack(fill="both", padx=20, pady=(4,8))

lbl_status = tk.Label(root, text="", font=("Segoe UI", 10), bg=BG, fg=FG2)
lbl_status.pack(pady=(0,12))

root.mainloop()
