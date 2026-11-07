"""Standalone POS launcher. Stores only the chosen Operations server address."""
import json,os,subprocess,sys,webbrowser
from pathlib import Path
from urllib.parse import urlsplit
import tkinter as tk
from tkinter import ttk,messagebox

VERSION='1.0.0'
def server_url(value):
 value=value.strip()
 if '://' not in value:value='http://'+value
 parts=urlsplit(value)
 if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.path not in ('','/') or parts.query or parts.fragment:
  raise ValueError('Enter the Operations server address, for example http://192.168.1.20:8080.')
 try:parts.port
 except ValueError:raise ValueError('Enter a valid server port.')
 return value.rstrip('/')

def open_pos(address):
 url=server_url(address)+'/pos'
 for base in [os.environ.get('PROGRAMFILES(X86)'),os.environ.get('PROGRAMFILES'),os.environ.get('LOCALAPPDATA')]:
  if not base:continue
  for relative in ['Microsoft/Edge/Application/msedge.exe','Google/Chrome/Application/chrome.exe']:
   browser=Path(base)/relative
   if browser.is_file():
    subprocess.Popen([str(browser),'--app='+url],close_fds=True)
    return
 if not webbrowser.open(url):raise RuntimeError('No browser could open Point of Sale.')

def main():
 if '--smoke-test' in sys.argv:
  assert server_url('localhost:8080')=='http://localhost:8080'
  assert server_url('https://store.example/')=='https://store.example'
  for bad in ['file:///C:/data','https://user:password@example.com','https://example.com/path']:
   try:server_url(bad)
   except ValueError:pass
   else:raise AssertionError('Unsafe URL accepted')
  root=tk.Tk();root.withdraw();root.destroy();return
 settings=Path(os.environ.get('APPDATA',str(Path.home())))/'MGCYFCPOS'/'settings.json'
 address='http://localhost:8080'
 try:address=server_url(json.loads(settings.read_text())['server'])
 except (OSError,ValueError,KeyError):pass
 if settings.exists() and '--configure' not in sys.argv:
  try:open_pos(address);return
  except Exception:pass
 root=tk.Tk();root.title('MGC YFC Point of Sale '+VERSION);root.geometry('520x270');root.resizable(False,False)
 frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Connect Point of Sale',font=('Segoe UI',18,'bold')).pack(anchor='w')
 ttk.Label(frame,text='Use the address shown by your Operations server.\nThis computer does not need a separate database.').pack(anchor='w',pady=14)
 value=tk.StringVar(value=address);entry=ttk.Entry(frame,textvariable=value);entry.pack(fill='x');entry.focus_set()
 def connect():
  try:
   normalized=server_url(value.get());open_pos(normalized)
   settings.parent.mkdir(parents=True,exist_ok=True)
   temp=settings.with_suffix('.tmp');temp.write_text(json.dumps({'server':normalized}));temp.replace(settings)
   root.destroy()
  except Exception as e:messagebox.showerror('Unable to open POS',str(e),parent=root)
 ttk.Button(frame,text='Open Point of Sale',command=connect).pack(anchor='e',pady=18)
 root.bind('<Return>',lambda e:connect());root.mainloop()

if __name__=='__main__':main()
