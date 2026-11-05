"""MGC YFC Operations Server: trusted-local-network scheduling server. Python 3.11+."""
import datetime as dt
import hashlib, hmac, json, os, secrets, socket, sqlite3, threading, time
import updater
import tempfile, zipfile, base64
from contextlib import contextmanager, closing
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('DISPATCH_DATA', ROOT/'data'))
DATA.mkdir(parents=True, exist_ok=True)
DB=DATA/'schedule.db'
LOCK=threading.RLock()
SESSIONS={}
ATTEMPTS={}
RESTART=False
STOPPING=False
STARTED=time.time()

@contextmanager
def connect():
    c=sqlite3.connect(DB, timeout=15)
    c.row_factory=sqlite3.Row
    try:
        with c: yield c
    finally: c.close()

def init():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY COLLATE NOCASE, salt TEXT, hash TEXT, admin INTEGER);
CREATE TABLE IF NOT EXISTS permissions(name TEXT PRIMARY KEY COLLATE NOCASE, can_create INTEGER NOT NULL DEFAULT 1, see_requests INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS photos(job TEXT, position INTEGER, body BLOB, PRIMARY KEY(job,position));
CREATE TABLE IF NOT EXISTS vehicles(name TEXT PRIMARY KEY COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, revision INTEGER, body TEXT);
CREATE TABLE IF NOT EXISTS update_notices(id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT, actor TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS landing_preferences(name TEXT PRIMARY KEY COLLATE NOCASE, section TEXT);
CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, actor TEXT, area TEXT);
CREATE TABLE IF NOT EXISTS login_security(id INTEGER PRIMARY KEY CHECK(id=1), max_attempts INTEGER NOT NULL);
INSERT OR IGNORE INTO login_security VALUES(1,5);
CREATE TABLE IF NOT EXISTS account_lockouts(name TEXT PRIMARY KEY COLLATE NOCASE, failures INTEGER NOT NULL DEFAULT 0, locked_at TEXT);
CREATE TABLE IF NOT EXISTS audit(at TEXT, actor TEXT, action TEXT, job TEXT);''')
        if 'chosen_on' not in {r[1] for r in c.execute('PRAGMA table_info(landing_preferences)')}:
            c.execute('ALTER TABLE landing_preferences ADD COLUMN chosen_on TEXT')
        c.execute('CREATE TABLE IF NOT EXISTS journal_archives(file TEXT PRIMARY KEY, sha256 TEXT NOT NULL, records INTEGER NOT NULL, archived_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS user_grants(name TEXT PRIMARY KEY COLLATE NOCASE, body TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS app_migrations(name TEXT PRIMARY KEY)')
        if not c.execute("SELECT 1 FROM app_migrations WHERE name='schedule-view-default-v1'").fetchone():
            for row in c.execute('SELECT name,body FROM user_grants').fetchall():
                grants=json.loads(row['body']);grants['view_schedule']=True
                c.execute('UPDATE user_grants SET body=? WHERE name=?',(json.dumps(grants),row['name']))
            c.execute("INSERT INTO app_migrations VALUES('schedule-view-default-v1')")


PERMISSIONS={
 'send_pages':'Page an associate to an area', 'receive_pages':'Use device as paging speaker',
 'show_vehicle_filter':'Show vehicle filter on main dashboard', 'show_search':'Show search bar on main dashboard',
 'view_reports':'Open and print schedule/request reports',
 'view_schedule':'View schedule, search and filter', 'create_appointments':'Create pickups and deliveries',
 'edit_appointments':'Edit appointment details', 'delete_appointments':'Remove appointments',
 'update_status':'Set Scheduled / In Progress / Completed', 'cancel_appointments':'Cancel existing appointments',
 'submit_requests':'Submit pickup and delivery requests', 'review_requests':'Review and approve requests',
 'see_requests':'Show flashing Pending Requests button', 'call_contacts':'Show customer call button',
 'text_contacts':'Show On Our Way text button', 'navigate':'Show navigation button',
 'manage_vehicles':'Add vehicles', 'manage_users':'Add/remove employees and edit permissions',
 'unlock_users':'Unlock employee accounts after failed logins',
 'reset_passwords':'Reset employee passwords/passcodes', 'change_own_password':'Change own password/passcode',
 'view_audit':'View recent changes', 'backup_settings':'Manage backup settings',
 'create_backups':'Create backups', 'check_updates':'Check server updates',
 'configure_updates':'Change update repository', 'install_updates':'Install server updates',
 'view_server':'View server status', 'restart_server':'Restart server'}
ROUTE_PERMISSIONS={'/api/admin/lockouts':'unlock_users','/api/admin/unlock-user':'unlock_users','/api/paging/send':'send_pages',
 'send_pages':'Page an associate to an area', 'receive_pages':'Use device as paging speaker',
 'show_vehicle_filter':'Show vehicle filter on main dashboard', 'show_search':'Show search bar on main dashboard',
 'view_reports':'Open and print schedule/request reports','/api/admin/users':'manage_users','/api/admin/permissions':'manage_users',
 '/api/user':'manage_users','/api/admin/remove-user':'manage_users','/api/admin/password':'reset_passwords',
 '/api/account/password':'change_own_password','/api/vehicle':'manage_vehicles',
 '/api/admin/backup-settings':'backup_settings','/api/admin/backup-now':'create_backups',
 '/api/admin/backup':'create_backups','/api/admin/status':'view_server','/api/admin/restart':'restart_server',
 '/api/updates':'check_updates','/api/update-check':'check_updates','/api/update-config':'configure_updates',
 '/api/update-install':'install_updates','/api/audit':'view_audit'}
def has_permission(u,key): return bool(u['admin'] or u.get('grants',{}).get(key,False))
def route_allowed(u,path): return has_permission(u,ROUTE_PERMISSIONS.get(path,''))

def section_options(u):
    options=[]
    if has_permission(u,'view_schedule'): options.append({'id':'dispatch','label':'Thrift Mart Dispatch'})
    if has_permission(u,'send_pages') or has_permission(u,'receive_pages'): options.append({'id':'paging','label':'Store Associate Paging'})
    options.append({'id':'receipts','label':'Receipts & Accounting'})
    return options

def valid_credential(p): return 8<=len(p)<=256 or (len(p)==4 and all(c in '0123456789' for c in p))
def password(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(s),200000).hex()
def backup():
    folder=DATA/'backups'; folder.mkdir(exist_ok=True)
    target=folder/(dt.date.today().isoformat()+'.db')
    if not target.exists():
        with connect() as src, closing(sqlite3.connect(target)) as dest: src.backup(dest)
        for old in sorted(folder.glob('*.db'))[:-30]: old.unlink()

def backup_config():
    p=DATA/'backup-settings.json'
    if p.exists(): return json.loads(p.read_text())
    base=os.environ.get('OneDriveCommercial') or os.environ.get('OneDriveConsumer') or os.environ.get('OneDrive')
    return {'enabled':False,'folder':str(Path(base)/'Thrift Mart Dispatch Backups') if base else ''}

def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def journal_folder():
    cfg=backup_config()
    folder=Path(cfg.get('folder',''))
    if not cfg.get('folder') or not folder.is_absolute():raise ValueError('Configure the server backup folder first.')
    return folder/'Dispatch Journal'

@contextmanager
def open_journal(row):
    name=row['file']
    if Path(name).name!=name or not name.endswith('.db'):raise ValueError('Invalid Dispatch Journal filename.')
    path=journal_folder()/name
    if not path.is_file() or file_digest(path)!=row['sha256']:raise ValueError('Dispatch Journal unavailable or damaged: '+name+'. Check OneDrive before continuing.')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Dispatch Journal integrity check failed: '+name)
        yield c

def all_report_jobs(c):
    jobs={}
    for archive in c.execute('SELECT * FROM journal_archives ORDER BY archived_at'):
        with open_journal(archive) as journal:
            for row in journal.execute('SELECT * FROM jobs'):jobs[row['id']]=dict(json.loads(row['body']),id=row['id'])
    for row in c.execute('SELECT * FROM jobs'):jobs[row['id']]=dict(json.loads(row['body']),id=row['id'])
    return list(jobs.values())

def merge_journals(snapshot):
    # Make every complete backup independently restorable, including journal history.
    with closing(sqlite3.connect(snapshot)) as c:
        c.row_factory=sqlite3.Row
        for archive in c.execute('SELECT * FROM journal_archives ORDER BY archived_at DESC').fetchall():
            with open_journal(archive) as j:
                for row in j.execute('SELECT * FROM jobs'):c.execute('INSERT OR IGNORE INTO jobs VALUES(?,?,?)',tuple(row))
                for row in j.execute('SELECT * FROM photos'):c.execute('INSERT OR IGNORE INTO photos VALUES(?,?,?)',tuple(row))
                for row in j.execute('SELECT * FROM audit'):
                    if not c.execute('SELECT 1 FROM audit WHERE at=? AND actor=? AND action=? AND job=?',tuple(row)).fetchone():c.execute('INSERT INTO audit VALUES(?,?,?,?)',tuple(row))
        c.execute('DELETE FROM journal_archives');c.commit()
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup database integrity check failed.')
        counts={'Pickup':0,'Delivery':0,'other':0,'total':0,'photos':c.execute('SELECT COUNT(*) FROM photos').fetchone()[0]}
        for row in c.execute('SELECT body FROM jobs'):
            kind=json.loads(row[0]).get('type');counts[kind if kind in ('Pickup','Delivery') else 'other']+=1;counts['total']+=1
        return counts

def verify_backup_archive(path,expected_digest):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Backup ZIP integrity check failed.')
        digest=hashlib.sha256(z.read('schedule.db')).hexdigest()
        manifest=json.loads(z.read('manifest.json'))
        if digest!=expected_digest or manifest.get('database_sha256')!=digest:raise ValueError('Saved backup does not match the database snapshot.')
        return manifest

def archive_dispatch(today=None):
    try:
        count=_archive_dispatch(today)
        (DATA/'journal-status.json').write_text(json.dumps({'at':dt.datetime.now().isoformat(),'archived':count,'error':None}))
        return count
    except Exception as e:
        (DATA/'journal-status.json').write_text(json.dumps({'at':dt.datetime.now().isoformat(),'error':str(e)}))
        raise

def _archive_dispatch(today=None):
    # The shared lock prevents an appointment changing between copy, verify and removal.
    with LOCK:
        cfg=backup_config()
        if not cfg.get('enabled') or not cfg.get('journal_enabled',True):return 0
        cutoff=(today or dt.date.today())-dt.timedelta(days=30)
        with connect() as c:
            selected=[]
            for row in c.execute('SELECT * FROM jobs'):
                job=json.loads(row['body'])
                if job.get('status') not in ('Completed','Canceled'):continue
                try:
                    event=dt.date.fromisoformat((job.get('end') or job.get('start') or '')[:10])
                    last=c.execute('SELECT MAX(at) FROM audit WHERE job=?',(row['id'],)).fetchone()[0]
                    modified=dt.date.fromisoformat(last[:10]) if last else event
                except ValueError:continue
                if max(event,modified)>=cutoff:continue
                selected.append(tuple(row))
            if not selected:return 0
        # A fresh, complete and verified fallback must exist before any local removal.
        complete_backup()
        folder=journal_folder();folder.mkdir(parents=True,exist_ok=True)
        target=folder/('Dispatch-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(6)+'.db')
        partial=target.with_suffix('.partial')
        try:
            with connect() as source, closing(sqlite3.connect(partial)) as dest:
                dest.executescript('CREATE TABLE jobs(id TEXT PRIMARY KEY,revision INTEGER,body TEXT); CREATE TABLE photos(job TEXT,position INTEGER,body BLOB,PRIMARY KEY(job,position)); CREATE TABLE audit(at TEXT,actor TEXT,action TEXT,job TEXT);')
                for row in selected:
                    dest.execute('INSERT INTO jobs VALUES(?,?,?)',row)
                    dest.executemany('INSERT INTO photos VALUES(?,?,?)',[tuple(r) for r in source.execute('SELECT * FROM photos WHERE job=?',(row[0],))])
                    dest.executemany('INSERT INTO audit VALUES(?,?,?,?)',[tuple(r) for r in source.execute('SELECT * FROM audit WHERE job=?',(row[0],))])
                dest.commit()
                if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Journal integrity check failed.')
            digest=file_digest(partial)
            os.replace(partial,target)
            record={'file':target.name,'sha256':digest}
            with open_journal(record) as saved, connect() as source:
                for row in selected:
                    current=source.execute('SELECT * FROM jobs WHERE id=?',(row[0],)).fetchone()
                    copy=saved.execute('SELECT * FROM jobs WHERE id=?',(row[0],)).fetchone()
                    if not current or tuple(current)!=row or not copy or tuple(copy)!=row:raise ValueError('Dispatch record changed during archiving; local data retained.')
                    for table,order in [('photos','position'),('audit','rowid')]:
                        query=f'SELECT * FROM {table} WHERE job=? ORDER BY {order}'
                        if [tuple(r) for r in source.execute(query,(row[0],))]!=[tuple(r) for r in saved.execute(query,(row[0],))]:raise ValueError('Journal attachments or history failed verification.')
                source.execute('INSERT INTO journal_archives VALUES(?,?,?,?)',(target.name,digest,len(selected),dt.datetime.now().isoformat()))
                for row in selected:
                    source.execute('DELETE FROM photos WHERE job=?',(row[0],))
                    source.execute('DELETE FROM audit WHERE job=?',(row[0],))
                    source.execute('DELETE FROM jobs WHERE id=?',(row[0],))
            # Reclaim the pages only after the verified archive and DB transaction succeed.
            with closing(sqlite3.connect(DB)) as c:c.execute('VACUUM')
            return len(selected)
        finally:partial.unlink(missing_ok=True)

def complete_backup():
    with LOCK:return _complete_backup()

def _complete_backup():
    cfg=backup_config()
    if not cfg.get('folder'): raise ValueError('Set up a OneDrive backup folder in Settings first.')
    folder=Path(cfg['folder'])
    if not folder.is_absolute(): raise ValueError('The backup folder must be an absolute path on the server computer.')
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/('Thrift-Mart-Dispatch-Backup-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.zip')
    partial=target.with_suffix('.partial')
    try:
        with tempfile.TemporaryDirectory(dir=DATA) as temp:
            snapshot=Path(temp)/'schedule.db'
            with connect() as src, closing(sqlite3.connect(snapshot)) as dst: src.backup(dst)
            counts=merge_journals(snapshot);digest=file_digest(snapshot)
            with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(snapshot,'schedule.db')
                for name in ('updates.json','backup-settings.json'):
                    if (DATA/name).exists(): z.write(DATA/name,name)
                z.writestr('manifest.json',json.dumps({'application':'thrift-mart-dispatch','format':1,'version':updater.current(),'created':dt.datetime.now().isoformat(),'database_sha256':digest,'verified_counts':counts,'includes_dispatch_journal':True}))
            verify_backup_archive(partial,digest)
            os.replace(partial,target)
            verify_backup_archive(target,digest)
        # Keep the latest 90 complete archives in the configured folder.
        for old in sorted(folder.glob('Thrift-Mart-Dispatch-Backup-*.zip'),key=lambda p:p.stat().st_mtime)[:-90]:old.unlink()
        (DATA/'backup-status.json').write_text(json.dumps({'file':str(target),'at':dt.datetime.now().isoformat(timespec='seconds'),'saved_at':time.time(),'error':None,'verified':True,'counts':counts,'database_sha256':digest,'cloud_sync':'Check OneDrive sync status on the host computer'}))
        return str(target)
    except Exception as e:
        partial.unlink(missing_ok=True)
        previous=DATA/'backup-status.json'
        try:status=json.loads(previous.read_text()) if previous.exists() else {}
        except ValueError:status={}
        status['error']=str(e);status['failed_at']=dt.datetime.now().isoformat(timespec='seconds');previous.write_text(json.dumps(status))
        raise

def background():
    while True:
        try:
            with LOCK:
                backup()
                status=DATA/'backup-status.json'
                last=json.loads(status.read_text()).get('saved_at',0) if status.exists() else 0
                if backup_config().get('enabled') and time.time()-last>=3600:
                    complete_backup();archive_dispatch()
        except Exception as e: print('Backup failed:',e)
        time.sleep(60)

# Keep a process-wide lock, also used by the offline restore utility.
def hold_data_lock():
    f=(DATA/'server.lock').open('a+b');f.seek(0);f.write(b'0');f.flush();f.seek(0)
    try:
        if os.name=='nt':
            import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        f.close();raise SystemExit('Another server or restore process is using this data folder.')
    return f

class Problem(Exception):
    def __init__(self,message,status=400): self.message=message; self.status=status

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): pass
    def external_scheme(self):
        # Only a connector on this server may describe the browser's TLS connection.
        # Keep Host unchanged: never trust X-Forwarded-Host for origin validation.
        if self.client_address[0] in ('127.0.0.1','::1') and self.headers.get('X-Forwarded-Proto')=='https':
            return 'https'
        return 'http'

    def send(self,data,status=200,cookie=None,kind='application/json'):
        raw=json.dumps(data).encode() if kind=='application/json' else data
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data: blob:; media-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if cookie: self.send_header('Set-Cookie',cookie+('; Secure' if self.external_scheme()=='https' else ''))
        self.end_headers(); self.wfile.write(raw)
    def user(self):
        cookie=SimpleCookie(); cookie.load(self.headers.get('Cookie',''))
        token=cookie.get('session'); token=token.value if token else ''
        session=SESSIONS.get(token)
        if not session or session['expires']<time.time(): raise Problem('Please sign in again.',401)
        with connect() as c:
            permission=c.execute('SELECT * FROM permissions WHERE name=?',(session['name'],)).fetchone()
        with connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS user_grants(name TEXT PRIMARY KEY COLLATE NOCASE, body TEXT)')
            saved=c.execute('SELECT body FROM user_grants WHERE name=?',(session['name'],)).fetchone()
        session['can_create']=bool(session['admin'] or not permission or permission['can_create'])
        session['see_requests']=bool(session['can_create'] and (permission['see_requests'] if permission else session['admin']))
        defaults={key:False for key in PERMISSIONS}
        defaults.update({key:True for key in ('view_schedule','submit_requests','cancel_appointments','call_contacts','text_contacts','navigate','change_own_password')})
        for key in ('create_appointments','edit_appointments','delete_appointments','update_status','review_requests'): defaults[key]=session['can_create']
        defaults['see_requests']=session['see_requests'];defaults['view_reports']=session['can_create']
        session['grants']=json.loads(saved['body']) if saved else defaults
        for key in ('view_schedule','show_vehicle_filter','show_search'): session['grants'].setdefault(key,True)
        session['can_create']=has_permission(session,'create_appointments')
        session['see_requests']=has_permission(session,'see_requests')
        return session
    def do_GET(self):
        try:
            if self.path in ('/','/mobile','/mobile/','/app.js','/style.css'):
                filename={'/':'index.html','/mobile':'index.html','/mobile/':'index.html','/app.js':'app.js','/style.css':'style.css'}[self.path]
                kind={'/':'text/html; charset=utf-8','/mobile':'text/html; charset=utf-8','/mobile/':'text/html; charset=utf-8','/app.js':'text/javascript','/style.css':'text/css'}[self.path]
                return self.send((ROOT/'static'/filename).read_bytes(),kind=kind)
            with LOCK, connect() as c:
                if self.path=='/api/session':
                    setup=not c.execute('SELECT 1 FROM users').fetchone()
                    try: u=self.user()
                    except Problem: u=None
                    return self.send({'application':'thrift-mart-dispatch','name':'MGC YFC Operations Server','version':updater.current(),'setup':setup,'user':u and {'name':u['name'],'admin':u['admin'],'can_create':u['can_create'],'see_requests':u['see_requests'],'grants':u['grants']},'local':self.client_address[0] in ('127.0.0.1','::1')})
                u=self.user()
                if self.path=='/api/admin/login-security':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    return self.send({'max_attempts':c.execute('SELECT max_attempts FROM login_security WHERE id=1').fetchone()[0]})
                if self.path=='/api/admin/lockouts':
                    if not has_permission(u,'unlock_users'): raise Problem('Unlock users permission required.',403)
                    return self.send({'users':[dict(r) for r in c.execute('SELECT l.name,l.failures,l.locked_at FROM account_lockouts l JOIN users u ON u.name=l.name WHERE l.locked_at IS NOT NULL ORDER BY l.name')]})
                if self.path=='/api/admin/permission-catalog':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    return self.send({'permissions':PERMISSIONS,'users':[{'name':r['name'],'grants':json.loads(r['body'])} for r in c.execute('SELECT * FROM user_grants')]})
                if self.path=='/api/admin/users':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    return self.send({'users':[dict(r) for r in c.execute('SELECT users.name,admin,COALESCE(permissions.can_create,1) AS can_create,COALESCE(permissions.see_requests,admin) AS see_requests FROM users LEFT JOIN permissions ON users.name=permissions.name ORDER BY users.name')]})
                if self.path=='/api/admin/backup-settings':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    p=DATA/'backup-status.json'
                    return self.send({'config':backup_config(),'status':json.loads(p.read_text()) if p.exists() else None,'journal':{'status':json.loads((DATA/'journal-status.json').read_text()) if (DATA/'journal-status.json').exists() else None,'archives':c.execute('SELECT COUNT(*) FROM journal_archives').fetchone()[0],'records':c.execute('SELECT COALESCE(SUM(records),0) FROM journal_archives').fetchone()[0]}})
                if self.path=='/api/admin/status':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    return self.send({'name':'MGC YFC Operations Server','version':updater.current(),'uptime_minutes':int((time.time()-STARTED)/60),'time':dt.datetime.now().isoformat(timespec='seconds'),'jobs':c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],'vehicles':c.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0],'users':c.execute('SELECT COUNT(*) FROM users').fetchone()[0]})
                if self.path=='/api/updates' and route_allowed(u,self.path):
                    last=DATA/'last-update.json'
                    return self.send({'current':updater.current(),'repository':updater.repo(),'launcher':os.environ.get('DISPATCH_LAUNCHER')=='1','last':json.loads(last.read_text()) if last.exists() else None})
                if self.path.startswith('/api/photo/'):
                    parts=self.path.split('/')
                    if len(parts)!=5: raise Problem('Not found',404)
                    row=c.execute('SELECT body FROM jobs WHERE id=?',(parts[3],)).fetchone()
                    if not row: raise Problem('Not found',404)
                    job=json.loads(row['body'])
                    if not has_permission(u,'view_schedule') or (job.get('request') and not u['can_create'] and job.get('requestedBy')!=u['name']): raise Problem('Permission required.',403)
                    photo=c.execute('SELECT body FROM photos WHERE job=? AND position=?',(parts[3],int(parts[4]))).fetchone()
                    if not photo: raise Problem('Not found',404)
                    return self.send(bytes(photo['body']),kind='image/jpeg')
                if self.path=='/api/account/landing':
                    preference=c.execute('SELECT section,chosen_on FROM landing_preferences WHERE name=?',(u['name'],)).fetchone()
                    today=dt.date.today().isoformat();options=section_options(u)
                    section=preference['section'] if preference and preference['chosen_on']==today and preference['section'] in {o['id'] for o in options} else None
                    return self.send({'section':section,'date':today,'options':options})
                if self.path=='/api/paging':
                    if not has_permission(u,'send_pages') and not has_permission(u,'receive_pages'): raise Problem('Paging permission required.',403)
                    return self.send({'pages':[dict(r) for r in c.execute('SELECT * FROM pages WHERE at>? ORDER BY id',(time.time()-60,))],'latest':c.execute('SELECT COALESCE(MAX(id),0) FROM pages').fetchone()[0]})
                if self.path=='/api/reports':
                    if not has_permission(u,'view_reports'): raise Problem('Reports permission required.',403)
                    try: jobs=all_report_jobs(c)
                    except Exception as e:raise Problem('Historical reports unavailable: '+str(e),503)
                    return self.send({'jobs':[j for j in jobs if not j.get('request') or u['can_create'] or j.get('requestedBy')==u['name']]})
                if self.path=='/api/state':
                    if not has_permission(u,'view_schedule'): raise Problem('Schedule access required.',403)
                    pending_counts={}
                    for row in c.execute('SELECT body FROM jobs'):
                        request=json.loads(row['body'])
                        if request.get('request') and request.get('status')!='Canceled':
                            date=request.get('start','')[:10]
                            counts=pending_counts.setdefault(date,{'Pickup':0,'Delivery':0})
                            if request.get('type') in counts: counts[request['type']]+=1
                    notice=c.execute('SELECT * FROM update_notices ORDER BY id DESC LIMIT 1').fetchone()
                    return self.send({'updateNotice':dict(notice) if notice else None,'pendingCounts':pending_counts,'jobs':[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM jobs') if not json.loads(r['body']).get('request')], 'requests':[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM jobs') if json.loads(r['body']).get('request') and (u['can_create'] or json.loads(r['body']).get('requestedBy')==u['name'])], 'permissions':{'can_create':u['can_create'],'see_requests':u['see_requests'],'grants':u['grants']}, 'vehicles':[r[0] for r in c.execute('SELECT name FROM vehicles ORDER BY name')], 'users':[dict(r) for r in c.execute('SELECT users.name,admin,COALESCE(permissions.can_create,1) AS can_create,COALESCE(permissions.see_requests,admin) AS see_requests FROM users LEFT JOIN permissions ON users.name=permissions.name ORDER BY users.name')]})
                if self.path=='/api/audit' and route_allowed(u,self.path):
                    return self.send([dict(r) for r in c.execute('SELECT * FROM audit ORDER BY rowid DESC LIMIT 100')])
                raise Problem('Not found',404)
        except Problem as e: self.send({'error':e.message},e.status)
    def do_POST(self):
        global RESTART, STOPPING
        try:
            if self.headers.get('X-Dispatch')!='1': raise Problem('Invalid request.',403)
            origin=self.headers.get('Origin')
            if origin and origin!=self.external_scheme()+'://'+self.headers.get('Host',''): raise Problem('Invalid origin.',403)
            n=int(self.headers.get('Content-Length','0'))
            if n>4500000: raise Problem('Request too large.')
            d=json.loads(self.rfile.read(n))
            if not isinstance(d,dict): raise Problem('Invalid request.')
            with LOCK, connect() as c:
                if RESTART or STOPPING: raise Problem('Update is restarting the server. Please wait and sign in again.',503)
                if self.path=='/api/local/stop':
                    expected=os.environ.get('DISPATCH_CONTROL_TOKEN','')
                    if self.client_address[0] not in ('127.0.0.1','::1') or not expected or not hmac.compare_digest(str(d.get('token','')),expected): raise Problem('Local server controller required.',403)
                    STOPPING=True
                    self.send({'ok':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                if self.path in ('/api/setup','/api/login'):
                    name=str(d.get('name','')).strip(); p=str(d.get('password',''))
                    if self.path=='/api/setup':
                        if self.client_address[0] not in ('127.0.0.1','::1') or self.headers.get('X-Forwarded-Proto') or self.headers.get('CF-Connecting-IP'): raise Problem('Create the first account on the server computer.',403)
                        if c.execute('SELECT 1 FROM users').fetchone(): raise Problem('Already set up.',409)
                        self.add_user(c,name,p,True)
                    r=c.execute('SELECT * FROM users WHERE name=?',(name,)).fetchone()
                    if not r:
                        key=self.client_address[0]; attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-300]
                        if len(attempts)>=15: raise Problem('Too many attempts. Wait five minutes.',429)
                        ATTEMPTS[key]=attempts+[time.time()]
                        raise Problem('Incorrect name or password.',401)
                    lockout=c.execute('SELECT * FROM account_lockouts WHERE name=?',(r['name'],)).fetchone()
                    if lockout and lockout['locked_at']: raise Problem('Account locked. Ask an administrator or authorized employee to unlock it.',423)
                    if not hmac.compare_digest(r['hash'],password(p,r['salt'])):
                        failures=(lockout['failures'] if lockout else 0)+1
                        limit=c.execute('SELECT max_attempts FROM login_security WHERE id=1').fetchone()[0]
                        locked_at=dt.datetime.now().astimezone().isoformat(timespec='seconds') if failures>=limit else None
                        c.execute('INSERT OR REPLACE INTO account_lockouts VALUES(?,?,?)',(r['name'],failures,locked_at))
                        if locked_at: c.execute('INSERT INTO audit VALUES(?,?,?,?)',(locked_at,r['name'],'Account locked after failed login attempts',''))
                        c.commit() # Persist failures even though the response below raises an error.
                        if locked_at: raise Problem('Account locked. Ask an administrator or authorized employee to unlock it.',423)
                        raise Problem('Incorrect name or password.',401)
                    c.execute('DELETE FROM account_lockouts WHERE name=?',(r['name'],))
                    token=secrets.token_urlsafe(32); SESSIONS[token]={'name':r['name'],'admin':bool(r['admin']),'expires':time.time()+43200}
                    return self.send({'ok':True},cookie=f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200')
                u=self.user()
                if self.path in ROUTE_PERMISSIONS and not route_allowed(u,self.path): raise Problem('Administrator or delegated permission required.',403)
                if self.path=='/api/admin/login-security':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    limit=d.get('max_attempts')
                    if type(limit) is not int or not 1<=limit<=100: raise Problem('Enter a whole number from 1 to 100.')
                    c.execute('UPDATE login_security SET max_attempts=? WHERE id=1',(limit,))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Login attempt limit changed to '+str(limit),''))
                    return self.send({'ok':True})
                if self.path=='/api/admin/unlock-user':
                    target=c.execute('SELECT name FROM users WHERE name=?',(str(d.get('name','')).strip(),)).fetchone()
                    if not target: raise Problem('Employee not found.',404)
                    if target['name'].casefold()==u['name'].casefold(): raise Problem('Ask another authorized employee to unlock your account.',403)
                    c.execute('DELETE FROM account_lockouts WHERE name=?',(target['name'],))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Account unlocked: '+target['name'],''))
                    return self.send({'ok':True})
                if self.path=='/api/admin/notify-update':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    c.execute('INSERT INTO update_notices(version,actor,at) VALUES(?,?,?)',(updater.current(),u['name'],dt.datetime.now().astimezone().isoformat(timespec='seconds')))
                    c.execute('DELETE FROM update_notices WHERE id NOT IN (SELECT id FROM update_notices ORDER BY id DESC LIMIT 10)')
                    return self.send({'ok':True})
                if self.path=='/api/account/landing':
                    section=d.get('section')
                    if section not in {o['id'] for o in section_options(u)}: raise Problem('Choose an available section.',403)
                    if section=='paging' and not has_permission(u,'send_pages') and not has_permission(u,'receive_pages'): raise Problem('Paging permission required.',403)
                    c.execute('INSERT OR REPLACE INTO landing_preferences(name,section,chosen_on) VALUES(?,?,?)',(u['name'],section,dt.date.today().isoformat()))
                    return self.send({'ok':True})
                if self.path=='/api/paging/send':
                    area=str(d.get('area','')).strip()
                    if not 1<=len(area)<=100: raise Problem('Enter an area (up to 100 characters).')
                    if c.execute('SELECT 1 FROM pages WHERE actor=? AND at>?',(u['name'],time.time()-10)).fetchone(): raise Problem('Please wait ten seconds before paging again.',429)
                    c.execute('INSERT INTO pages(at,actor,area) VALUES(?,?,?)',(time.time(),u['name'],area))
                    c.execute('DELETE FROM pages WHERE at<?',(time.time()-86400,))
                    return self.send({'ok':True})
                if self.path=='/api/logout':
                    for k,v in list(SESSIONS.items()):
                        if v is u: del SESSIONS[k]
                    return self.send({'ok':True},cookie='session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if self.path=='/api/admin/permissions':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    target=c.execute('SELECT * FROM users WHERE name=?',(str(d.get('name','')),)).fetchone()
                    if not target: raise Problem('User not found.',404)
                    if 'grants' in d:
                        if not isinstance(d['grants'],dict) or any(k not in PERMISSIONS or not isinstance(v,bool) for k,v in d['grants'].items()): raise Problem('Invalid permission list.')
                        grants={k:bool(d['grants'].get(k,k=='view_schedule')) for k in PERMISSIONS}
                        c.execute('INSERT OR REPLACE INTO user_grants VALUES(?,?)',(target['name'],json.dumps(grants)))
                    create=bool(target['admin'] or d.get('can_create') is True)
                    see=bool(create and d.get('see_requests') is True)
                    c.execute('INSERT OR REPLACE INTO permissions VALUES(?,?,?)',(target['name'],int(create),int(see)))
                    return self.send({'ok':True})
                if self.path in ('/api/admin/password','/api/account/password'):
                    if self.path=='/api/admin/password' and not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    name=u['name'] if self.path=='/api/account/password' else str(d.get('name','')).strip()
                    if self.path=='/api/account/password':
                        account=c.execute('SELECT * FROM users WHERE name=?',(u['name'],)).fetchone()
                        if not hmac.compare_digest(account['hash'],password(str(d.get('current','')),account['salt'])): raise Problem('Current password or passcode is incorrect.',403)
                    new_password=str(d.get('password',''))
                    if not valid_credential(new_password): raise Problem('Use an 8–256 character password or exactly 4 digits.')
                    if new_password!=d.get('confirm'): raise Problem('The passwords do not match.')
                    target=c.execute('SELECT name FROM users WHERE name=?',(name,)).fetchone()
                    if not target: raise Problem('User not found.',404)
                    salt=secrets.token_hex(16)
                    c.execute('UPDATE users SET salt=?,hash=? WHERE name=?',(salt,password(new_password,salt),target['name']))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Password changed for: '+target['name'],''))
                    c.commit()
                    for token,session in list(SESSIONS.items()):
                        if session['name']==target['name']: del SESSIONS[token]
                    return self.send({'ok':True,'signed_out':u['name']==target['name']})
                elif self.path in ('/api/admin/backup-settings','/api/admin/backup-now'):
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    if self.path=='/api/admin/backup-settings':
                        folder=str(d.get('folder','')).strip()
                        enabled=d.get('enabled') is True
                        if enabled and (not folder or not Path(folder).is_absolute()): raise Problem('Enter the full OneDrive folder path on the SERVER computer.')
                        if folder:
                            candidate=Path(folder).resolve()
                            if candidate==ROOT or candidate==DATA or ROOT in candidate.parents: raise Problem('Choose a OneDrive folder outside the program folder.')
                        if folder!=backup_config().get('folder','') and c.execute('SELECT 1 FROM journal_archives').fetchone():raise Problem('Dispatch Journal exists. Keep the current backup folder until the journal has been migrated and verified.')
                        cfg={'folder':folder,'enabled':enabled,'journal_enabled':d.get('journal_enabled',backup_config().get('journal_enabled',True)) is True}
                        tmp=DATA/'backup-settings.tmp';tmp.write_text(json.dumps(cfg));os.replace(tmp,DATA/'backup-settings.json')
                    else:
                        try: return self.send({'ok':True,'backup':complete_backup()})
                        except Exception as e: raise Problem('Backup failed: '+str(e))
                elif self.path in ('/api/admin/backup','/api/admin/restart'):
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    if self.path=='/api/admin/backup':
                        folder=DATA/'manual-backups'; folder.mkdir(exist_ok=True)
                        target=folder/(dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.db')
                        with connect() as src, closing(sqlite3.connect(target)) as dst: src.backup(dst)
                        return self.send({'ok':True,'backup':str(target)})
                    if os.environ.get('DISPATCH_LAUNCHER_PROTOCOL')!='2': raise Problem('Install the full version 0.3.0 server package and use its launcher to enable remote restart.')
                    RESTART=76
                    self.send({'ok':True,'restarting':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                elif self.path.startswith('/api/update-'):
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    try:
                        if self.path=='/api/update-config': updater.configure(str(d.get('repository','')).strip())
                        elif self.path=='/api/update-check':
                            result=updater.check(); result.pop('asset',None); return self.send(result)
                        elif self.path=='/api/update-install':
                            if os.environ.get('DISPATCH_LAUNCHER')!='1': raise ValueError('Restart using Start-Store-Dispatch.bat to enable installation.')
                            updater.stage(str(d.get('version','')))
                            RESTART=True
                            self.send({'ok':True,'restarting':True})
                            threading.Thread(target=self.server.shutdown,daemon=True).start()
                            return
                        else: raise Problem('Not found',404)
                    except ValueError as e: raise Problem(str(e))
                elif self.path=='/api/user':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    self.add_user(c,str(d.get('name','')).strip(),str(d.get('password','')),False)
                elif self.path=='/api/admin/remove-user':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    target=c.execute('SELECT name,admin FROM users WHERE name=?',(str(d.get('name','')).strip(),)).fetchone()
                    if not target: raise Problem('Employee not found.',404)
                    if target['admin']: raise Problem('Administrator accounts cannot be removed here.',403)
                    c.execute('DELETE FROM users WHERE name=?',(target['name'],))
                    c.execute('DELETE FROM account_lockouts WHERE name=?',(target['name'],))
                    for token in list(SESSIONS):
                        if SESSIONS[token]['name'].casefold()==target['name'].casefold(): del SESSIONS[token]
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Removed employee: '+target['name'],''))
                elif self.path=='/api/vehicle':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    name=str(d.get('name','')).strip()
                    if not 1<=len(name)<=80: raise Problem('Enter a vehicle name.')
                    c.execute('INSERT INTO vehicles VALUES(?)',(name,))
                elif self.path=='/api/status':
                    jid=str(d.get('id',''))
                    old=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
                    if not old or d.get('revision')!=old['revision']: raise Problem('Someone changed this appointment. Close this popup, refresh, and try again.',409)
                    status=d.get('status')
                    j=json.loads(old['body'])
                    if not u['can_create']:
                        if status=='Canceled' and not has_permission(u,'cancel_appointments'): raise Problem('Cancellation permission required.',403)
                        if status not in ('Requested','Canceled'): raise Problem('Request-only users may only request or cancel appointments.',403)
                        if status=='Requested' and (not j.get('request') or j.get('requestedBy')!=u['name']): raise Problem('Only your pending requests can have Requested status.',403)
                    elif not has_permission(u,'cancel_appointments' if status=='Canceled' else 'update_status'): raise Problem('Status permission required.',403)
                    elif status not in ('Scheduled','In Route / In Progress','Completed','Canceled'): raise Problem('Choose a valid status.')
                    if status not in ('Completed','Canceled','Requested'):

                        for r in c.execute('SELECT * FROM jobs WHERE id!=?',(jid,)):
                            other=json.loads(r['body'])
                            if not other.get('request') and other['vehicle']==j['vehicle'] and other['status'] not in ('Completed','Canceled') and j['start']<other['end'] and j['end']>other['start']:
                                raise Problem('This vehicle is already booked during that time. Edit the appointment time or vehicle first.',409)
                    previous=j['status'];j['status']=status
                    j['statusUpdatedBy']=u['name'];j['statusUpdatedAt']=dt.datetime.now().astimezone().isoformat(timespec='seconds')
                    c.execute('UPDATE jobs SET revision=?,body=? WHERE id=?',(old['revision']+1,json.dumps(j),jid))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Status: '+previous+' → '+status+' · '+j['customer'],jid))
                elif self.path in ('/api/save','/api/delete'):
                    if not d.get('id') and not has_permission(u,'create_appointments') and not has_permission(u,'submit_requests'): raise Problem('Request permission required.',403)
                    if d.get('id') and not has_permission(u,'delete_appointments' if self.path=='/api/delete' else 'edit_appointments'): raise Problem('Edit permission required.',403)
                    jid=str(d.get('id') or secrets.token_hex(12))
                    old=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
                    if d.get('id') and (not old or d.get('revision')!=old['revision']): raise Problem('Someone changed this job. Close this form, refresh, and try again.',409)
                    if old and json.loads(old['body']).get('request') and self.path=='/api/save' and not has_permission(u,'review_requests'): raise Problem('Request approval permission required.',403)
                    if self.path=='/api/delete':
                        if not old: raise Problem('Job not found.',404)
                        c.execute('DELETE FROM jobs WHERE id=?',(jid,)); action='Removed: '+json.loads(old['body'])['customer']
                    else:
                        fields=['type','customer','phone','address','items','vehicle','start','end','staff','notes','status']
                        j={k:str(d.get(k,'Scheduled' if k=='status' and not old else '')).strip() for k in fields}
                        if any(k in d for k in ('street','city','state','zip')):
                            for k in ('street','city','state','zip'): j[k]=str(d.get(k,'')).strip()
                            if u['can_create'] and any(not j[k] for k in ('street','city','state','zip')): raise Problem('Enter street address, city, state and ZIP code.')
                            j['address']='\n'.join(part for part in [j['street'],', '.join(part for part in [j['city'],' '.join(part for part in [j['state'],j['zip']] if part)] if part)] if part) if any(j[k] for k in ('street','city','zip')) else ''
                        if any(len(v)>5000 for v in j.values()): raise Problem('A field is too long.')
                        if any(not j[k] for k in (('customer','phone','address','items','vehicle','start','end') if u['can_create'] else ('customer',))): raise Problem('Complete the required fields.')
                        if 'staffNames' in d:
                            names=d['staffNames']
                            if not isinstance(names,list) or len(names)>100 or any(not isinstance(n,str) or len(n)>5000 for n in names): raise Problem('Choose valid employees.')
                            previous=json.loads(old['body']) if old else {}
                            allowed={r['name'] for r in c.execute('SELECT name FROM users')}
                            allowed.update(previous.get('staffNames', [previous['staff']] if previous.get('staff') else []))
                            if any(n not in allowed for n in names): raise Problem('An employee was removed. Reopen the appointment and select current employees.')
                            j['staffNames']=list(dict.fromkeys(names));j['staff']=', '.join(j['staffNames'])
                        if j['type'] not in ('Pickup','Delivery') or j['status'] not in ('Requested','Scheduled','Confirmed','In Route / In Progress','Completed','Canceled'): raise Problem('Invalid type or status.')
                        if u['can_create']:
                            try:
                                start=dt.datetime.strptime(j['start'],'%Y-%m-%dT%H:%M'); end=dt.datetime.strptime(j['end'],'%Y-%m-%dT%H:%M')
                            except ValueError: raise Problem('Choose a valid date and time.')
                            if end<=start: raise Problem('End time must be after start time.')
                            if not c.execute('SELECT 1 FROM vehicles WHERE name=?',(j['vehicle'],)).fetchone(): raise Problem('Choose an existing vehicle.')
                        else:
                            if j['start']:
                                try: dt.datetime.strptime(j['start'],'%Y-%m-%dT%H:%M')
                                except ValueError: raise Problem('Choose a valid requested date and time.')
                            j['end']='';j['vehicle']='';j['staff']='';j['staffNames']=[]
                        pending=not u['can_create'] and not old
                        if pending:
                            if j['status'] not in ('Requested','Canceled'): raise Problem('Request-only users may only request or cancel appointments.',403)
                            j['request']=True;j['requestedBy']=u['name']
                        if not pending and j['status'] not in ('Completed','Canceled'):
                            for r in c.execute('SELECT * FROM jobs WHERE id!=?',(jid,)):
                                other=json.loads(r['body'])
                                if not other.get('request') and other['vehicle']==j['vehicle'] and other['status'] not in ('Completed','Canceled') and j['start']<other['end'] and j['end']>other['start']:
                                    raise Problem('This vehicle is already booked during that time. Choose another time or vehicle.',409)
                        previous_job=json.loads(old['body']) if old else {}
                        if old and previous_job.get('status')!=j['status'] and not has_permission(u,'cancel_appointments' if j['status']=='Canceled' else 'update_status'): raise Problem('Status permission required.',403)
                        if not old or previous_job.get('status')!=j['status']:
                            j['statusUpdatedBy']=u['name'];j['statusUpdatedAt']=dt.datetime.now().astimezone().isoformat(timespec='seconds')
                        else:
                            for key in ('statusUpdatedBy','statusUpdatedAt'):
                                if key in previous_job: j[key]=previous_job[key]
                        if not old:
                            images=d.get('photos',[])
                            if not isinstance(images,list) or len(images)>3: raise Problem('Attach up to 3 photos.')
                            for i,encoded in enumerate(images):
                                try: raw=base64.b64decode(encoded,validate=True)
                                except Exception: raise Problem('Invalid photo.')
                                if len(raw)>1000000 or not raw.startswith(b'\xff\xd8\xff'): raise Problem('Photos must be JPEG and under 1 MB each.')
                                c.execute('INSERT INTO photos VALUES(?,?,?)',(jid,i,raw))
                            j['photoCount']=len(images)
                        else: j['photoCount']=previous_job.get('photoCount',0)
                        rev=old['revision']+1 if old else 1
                        c.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?)',(jid,rev,json.dumps(j)))
                        action=('Updated: ' if old else 'Created: ')+j['customer']
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],action,jid))
                else: raise Problem('Not found',404)
            self.send({'ok':True})
        except Problem as e: self.send({'error':e.message},e.status)
        except sqlite3.IntegrityError: self.send({'error':'That name already exists.'},409)
        except (ValueError,TypeError): self.send({'error':'Invalid request.'},400)
        except Exception as e:
            print('Request failed:',e); self.send({'error':'Unable to save. Check the server and try again.'},500)
    def add_user(self,c,name,p,admin):
        if not 1<=len(name)<=80 or not valid_credential(p): raise Problem('Enter a name and a password of 8–256 characters.')
        salt=secrets.token_hex(16)
        c.execute('INSERT INTO users VALUES(?,?,?,?)',(name,salt,password(p,salt),int(admin)))

if __name__=='__main__':
    if os.name=='nt':
        import ctypes
        kernel=ctypes.windll.kernel32
        kernel.CreateMutexW.restype=ctypes.c_void_p
        instance_mutex=kernel.CreateMutexW(None,False,'ThriftMartDispatchServer')
        if kernel.GetLastError()==183: raise SystemExit('MGC YFC Operations Server is already running.')
    data_lock=hold_data_lock()
    init(); threading.Thread(target=background,daemon=True).start()
    port=int(os.environ.get('DISPATCH_PORT','8080'))
    print('MGC YFC Operations Server '+updater.current())
    print(f'On this computer: http://localhost:{port}')
    for address in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
        if not address.startswith('127.'): print(f'On store Wi-Fi: http://{address}:{port}')
    print('Managed by the truck tray icon. Minimize to tray; use Exit server to stop.' if os.environ.get('DISPATCH_CONTROL_TOKEN') else 'Keep this window open. Press Ctrl+C to stop.')
    http=ThreadingHTTPServer(('0.0.0.0',port),Handler)
    http.serve_forever()
    http.server_close()
    if RESTART: raise SystemExit(76 if RESTART==76 else 75)
