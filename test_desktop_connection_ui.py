"""Real startup recovery dialogs, isolated connection/settings fixtures only."""
import json
import os
from pathlib import Path
import tempfile
import threading
import tkinter as tk
from tkinter import ttk
import traceback
from unittest.mock import Mock, patch

import desktop_connection as connection
from office_desktop import save_connection
from pos_kiosk import KioskStore


def controls(root):
    out = []
    def visit(widget):
        out.append(widget)
        for child in widget.winfo_children():visit(child)
    visit(root)
    return out


def run_case(app, action):
    factory = tk.Tk
    errors, stages = [], []
    old = 'http://store-server:8080'
    new = connection.PUBLIC_SERVER
    blocker = threading.Event()
    def probe(address, kind):
        assert kind == app
        if action == 'close-pending':blocker.wait(5); return address
        if not stages:raise ValueError('The server did not respond. Check your internet or VPN connection, then retry.')
        return address
    authorize = Mock(return_value=action != 'denied')
    def make_root():
        root = factory();root.withdraw()
        original_destroy = root.destroy
        def destroy():
            for timer in root.tk.call('after', 'info'):root.after_cancel(timer)
            original_destroy()
        root.destroy = destroy
        ticks = [0]
        def act():
            try:
                ticks[0] += 1
                assert ticks[0] < 120, 'Connection dialog timed out: ' + action
                widgets = controls(root)
                buttons = {str(w.cget('text')): w for w in widgets if isinstance(w, ttk.Button)}
                labels = ' '.join(str(w.cget('text')) for w in widgets if isinstance(w, ttk.Label))
                entry = next(w for w in widgets if isinstance(w, ttk.Entry))
                if action == 'first' and not stages:
                    stages.append('first connection')
                    entry.delete(0, 'end');entry.insert(0, new);buttons['Connect'].invoke()
                if action == 'close-pending' and check.called:
                    buttons['Close'].invoke();return
                if 'Unable to connect' in labels and not stages:
                    assert 'VPN' in labels
                    assert not buttons['Retry connection'].instate(['disabled'])
                    preview = os.environ.get('RETAIL_CONNECTION_PREVIEW')
                    if preview and action == 'retry':
                        from PIL import ImageGrab
                        root.deiconify();root.attributes('-topmost', True);root.update()
                        folder = Path(preview);folder.mkdir(parents=True, exist_ok=True)
                        ImageGrab.grab((root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(folder / (app + '-connection-recovery.png'))
                        root.withdraw()
                    stages.append('failure')
                    if action in ('close', 'cancel-edit'):
                        if action == 'cancel-edit':buttons['Change server'].invoke();entry.delete(0, 'end');entry.insert(0, new)
                        buttons['Close'].invoke();return
                    if action == 'retry':buttons['Retry connection'].invoke()
                    else:
                        buttons['Change server'].invoke();entry.delete(0, 'end');entry.insert(0, new)
                        buttons['Retry connection'].invoke()
                elif action == 'denied' and stages and 'not changed' in labels:
                    buttons['Close'].invoke();return
                elif action == 'save-failure' and stages and 'could not be saved' in labels:
                    stages.append('save error');buttons['Close'].invoke();return
                root.after(60, act)
            except Exception:
                errors.append(traceback.format_exc())
                next(w for w in controls(root) if isinstance(w, ttk.Button) and str(w.cget('text')) == 'Close').invoke()
        root.after(100, act)
        return root

    with tempfile.TemporaryDirectory() as tmp:
        settings = Path(tmp) / 'settings.json'
        store = KioskStore(settings);store.data.update(server=old, custom='retained');store.save()
        before = settings.read_bytes();identity = store.data['device']
        save = Mock(side_effect=OSError('fixture settings are read-only') if action == 'save-failure' else lambda address: save_connection(settings, address))
        with patch.object(tk, 'Tk', side_effect=make_root), patch.object(connection, 'probe_server', side_effect=probe) as check:
            result = connection.connect_before_open(app, old, save, authorize=authorize, configure=action == 'first')
            blocker.set()
        assert not errors, errors
        if action == 'retry':
            assert result == old and check.call_count == 2
            save.assert_not_called();authorize.assert_not_called()
        elif action in ('change', 'first'):
            assert result == new
            assert json.loads(settings.read_text()) == {**json.loads(before), 'server': new}
            assert json.loads(settings.read_text())['device'] == identity
            assert authorize.call_count == save.call_count == 1
        else:
            assert result is None
            assert settings.read_bytes() == before
            if action == 'save-failure':assert stages == ['failure', 'save error']
            else:save.assert_not_called()
            if action == 'denied':assert check.call_count == 1


if __name__ == '__main__':
    for app in ('pos', 'office', 'ops'):
        run_case(app, 'retry');run_case(app, 'change');run_case(app, 'close');run_case(app, 'first')
    for action in ('denied', 'cancel-edit', 'save-failure', 'close-pending'):run_case('pos', action)
    print('PASS connection dialogs: VPN retry, verified address change, canceled/denied/failed changes, close during check, and retained registration/settings')
