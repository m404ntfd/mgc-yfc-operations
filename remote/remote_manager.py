"""MGC YFC Operations Remote Manager — native Windows control panel."""
import json,os,queue,sys,threading,webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
try:
    from .client import Client
except ImportError:
    from client import Client
NAME='MGC YFC Operations Remote Manager'
VERSION='0.39.0'
CONFIG=Path(os.environ.get('APPDATA',Path.home()))/'ThriftMartDispatchRemoteManager'/'config.json'

class App:
    def __init__(self,root,local=False,container=None,address=None,local_control=None,session_path=None):
        self.root=root;self.client=None;self.release=None;self.busy=False;self.results=queue.Queue()
        self.local=local;self.local_control=local_control;self.session_path=session_path
        if container is None:
            root.title('MGC YFC Operations Server — Administration' if local else NAME);root.geometry('800x830');root.minsize(720,760)
            icon=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))/'assets'/('dispatch.ico' if local else 'remote.ico')
            if icon.exists():root.iconbitmap(str(icon))
        style=ttk.Style();style.theme_use('clam');style.configure('TButton',padding=9);style.configure('TLabel',font=('Segoe UI',10));style.configure('Title.TLabel',font=('Segoe UI',22,'bold'));style.configure('TEntry',padding=7)
        frame=ttk.Frame(container if container is not None else root,padding=16);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='MGC YFC Operations',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text=('Server administration' if local else 'Remote Manager')+' • '+VERSION+'  |  Staff network').pack(anchor='w',pady=(2,16))
        box=ttk.LabelFrame(frame,text='Connect to your store server',padding=12);box.pack(fill='x')
        try:saved=json.loads(CONFIG.read_text())
        except (OSError,ValueError):saved={}
        self.address=tk.StringVar(value=(address or 'http://localhost:8080') if local else saved.get('address',''));self.username=tk.StringVar(value=saved.get('username',''));self.password=tk.StringVar()
        for label,var,secret in [('Server IP or computer name',self.address,False),('Administrator name',self.username,False),('Password',self.password,True)]:
            row=ttk.Frame(box);row.pack(fill='x',pady=3);ttk.Label(row,text=label,width=27).pack(side='left');ttk.Entry(row,textvariable=var,show='•' if secret else '',state='readonly' if local and var is self.address else 'normal').pack(side='left',fill='x',expand=True)
        ttk.Label(box,text='Example: 192.168.1.50:8080 • Passwords are never saved.').pack(anchor='w',pady=5)
        buttons=ttk.Frame(box);buttons.pack(fill='x');ttk.Button(buttons,text='Test connection',command=self.probe).pack(side='left');ttk.Button(buttons,text='Connect / Sign in',command=self.login).pack(side='left',padx=8);ttk.Button(buttons,text='Disconnect',command=self.disconnect).pack(side='left')
        self.status=tk.StringVar(value='Enter the server address shown on the store computer.')
        ttk.Label(frame,textvariable=self.status,wraplength=690).pack(fill='x',pady=12)
        self.details=tk.StringVar(value='Not connected')
        ttk.Label(frame,textvariable=self.details,wraplength=690).pack(fill='x',pady=(0,12))
        actions=ttk.Frame(frame);actions.pack(fill='x')
        ttk.Button(actions,text='Open schedule / settings',command=self.open_browser).pack(side='left')
        ttk.Button(actions,text='Refresh status',command=self.refresh).pack(side='left',padx=6)
        ttk.Button(actions,text='OneDrive backup',command=self.backup).pack(side='left')
        ttk.Button(actions,text='Restart server',command=self.restart).pack(side='left',padx=6)
        account_actions=ttk.Frame(frame);account_actions.pack(fill='x',pady=(8,0))
        ttk.Button(account_actions,text='Manage employees',command=self.employees).pack(side='left')
        ttk.Button(account_actions,text='Change a user’s password',command=self.passwords).pack(side='left',padx=8)
        ttk.Button(account_actions,text='Login security / unlock',command=self.login_security).pack(side='left')
        updates=ttk.LabelFrame(frame,text='Server updates from GitHub',padding=12);updates.pack(fill='both',expand=True,pady=16)
        row=ttk.Frame(updates);row.pack(fill='x');ttk.Button(row,text='Check for server updates',command=self.check).pack(side='left');self.install=ttk.Button(row,text='Install update & restart',command=self.install_update,state='disabled');self.install.pack(side='left',padx=8)
        self.notes=tk.Text(updates,height=7,wrap='word',font=('Segoe UI',10),state='disabled');self.notes.pack(fill='both',expand=True,pady=8)
        ttk.Label(frame,text='Manage employee accounts here; open the browser for schedules and vehicles.\nThe browser requires its own sign-in. Closing this app does not stop the server.',wraplength=690).pack(anchor='w')
        ttk.Button(frame,text='Remote Manager downloads / updates',command=lambda:webbrowser.open('https://github.com/m404ntfd/mgc-yfc-operations/releases/latest')).pack(anchor='w',pady=(8,0))
        root.after(100,self.deliver)
        if local_control and session_path:
            client=self.new_client()
            def restored(result):
                if result:self.client=client;self.show_status(result)
                else:self.status.set('Sign in with an administrator account. Local sign-in is kept until an application update or sign-out.')
            self.run(client.restore_local_session,restored)
    def run(self,work,done):
        if self.busy:return
        self.busy=True;self.status.set('Working…')
        def worker():
            try:self.results.put((True,work(),done))
            except Exception as e:self.results.put((False,str(e),done))
        threading.Thread(target=worker,daemon=True).start()
    def deliver(self):
        try:
            ok,value,done=self.results.get_nowait();self.busy=False
            if ok:done(value)
            else:
                self.status.set(value)
                if self.root.grab_current():messagebox.showerror(NAME,value,parent=self.root.grab_current())
        except queue.Empty:pass
        self.root.after(100,self.deliver)
    def new_client(self):return Client(self.address.get(),local_control=self.local_control,session_path=self.session_path)
    def probe(self):
        if self.busy:return
        try:c=self.new_client()
        except ValueError as e:self.status.set(str(e));return
        self.run(c.probe,lambda r:self.status.set('Server is reachable • version '+r['version']))
    def login(self):
        if self.busy:return
        self.client=None;self.install.config(state='disabled');self.release=None
        try:c=self.new_client()
        except ValueError as e:self.status.set(str(e));return
        name=self.username.get().strip();password=self.password.get();self.password.set('')
        def done(r):
            self.client=c;self.show_status(r)
            try:
                if self.local:return
                CONFIG.parent.mkdir(parents=True,exist_ok=True);CONFIG.write_text(json.dumps({'address':c.address,'username':name}))
            except OSError:self.status.set('Connected, but the server address could not be saved on this computer.')
        self.run(lambda:c.login(name,password),done)
    def disconnect(self):
        if self.busy:return
        c=self.client;self.client=None;self.release=None;self.install.config(state='disabled');self.details.set('Not connected')
        if self.session_path:Path(self.session_path).unlink(missing_ok=True)
        if c:self.run(lambda:c.request('logout',{}),lambda _:self.status.set('Disconnected.'))
        else:self.status.set('Disconnected.')
    def require(self):
        if not self.client:self.status.set('Connect with an administrator account first.');return False
        if self.busy:return False
        return True
    def show_status(self,r):
        self.status.set('Connected to '+self.client.address)
        self.details.set(f"{r['name']} • v{r['version']}\n{r['jobs']} appointments · {r['vehicles']} vehicles · {r['users']} accounts\nUptime: {r['uptime_minutes']} minutes · Server time: {r['time']}")
    def refresh(self):
        if self.require():self.run(lambda:self.client.request('admin/status'),self.show_status)
    def open_browser(self):
        try:c=self.client or self.new_client();webbrowser.open(c.address)
        except ValueError as e:self.status.set(str(e))
    def backup(self):
        if self.require():self.run(lambda:self.client.request('admin/backup-now',{}),lambda r:self.status.set('Saved to server OneDrive folder (check sync): '+r['backup']))
    def employees(self):
        if not self.require():return
        client=self.client
        def show(result):
            dialog=tk.Toplevel(self.root);dialog.title('Manage store employees');dialog.geometry('540x510');dialog.transient(self.root);dialog.grab_set()
            frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True)
            ttk.Label(frame,text='Store employees',font=('Segoe UI',16,'bold')).pack(anchor='w')
            ttk.Label(frame,text='Removing an employee signs them out. Existing appointment assignments are kept.',wraplength=490).pack(anchor='w',pady=8)
            selected=tk.StringVar()
            combo=ttk.Combobox(frame,textvariable=selected,state='readonly');combo.pack(fill='x',pady=6)
            def populate(result):
                names=[u['name'] for u in result['users'] if not u['admin']]
                combo.configure(values=names);selected.set(names[0] if names else '')
            populate(result)
            def complete(result):
                if dialog.winfo_exists():populate(result);message.set('Employee list updated.')
                self.status.set('Employee list updated.')
            def remove():
                if not self.require() or not selected.get():return
                name=selected.get()
                if not messagebox.askyesno(NAME,'Remove employee '+name+'? They will no longer be able to sign in.',parent=dialog):return
                def work():client.request('admin/remove-user',{'name':name});return client.request('admin/users')
                self.run(work,complete)
            ttk.Button(frame,text='Remove selected employee',command=remove).pack(anchor='w',pady=4)
            ttk.Separator(frame).pack(fill='x',pady=12)
            name=tk.StringVar();password=tk.StringVar();confirm=tk.StringVar();message=tk.StringVar()
            for label,var in [('New employee name',name),('Password (8–256 characters or exactly 4 digits)',password),('Confirm password',confirm)]:
                ttk.Label(frame,text=label).pack(anchor='w');ttk.Entry(frame,textvariable=var,show='' if var is name else '•').pack(fill='x',pady=3)
            def add():
                if not self.require():return
                if not name.get().strip() or not (8<=len(password.get())<=256 or (len(password.get())==4 and all(c in '0123456789' for c in password.get()))):message.set('Enter a name and password of 8–256 characters or exactly 4 digits.');return
                if password.get()!=confirm.get():message.set('Passwords do not match.');return
                payload={'name':name.get().strip(),'password':password.get()}
                def work():client.request('user',payload);return client.request('admin/users')
                def done(result):
                    if dialog.winfo_exists():name.set('');password.set('');confirm.set('')
                    complete(result)
                self.run(work,done)
            ttk.Button(frame,text='Add employee',command=add).pack(anchor='w',pady=8)
            ttk.Label(frame,textvariable=message,wraplength=490).pack(anchor='w')
        self.run(lambda:client.request('admin/users'),show)
    def login_security(self):
        if not self.client:
            self.status.set('Sign in first.');return
        def show(data):
            dialog=tk.Toplevel(self.root);dialog.title('Login security / unlock users');dialog.geometry('620x480');dialog.transient(self.root)
            f=ttk.Frame(dialog,padding=20);f.pack(fill='both',expand=True)
            ttk.Label(f,text='Failed attempts before account lockout').pack(anchor='w')
            limit=tk.StringVar(value=str(data['max_attempts']));ttk.Spinbox(f,from_=1,to=100,textvariable=limit).pack(anchor='w',pady=6)
            message=tk.StringVar();ttk.Label(f,textvariable=message,wraplength=560).pack(anchor='w')
            def save():
                try:value=int(limit.get())
                except ValueError:message.set('Enter a whole number from 1 to 100.');return
                self.run(lambda:self.client.request('admin/login-security',{'max_attempts':value}),lambda r:message.set('Login limit saved. Existing locks remain.'))
            ttk.Button(f,text='Save login limit',command=save).pack(anchor='w',pady=8)
            ttk.Label(f,text='Locked accounts').pack(anchor='w');names=tk.StringVar();choice=ttk.Combobox(f,textvariable=names,state='readonly',width=50);choice.pack(anchor='w',pady=8)
            def refresh():
                def fill(r):
                    choice['values']=[u['name'] for u in r['users']];names.set(choice['values'][0] if choice['values'] else '')
                    message.set('Select an account to unlock.' if choice['values'] else 'No locked accounts.')
                self.run(lambda:self.client.request('admin/lockouts'),fill)
            def unlock():
                name=names.get()
                if not name:return
                self.run(lambda:self.client.request('admin/unlock-user',{'name':name}),lambda r:refresh())
            ttk.Button(f,text='Unlock selected user',command=unlock).pack(anchor='w',pady=8)
            ttk.Button(f,text='Refresh locked accounts',command=refresh).pack(anchor='w');refresh()
        self.run(lambda:self.client.request('admin/login-security'),show)

    def passwords(self):
        if not self.require():return
        def show(r):
            self.status.set('Select the user whose password you want to change.')
            dialog=tk.Toplevel(self.root);dialog.title('Change user password');dialog.geometry('520x400');dialog.transient(self.root);dialog.grab_set()
            f=ttk.Frame(dialog,padding=20);f.pack(fill='both',expand=True)
            ttk.Label(f,text='Administrator password reset',font=('Segoe UI',16,'bold')).pack(anchor='w')
            ttk.Label(f,text='The selected user will be signed out on all devices.',wraplength=470).pack(anchor='w',pady=10)
            selected=tk.StringVar();first=tk.StringVar();second=tk.StringVar();error=tk.StringVar()
            ttk.Label(f,text='User').pack(anchor='w');combo=ttk.Combobox(f,textvariable=selected,values=[u['name'] for u in r['users']],state='readonly');combo.pack(fill='x',pady=4)
            if r['users']:combo.current(0)
            for label,var in [('New password',first),('Confirm new password',second)]:
                ttk.Label(f,text=label).pack(anchor='w');ttk.Entry(f,textvariable=var,show='•').pack(fill='x',pady=4)
            ttk.Label(f,textvariable=error,wraplength=470).pack(anchor='w',pady=6)
            def save():
                if not self.require():return
                if not selected.get():error.set('Select a user.');return
                if not (8<=len(first.get())<=256 or (len(first.get())==4 and all(c in '0123456789' for c in first.get()))):error.set('Use 8–256 characters or exactly 4 digits.');return
                if first.get()!=second.get():error.set('The passwords do not match.');return
                payload={'name':selected.get(),'password':first.get(),'confirm':second.get()}
                first.set('');second.set('');dialog.destroy()
                def done(result):
                    if result['signed_out']:
                        self.client=None;self.release=None;self.install.config(state='disabled');self.details.set('Sign in again with your new password.')
                    self.status.set('Password changed. The user must sign in again on all devices.')
                self.run(lambda:self.client.request('admin/password',payload),done)
            ttk.Button(f,text='Change password',command=save).pack(anchor='w')
        self.run(lambda:self.client.request('admin/users'),show)
    def restart(self):
        if not self.require():return
        if not messagebox.askyesno(NAME,'Restart the server? Ask employees to save their appointments first. Everyone will be signed out.'):return
        self.run(lambda:self.client.request('admin/restart',{}),self.restarting)
    def restarting(self,r):
        self.client=None;self.release=None;self.install.config(state='disabled');self.details.set('Server restarting')
        self.status.set('Restart requested. Wait a few seconds, then Test connection and sign in again.')
    def check(self):
        if not self.require():return
        self.install.config(state='disabled');self.release=None
        def done(r):
            self.release=r['latest'] if r['available'] else None
            self.status.set('Version '+r['latest']+' available.' if self.release else 'Server is up to date: '+r['current'])
            self.notes.config(state='normal');self.notes.delete('1.0','end');self.notes.insert('1.0',r['notes']);self.notes.config(state='disabled');self.install.config(state='normal' if self.release else 'disabled')
        self.run(lambda:self.client.request('update-check',{}),done)
    def install_update(self):
        if not self.require() or not self.release:return
        if not messagebox.askyesno(NAME,'Back up, install server version '+self.release+' and restart? Ask all employees to save their appointments first.'):return
        version=self.release;self.run(lambda:self.client.request('update-install',{'version':version}),self.restarting)

def main():
    if '--restore-self-test' in sys.argv:
        from restore import restore_self_test
        restore_self_test();return
    if '--restore-dir' in sys.argv:
        from restore import restore_window
        restore_window(Path(sys.argv[sys.argv.index('--restore-dir')+1]));return
    if '--smoke-test' in sys.argv:
        root=tk.Tk();root.withdraw();App(root);root.update();root.destroy();return
    root=tk.Tk();App(root,local='--local-server' in sys.argv);root.mainloop()
if __name__=='__main__':main()
