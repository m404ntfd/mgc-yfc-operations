"""CoastYouth Retail OFFICE desktop client; shares the Operations server."""
import json,os,sys,threading
from pathlib import Path
from pos_desktop import server_url

class OfficeBridge:
 def __init__(self,address=None):self._window=None;self._exiting=False;self._checking=False;self._address=address;self._kiosk=None
 def _trusted(self):
  from urllib.parse import urlsplit
  if not self._window:return False
  actual=urlsplit(self._window.get_current_url());expected=urlsplit(self._address)
  return (actual.scheme,actual.netloc)==(expected.scheme,expected.netloc) and actual.path in ('/office','/office/')
 def office_update_info(self):
  from pos_kiosk import KioskStore
  from pos_updater import PosUpdater
  if not self._trusted():return {'error':'Open the configured OFFICE server.'}
  if not hasattr(self,'_updates'):
   self._store=KioskStore(Path(os.environ.get('APPDATA',str(Path.home())))/'CoastYouthRetailOffice'/'settings.json')
   self._updates=PosUpdater(self,app='office',current='1.9.1')
  from computer_identity import computer_info
  return {'computer':computer_info(),'device':self._store.data['device'],'version':self._updates.version,'updater':True}
 def office_update_status(self,ident=None):
  self.office_update_info();return self._updates.observe(ident)
 def office_install_update(self):
  try:return self._updates.install()
  except Exception as e:return {'error':str(e)}
 def office_kiosk_info(self):
  # Only expose settings for DESK installed on this Windows login and server.
  from pos_kiosk import KioskStore,KioskBridge
  path=Path(os.environ.get('APPDATA',str(Path.home())))/'MGCYFCPOS'/'settings.json'
  if not self._address or not path.exists():return {'unavailable':True}
  try:
   store=KioskStore(path)
   if store.data.get('server','').rstrip('/')!=self._address.rstrip('/'):return {'unavailable':True}
   if self._kiosk is None:self._kiosk=KioskBridge(store,self._address)
   self._kiosk._store=store;self._kiosk._window=self._window
   return self._kiosk.kiosk_info()
  except Exception as e:return {'error':str(e)}
 def office_configure_passcode(self,token,code,confirmation):
  info=self.office_kiosk_info()
  if info.get('error') or info.get('unavailable'):return {'error':'Open OFFICE on the checkout computer connected to the same server.'}
  return self._kiosk.configure_passcode(token,code,confirmation)
 def office_close(self):
  try:
   if self._window.evaluate_js('typeof unfinished === "function" && unfinished()'):
    self._window.run_js("posMessage('Save or clear unfinished entries before closing OFFICE.')");return {'error':'Unsaved work'}
   self._exiting=True;self._window.destroy();return {'ok':True}
  except Exception as e:return {'error':str(e)}
  finally:self._checking=False
 def _closing(self):
  if self._exiting:return True
  if not self._checking:
   self._checking=True;threading.Thread(target=self.office_close,daemon=True).start()
  return False

def office_window(address,storage,hidden=False):
 import webview
 bridge=OfficeBridge(server_url(address))
 window=webview.create_window('CoastYouth Retail OFFICE',server_url(address)+'/office',js_api=bridge,width=1366,height=900,min_size=(1000,700),hidden=hidden)
 bridge._window=window;window.events.closing+=bridge._closing
 return window

def main():
 if '--apply-pos-update' in sys.argv:
  from pos_updater import apply_update
  apply_update(sys.argv[sys.argv.index('--apply-pos-update')+1]);return
 import tkinter as tk
 from tkinter import ttk,messagebox
 import webview
 if '--smoke-test' in sys.argv:
  errors=[];window=webview.create_window('OFFICE startup check',html='<html><body>OFFICE</body></html>',hidden=True)
  def check():
   try:
    if not window.events.loaded.wait(20):raise RuntimeError('OFFICE did not load')
    assert window.evaluate_js('1+1')==2
   except Exception as e:errors.append(str(e))
   finally:window.destroy()
  webview.start(check,gui='edgechromium',private_mode=True)
  raise SystemExit(1 if errors else 0)
 directory=Path(os.environ.get('APPDATA',str(Path.home())))/'CoastYouthRetailOffice'
 settings=directory/'settings.json';address='http://localhost:8080'
 if settings.exists():
  try:address=server_url(json.loads(settings.read_text(encoding='utf-8'))['server'])
  except Exception:pass
 if not settings.exists() or '--configure' in sys.argv:
  root=tk.Tk();root.title('CoastYouth Retail OFFICE');root.geometry('550x260');root.resizable(False,False)
  frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
  ttk.Label(frame,text='Connect OFFICE',font=('Segoe UI',20,'bold')).pack(anchor='w')
  ttk.Label(frame,text='Use your existing Operations server address.\nCatalog, accounts and permissions stay on that server.').pack(anchor='w',pady=16)
  value=tk.StringVar(value=address);ttk.Entry(frame,textvariable=value).pack(fill='x');chosen=[]
  def save():
   try:
    url=server_url(value.get());directory.mkdir(parents=True,exist_ok=True)
    temp=settings.with_suffix('.tmp');temp.write_text(json.dumps({'server':url}),encoding='utf-8');os.replace(temp,settings);chosen.append(url);root.destroy()
   except Exception as e:messagebox.showerror('OFFICE connection',str(e),parent=root)
  ttk.Button(frame,text='Connect',command=save).pack(anchor='e',pady=16);root.mainloop()
  if not chosen:return
  address=chosen[0]
 directory.mkdir(parents=True,exist_ok=True);office_window(address,directory)
 webview.settings['OPEN_DEVTOOLS_IN_DEBUG']=False
 webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(directory/'webview'))

if __name__=='__main__':main()
