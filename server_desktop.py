"""Windows tray host for MGC YFC Operations Server; data/code stay external."""
import ctypes,json,os,queue,secrets,socket,subprocess,sys,threading,time,urllib.request,webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from PIL import Image,ImageTk
import pystray
NAME='MGC YFC Operations Server'
ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
ASSETS=Path(getattr(sys,'_MEIPASS',ROOT))/'assets'
DATA=Path(os.environ.get('DISPATCH_DATA',ROOT/'data'))
PORT=int(os.environ.get('DISPATCH_PORT','8080'))
URL=f'http://127.0.0.1:{PORT}'

def request(path,data=None):
    req=urllib.request.Request(URL+'/api/'+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Dispatch':'1'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=4) as response:return json.load(response)

class ServerWindow:
    def __init__(self,root,smoke=False,console=False):
        self.root=root;self.smoke=smoke;self.console=None;self.pump=None;self.smoke_phase=0;self.process=None;self.log=None;self.stopping=False;self.tray_ready=False;self.queue=queue.Queue();self.token=secrets.token_urlsafe(48);self.deadline=time.time()+45;self.smoke_done=False;self.notice=None
        DATA.mkdir(parents=True,exist_ok=True)
        root.title(NAME);root.geometry('820x580');root.minsize(800,560);root.iconbitmap(str(ASSETS/'dispatch.ico'))
        if console:
            from console_control import ConsoleWindow
            self.console=ConsoleWindow(ASSETS/'dispatch.ico');root.withdraw()
            print('MGC YFC Operations Server — console mode',flush=True)
            print('Minimize sends this command window to the three red rings and computer icon in the system tray.',flush=True)
            print('Double-click the YFC icon to reopen. To stop: right-click the YFC icon > Exit server.',flush=True)
        root.protocol('WM_DELETE_WINDOW',self.hide);root.bind('<Unmap>',self.on_minimize)
        style=ttk.Style();style.theme_use('clam');style.configure('TButton',padding=10);style.configure('TLabel',font=('Segoe UI',10))
        self.admin_panel=None;self.cleanup_checked=False
        self.tabs=ttk.Notebook(root);self.tabs.pack(fill='both',expand=True)
        self.server_tab=ttk.Frame(self.tabs);self.admin_tab=ttk.Frame(self.tabs)
        self.tabs.add(self.server_tab,text='Server');self.tabs.add(self.admin_tab,text='Administration')
        self.tabs.bind('<<NotebookTabChanged>>',self.on_tab_changed)
        f=ttk.Frame(self.server_tab,padding=24);f.pack(fill='both',expand=True)
        self.picture=ImageTk.PhotoImage(Image.open(ASSETS/'dispatch.png').resize((72,72)))
        top=ttk.Frame(f);top.pack(fill='x');ttk.Label(top,image=self.picture).pack(side='left',padx=(0,16));ttk.Label(top,text='MGC YFC\nOperations Server',font=('Segoe UI',20,'bold')).pack(side='left')
        self.status=tk.StringVar(value='Starting server…');ttk.Label(f,textvariable=self.status,wraplength=600).pack(anchor='w',pady=(20,12))
        try:addresses=[a for a in socket.gethostbyname_ex(socket.gethostname())[2] if not a.startswith('127.')]
        except OSError:addresses=[]
        address_text='This computer: '+URL+'\nStaff network: '+(', '.join(f'http://{a}:{PORT}' for a in addresses) or 'Check this computer’s network address')
        ttk.Label(f,text=address_text,wraplength=600).pack(anchor='w')
        row=ttk.Frame(f);row.pack(fill='x',pady=18)
        ttk.Button(row,text='Login to Operations',command=self.open_login).pack(side='left')
        ttk.Button(row,text='Retail OFFICE',command=lambda:self.open_page('office')).pack(side='left',padx=4)
        ttk.Button(row,text='Terminals',command=lambda:self.open_page('office#terminals')).pack(side='left',padx=4)
        ttk.Button(row,text='Manage / update server',command=self.manage).pack(side='left',padx=8)
        updates=ttk.LabelFrame(f,text='Software updates',padding=10);updates.pack(fill='x',pady=(0,12))
        ttk.Button(updates,text='Operations / server update',command=self.manage).pack(side='left')
        ttk.Button(updates,text='Update POS applications',command=lambda:self.open_page('#pos-updates')).pack(side='left',padx=8)
        ttk.Button(updates,text='Server / controller installer',command=self.installer_downloads).pack(side='left')
        ttk.Button(row,text='Minimize to tray',command=self.hide).pack(side='left')
        ttk.Label(f,text='Minimize or close this window to keep the server running in the tray.\nDouble-click the three red rings and computer icon to reopen. Use Exit server to stop it.',wraplength=600).pack(anchor='w')
        bottom=ttk.Frame(f);bottom.pack(fill='x',pady=14)
        ttk.Button(bottom,text='Open server log',command=self.open_log).pack(side='left')
        self.exit_button=ttk.Button(bottom,text='Exit server',command=self.ask_exit);self.exit_button.pack(side='right')
        self.icon=pystray.Icon('ThriftMartDispatch',Image.open(ASSETS/'dispatch.png'),NAME,pystray.Menu(
            pystray.MenuItem('Open server console' if self.console else 'Open server window',lambda icon,item:self.queue.put(('show',None)),default=True),
            pystray.MenuItem('Login to Operations',lambda icon,item:self.queue.put(('schedule',None))),
            pystray.MenuItem('Manage / update server',lambda icon,item:self.queue.put(('manage',None))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit server',lambda icon,item:self.queue.put(('exit',None)))))
        def ready(icon):icon.visible=True;self.queue.put(('ready',None))
        def tray():
            try:self.icon.run(setup=ready)
            except Exception as e:self.queue.put(('tray_error',str(e)))
        threading.Thread(target=tray,daemon=True).start()
        self.start();root.after(150,self.poll)
    def start(self):
        try:
            logpath=DATA/'server-console.log'
            if logpath.exists() and logpath.stat().st_size>5*1024*1024:logpath.replace(DATA/'server-console.previous.log')
            self.log=logpath.open('ab',buffering=0)
            python=ROOT/'runtime/python.exe'
            if not python.exists():raise RuntimeError('The bundled runtime is missing. Run the latest installer again.')
            env={**os.environ,'DISPATCH_CONTROL_TOKEN':self.token,'PYTHONUNBUFFERED':'1'}
            # Do not let the frozen host's DLL directory override the external runtime.
            ctypes.windll.kernel32.SetDllDirectoryW(None)
            self.process=subprocess.Popen([str(python),str(ROOT/'launcher.py')],cwd=ROOT,env=env,stdout=subprocess.PIPE if self.console else self.log,stderr=subprocess.STDOUT if self.console else self.log,creationflags=subprocess.CREATE_NO_WINDOW)
            if self.console:
                def pump():
                    for line in iter(self.process.stdout.readline,b''):
                        self.log.write(line)
                        try:sys.stdout.write(line.decode('utf-8',errors='replace'));sys.stdout.flush()
                        except (OSError,UnicodeError):pass
                self.pump=threading.Thread(target=pump,daemon=True);self.pump.start()
        except Exception as e:self.status.set('Unable to start: '+str(e))
    def on_minimize(self,event):
        if event.widget is self.root and self.root.state()=='iconic':self.root.after(0,self.hide)
    def hide(self):
        if not self.tray_ready:
            self.show();self.status.set('Tray is not ready. Keep this window open for now.');return
        self.root.withdraw()
        if self.console:self.console.hide()
    def show(self):
        if self.console:self.console.show()
        else:self.root.deiconify();self.root.lift();self.root.focus_force()
    def open_page(self,fragment):
        target=URL+'/'+fragment
        try:
            if not webbrowser.open(target,new=2):raise OSError('No browser accepted the request.')
        except OSError as e:messagebox.showerror(NAME,'Cannot open the browser. Open '+target+' manually.\n'+str(e))
    def installer_downloads(self):
        webbrowser.open('https://github.com/m404ntfd/mgc-yfc-operations/releases/latest',new=2)
    def open_login(self):self.open_page('#login')
    def on_tab_changed(self,event=None):
        if self.tabs.select()==str(self.admin_tab):self.manage()
    def manage(self):
        if self.admin_panel is None:
            from remote.remote_manager import App
            self.admin_panel=App(self.root,local=True,container=self.admin_tab,address=URL,local_control=self.token,session_path=DATA/'native-admin-session.bin')
        self.root.geometry('820x900');self.tabs.select(self.admin_tab);self.root.deiconify();self.root.lift()
    def offer_remote_cleanup(self):
        marker=ROOT/'remove-standalone-manager.pending'
        if self.cleanup_checked or self.smoke or not marker.exists():return
        try:
            if request('session').get('application')!='thrift-mart-dispatch':return
        except Exception:return
        self.cleanup_checked=True
        if not messagebox.askyesno(NAME,'The combined server application is installed and running. Administration is now included here. Remove the old standalone Remote Manager and its shortcuts from this computer? Your server, settings and data will be kept.'):
            marker.unlink(missing_ok=True);return
        from manager_cleanup import remove_standalone_manager
        try:
            remove_standalone_manager(ROOT);marker.unlink(missing_ok=True)
            messagebox.showinfo(NAME,'The standalone Remote Manager was removed. Use the Administration tab in this server application.')
        except OSError:
            self.cleanup_checked=False
            messagebox.showwarning(NAME,'Close the standalone Remote Manager before trying again. The server application will offer removal the next time it starts.')
            self.cleanup_checked=True

    def open_log(self):os.startfile(DATA/'server-console.log')
    def ask_exit(self):
        if self.stopping:return
        if messagebox.askyesno(NAME,'Stop the server? Employees will not be able to access the schedule until you start it again.'):
            self.stop()
    def stop(self):
        if not self.process or self.process.poll() is not None:self.finish();return
        self.notice=None;self.stopping=True;self.status.set('Stopping server safely…')
        def worker():
            try:
                request('local/stop',{'token':self.token});self.process.wait(timeout=20);self.queue.put(('stopped',None))
            except Exception as e:self.queue.put(('stop_error',str(e)))
        threading.Thread(target=worker,daemon=True).start()
    def finish(self):
        if self.smoke and self.smoke_done:
            (DATA/'tray-smoke.json').write_text(json.dumps({'passed':True,'console':bool(self.console)}))
        self.icon.stop()
        if self.pump:self.pump.join(timeout=2)
        if self.log:self.log.close()
        self.root.destroy()
    def poll(self):
        if self.console and self.tray_ready and self.console.minimized():self.hide()
        try:
            while True:
                kind,value=self.queue.get_nowait()
                if kind=='show':self.show()
                elif kind=='schedule':self.open_login()
                elif kind=='manage':self.manage()
                elif kind=='exit':self.ask_exit()
                elif kind=='ready':self.tray_ready=True
                elif kind=='tray_error':self.tray_ready=False;self.show();self.notice='Tray is unavailable: '+value;self.status.set(self.notice)
                elif kind=='stopped':self.finish();return
                elif kind=='stop_error':self.stopping=False;self.show();self.notice='Could not stop safely. Wait for any update to finish, then try Exit server again.';self.status.set(self.notice)
        except queue.Empty:pass
        if self.process and self.process.poll() is not None and not self.stopping:
            self.status.set('Server stopped. Check the log, then close and reopen the application.');self.show()
        elif self.process and not self.stopping and not self.notice:
            self.status.set('Server running • minimize safely to the system tray')
        if not self.smoke and self.process and self.process.poll() is None:self.offer_remote_cleanup()
        if self.smoke and not self.smoke_done:
            try:
                r=request('session')
                if r.get('application')=='thrift-mart-dispatch' and self.tray_ready:
                    if self.console:
                        assert self.console.verify_icons()
                        if self.smoke_phase==0:
                            self.console.show();self.console.minimize();self.smoke_phase=1
                        else:
                            assert not self.console.visible()
                            assert request('session')['application']=='thrift-mart-dispatch'
                            self.show();assert self.console.visible()
                            self.smoke_done=True;self.stop()
                    else:
                        self.root.update_idletasks()
                        assert self.root.title()==NAME
                        opened=[];original_open=webbrowser.open
                        try:
                            webbrowser.open=lambda url,**kw:opened.append(url) or True
                            self.open_login();self.manage()
                        finally:webbrowser.open=original_open
                        assert opened==[URL+'/#login']
                        assert self.admin_panel is not None and self.admin_panel.address.get()==URL
                        assert self.admin_panel.client is None
                        admin=self.admin_panel.new_client()
                        admin.request('setup',{'name':'SmokeAdmin','password':'TestPasswordOnly'})
                        assert admin.login('SmokeAdmin','TestPasswordOnly')['name']==NAME
                        assert admin.request('admin/users')['users']
                        restored_admin=self.admin_panel.new_client()
                        assert restored_admin.restore_local_session()['name']==NAME
                        self.tabs.select(self.server_tab);self.root.geometry('820x580');self.root.update_idletasks()
                        assert self.exit_button.winfo_rooty()+self.exit_button.winfo_height() <= self.root.winfo_rooty()+self.root.winfo_height()
                        self.hide();self.root.update_idletasks()
                        assert self.root.state()=='withdrawn'
                        assert request('session')['application']=='thrift-mart-dispatch'
                        self.show();self.root.update_idletasks();assert self.root.state()=='normal'
                        self.smoke_done=True;self.stop()
            except Exception:
                if time.time()>self.deadline:os._exit(2)
        self.root.after(300,self.poll)

def main():
    if '--restore-self-test' in sys.argv:
        from remote.restore import restore_self_test
        restore_self_test();return
    if '--restore-dir' in sys.argv:
        from remote.restore import restore_window
        restore_window(Path(sys.argv[sys.argv.index('--restore-dir')+1]));return
    kernel=ctypes.windll.kernel32;kernel.CreateMutexW.restype=ctypes.c_void_p
    mutex=kernel.CreateMutexW(None,False,'ThriftMartDispatchTray')
    if kernel.GetLastError()==183:
        root=tk.Tk();root.withdraw();messagebox.showinfo(NAME,'The server application is already open. Double-click its three red rings and computer icon in the system tray.');root.destroy();return
    root=tk.Tk();ServerWindow(root,smoke='--smoke-test' in sys.argv,console='--console' in sys.argv);root.mainloop()
if __name__=='__main__':main()
