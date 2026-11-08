"""MGC YFC Operations Remote Manager — native Windows control panel."""
import json,os,queue,sys,threading,webbrowser,time
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
try:
    from .client import Client
except ImportError:
    from client import Client
NAME='MGC YFC Operations Remote Manager'
VERSION='0.46.0'
CONFIG=Path(os.environ.get('APPDATA',Path.home()))/'ThriftMartDispatchRemoteManager'/'config.json'

class App:
    def __init__(self,root,local=False,container=None,address=None,local_control=None,session_path=None,updates_container=None):
        self.root=root;self.client=None;self.release=None;self.busy=False;self.results=queue.Queue()
        self.local=local;self.local_control=local_control;self.session_path=session_path;self.update_receipt=None;self.flow=None;self.notice_id=None;self.monitor_client=None
        if container is None:
            root.title('MGC YFC Operations Server — Administration' if local else NAME);root.geometry('800x830');root.minsize(720,760)
            icon=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))/'assets'/('dispatch.ico' if local else 'remote.ico')
            if icon.exists():root.iconbitmap(str(icon))
        style=ttk.Style();style.theme_use('clam');style.configure('TButton',padding=9);style.configure('TLabel',font=('Segoe UI',10));style.configure('Title.TLabel',font=('Segoe UI',22,'bold'));style.configure('TEntry',padding=7)
        outer=ttk.Frame(container if container is not None else root);outer.pack(fill='both',expand=True)
        canvas=tk.Canvas(outer,highlightthickness=0);scrollbar=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
        scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scrollbar.set)
        frame=ttk.Frame(canvas,padding=16);window=canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
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
        ttk.Button(actions,text='Refresh status',command=self.refresh).pack(side='left',padx=6)
        ttk.Button(actions,text='OneDrive backup',command=self.backup).pack(side='left')
        ttk.Button(actions,text='Restart server',command=self.restart).pack(side='left',padx=6)
        connections=ttk.LabelFrame(frame,text='Active connections',padding=10);connections.pack(fill='x',pady=(12,0))
        self.connection_summary=tk.StringVar(value='Sign in to view active and inactive users. The server itself is excluded.')
        ttk.Label(connections,textvariable=self.connection_summary,wraplength=690).pack(anchor='w')
        self.connection_list=ttk.Treeview(connections,columns=('name','state','activity'),show='headings',height=4)
        for key,title,width in [('name','User / connection',260),('state','Status',130),('activity','Last interaction',170)]:self.connection_list.heading(key,text=title);self.connection_list.column(key,width=width)
        self.connection_list.pack(fill='x',pady=6)
        ttk.Button(connections,text='Refresh connections',command=self.refresh_connections).pack(anchor='w')
        updates=ttk.LabelFrame(updates_container if updates_container is not None else frame,text='Operations server updates',padding=12);updates.pack(fill='x',pady=16)
        row=ttk.Frame(updates);row.pack(fill='x');ttk.Button(row,text='Check for server updates',command=self.check).pack(side='left');self.install=ttk.Button(row,text='Install update & restart',command=self.install_update,state='disabled');self.install.pack(side='left',padx=8)
        flow_buttons=ttk.Frame(updates);flow_buttons.pack(fill='x',pady=8)
        self.notify=ttk.Button(flow_buttons,text='Notify users & update when ready',command=self.notify_update);self.notify.pack(side='left')
        self.cancel_pending=ttk.Button(flow_buttons,text='Cancel pending update',command=self.cancel_update);self.cancel_pending.pack(side='left',padx=6)
        if self.local_control:
            self.override=ttk.Button(updates,text='Force Update',command=self.force_update);self.override.pack(anchor='w',pady=4)
        if not self.local_control:ttk.Button(updates,text='Ready for pending update',command=self.acknowledge_update).pack(anchor='w',pady=4)
        self.notes=tk.Text(updates,height=5,wrap='word',font=('Segoe UI',10),state='disabled');self.notes.pack(fill='x',pady=8)
        ttk.Label(frame,text='Manage employees and login security in OFFICE. Closing this panel does not stop the server.',wraplength=690).pack(anchor='w')
        ttk.Button(updates_container if updates_container is not None else frame,text='Server / controller installer downloads',command=lambda:webbrowser.open('https://github.com/m404ntfd/mgc-yfc-operations/releases/latest')).pack(anchor='w',pady=(8,0))
        self.client_update_notes={}
        for kind,label in [('pos','DESK'),('office','OFFICE')]:
            section=ttk.LabelFrame(updates_container if updates_container is not None else frame,text=label+' application updates',padding=12);section.pack(fill='x',pady=8)
            line=ttk.Frame(section);line.pack(fill='x')
            for text,action in [('Check for updates','check'),('Install and restart','install'),('Notify Users & Update when ready','notify')]:ttk.Button(line,text=text,command=lambda k=kind,a=action:self.client_update(k,a)).pack(side='left',padx=2)
            line=ttk.Frame(section);line.pack(fill='x')
            if self.local_control:ttk.Button(line,text='Force Update',command=lambda k=kind:self.client_update(k,'force')).pack(side='left')
            ttk.Button(line,text='Cancel pending update',command=lambda k=kind:self.client_update(k,'cancel')).pack(side='left',padx=4)
            value=tk.StringVar(value='Check for the latest release. Targets connected '+label+' applications.');self.client_update_notes[kind]=value;ttk.Label(section,textvariable=value,wraplength=700).pack(anchor='w',pady=6)
        root.after(100,self.deliver)
        root.after(2000,self.poll_connections)
        if local_control and session_path:
            client=self.new_client()
            def restored(result):
                if result:self.client=client;self.show_status(result)
                else:self.status.set('Sign in with an administrator account. Local sign-in is kept until an application update or sign-out.')
            self.run(client.restore_local_session,restored)
    def run(self,work,done,quiet=False):
        if self.busy:return
        self.busy=True
        if not quiet:self.status.set('Working…')
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
        if not self.require():return
        dialog=tk.Toplevel(self.root);dialog.title('OneDrive backup');dialog.transient(self.root);dialog.grab_set();dialog.geometry('560x280');dialog.protocol('WM_DELETE_WINDOW',lambda:None)
        frame=ttk.Frame(dialog,padding=24);frame.pack(fill='both',expand=True)
        message=tk.StringVar(value='Creating the backup and verifying the saved archive…');dialog.backup_message=message
        ttk.Label(frame,textvariable=message,wraplength=500).pack(fill='x',pady=10)
        progress=ttk.Progressbar(frame,mode='indeterminate',length=440);progress.pack(fill='x');progress.start(15)
        okay=ttk.Button(frame,text='Okay',command=dialog.destroy,state='disabled');okay.pack(pady=15)
        client=self.client
        def work():
            try:return client.request('admin/backup-now',{})
            except Exception as e:return {'error':str(e)}
        def done(r):
            progress.stop();progress.configure(mode='determinate',value=0 if r.get('error') else 100)
            if r.get('error'):message.set('Backup failed. '+r['error'])
            elif r.get('verified'):message.set('Backup completed and verified in the configured folder:\n'+r['backup']+'\n\nCheck OneDrive separately to confirm cloud synchronization.');self.status.set('Verified backup completed.')
            else:message.set('The server did not confirm verification. Check backup status before installing updates.')
            okay.configure(state='normal');dialog.protocol('WM_DELETE_WINDOW',dialog.destroy)
        self.run(work,done)
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
    def render_connections(self,data):
        self.connection_list.delete(*self.connection_list.get_children())
        count=sum(row['status']=='active' for row in data['connections'])
        self.connection_summary.set(f"{count} active · {data.get('inactive_connections',0)} inactive · inactive after {data.get('inactive_minutes',5)} minutes. Server controller excluded.")
        for row in data['connections']:
            stamp=row.get('last_active');age='Just now' if stamp and time.time()-stamp<60 else f"{int((time.time()-stamp)/60)} min ago" if stamp else 'PIN task'
            self.connection_list.insert('', 'end',values=(row['name']+' · '+row['kind'],row['status'].title(),age))
    def refresh_connections(self):
        if self.require():self.run(lambda:self.client.request('admin/update-connections',activity=False),self.render_connections,quiet=True)
    def poll_connections(self):
        self.root.after(5000,self.poll_connections)
        if self.busy:return
        if self.update_receipt and self.monitor_client:
            def complete(result):
                phase=result['phase']
                if phase in ('complete','failed','canceled'):
                    self.update_receipt=None;self.flow=None
                    text='Update complete: version '+result['version']+'. Sign in again.' if phase=='complete' else result.get('error') or 'Update request canceled.'
                    self.status.set(text)
                    if phase=='complete':self.client=None;self.release=None;self.install.config(state='disabled');messagebox.showinfo(NAME,text,parent=self.root)
                else:
                    self.status.set('Update '+result['version']+' · '+phase+'. Keep this window open.')
                    if self.client and phase in ('preparing','waiting'):self.refresh_flow()
            self.run(lambda:self.monitor_client.request('update-result?receipt='+self.update_receipt,activity=False),complete,quiet=True)
        elif self.client:self.refresh_flow()
    def refresh_flow(self):
        if not self.require():return
        client=self.client
        def work():return client.request('admin/update-connections',activity=False),client.request('update-flow',activity=False)
        def done(result):
            connections,flow=result;self.render_connections(connections);self.flow=flow
            if not flow.get('active'):return
            self.status.set('Update '+flow['version']+': '+str(flow['waiting'])+' active connection(s) still finishing.')
            if flow.get('receipt'):self.update_receipt=flow['receipt'];self.monitor_client=client
            if not self.local_control and not flow.get('requester') and not flow.get('ready') and self.notice_id!=flow['id']:
                self.notice_id=flow['id']
                if messagebox.askyesno(NAME,'An update is pending. Is your current work saved and are you ready? Choose No to finish your work first.',parent=self.root):
                    self.run(lambda:client.request('update-flow/acknowledge',{'id':flow['id'],'ready':True}),lambda r:self.status.set('Ready. Waiting for the update.'))
        self.run(work,done,quiet=True)
    def start_flow(self,force=False):
        if not self.require():return
        version=(self.flow or {}).get('version') if force and (self.flow or {}).get('active') else self.release
        if not version:self.status.set('Check for a newer release first.');return
        question=('Override user notifications and acknowledgements and install version '+version+' now? This can interrupt unsaved work. Saved records are backed up before installation.' if force else 'Notify active users, let them finish, and install version '+version+' automatically when ready? Your current work must be saved.')
        if not messagebox.askyesno(NAME,question,parent=self.root):return
        client=self.client
        def done(result):
            self.flow=result;self.update_receipt=result['receipt'];self.monitor_client=client
            self.status.set('Override requested. Downloading/installing safely.' if force else 'Users notified. Waiting for active users to finish.')
        self.run(lambda:client.request('update-flow/'+('force' if force else 'start'),{'version':version,'ready':True}),done)
    def acknowledge_update(self):
        if not self.require():return
        if not messagebox.askyesno(NAME,'Confirm your work is saved. This connection will pause until the update finishes.',parent=self.root):return
        client=self.client
        def work():
            flow=client.request('update-flow',activity=False)
            if not flow.get('active'):raise ValueError('There is no pending update.')
            return client.request('update-flow/acknowledge',{'id':flow['id'],'ready':True})
        self.run(work,lambda result:self.status.set('Ready. Waiting for the update.'))
    def notify_update(self):self.start_flow()
    def force_update(self):
        if self.local_control:self.start_flow(force=True)
    def cancel_update(self):
        if not self.require():return
        client=self.client
        def work():
            flow=client.request('update-flow',activity=False)
            if not flow.get('active'):raise ValueError('There is no pending update.')
            return client.request('update-flow/cancel',{'id':flow['id']})
        self.run(work,lambda r:self.status.set('Update request canceled.'))
    def client_update(self,kind,action):
        if not self.require():return
        if action in ('install','notify','force'):
            text='Force installation on connected applications? Saved sales remain on the server; in-progress writes must finish.' if action=='force' else 'Update connected applications after their work is saved?'
            if not messagebox.askyesno(NAME,text,parent=self.root):return
        route='start' if action in ('install','notify','force') else action
        payload={'target':'all','mode':action} if route=='start' else {}
        def done(data):
            release=data.get('release',{});campaign=data.get('campaign')
            self.client_update_notes[kind].set(release.get('error') or ('Checking…' if release.get('checking') else 'Latest: '+release.get('version','Not checked'))+(' · Update pending' if campaign else ''))
            if release.get('checking'):self.root.after(2000,lambda:self.client_update_status(kind))
        self.run(lambda:self.client.request(kind+'-update/'+route,payload),done)
    def client_update_status(self,kind):
        if not self.require():return
        def done(data):
            r=data.get('release',{});self.client_update_notes[kind].set(r.get('error') or ('Checking…' if r.get('checking') else 'Latest: '+r.get('version','Not checked'))+' · '+str(len(data.get('devices',[])))+' connected devices')
            if r.get('checking'):self.root.after(2000,lambda:self.client_update_status(kind))
        self.run(lambda:self.client.request(kind+'-update/state',activity=False),done,quiet=True)
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
