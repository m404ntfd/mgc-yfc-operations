"""Full-screen POS launcher with device-local administrator exit protection."""
import json,os,sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from pos_updater import VERSION
from desktop_connection import server_url, connect_before_open

def open_pos(address,store):
 import webview
 from pos_kiosk import KioskBridge
 address=server_url(address)
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
 from desktop_startup import startup_update
 if startup_update('pos',VERSION,settings):return
 from pos_kiosk import KioskStore
 try:store=KioskStore(settings)
 except ValueError as e:
  root=tk.Tk();root.withdraw();messagebox.showerror('POS protection needs attention',str(e));root.destroy();return
 address='http://localhost:8080'
 try:address=server_url(json.loads(settings.read_text())['server'])
 except (OSError,ValueError,KeyError):pass
 def authorize(candidate,parent):
  if not store.configured:return True
  from tkinter.simpledialog import askstring
  code=askstring('Administrator exit passcode','Enter the current exit passcode to change servers:',show='*',parent=parent)
  if code is None:return False
  if not store.verify(code):raise ValueError('Incorrect admin passcode.')
  return True
 def save(candidate):
  previous=dict(store.data);store.data['server']=candidate
  try:store.save()
  except Exception:store.data=previous;raise
 address=connect_before_open('pos',address,save,configure=not store.data.get('server') or '--configure' in sys.argv,authorize=authorize)
 if not address:return
 try:open_pos(address,store)
 except Exception as e:
  root=tk.Tk();root.withdraw();messagebox.showerror('Unable to open DESK',str(e),parent=root);root.destroy()

if __name__=='__main__':main()
