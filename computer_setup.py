"""Computer registration wizard launched by the all-in-one Windows installer."""
import argparse
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox

from installer_registration import SetupRegistration


class RegistrationWizard:
    def __init__(self,root,client,name='',role='office',default_server=''):
        self.root=root;self.client=client;self.role=role;self.busy=False;self.complete=False;self.result=2;self.jobs=queue.Queue()
        root.title('CoastYouth Retail — Connect & register computer');root.geometry('840x780');root.minsize(800,740)
        root.protocol('WM_DELETE_WINDOW',self.close)
        ttk.Style(root).configure('Setup.TButton',padding=(12,9))
        outer=ttk.Frame(root,padding=24);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Connect & register this computer',font=('Segoe UI',21,'bold')).pack(anchor='w')
        ttk.Label(outer,text='Windows computer: '+client.identity['hostname'],font=('Segoe UI',11)).pack(anchor='w',pady=(8,0))
        ttk.Label(outer,text='Your existing sales, timecards, reservations and settings stay in place.',wraplength=760).pack(anchor='w',pady=(4,14))
        self.progress=ttk.Progressbar(outer,maximum=3,value=1);self.progress.pack(fill='x',pady=(0,12))
        self.form=ttk.Frame(outer);self.form.pack(fill='x')
        addresses=client.saved_addresses();unique=list(dict.fromkeys(v for v in addresses.values() if v))
        self.address=tk.StringVar(value=unique[0] if len(unique)==1 else default_server)
        self.username=tk.StringVar();self.password=tk.StringVar();self.name=tk.StringVar(value=name or client.identity['hostname'])
        self.exit_code=tk.StringVar();self.restore=tk.BooleanVar();self.reuse=tk.BooleanVar()
        self.entries=[]
        def entry(label,value,secret=False):
            ttk.Label(self.form,text=label).pack(anchor='w',pady=(6,3))
            widget=ttk.Entry(self.form,textvariable=value,font=('Segoe UI',12),show='*' if secret else '')
            widget.pack(fill='x',ipady=4);self.entries.append(widget);return widget
        self.address_entry=entry('Operations server address',self.address)
        ttk.Label(self.form,text='Examples: https://operations.coastyfc.com or http://SERVER-PC:8080').pack(anchor='w')
        if len(unique)>1:ttk.Label(self.form,text='These applications use different saved addresses. Choose the server they should all use.',wraplength=750).pack(anchor='w')
        entry('Administrator username',self.username);entry('Administrator password',self.password,True)
        self.connect_button=ttk.Button(self.form,text='Check connection & sign in',command=self.connect,style='Setup.TButton');self.connect_button.pack(anchor='w',pady=10)
        self.registration=ttk.Frame(outer)
        ttk.Label(self.registration,text='Name shown in OFFICE',font=('Segoe UI',10,'bold')).pack(anchor='w')
        self.name_entry=ttk.Entry(self.registration,textvariable=self.name,font=('Segoe UI',12));self.name_entry.pack(fill='x',ipady=4)
        self.assignment=ttk.Label(self.registration,text='',wraplength=740);self.assignment.pack(anchor='w',pady=7)
        self.store_label=ttk.Label(self.registration,text='Store for this new checkout')
        self.store=ttk.Combobox(self.registration,state='readonly')
        self.terminal_label=ttk.Label(self.registration,text='Checkout terminal')
        self.terminal=ttk.Combobox(self.registration,state='readonly')
        self.restore_check=ttk.Checkbutton(self.registration,text='Re-register the removed checkout and keep its original store and history',variable=self.restore)
        self.reuse_check=ttk.Checkbutton(self.registration,text='This is the matching computer — update its existing registration',variable=self.reuse)
        self.exit_label=ttk.Label(self.registration,text='Existing DESK admin exit passcode (only if changing its server)')
        self.exit_entry=ttk.Entry(self.registration,textvariable=self.exit_code,show='*')
        self.status=tk.StringVar(value='Enter the Operations server address and administrator credentials. If this is a new server, start it and create its administrator account first.')
        ttk.Label(outer,textvariable=self.status,wraplength=760,font=('Segoe UI',10)).pack(anchor='w',pady=14)
        footer=ttk.Frame(outer);footer.pack(side='bottom',fill='x')
        self.back=ttk.Button(footer,text='Change connection',command=self.change,style='Setup.TButton');self.back.pack(side='left');self.back.state(['disabled'])
        self.register_button=ttk.Button(footer,text='Register computer',command=self.register,style='Setup.TButton');self.register_button.pack(side='right');self.register_button.state(['disabled'])
        self.cancel=ttk.Button(footer,text='Close',command=self.close,style='Setup.TButton');self.cancel.pack(side='right',padx=8)
        self.address_entry.focus_set();self.timer=root.after(80,self.pump)

    def work(self,action,done):
        if self.busy:return
        self.busy=True
        for control in self.entries+[self.connect_button,self.back,self.register_button,self.name_entry,self.store,self.terminal,self.restore_check,self.reuse_check,self.exit_entry]:control.configure(state='disabled')
        def run():
            try:self.jobs.put((done,action(),None))
            except Exception as error:self.jobs.put((done,None,str(error)))
        threading.Thread(target=run,daemon=True).start()

    def pump(self):
        try:
            done,value,error=self.jobs.get_nowait();self.busy=False
            if error:
                self.status.set(error)
                if self.client.details:
                    self.register_button.configure(state='normal',text='Retry registration' if self.client.pending else 'Register computer')
                    if not self.client.pending:self.enable_registration()
                else:
                    for control in self.entries+[self.connect_button]:control.configure(state='normal')
            else:done(value)
        except queue.Empty:pass
        self.timer=self.root.after(80,self.pump)

    def connect(self):
        address=self.address.get();name=self.username.get().strip();password=self.password.get()
        if not name or not password:self.status.set('Enter an administrator username and password.');return
        self.password.set('');self.status.set('Checking the server and administrator account…')
        self.work(lambda:self.client.connect(address,name,password),self.connected)

    def connected(self,details):
        self.form.pack_forget();self.registration.pack(fill='x',after=self.progress);self.progress.configure(value=2)
        pc=details['computer']
        if pc['registered']:
            if self.name.get()==self.client.identity['hostname']:self.name.set(pc['name'])
            self.role=pc['role']
        self.stores=details['stores'];self.terminals=details['available_terminals']
        self.store.configure(values=[s['name'] for s in self.stores]);self.store.current(0)
        self.terminal.configure(values=['Create a new checkout']+[t['name'] for t in self.terminals]);self.terminal.current(0)
        current=details['terminal']
        self.assignment.configure(text=('Existing checkout: '+current['name']+' — store and history will be kept.') if current else 'This PC will appear in OFFICE → Terminals / Registered computers.')
        network='\nAdapter: '+details.get('active_adapter','')+' · MAC: '+details['active_mac'] if details.get('active_mac') else '\nNo adapter MAC is available for this connection; the persistent computer identity will be used.'
        self.assignment.configure(text=self.assignment.cget('text')+network)
        if details.get('matched_by_mac'):
            self.assignment.configure(text=self.assignment.cget('text')+'\nExisting MAC match: '+pc['name']+' ('+pc['hostname']+'). Confirm it is this PC.')
            self.reuse_check.pack(anchor='w',pady=7)
        if 'pos' in self.client.apps and not current:
            for widget in (self.store_label,self.store,self.terminal_label,self.terminal):widget.pack(fill='x',pady=3)
        if details.get('removed_terminal'):self.restore_check.pack(anchor='w',pady=7)
        if self.client.requires_exit_code():
            for widget in (self.exit_label,self.exit_entry):widget.pack(fill='x',pady=3)
        self.status.set('Server connection verified. Administrator approved. Confirm the name and checkout assignment, then select Register computer.')
        self.enable_registration();self.name_entry.focus_set()

    def enable_registration(self):
        for control in (self.back,self.register_button,self.name_entry,self.restore_check,self.reuse_check,self.exit_entry):control.configure(state='normal')
        self.store.configure(state='readonly');self.terminal.configure(state='readonly')

    def register(self):
        if self.complete:self.close();return
        name=self.name.get().strip()
        if not name or len(name)>60:self.status.set('Enter a registered computer name of 1–60 characters.');return
        if self.client.details.get('removed_terminal') and not self.restore.get():self.status.set('Confirm re-registration of the removed checkout to continue, or close setup. Its historical data will be retained.');return
        if self.client.details.get('matched_by_mac') and not self.reuse.get():self.status.set('Confirm this is the matching registered computer. A duplicate will not be created.');return
        store=self.stores[max(0,self.store.current())]['id'];index=self.terminal.current()
        terminal=self.terminals[index-1]['id'] if index>0 else ''
        code=self.exit_code.get();restore=self.restore.get();reuse=self.reuse.get();self.exit_code.set('');self.status.set('Registering this computer and saving verified connections…')
        self.work(lambda:self.client.register(name,self.role,store,terminal,restore,code,reuse),self.registered)

    def registered(self,result):
        self.complete=True;self.result=0;self.progress.configure(value=3)
        self.status.set('Registered: '+result['computer']['name']+'\nConnected to '+self.client.address+'\nRegistration is saved in OFFICE. Your existing data and application settings are kept.')
        self.register_button.configure(state='normal',text='Finish');self.cancel.pack_forget()

    def change(self):
        if self.busy or self.client.pending:return
        self.client.close();self.registration.pack_forget();self.form.pack(fill='x',after=self.progress)
        for widget in (self.store_label,self.store,self.terminal_label,self.terminal,self.restore_check,self.reuse_check,self.exit_label,self.exit_entry):widget.pack_forget()
        for control in self.entries+[self.connect_button]:control.configure(state='normal')
        self.back.state(['disabled']);self.register_button.state(['disabled']);self.progress.configure(value=1)
        self.status.set('Enter the server address and sign in again. Saved connections have not been changed.')

    def close(self):
        if self.busy:self.status.set('Please wait for the connection or registration check to finish.');return
        if not self.complete and not messagebox.askyesno('Registration unfinished','Close without finishing registration? Installed applications and all existing data will remain in place. Run Computer Setup again to finish.',parent=self.root):return
        self.root.after_cancel(self.timer);self.client.close();self.root.destroy()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apps',default='');parser.add_argument('--name',default='');parser.add_argument('--role',choices=['server','office','pos','other'],default='office');parser.add_argument('--server',default='');parser.add_argument('--smoke-test',action='store_true')
    args=parser.parse_args()
    from pos_updater import VERSION as desk_version
    from office_desktop import VERSION as office_version
    from store_ops_desktop import VERSION as ops_version
    if args.smoke_test:
        assert all(isinstance(v,str) and len(v.split('.'))==3 for v in (desk_version,office_version,ops_version))
        root=tk.Tk();root.withdraw();root.destroy();return 0
    root=tk.Tk()
    try:
        client=SetupRegistration([a for a in args.apps.split(',') if a],{'pos':desk_version,'office':office_version,'ops':ops_version})
        wizard=RegistrationWizard(root,client,args.name,args.role,args.server);root.mainloop();return wizard.result
    except Exception as error:
        root.withdraw();messagebox.showerror('Computer registration',str(error),parent=root);root.destroy();return 1


if __name__=='__main__':raise SystemExit(main())
