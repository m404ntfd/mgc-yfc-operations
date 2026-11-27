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
    def probe(address, kind, **options):
        assert options == {"timeout_seconds":1 if action=="late" else 10}
        assert kind == app
        if action in ('close-pending','late'):blocker.wait(5); return address
        if not stages:raise ValueError('The server did not respond. Check your internet or VPN connection, then retry.')
        return address
    authorize = Mock(return_value=action != 'denied');register=Mock()
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
                labels = ' '.join(str(w.cget('text')) for w in widgets if isinstance(w, (ttk.Label,tk.Label)))
                entry = next(w for w in widgets if isinstance(w, ttk.Entry))
                if action == 'first' and not stages:
                    stages.append('first connection')
                    entry.delete(0, 'end');entry.insert(0, new);buttons['Connect'].invoke()
                if action == 'close-pending' and check.called:
                    root.tk.call('eval',root.protocol('WM_DELETE_WINDOW'));return
                if 'Can Not Connect to Operations Server' in labels and not stages:
                    assert 'VPN' in labels
                    assert not buttons['Retry Connection'].instate(['disabled'])
                    preview = os.environ.get('RETAIL_CONNECTION_PREVIEW')
                    if preview and action == 'retry':
                        from PIL import ImageGrab
                        root.deiconify();root.attributes('-topmost', True);root.update()
                        folder = Path(preview);folder.mkdir(parents=True, exist_ok=True)
                        ImageGrab.grab((root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(folder / (app + '-connection-recovery.png'))
                        root.withdraw()
                    stages.append('failure')
                    if action=='late':
                        blocker.set()
                        def after_late():
                            try:
                                assert 'Can Not Connect' in ' '.join(str(w.cget('text')) for w in controls(root) if isinstance(w,tk.Label))
                                save.assert_not_called()
                            except Exception:errors.append(traceback.format_exc())
                            root.tk.call('eval',root.protocol('WM_DELETE_WINDOW'))
                        root.after(250,after_late);return
                    if action in ('close', 'cancel-edit'):
                        if action == 'cancel-edit':buttons['Configure Server Connection'].invoke();entry.delete(0, 'end');entry.insert(0, new)
                        root.tk.call('eval',root.protocol('WM_DELETE_WINDOW'));return
                    if action == 'retry':buttons['Retry Connection'].invoke()
                    else:
                        buttons['Configure Server Connection'].invoke();entry.delete(0, 'end');entry.insert(0, new)
                        buttons['Retry Connection'].invoke()
                elif action == 'denied' and stages and 'not changed' in labels:
                    root.tk.call('eval',root.protocol('WM_DELETE_WINDOW'));return
                elif action == 'save-failure' and stages and 'could not be saved' in labels:
                    stages.append('save error');root.tk.call('eval',root.protocol('WM_DELETE_WINDOW'));return
                root.after(60, act)
            except Exception:
                errors.append(traceback.format_exc())
                root.tk.call('eval',root.protocol('WM_DELETE_WINDOW'))
        root.after(100, act)
        return root

    with tempfile.TemporaryDirectory() as tmp:
        settings = Path(tmp) / 'settings.json'
        store = KioskStore(settings);store.data.update(server=old, custom='retained');store.save()
        before = settings.read_bytes();identity = store.data['device']
        save = Mock(side_effect=OSError('fixture settings are read-only') if action == 'save-failure' else lambda address: save_connection(settings, address))
        with patch.dict(os.environ, {'APPDATA':tmp}), patch.object(tk, 'Tk', side_effect=make_root), patch.object(connection, 'probe_server', side_effect=probe) as check:
            if action=='late':
                from connection_preferences import save as save_preferences
                save_preferences(app,{'timeout_seconds':1})
            result = connection.connect_before_open(app, old, save, authorize=authorize, configure=action == 'first',on_register=register)
            blocker.set()
        assert not errors, errors
        if action == 'retry':
            assert result == old and check.call_count == 2
            save.assert_not_called();authorize.assert_not_called()
        elif action in ('change', 'first','register'):
            assert result == new
            assert json.loads(settings.read_text()) == {**json.loads(before), 'server': new}
            assert json.loads(settings.read_text())['device'] == identity
            assert authorize.call_count == save.call_count == 1
            if action=='register':register.assert_called_once_with()
        else:
            assert result is None
            assert settings.read_bytes() == before
            if action == 'save-failure':assert stages == ['failure', 'save error']
            else:save.assert_not_called()
            if action == 'denied':assert check.call_count == 1


if __name__ == '__main__':
    for app in ('pos', 'office', 'ops'):
        run_case(app, 'retry');run_case(app, 'change');run_case(app, 'close');run_case(app, 'first')
    for action in ('denied', 'cancel-edit', 'save-failure', 'close-pending','late'):run_case('pos', action)
    for app in ('pos','office'):run_case(app,'register')
    print('PASS connection dialogs: VPN retry, verified address change, canceled/denied/failed changes, close during check, and retained registration/settings')
