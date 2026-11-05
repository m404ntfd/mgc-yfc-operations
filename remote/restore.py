"""Offline restore for complete Thrift Mart Dispatch backups."""
import contextlib,json,os,shutil,sqlite3,tempfile,time,zipfile
from pathlib import Path
ALLOWED={'schedule.db','updates.json','backup-settings.json','manifest.json'}
@contextlib.contextmanager
def data_lock(data):
    data=Path(data);data.mkdir(parents=True,exist_ok=True)
    f=(data/'server.lock').open('a+b');f.seek(0);f.write(b'0');f.flush();f.seek(0)
    try:
        try:
            if os.name=='nt':
                import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise ValueError('The server is running. Choose Exit server from its truck tray menu before restoring.')
        yield
    finally:f.close()

def restore_backup(source,data):
    data=Path(data)
    with data_lock(data),tempfile.TemporaryDirectory(dir=data) as temp:
        temp=Path(temp)
        with zipfile.ZipFile(source) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or not set(names)<=ALLOWED or not {'manifest.json','schedule.db'}<=set(names):raise ValueError('This is not a supported complete dispatch backup.')
            if sum(i.file_size for i in z.infolist())>512*1024*1024:raise ValueError('Backup is too large for this restore tool.')
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('application')!='thrift-mart-dispatch' or manifest.get('format')!=1:raise ValueError('Unrecognized backup format.')
            for n in names:
                if n!='manifest.json':(temp/n).write_bytes(z.read(n))
        for n in ('updates.json','backup-settings.json'):
            if (temp/n).exists() and not isinstance(json.loads((temp/n).read_text()),dict):raise ValueError('Invalid settings file.')
        with contextlib.closing(sqlite3.connect(temp/'schedule.db')) as c:
            if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('The backup database failed its integrity check.')
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'jobs','vehicles','users','audit'}<=tables:raise ValueError('The backup is not a dispatch database.')
        # A replacement PC may not have the original OneDrive location. Keep it as a
        # hint, but require deliberate reconnection before writing new cloud backups.
        settings=temp/'backup-settings.json'
        if settings.exists():
            cfg=json.loads(settings.read_text());cfg['enabled']=False;settings.write_text(json.dumps(cfg))
        before=data/'restore-safety'/str(time.time_ns());before.mkdir(parents=True)
        names=('schedule.db','updates.json','backup-settings.json')
        existed={n:(data/n).exists() for n in names}
        for n in names:
            if existed[n]:shutil.copy2(data/n,before/n)
        try:
            for n in names:
                if (temp/n).exists():os.replace(temp/n,data/n)
                elif (data/n).exists():(data/n).unlink()
        except Exception:
            for n in names:
                if existed[n]:shutil.copy2(before/n,data/n)
                elif (data/n).exists():(data/n).unlink()
            raise
        return str(before)

def restore_window(data):
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    root=tk.Tk();root.title('Restore MGC YFC Operations Server');root.geometry('650x300')
    frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Restore server from OneDrive backup',font=('Segoe UI',16,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Choose Exit server from the truck tray menu first. Choose a downloaded backup ZIP from OneDrive.\nThis replaces appointments, accounts, vehicles and settings with the backup.\nCurrent data is saved separately before replacement.',wraplength=590).pack(anchor='w',pady=16)
    status=tk.StringVar(value='Destination: '+str(data));ttk.Label(frame,textvariable=status,wraplength=590).pack(anchor='w')
    def choose():
        path=filedialog.askopenfilename(title='Select dispatch backup',filetypes=[('Dispatch backup ZIP','*.zip')])
        if not path:return
        if not messagebox.askyesno('Restore backup','Replace current server data with this backup?'):return
        try:
            saved=restore_backup(path,data);status.set('Restore complete. Start the server and sign in using an account from the backup. Reconnect OneDrive backups in Settings.');messagebox.showinfo('Restored','Restored successfully. Previous data was saved in '+saved)
        except Exception as e:messagebox.showerror('Restore failed',str(e))
    ttk.Button(frame,text='Choose backup and restore…',command=choose).pack(anchor='w',pady=20)
    root.mainloop()

def restore_self_test():
    with tempfile.TemporaryDirectory() as t:
        root=Path(t);db=root/'source.db'
        with contextlib.closing(sqlite3.connect(db)) as c:
            for name in ('jobs','users','vehicles','audit'):c.execute('CREATE TABLE '+name+'(name TEXT)')
            c.execute("INSERT INTO users VALUES('RestoreTest')");c.commit()
        archive=root/'backup.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.write(db,'schedule.db');z.writestr('manifest.json',json.dumps({'application':'thrift-mart-dispatch','format':1}));z.writestr('backup-settings.json',json.dumps({'enabled':True,'folder':'old'}))
        restore_backup(archive,root/'restored')
        assert not json.loads((root/'restored/backup-settings.json').read_text())['enabled']
