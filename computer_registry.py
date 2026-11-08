# Computer inventory and coordinated client rollouts. Additive tables only.
def init_computers(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS retail_computers(id TEXT PRIMARY KEY,hostname TEXT NOT NULL,macs TEXT NOT NULL,os TEXT NOT NULL,name TEXT NOT NULL DEFAULT '',role TEXT NOT NULL DEFAULT 'office',registered INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 0,seen REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS retail_computer_apps(app TEXT NOT NULL,device TEXT NOT NULL,computer TEXT NOT NULL REFERENCES retail_computers(id),version TEXT NOT NULL,status TEXT NOT NULL,seen REAL NOT NULL,ip TEXT NOT NULL,PRIMARY KEY(app,device));
    CREATE TABLE IF NOT EXISTS retail_computer_updates(app TEXT PRIMARY KEY,body TEXT NOT NULL);
    ''')

def computer_heartbeat(handler,app,d):
    meta=d.get('computer')
    if not isinstance(meta,dict) or not re.fullmatch('[a-f0-9]{32}',str(meta.get('id',''))):return
    ident=meta['id'];hostname=str(meta.get('hostname',''))[:120];system=str(meta.get('os',''))[:160]
    macs=meta.get('macs',[])
    if not isinstance(macs,list):raise Problem('Invalid computer information.')
    macs=sorted({str(m).upper() for m in macs[:16] if re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',str(m))})
    with connect() as c:
        previous=c.execute('SELECT computer FROM retail_computer_apps WHERE app=? AND device=?',(app,d['device'])).fetchone()
        if previous and previous['computer']!=ident:raise Problem('This installation belongs to a different computer. Ask an administrator to review its registration.',409)
        c.execute('INSERT INTO retail_computers(id,hostname,macs,os,seen) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET hostname=excluded.hostname,macs=excluded.macs,os=excluded.os,seen=excluded.seen',(ident,hostname,json.dumps(macs),system,time.time()))
        c.execute('INSERT INTO retail_computer_apps VALUES(?,?,?,?,?,?,?) ON CONFLICT(app,device) DO UPDATE SET version=excluded.version,status=excluded.status,seen=excluded.seen,ip=excluded.ip',(app,d['device'],ident,d['version'],str(d.get('status','Connected'))[:200],time.time(),handler.client_address[0]))

def computer_campaign(c,app):
    row=c.execute('SELECT body FROM retail_computer_updates WHERE app=?',(app,)).fetchone()
    return json.loads(row['body']) if row else None

def computer_ticket(c,app,ident):
    job=computer_campaign(c,app)
    return job if job and secrets.compare_digest(job['id'],ident) else None

def computer_client_state(app,device,result):
    with connect() as c:
        job=computer_campaign(c,app)
        if job and device in job['targets']:
            member=c.execute('SELECT registered FROM retail_computers pc JOIN retail_computer_apps a ON a.computer=pc.id WHERE a.app=? AND a.device=?',(app,device)).fetchone()
            if member and member['registered']:result['campaign']=job
    return result

def computer_require_admin(u):
    if not u.get('admin'):raise Problem('Administrator access required to manage computers and updates.',403)

def computer_check(force=False):
    global POS_UPDATE_RELEASE,OFFICE_UPDATE_RELEASE
    for app in ('pos','office'):
        release=POS_UPDATE_RELEASE if app=='pos' else OFFICE_UPDATE_RELEASE
        if not release.get('checking') and (force or time.time()-release.get('attempted',release.get('checked',0))>3600):
            pending={**release,'checking':True,'attempted':time.time()}
            if app=='pos':POS_UPDATE_RELEASE=pending
            else:OFFICE_UPDATE_RELEASE=pending
            def check(kind=app,attempt=pending['attempted']):
                (pos_update_check if kind=='pos' else office_update_check)()
                with LOCK:(POS_UPDATE_RELEASE if kind=='pos' else OFFICE_UPDATE_RELEASE)['attempted']=attempt
            threading.Thread(target=check,daemon=True).start()

def computer_state(c,u,check=True):
    computer_require_admin(u)
    if check:computer_check()
    jobs={app:computer_campaign(c,app) for app in ('pos','office')}
    releases={'pos':POS_UPDATE_RELEASE,'office':OFFICE_UPDATE_RELEASE};computers=[]
    for row in c.execute('SELECT * FROM retail_computers ORDER BY registered DESC,name,hostname'):
        pc=dict(row);pc['macs']=json.loads(pc['macs']);pc['apps']=[]
        for record in c.execute('SELECT * FROM retail_computer_apps WHERE computer=? ORDER BY app,device',(pc['id'],)):
            item=dict(record);item['online']=time.time()-item['seen']<60;job=jobs[item['app']];latest=releases[item['app']].get('version')
            item['available']=bool(latest and updater.version(latest)>updater.version(item['version']))
            item['target']=job['version'] if job and item['device'] in job['targets'] else None
            item['complete']=bool(item['target'] and updater.version(item['version'])>=updater.version(item['target']))
            item['progress']='Updated' if item['complete'] else ('Waiting for application to reconnect' if not item['online'] else item['status'])
            pc['apps'].append(item)
        computers.append(pc)
    return {'computers':computers,'releases':releases,'campaigns':jobs,'server_version':updater.current()}

def computer_post(handler,c,u,path,d):
    computer_require_admin(u)
    if path=='register':
        ident=d.get('id');row=c.execute('SELECT * FROM retail_computers WHERE id=?',(ident,)).fetchone()
        if not row:raise Problem('Open the updated DESK or OFFICE on that computer first.',404)
        if d.get('revision')!=row['revision']:raise Problem('Computer registration changed. Refresh and try again.',409)
        name=str(d.get('name','')).strip();role=d.get('role','office')
        if not 1<=len(name)<=80 or role not in ('pos','office','server','other'):raise Problem('Enter a computer name and valid role.')
        c.execute('UPDATE retail_computers SET name=?,role=?,registered=1,revision=revision+1 WHERE id=?',(name,role,ident))
        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Registered or renamed computer',json.dumps({'id':ident,'name':name,'role':role})))
    elif path=='check':computer_check(True)
    elif path=='start':
        seconds=d.get('seconds',120);selected=d.get('computers')
        if type(seconds) is not int or not 30<=seconds<=3600:raise Problem('Choose a warning period of 30 to 3600 seconds.')
        if not isinstance(selected,list) or not selected or len(selected)>1000 or any(not isinstance(x,str) for x in selected):raise Problem('Select registered computers to update.')
        selected=set(selected);known={r['id'] for r in c.execute('SELECT id FROM retail_computers WHERE registered=1')}
        if not selected<=known:raise Problem('Register the selected computers first.')
        pending=[]
        for app,release in [('pos',POS_UPDATE_RELEASE),('office',OFFICE_UPDATE_RELEASE)]:
            if release.get('checking') or release.get('error') or not release.get('version') or time.time()-release.get('checked',0)>3600:raise Problem('Finish checking both applications for updates first.',409)
            if (pos_update_read() if app=='pos' else office_update_read()).get('campaign'):raise Problem('Cancel the existing '+app.upper()+' update request before starting a computer rollout.',409)
            old=computer_campaign(c,app)
            if old:
                versions={r['device']:r['version'] for r in c.execute('SELECT device,version FROM retail_computer_apps WHERE app=?',(app,))}
                if any(updater.version(versions.get(device,'0.0.0'))<updater.version(old['version']) for device in old['targets']):raise Problem('Complete or cancel the current rollout first.',409)
            targets=[r['device'] for r in c.execute('SELECT * FROM retail_computer_apps WHERE app=?',(app,)) if r['computer'] in selected and updater.version(r['version'])<updater.version(release['version'])]
            if targets:pending.append((app,{'id':secrets.token_hex(32),'mode':'notify','automatic':True,'version':release['version'],'seconds':seconds,'target':'registered','targets':targets,'by':u['name'],'at':time.time()}))
        if not pending:raise Problem('The selected applications are already up to date.')
        for app,job in pending:c.execute('INSERT OR REPLACE INTO retail_computer_updates VALUES(?,?)',(app,json.dumps(job)))
        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Started registered computer rollout',json.dumps({'computers':sorted(selected),'seconds':seconds})))
    elif path=='cancel':
        c.execute('DELETE FROM retail_computer_updates')
        for read,save in ((pos_update_read,pos_update_save),(office_update_read,office_update_save)):
            legacy=read();legacy['campaign']=None;save(legacy)
        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Canceled pending computer rollout','Installers already launched cannot be canceled.'))
    else:raise Problem('Unknown computer action.',404)
    c.commit()
    return handler.send(computer_state(c,u,False))
