"""Themed native startup connection dialog. Background checks cannot save settings."""
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from connection_preferences import load

def connect(app,address,save,probe,normalize,*,configure=False,authorize=None,on_register=None):
    preferences=load(app); root=tk.Tk();root.title('CoastYouth Retail — Server Connection')
    root.geometry('720x440');root.resizable(False,False);root.configure(bg=preferences['background'])
    style=ttk.Style(root);style.theme_use('clam')
    style.configure('Connection.TButton',padding=(15,13),font=('Segoe UI',11,'bold'),background=preferences['panel'],foreground=preferences['text'],bordercolor=preferences['border'])
    style.map('Connection.TButton',background=[('active',preferences['background'])],foreground=[('active',preferences['text'])])
    style.configure('Connection.TEntry',fieldbackground=preferences['panel'],foreground=preferences['text'],padding=8)
    panel=tk.Frame(root,bg=preferences['panel'],padx=30,pady=24);panel.pack(fill='both',expand=True,padx=14,pady=14)
    def label(parent,text='',**kwargs):return tk.Label(parent,text=text,bg=preferences['panel'],fg=preferences['text'],font=('Segoe UI',11),**kwargs)
    logo=tk.Canvas(panel,width=188,height=112,bg=preferences['panel'],highlightthickness=0);logo.pack(pady=(0,14))
    for left,top in ((88,4),(64,39),(92,53)):logo.create_oval(left,top,left+42,top+54,outline=preferences['text'],width=5)
    track=tk.Canvas(panel,width=610,height=50,bg=preferences['panel'],highlightthickness=0)
    heading=tk.StringVar();title=label(panel,textvariable=heading,wraplength=620);title.configure(font=('Segoe UI',22,'bold'))
    status=tk.StringVar();detail=label(panel,textvariable=status,wraplength=610,justify='center')
    editor=tk.Frame(panel,bg=preferences['panel']);value=tk.StringVar(value=address)
    label(editor,'Server address',anchor='w').pack(fill='x');entry=ttk.Entry(editor,textvariable=value,font=('Segoe UI',13),style='Connection.TEntry');entry.pack(fill='x',pady=(5,12))
    label(editor,'Connection timeout: '+str(preferences['timeout_seconds'])+' seconds. Managed in OFFICE.\nThe saved setting refreshes after a successful login.\nConnect your VPN first if needed. An administrator can then register this PC.',wraplength=610,justify='left').pack(fill='x')
    actions=tk.Frame(panel,bg=preferences['panel']);results=queue.Queue();selected=[]
    state=dict(busy=False,closed=False,editing=configure,generation=0,deadline=0,position=0,direction=1,timer=None)
    def layout(mode):
        for widget in (track,title,detail,editor,actions):widget.pack_forget()
        for button in (primary,change,leave):button.pack_forget()
        state['editing']=mode=='configure';state['busy']=mode=='connecting'
        root.geometry('720x610' if mode=='configure' else '720x440')
        if mode=='connecting':track.pack(pady=(0,12))
        title.pack(fill='x',pady=(4,10))
        if mode!='connecting':detail.pack(fill='x',pady=(0,12))
        if mode=='configure':editor.pack(fill='x',pady=(0,12))
        if mode!='connecting':
            actions.pack(side='bottom',fill='x',pady=(12,0));primary.configure(text='Connect' if mode=='configure' else 'Retry Connection');primary.pack(side='left')
            if mode!='configure':change.pack(side='left',padx=10)
            leave.pack(side='right')
    def close():
        state['closed']=True;state['generation']+=1
        if state['timer'] is not None:root.after_cancel(state['timer'])
        root.destroy()
    def configure_server():
        if state['busy']:return
        if on_register:on_register()
        heading.set('Configure Server Connection');status.set('Your server address is saved only after a successful connection.')
        layout('configure');entry.focus_set();entry.selection_range(0,'end')
    def failure(message):
        state['generation']+=1;heading.set('Can Not Connect to Operations Server');status.set(message);layout('failed');primary.focus_set()
    def check():
        if state['busy']:return
        try:
            candidate=normalize(value.get());duration_value=preferences['timeout_seconds']
            if candidate!=address and authorize and not authorize(candidate,root):
                status.set('The connection was not changed. Enter the current administrator passcode to change servers.');return
        except Exception as error:
            heading.set('Configure Server Connection');status.set(str(error));layout('configure');return
        state['generation']+=1;generation=state['generation'];state['deadline']=time.monotonic()+duration_value
        state['position']=0;state['direction']=1;heading.set('Connecting to Server');status.set('');layout('connecting')
        def worker():
            try:probe(candidate,app,timeout_seconds=duration_value);results.put((generation,candidate,None))
            except Exception as error:results.put((generation,candidate,str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def poll():
        state['timer']=None
        if state['busy']:
            # A monotonic deadline bounds the complete attempt, including DNS,
            # TLS and both DESK probes. Late results never navigate or save.
            if time.monotonic()>=state['deadline']:failure('No response within '+str(preferences['timeout_seconds'])+' seconds. Check the network or VPN, then retry.')
            else:
                track.delete('all');track.create_rectangle(2,2,608,48,outline=preferences['text'],width=2)
                for i in range(22):
                    left=12+i*26.7;lit=state['position']<=i<state['position']+7
                    track.create_rectangle(left,9,left+21,41,fill=preferences['text'] if lit else preferences['background'],outline=preferences['border'],width=0 if lit else 1)
                state['position']+=state['direction']
                if state['position'] in (0,15):state['direction']*=-1
        try:
            while True:
                generation,candidate,error=results.get_nowait()
                if generation!=state['generation'] or not state['busy']:continue
                if error:failure(error);continue
                try:
                    if configure or candidate!=address:save(candidate)
                    selected.append(candidate);close();return
                except Exception as error:failure('The connection worked, but its settings could not be saved: '+str(error))
        except queue.Empty:pass
        if not state['closed']:state['timer']=root.after(80,poll)
    primary=ttk.Button(actions,text='Retry Connection',command=check,style='Connection.TButton')
    change=ttk.Button(actions,text='Configure Server Connection',command=configure_server,style='Connection.TButton')
    leave=ttk.Button(actions,text='Log Out',command=close,style='Connection.TButton')
    root.protocol('WM_DELETE_WINDOW',close);root.bind('<Return>',lambda e:check())
    if configure:configure_server()
    else:root.after(0,check)
    state['timer']=root.after(80,poll);root.mainloop();return selected[0] if selected else None
