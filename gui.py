import tkinter as tk
from tkinter import messagebox
import subprocess

def run_scripts():
    url = url_entry.get()
    venue = venue_entry.get()

    if not url or not venue:
        messagebox.showerror("Input Error", "Please enter both Match URL and Venue ID. 1. Cheyenne 2. Laramie 3. Pawnee 4. Larkspur 5. Rawlins ")
        return

    try:
        # Run script 1 with arguments
        subprocess.run(["python", "scraperv2.py", url, venue], check=True)

        # Run script 2 (no args, or add if needed)
        subprocess.run(["python", "pointsv2.py"], check=True)

        # Run script 3
        subprocess.run(["python", "classify_shooters.py"], check=True)

        messagebox.showinfo("Success", "All scripts executed successfully.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script failed: {e}")

# GUI Setup
root = tk.Tk()
root.title("Score Updater")

tk.Label(root, text="Match URL:").pack(pady=(10,0))
url_entry = tk.Entry(root, width=50)
url_entry.pack()

tk.Label(root, text="Venue ID:").pack(pady=(10,0))
venue_entry = tk.Entry(root, width=20)
venue_entry.pack()

tk.Button(root, text="Run Scripts", command=run_scripts).pack(pady=20)

root.mainloop()
