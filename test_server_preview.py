"""Render the real native server UI without launching a server or changing live data."""
import sys,tempfile,types,time
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from PIL import ImageGrab

class Icon:
 def __init__(self,*a,**k):self.visible=False
 def run(self,setup):setup(self)
 def stop(self):pass
class Menu:
 SEPARATOR=None
 def __init__(self,*a):pass
sys.modules['pystray']=types.SimpleNamespace(Icon=Icon,Menu=Menu,MenuItem=lambda *a,**k:None)
import server_desktop
out=Path('test-artifacts');out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp,patch.object(server_desktop,'DATA',Path(tmp)),patch.object(server_desktop.ServerWindow,'start',lambda self:None):
 root=tk.Tk();root.attributes('-topmost',True);app=server_desktop.ServerWindow(root,smoke=False);app.status.set('Preview — no live server started');root.geometry('1000x900+20+20')
 def snap(name):
  for _ in range(8):root.update();time.sleep(.05)
  ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(out/name)
 app.manage();root.geometry('1000x900+20+20');app.tabs.select(app.updates_tab);snap('Next-Server-Updates.png')
 app.tabs.select(app.settings_tab);snap('Next-Server-Settings.png')
 app.tabs.select(app.admin_tab)
 # Exercise the backup progress UI with a simulated verified response only.
 class Client:
  def request(self,*a,**k):time.sleep(.6);return {'verified':True,'backup':'OneDrive / Sample backup folder / Verified backup.zip'}
 while app.admin_panel.busy:root.update();time.sleep(.05)
 app.admin_panel.client=Client();app.admin_panel.backup()
 for _ in range(25):root.update();time.sleep(.05)
 dialog=root.grab_current();assert dialog is not None;dialog.attributes('-topmost',True);dialog.lift();dialog.update();assert 'Backup completed' in dialog.backup_message.get()
 ImageGrab.grab(bbox=(dialog.winfo_rootx(),dialog.winfo_rooty(),dialog.winfo_rootx()+dialog.winfo_width(),dialog.winfo_rooty()+dialog.winfo_height())).save(out/'Next-Backup-Verified.png')
 dialog.destroy();root.destroy()
print('PASS native Updates, Server settings and verified-backup dialog preview. No live server or backup was accessed.')
