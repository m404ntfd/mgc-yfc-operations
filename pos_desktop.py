"""Full-screen POS launcher with device-local administrator exit protection."""
import json,os,sys
from pathlib import Path
from urllib.parse import urlsplit
import tkinter as tk
from tkinter import ttk,messagebox

from pos_updater import VERSION
def server_url(value):
 value=value.strip()
 if '://' not in value:value='http://'+value
 parts=urlsplit(value)
 if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.path not in ('','/') or parts.query or parts.fragment:
  raise ValueError('Enter the Operations server address, for example http://192.168.1.20:8080.')
 try:parts.port
 except ValueError:raise ValueError('Enter a valid server port.')
 return value.rstrip('/')

def open_pos(address,store):
 import webview
 from pos_kiosk import KioskBridge
 address=server_url(address)
 from urllib.request import build_opener,ProxyHandler
 try:
  with build_opener(ProxyHandler({})).open(address+'/pos.js',timeout=10) as response:
   compatible=b'kioskSetupDialog' in response.read(2000000)
 except Exception as e:raise ValueError('Cannot reach the Operations server. Check that it is running and that this computer is connected to the store network.') from e
 if not compatible:raise ValueError('Update the Operations server to the matching full-screen POS release before opening this POS version.')
 bridge=KioskBridge(store,address)
 window=webview.create_window('CoastYouth Retail DESK',address+'/pos?kiosk=1',js_api=bridge,fullscreen=True,frameless=True,easy_drag=False,resizable=False,confirm_close=False)
 bridge._window=window
 window.events.closing+=bridge._closing
 webview.settings['OPEN_DEVTOOLS_IN_DEBUG']=False
 webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(store.path.parent/'webview'))

def main():
 if '--apply-pos-update' in sys.argv:
  from pos_updater import apply_update
  apply_update(sys.argv[sys.argv.index('--apply-pos-update')+1]);return
 if '--smoke-test' in sys.argv:
  assert server_url('localhost:8080')=='http://localhost:8080'
  assert server_url('https://store.example/')=='https://store.example'
  for bad in ['file:///C:/data','https://user:password@example.com','https://example.com/path']:
   try:server_url(bad)
   except ValueError:pass
   else:raise AssertionError('Unsafe URL accepted')
  root=tk.Tk();root.withdraw();root.destroy()
  # Exercise the packaged WebView2 runtime, not just the configuration dialog.
  import webview,tempfile,time
  failures=[]
  window=webview.create_window('POS startup check',html='<html><body>POS startup check</body></html>',hidden=True,fullscreen=True,frameless=True,resizable=False)
  def check():
   try:
    if not window.events.loaded.wait(20):raise RuntimeError('WebView2 did not load')
    assert window.evaluate_js('1+1')==2
    assert window.fullscreen and window.frameless and not window.resizable
   except Exception as e:failures.append(str(e))
   finally:window.destroy()
  try:webview.start(check,gui='edgechromium',private_mode=True)
  except Exception:raise SystemExit(1)
  raise SystemExit(1 if failures else 0)
 # One shell per Windows login prevents competing passcode/settings writes.
 import ctypes
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
 kernel.CreateMutexW.restype=ctypes.c_void_p
 mutex=kernel.CreateMutexW(None,False,'Local\\MGCYFCPOS')
 if not mutex:raise OSError('Unable to protect the POS session.')
 if ctypes.get_last_error()==183:
  root=tk.Tk();root.withdraw();messagebox.showinfo('Point of Sale','Point of Sale is already running on this Windows login.');root.destroy();return
 settings=Path(os.environ.get('APPDATA',str(Path.home())))/'MGCYFCPOS'/'settings.json'
 from pos_kiosk import KioskStore
 try:store=KioskStore(settings)
 except ValueError as e:
  root=tk.Tk();root.withdraw();messagebox.showerror('POS protection needs attention',str(e));root.destroy();return
 address='http://localhost:8080'
 try:address=server_url(json.loads(settings.read_text())['server'])
 except (OSError,ValueError,KeyError):pass
 if store.data.get('server') and '--configure' not in sys.argv:
  try:open_pos(address,store);return
  except Exception as e:
   root=tk.Tk();root.withdraw();messagebox.showerror('Unable to open POS',str(e));root.destroy();return
 root=tk.Tk();root.title('CoastYouth Retail DESK '+VERSION);root.geometry('620x280');root.resizable(False,False)
 frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Connect CoastYouth Retail DESK',font=('Segoe UI',18,'bold')).pack(anchor='w')
 ttk.Label(frame,text='Use the address shown by your Operations server.\nSign in as an administrator next to register this checkout.').pack(anchor='w',pady=14)
 value=tk.StringVar(value=address);entry=ttk.Entry(frame,textvariable=value);entry.pack(fill='x');entry.focus_set()
 selected=[]
 def connect():
  try:
   normalized=server_url(value.get())
   if store.configured and normalized!=store.data.get('server'):
    from tkinter.simpledialog import askstring
    code=askstring('Administrator exit passcode','Enter the current exit passcode to change servers:',show='*',parent=root)
    if code is None:return
    if not store.verify(code):raise ValueError('Incorrect admin passcode.')
   store.data['server']=normalized;store.save();selected.append(normalized);root.destroy()
  except Exception as e:messagebox.showerror('Unable to open POS',str(e),parent=root)
 ttk.Button(frame,text='Open Point of Sale',command=connect).pack(anchor='e',pady=18)
 root.bind('<Return>',lambda e:connect());root.mainloop()
 if selected:
  try:open_pos(selected[0],store)
  except Exception as e:
   root=tk.Tk();root.withdraw();messagebox.showerror('Unable to open POS',str(e));root.destroy()

if __name__=='__main__':main()
