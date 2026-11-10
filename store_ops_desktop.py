"""STORE OPS desktop: the complete existing web app, no local business database."""
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit

TITLE = "CoastYouth Retail STORE OPS"
VERSION = "1.0.1"
DEFAULT_SERVER = "https://operations.coastyfc.com"

def server_url(value):
    value = value.strip()
    if "://" not in value: value = "http://" + value
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError("Enter the server address only, such as https://operations.coastyfc.com")
    parts.port
    return value.rstrip("/")

class CloseGuard:
    def __init__(self, window):
        self.window, self.exiting, self.checking = window, False, False
    def closing(self):
        if self.exiting: return True
        if not self.checking:
            self.checking = True
            threading.Thread(target=self.check, daemon=True).start()
        return False
    def check(self):
        try:
            busy = self.window.evaluate_js('typeof hasUnfinishedWork === "function" && hasUnfinishedWork()')
            if busy:
                self.window.evaluate_js('typeof toast === "function" ? toast("Save or discard your unfinished work before closing STORE OPS.") : alert("Save your work before closing STORE OPS.")')
                return
            self.exiting = True
            self.window.destroy()
        except Exception:
            # Never interpret an unsuccessful work-state check as permission to close.
            pass
        finally:
            self.checking = False

def ops_window(address, hidden=False):
    import webview
    window = webview.create_window(TITLE, server_url(address) + "/", width=1366, height=900, min_size=(900, 650), hidden=hidden)
    guard = CloseGuard(window)
    window.events.closing += guard.closing
    window._ops_guard = guard
    return window

def configure(directory, address):
    import tkinter as tk
    from tkinter import ttk, messagebox
    root = tk.Tk(); root.title(TITLE); root.geometry("620x310"); root.resizable(False, False)
    frame = ttk.Frame(root, padding=24); frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Connect STORE OPS", font=("Segoe UI", 22, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Use the same server as your website, DESK and OFFICE.\nAll timecards, reservations and sales stay on that server.").pack(anchor="w", pady=18)
    ttk.Label(frame, text="Server address").pack(anchor="w")
    value = tk.StringVar(value=address); ttk.Entry(frame, textvariable=value).pack(fill="x", pady=6)
    chosen = []
    def save():
        try:
            url = server_url(value.get())
            directory.mkdir(parents=True, exist_ok=True)
            temp = directory / "connection.tmp"
            temp.write_text(json.dumps({"server": url}), encoding="utf-8")
            os.replace(temp, directory / "connection.json")
            chosen.append(url); root.destroy()
        except Exception as exc: messagebox.showerror(TITLE, str(exc), parent=root)
    ttk.Button(frame, text="Save & open STORE OPS", command=save).pack(anchor="e", pady=18)
    root.mainloop()
    return chosen[0] if chosen else None

def main():
    import sys
    import webview
    if "--smoke-test" in sys.argv:
        errors = []
        window = webview.create_window(TITLE, html="<html><body>STORE OPS</body></html>", hidden=True)
        def check():
            try:
                if not window.events.loaded.wait(20): raise RuntimeError("STORE OPS did not load")
                assert window.evaluate_js("1+1") == 2
            except Exception as exc: errors.append(str(exc))
            finally: window.destroy()
        webview.start(check, gui="edgechromium", private_mode=True)
        raise SystemExit(1 if errors else 0)
    directory = Path(os.environ.get("APPDATA", str(Path.home()))) / "CoastYouthRetailStoreOps"
    config = directory / "connection.json"
    address = DEFAULT_SERVER
    try: address = server_url(json.loads(config.read_text(encoding="utf-8"))["server"])
    except (OSError, ValueError, KeyError): pass
    if not config.exists() or "--configure" in sys.argv:
        address = configure(directory, address)
        if not address: return
    directory.mkdir(parents=True, exist_ok=True)
    ops_window(address)
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
    webview.start(gui="edgechromium", debug=False, private_mode=False, storage_path=str(directory / "webview"))

if __name__ == "__main__": main()
