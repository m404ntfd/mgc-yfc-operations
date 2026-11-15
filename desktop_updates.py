"""Read-only hourly desktop update notices. Installation happens at user restart."""
import threading
import time
import datetime as dt
from desktop_startup import check_release, APPS


class DesktopUpdateNotice:
    def __init__(self, app, version):
        self.app, self.version = app, version
        self.checked = None
        self.offer = None
        self.error = ''
        self.lock = threading.Lock()

    def status(self):
        with self.lock:
            now = time.monotonic()
            if self.checked is None or now-self.checked >= 3600:
                self.checked = now
                try:
                    self.offer = check_release(self.app, self.version)
                    self.error = ''
                except Exception as exc:
                    self.error = str(exc)
            return {'available':bool(self.offer), 'current':self.version,
                    'version':self.offer['version'] if self.offer else None,
                    'name':APPS[self.app][0], 'error':self.error,
                    'message':('An update is available. Restart '+APPS[self.app][0]+' to install it.') if self.offer else ''}


def bridge_update_status(bridge, app, version):
    if not bridge._trusted():return {'error':'Open the configured application server.'}
    if not hasattr(bridge,'_update_notice'):
        bridge._update_notice=DesktopUpdateNotice(app,version)
    return bridge._update_notice.status()


MAINTENANCE_MESSAGE='YFC OPERATIONS SERVER UPDATES & RESTARTS AT 4:00AM. SAVE ALL WORK AND EXIT APPLICATIONS UNTIL 04:05. APPLICATIONS WILL BE OFFLINE DURING THIS TIME'

def maintenance_banner_active(now=None):
    now=(now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    march=dt.datetime(now.year,3,8,8,tzinfo=dt.timezone.utc)
    march+=dt.timedelta(days=(6-march.weekday())%7)
    november=dt.datetime(now.year,11,1,7,tzinfo=dt.timezone.utc)
    november+=dt.timedelta(days=(6-november.weekday())%7)
    central=now.astimezone(dt.timezone(dt.timedelta(hours=-5 if march<=now<november else -6)))
    return 230<=central.hour*60+central.minute<=241

def maintenance_warning(parent,before):
    import tkinter as tk
    label=tk.Label(parent,text=MAINTENANCE_MESSAGE,background='#fff1c2',foreground='#312600',font=('Segoe UI',11,'bold'),padx=14,pady=12,justify='left',wraplength=700)
    def tick():
        if not label.winfo_exists():return
        if maintenance_banner_active():
            label.configure(wraplength=max(300,parent.winfo_width()-32));label.pack(fill='x',before=before)
        else:label.pack_forget()
        parent.after(1000,tick)
    tick()
    return label
