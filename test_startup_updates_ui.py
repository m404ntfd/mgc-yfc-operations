"""Exercise real Windows startup dialogs with isolated fake release/download results."""
import tempfile
import ssl
from urllib.error import URLError
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


def run_case(app,action,offline=False,download_error=False,certificate_error=False,retry_check=False):
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
            if certificate_error and 'security certificate' in labels:
                assert 'Unable to check for updates' in labels
                assert '_ssl.c' not in labels and 'No update was installed' in labels
                assert 'Check again' in buttons
                steps.append('certificate error')
                if retry_check and 'retry' not in steps:
                    steps.append('retry');buttons['Check again'].invoke();root.after(50,act)
                else:buttons['Continue opening'].invoke()
                return
            if offline and 'could not be completed' in labels:
                steps.append('error');buttons['Continue opening'].invoke();return
            if download_error and 'could not be completed' in labels:
                steps.append('download error')
                if retry_check and 'retry' not in steps:
                    steps.append('retry');steps.remove('chosen');buttons['Check again'].invoke();root.after(50,act)
                else:buttons['Continue opening'].invoke()
                return
            if 'Not now' in buttons and 'chosen' not in steps:
                assert 'Restart CoastYouth Retail' in labels
                assert not buttons['Restart & update'].instate(['disabled'])
                steps.append('chosen');buttons['Restart & update' if action=='Update' else action].invoke()
                if action=='Not now':return
            root.after(50,act)
        root.after(100,act)
        return root
    check_error=URLError(ssl.SSLCertVerificationError('unable to get local issuer certificate (_ssl.c:1032)')) if certificate_error else OSError('Offline') if offline else None
    check_effect=[check_error or offer,offer] if retry_check else check_error
    stage_error=[ValueError('Download failed'),(Path('unused-test-installer.exe'),'a'*64)] if download_error and retry_check else ValueError('Download failed') if download_error else None
    with tempfile.TemporaryDirectory() as tmp,patch.object(startup.sys,'frozen',True,create=True),patch.object(tk,'Tk',side_effect=make_root),patch.object(startup,'check_release',side_effect=check_effect,return_value=offer) as check,patch.object(startup,'stage_installer',side_effect=stage_error,return_value=(Path(tmp)/'setup.exe','a'*64)) as stage,patch.object(startup,'launch_installer') as launch:
        result=startup.startup_update(app,'1.0.0',Path(tmp)/'settings.json')
        assert check.call_count==(2 if retry_check else 1)
        check.assert_called_with(app,'1.0.0')
        assert not errors,errors
        expected=action=='Update' and not offline and (not download_error or retry_check) and (not certificate_error or retry_check)
        assert result==expected
        assert launch.call_count==int(expected)
        if action=='Not now' or offline or (certificate_error and not retry_check):stage.assert_not_called()
        if certificate_error:assert 'certificate error' in steps


if __name__=='__main__':
    for app in ('pos','office','ops','remote'):
        run_case(app,'Update');run_case(app,'Not now')
    run_case('office','Update',offline=True)
    run_case('pos','Update',download_error=True)
    run_case('pos','Update',certificate_error=True)
    run_case('pos','Update',certificate_error=True,retry_check=True)
    run_case('pos','Update',download_error=True,retry_check=True)
    root=tk.Tk();root.withdraw();accept=Mock()
    dialog=startup.server_offer(root,{'version':'0.60.0'},accept)
    buttons={str(w.cget('text')):w for w in controls(dialog) if isinstance(w,ttk.Button)}
    buttons['Update'].invoke();accept.assert_called_once_with('0.60.0');root.destroy()
    print('PASS startup dialogs: Update, Not now, offline, certificate guidance and retry, failed download and coordinated server consent')
