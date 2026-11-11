"""One update check before desktop work starts; never opens a store database."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
from urllib.request import Request, urlopen

REPO = 'm404ntfd/mgc-yfc-operations'
APPS = {
    'pos': ('CoastYouth Retail DESK', 'MGC-YFC-POS-Setup-v'),
    'office': ('CoastYouth Retail OFFICE', 'CoastYouth-Retail-OFFICE-Setup-v'),
    'ops': ('CoastYouth Retail STORE OPS', 'CoastYouth-Retail-STORE-OPS-Setup-v'),
    'remote': ('CoastYouth Retail Server Admin', 'MGC-YFC-Operations-Setup-v'),
    'server': ('CoastYouth Retail Server', 'MGC-YFC-Operations-Setup-v'),
}
_instance_handles = []


def claim_instance(app):
    """Keep a second launch from updating an instance that has work in progress."""
    if not getattr(sys, 'frozen', False):
        return True
    import ctypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel.CreateMutexW(None, False, 'Local\\CoastYouthStartup-' + app)
    error = ctypes.get_last_error()
    if not handle:
        raise OSError('Unable to protect the application startup.')
    _instance_handles.append(handle)
    if error == 183:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk();root.withdraw()
        messagebox.showinfo(APPS[app][0], 'This application is already running. Return to its existing window to finish your work.', parent=root)
        root.destroy()
        return False
    return True


def check_release(app, current):
    from pos_updater import version
    prefix = APPS[app][1]
    request = Request('https://api.github.com/repos/' + REPO + '/releases/latest',
                      headers={'User-Agent': 'CoastYouth-Startup-Updater', 'Accept': 'application/vnd.github+json'})
    with urlopen(request, timeout=10) as response:
        raw = response.read(1000001)
    if len(raw) > 1000000:
        raise ValueError('Update information is too large.')
    release = json.loads(raw)
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('A stable published release is required.')
    candidates = []
    for asset in release.get('assets', []):
        match = re.fullmatch(re.escape(prefix) + r'(\d+\.\d+\.\d+)\.exe', asset.get('name', ''))
        if match:
            candidates.append((version(match[1]), match[1], asset))
    if not candidates:
        raise ValueError('No compatible installer was found. Use the update area to check again later.')
    _, target, asset = max(candidates, key=lambda candidate: candidate[0])
    if version(target) <= version(current):
        return None
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', asset.get('digest', '')):
        raise ValueError('The update does not have verified download information.')
    if not asset.get('browser_download_url', '').startswith('https://github.com/' + REPO + '/releases/download/'):
        raise ValueError('Unexpected update download address.')
    return {'app': app, 'current': current, 'version': target, 'name': APPS[app][0]}


def stage_installer(offer, settings):
    """Download only. A failed download never closes the application or changes settings."""
    from pos_updater import verified_installer
    if offer['app'] == 'server':
        raise ValueError('Shared-server updates must use administrator and staff-readiness checks.')
    if offer['app'] == 'remote' and (Path(sys.executable).resolve().parent / 'server.py').exists():
        raise ValueError('This computer has the combined server. Update it through the server Updates tab.')
    raw, digest = verified_installer(offer['version'], offer['app'])
    folder = Path(settings).parent / 'updates' / ('startup-' + secrets.token_hex(16))
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / 'installer.exe'
    path.write_bytes(raw)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Installer verification failed. Nothing was installed.')
    return path, digest


def launch_installer(offer, settings, path, digest):
    """Called before any work screen opens, only after the user's Update selection."""
    if not getattr(sys, 'frozen', False):
        raise ValueError('Automatic installation requires the installed Windows application.')
    if offer['app'] not in ('pos', 'office', 'ops', 'remote'):
        raise ValueError('Unsupported desktop application.')
    exe = Path(sys.executable).resolve()
    if offer['app'] == 'remote' and (exe.parent / 'server.py').exists():
        raise ValueError('Use the combined server Updates tab on this computer.')
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Installer verification failed. Nothing was installed.')
    helper = path.parent / 'startup-update-helper.exe'
    shutil.copy2(exe, helper)
    meta = {'installer': str(path), 'sha256': digest, 'exe': str(exe), 'pid': os.getpid(),
            'version': offer['version'], 'settings': str(settings)}
    if offer['app'] == 'remote':
        meta['install_type'] = 'remote'
    manifest = path.parent / 'install.json'
    manifest.write_text(json.dumps(meta), encoding='utf-8')
    subprocess.Popen([str(helper), '--apply-pos-update', str(manifest)],
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def startup_update(app, current, settings):
    """Return True only when a verified installer helper has taken over startup."""
    if not getattr(sys, 'frozen', False):
        return False
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title(APPS[app][0] + ' — Updates')
    root.geometry('620x330')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Checking for updates', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    text = tk.StringVar(value='Checking for a newer version of ' + APPS[app][0] + '…')
    ttk.Label(frame, textvariable=text, wraplength=560, font=('Segoe UI', 11)).pack(fill='x', pady=18)
    progress = ttk.Progressbar(frame, mode='indeterminate')
    progress.pack(fill='x', pady=8)
    progress.start(15)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=16)
    results = queue.Queue()
    state = {'offer': None, 'installing': False, 'launched': False, 'closed': False, 'timer': None}

    def finish():
        state['closed'] = True
        if state['timer']:
            root.after_cancel(state['timer'])
            state['timer'] = None
        root.destroy()

    def close():
        if not state['installing']:
            finish()

    later = ttk.Button(buttons, text='Continue opening', command=close, padding=12)
    later.pack(side='right')
    update = ttk.Button(buttons, text='Update', padding=12)

    def work(fn):
        def worker():
            try: results.put(('ok', fn()))
            except Exception as exc: results.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def install():
        if state['installing'] or not state['offer']:
            return
        state['installing'] = True
        update.configure(state='disabled')
        later.configure(state='disabled')
        text.set('Downloading and verifying the update. The application will restart when it is ready. Your saved data and connection settings will be kept.')
        progress.start(15)
        work(lambda: stage_installer(state['offer'], settings))

    update.configure(command=install)
    root.protocol('WM_DELETE_WINDOW', close)

    def poll():
        if state['closed']:
            return
        try:
            kind, value = results.get_nowait()
        except queue.Empty:
            state['timer'] = root.after(100, poll)
            return
        progress.stop()
        if kind == 'error':
            state['installing'] = False
            text.set('The update could not be completed. ' + value + '\nYou can continue opening the application and try again later.')
            later.configure(state='normal', text='Continue opening')
            update.pack_forget()
        elif state['installing']:
            try:
                launch_installer(state['offer'], settings, *value)
                state['launched'] = True
                finish()
                return
            except Exception as exc:
                state['installing'] = False
                text.set('The application could not start the update. ' + str(exc))
                later.configure(state='normal', text='Continue opening')
                update.configure(state='normal')
        elif value is None:
            close()
            return
        else:
            state['offer'] = value
            frame.winfo_children()[0].configure(text='Update available')
            text.set(value['name'] + ' ' + value['version'] + ' is available.\n\nSelect Update to install it and restart this application. Your saved data and connection settings will be kept.')
            later.configure(text='Not now')
            update.pack(side='right', padx=12)
        state['timer'] = root.after(100, poll)

    # Surface a failed helper run once, instead of immediately repeating the update.
    result_path = Path(settings).parent / 'pos-update-result.json'
    failure = None
    try:
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if result.get('ok') is False and not result.get('acknowledged'):
            failure = result.get('error') or 'The previous installer did not finish.'
            result['acknowledged'] = True
            result_path.write_text(json.dumps(result), encoding='utf-8')
    except (OSError, ValueError):
        pass
    work(lambda: check_release(app, current))
    if failure:
        # Still perform this launch's check, but keep the failure visible until dismissed.
        progress.stop()
        text.set('The previous update did not finish. ' + failure + '\nContinue opening to use the application and review updates in settings.')
    else:
        state['timer'] = root.after(100, poll)
    root.mainloop()
    return state['launched']


def server_offer(root, offer, accept):
    """Shared server: consent leads to the authenticated, coordinated update flow."""
    import tkinter as tk
    from tkinter import ttk
    dialog = tk.Toplevel(root)
    dialog.title('Server update available')
    dialog.geometry('610x310')
    dialog.resizable(False, False)
    dialog.transient(root)
    frame = ttk.Frame(dialog, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Update available', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, wraplength=550, text='Server ' + offer['version'] + ' is available.\n\nSelect Update to sign in as an administrator if needed. Staff will be notified and allowed to finish their work. The server and web app will update and restart when everyone is ready.').pack(fill='x', pady=20)
    row = ttk.Frame(frame)
    row.pack(fill='x')
    ttk.Button(row, text='Not now', command=dialog.destroy, padding=12).pack(side='right')
    def proceed():
        dialog.destroy()
        accept(offer['version'])
    ttk.Button(row, text='Update', command=proceed, padding=12).pack(side='right', padx=12)
    dialog.grab_set()
    return dialog
