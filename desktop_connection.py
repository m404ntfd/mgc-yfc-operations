"""Read-only startup connection checks; never opens a business database."""
import json
import queue
import ssl
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

USER_AGENT = 'CoastYouth-Retail-Desktop/0.57.0'
PUBLIC_SERVER = 'https://operations.coastyfc.com'


def server_url(value):
    if not isinstance(value, str):
        raise ValueError('Enter a server address.')
    value = value.strip()
    if '://' not in value:
        host = value.split('/')[0].split(':')[0].lower()
        value = ('https://' if host == 'operations.coastyfc.com' else 'http://') + value
    parts = urlsplit(value)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username or parts.password or parts.path not in ('', '/')
            or parts.query or parts.fragment or any(c.isspace() for c in value)):
        raise ValueError('Enter only the server address, such as https://operations.coastyfc.com or http://192.168.1.20:8080.')
    try:
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError()
    except ValueError:
        raise ValueError('Enter a valid server port.') from None
    return value.rstrip('/')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe_server(address, app='office'):
    """No cookies, credentials or writes. Never follows a redirect to another server."""
    address = server_url(address)
    opener = build_opener(ProxyHandler({}), NoRedirect())

    def read(path, limit):
        request = Request(address + path, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
        with opener.open(request, timeout=8) as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('The address returned an unexpected response. Check the server address.')
        return raw

    try:
        try:
            session = json.loads(read('/api/session', 128000))
        except (json.JSONDecodeError, UnicodeError):
            raise ValueError('This address did not return the CoastYouth server. Check the address or contact your administrator.') from None
        if not isinstance(session, dict) or session.get('application') != 'thrift-mart-dispatch':
            raise ValueError('This is not a compatible CoastYouth server. Check the server address.')
        if app == 'pos' and b'kioskSetupDialog' not in read('/pos.js', 2000000):
            raise ValueError('The server needs a DESK-compatible update. Ask an administrator to update the server, then retry.')
        return address
    except HTTPError as exc:
        exc.close()
        if 300 <= exc.code < 400:
            raise ValueError('The server redirected the connection. Enter its final HTTPS address; automatic redirects are not allowed.') from None
        if exc.code in (401, 403):
            raise ValueError('The server refused this connection. Ask an administrator to check remote access permissions, then retry.') from None
        raise ValueError('The server is unavailable (HTTP ' + str(exc.code) + '). Check the address and try again.') from None
    except (ssl.SSLError, URLError, OSError) as exc:
        reason = getattr(exc, 'reason', exc)
        if isinstance(reason, ssl.SSLError):
            raise ValueError('The secure connection could not be verified. Check this computer’s date and the server certificate with your administrator.') from None
        raise ValueError('The server did not respond. Check that the server is running and your internet or VPN connection is connected.') from None


def reconnect_desktop(bridge, app, address, exit_code=''):
    """Verify a new endpoint before changing only this app's saved server address."""
    import os
    import secrets
    from pathlib import Path
    from pos_kiosk import KioskStore
    try:
        if app not in ('pos','office') or not bridge._trusted():
            raise ValueError('Open the configured application before changing its server.')
        if bridge._window.evaluate_js('window.desktopConnectionCanChange ? window.desktopConnectionCanChange() : false') is not True:
            raise ValueError('Finish or save current work before changing the server connection.')
        candidate=server_url(address)
        path=bridge._store.path if app=='pos' else Path(os.environ.get('APPDATA',str(Path.home())))/'CoastYouthRetailOffice'/'settings.json'
        store=bridge._store if app=='pos' else KioskStore(path)
        if app=='pos' and candidate!=bridge._address and store.configured and not store.verify(exit_code):
            raise ValueError('Enter the current admin exit passcode to change this DESK server.')
        probe_server(candidate,app)
        # Recheck after the network operation so intervening edits cannot be lost.
        if not bridge._trusted():
            raise ValueError('The application page changed. Reopen connection settings and try again.')
        if bridge._window.evaluate_js('window.desktopConnectionCanChange ? window.desktopConnectionCanChange() : false') is not True:
            raise ValueError('New work is in progress. Save it before reconnecting.')
        previous_data=dict(store.data)
        store.data['server']=candidate
        try:store.save()
        except Exception:
            store.data=previous_data
            raise
        bridge._store=store;bridge._address=candidate
        if app=='pos':bridge._nonce=secrets.token_hex(32)
        else:bridge._signed_in=False;bridge._kiosk=None
        if hasattr(bridge,'_updates'):
            from pos_updater import PosUpdater
            previous=bridge._updates
            bridge._updates=PosUpdater(bridge,app=app,current=previous.version)
        try:bridge._window.load_url(candidate+('/pos?kiosk=1&setup=1' if app=='pos' else '/office?setup=1'))
        except Exception:
            return {'error':'The server address was saved. Close and reopen the application to sign in and register this PC.','saved':True}
        return {'ok':True}
    except Exception as exc:
        return {'error':str(exc)}


def connect_before_open(app, address, save, *, configure=False, authorize=None, on_register=None):
    """Allow retry/address correction before any work screen or sale is opened.

    Only the UI thread saves a verified address. Failed, canceled or abandoned
    attempts leave the saved connection and device identity unchanged.
    """
    import tkinter as tk
    from tkinter import ttk
    name = {'pos': 'DESK', 'office': 'OFFICE', 'ops': 'STORE OPS'}[app]
    root = tk.Tk()
    root.title('CoastYouth Retail ' + name + ' — Connection')
    root.geometry('760x480')
    root.resizable(False, False)
    style = ttk.Style(root)
    style.configure('Connection.TButton', padding=(14, 12))
    frame = ttk.Frame(root, padding=26)
    frame.pack(fill='both', expand=True)
    heading = tk.StringVar(value='Connect to ' + name)
    status = tk.StringVar(value='Check the server address, then select Connect.')
    value = tk.StringVar(value=address)
    ttk.Label(frame, textvariable=heading, font=('Segoe UI', 21, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Server address', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(22, 5))
    entry = ttk.Entry(frame, textvariable=value, font=('Segoe UI', 13))
    entry.pack(fill='x', ipady=7)
    ttk.Label(frame, textvariable=status, wraplength=640, font=('Segoe UI', 11)).pack(anchor='w', pady=(18, 10))
    progress = ttk.Progressbar(frame, mode='indeterminate')
    progress.pack(fill='x')
    ttk.Label(frame, text='Using a VPN? Connect it first, then retry.\nFor access over the internet: ' + PUBLIC_SERVER+'\nAfter connecting, sign in with an administrator account to register this PC.',
              wraplength=640, font=('Segoe UI', 10)).pack(anchor='w', pady=(14, 0))
    buttons = ttk.Frame(frame)
    buttons.pack(side='bottom', fill='x', pady=(12, 0))
    results = queue.Queue()
    selected = []
    state = {'busy': False, 'editing': configure, 'closed': False, 'timer': None}

    def close():
        state['closed'] = True
        progress.stop()
        if state['timer'] is not None:
            root.after_cancel(state['timer'])
        root.destroy()

    def enable():
        state['busy'] = False
        progress.stop()
        progress.configure(value=0)
        primary.configure(state='normal', text='Connect' if state['editing'] else 'Retry connection')
        change.configure(state='normal')
        if app in ('pos','office'):register.configure(state='normal')
        entry.configure(state='normal' if state['editing'] else 'readonly')

    def change_server():
        state['editing'] = True
        heading.set('Change server connection')
        status.set('Enter the server address. It will be saved only after a successful connection.')
        enable()
        entry.focus_set()
        entry.selection_range(0, 'end')

    def register_pc():
        if on_register:on_register()
        change_server()
        heading.set('Connect and register this PC')
        status.set('Set the server address and select Connect. You can then enter administrator credentials to register this PC. Existing records and device identity are retained.')

    def check():
        if state['busy']:
            return
        try:
            candidate = server_url(value.get())
            if candidate != address and authorize and not authorize(candidate, root):
                status.set('The connection was not changed. Enter the current administrator passcode to change servers.')
                return
        except Exception as exc:
            heading.set('Check the server address')
            status.set(str(exc))
            return
        state['busy'] = True
        entry.configure(state='readonly')
        primary.configure(state='disabled')
        change.configure(state='disabled')
        if app in ('pos','office'):register.configure(state='disabled')
        heading.set('Connecting to ' + name)
        status.set('Checking the server. Your saved connection and records are kept while this runs.')
        progress.start(12)

        def worker():
            try:
                probe_server(candidate, app)
                results.put((candidate, None))
            except Exception as exc:
                results.put((candidate, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll():
        state['timer'] = None
        try:
            candidate, error = results.get_nowait()
        except queue.Empty:
            pass
        else:
            if not error:
                try:
                    if configure or candidate != address:
                        save(candidate)
                    selected.append(candidate)
                    close()
                    return
                except Exception as exc:
                    error = 'The connection worked, but its settings could not be saved: ' + str(exc)
            heading.set('Unable to connect')
            status.set(error)
            enable()
        if not state['closed']:
            state['timer'] = root.after(80, poll)

    primary = ttk.Button(buttons, text='Connect' if configure else 'Retry connection', command=check, style='Connection.TButton')
    primary.pack(side='left')
    change = ttk.Button(buttons, text='Change server', command=change_server, style='Connection.TButton')
    change.pack(side='left', padx=10)
    if app in ('pos','office'):
        register=ttk.Button(buttons, text='Register / configure PC', command=register_pc, style='Connection.TButton')
        register.pack(side='left')
    ttk.Button(buttons, text='Close', command=close, style='Connection.TButton').pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    root.bind('<Return>', lambda event: check())
    entry.configure(state='normal' if configure else 'readonly')
    state['timer'] = root.after(80, poll)
    if not configure:
        root.after(0, check)
    root.mainloop()
    return selected[0] if selected else None
