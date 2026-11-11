"""Exercise real Windows startup dialogs with isolated fake release/download results."""
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from unittest.mock import Mock,patch
import desktop_startup as startup


def controls(root):
    out=[]
    def visit(widget):
        out.append(widget)
        for child in widget.winfo_children():visit(child)
    visit(root)
    return out


def run_case(app,action,offline=False,download_error=False):
    factory=tk.Tk;errors=[];roots=[];steps=[]
    offer={'app':app,'current':'1.0.0','version':'1.20.0','name':startup.APPS[app][0]}
    def make_root():
        root=factory();roots.append(root);root.withdraw()
        destroy=root.destroy
        def cleanup():
            for timer in root.tk.call('after','info'):root.after_cancel(timer)
            destroy()
        root.destroy=cleanup
        ticks=[0]
        def act():
            ticks[0]+=1
            if ticks[0]>100:
                errors.append('Startup dialog timed out');root.destroy();return
            buttons={str(w.cget('text')):w for w in controls(root) if isinstance(w,ttk.Button)}
            labels=' '.join(str(w.cget('text')) for w in controls(root) if isinstance(w,ttk.Label))
            if offline and 'could not be completed' in labels:
                steps.append('error');buttons['Continue opening'].invoke();return
            if download_error and 'could not be completed' in labels:
                steps.append('download error');buttons['Continue opening'].invoke();return
            if 'Not now' in buttons and 'chosen' not in steps:
                assert 'restart this application' in labels
                steps.append('chosen');buttons[action].invoke()
                if action=='Not now':return
            root.after(50,act)
        root.after(100,act)
        return root
    with tempfile.TemporaryDirectory() as tmp,patch.object(startup.sys,'frozen',True,create=True),patch.object(tk,'Tk',side_effect=make_root),patch.object(startup,'check_release',side_effect=OSError('Offline') if offline else None,return_value=offer) as check,patch.object(startup,'stage_installer',side_effect=ValueError('Download failed') if download_error else None,return_value=(Path(tmp)/'setup.exe','a'*64)) as stage,patch.object(startup,'launch_installer') as launch:
        result=startup.startup_update(app,'1.0.0',Path(tmp)/'settings.json')
        check.assert_called_once_with(app,'1.0.0')
        assert not errors,errors
        expected=action=='Update' and not offline and not download_error
        assert result==expected
        assert launch.call_count==int(expected)
        if action=='Not now' or offline:stage.assert_not_called()


if __name__=='__main__':
    for app in ('pos','office','ops','remote'):
        run_case(app,'Update');run_case(app,'Not now')
    run_case('office','Update',offline=True)
    run_case('pos','Update',download_error=True)
    root=tk.Tk();root.withdraw();accept=Mock()
    dialog=startup.server_offer(root,{'version':'0.60.0'},accept)
    buttons={str(w.cget('text')):w for w in controls(dialog) if isinstance(w,ttk.Button)}
    buttons['Update'].invoke();accept.assert_called_once_with('0.60.0');root.destroy()
    print('PASS startup dialogs for all desktop apps: Update, Not now, offline, failed download and coordinated server consent')
