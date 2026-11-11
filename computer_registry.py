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
    if force or OPS_UPDATE_RELEASE.get('attempted',0)<time.time()-3600:
        with connect() as c:has_ops=c.execute("SELECT 1 FROM retail_computer_apps WHERE app='ops'").fetchone()
        if has_ops and not OPS_UPDATE_RELEASE.get('checking'):
            OPS_UPDATE_RELEASE.update(checking=True,attempted=time.time());threading.Thread(target=ops_update_check,daemon=True).start()
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
    jobs={app:computer_campaign(c,app) for app in ('pos','office','ops')}
    releases={'pos':POS_UPDATE_RELEASE,'office':OFFICE_UPDATE_RELEASE,'ops':OPS_UPDATE_RELEASE};computers=[]
    for row in c.execute('SELECT * FROM retail_computers ORDER BY registered DESC,name,hostname'):
        pc=dict(row);pc['macs']=json.loads(pc['macs']);pc['apps']=[]
        for record in c.execute('SELECT * FROM retail_computer_apps WHERE computer=? ORDER BY app,device',(pc['id'],)):
            item=dict(record);item['online']=time.time()-item['seen']<60;job=jobs.get(item['app']);latest=releases[item['app']].get('version')
            item['available']=bool(latest and updater.version(latest)>updater.version(item['version']))
            item['target']=job['version'] if job and item['device'] in job['targets'] else None
            item['complete']=bool(item['target'] and updater.version(item['version'])>=updater.version(item['target']))
            item['progress']='Updated' if item['complete'] else ('Waiting for application to reconnect' if not item['online'] else item['status'])
            pc['apps'].append(item)
        computers.append(pc)
    return {'computers':computers,'releases':releases,'campaigns':jobs,'server_version':updater.current()}

def computer_post(handler,c,u,path,d):
    if path=='self':return computer_self(handler,c,u,d)
    computer_require_admin(u)
    if path=='register':
        ident=d.get('id');row=c.execute('SELECT * FROM retail_computers WHERE id=?',(ident,)).fetchone()
        if not row:raise Problem('Open DESK, STORE OPS or OFFICE on that computer and sign in first.',404)
        if d.get('revision')!=row['revision']:raise Problem('Computer registration changed. Refresh and try again.',409)
        name=str(d.get('name','')).strip();role=d.get('role','office')
        if not 1<=len(name)<=80 or role not in ('pos','office','server','other'):raise Problem('Enter a computer name and valid role.')
        computer_link_terminal(c,ident,d,name,row['hostname'])
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
        for app,release in [('pos',POS_UPDATE_RELEASE),('office',OFFICE_UPDATE_RELEASE),('ops',OPS_UPDATE_RELEASE)]:
            if not any(r['computer'] in selected for r in c.execute('SELECT computer FROM retail_computer_apps WHERE app=?',(app,))):continue
            if release.get('checking') or release.get('error') or not release.get('version') or time.time()-release.get('checked',0)>3600:raise Problem('Finish checking the selected applications for updates first.',409)
            if app!='ops' and (pos_update_read() if app=='pos' else office_update_read()).get('campaign'):raise Problem('Cancel the existing '+app.upper()+' update request before starting a computer rollout.',409)
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


OPS_UPDATE_RELEASE={'checking':False}
def ops_update_check():
    try:
        repository='m404ntfd/mgc-yfc-operations'
        release=json.loads(updater.fetch('https://api.github.com/repos/'+repository+'/releases/latest',1000000))
        if release.get('draft') or release.get('prerelease'):raise ValueError('A stable release is required.')
        candidates=[]
        for asset in release.get('assets',[]):
            match=re.fullmatch(r'CoastYouth-Retail-STORE-OPS-Setup-v(\d+\.\d+\.\d+)\.exe',asset.get('name',''))
            if match and re.fullmatch(r'sha256:[a-f0-9]{64}',asset.get('digest') or ''):candidates.append((updater.version(match[1]),match[1],asset))
        if not candidates:raise ValueError('No verified STORE OPS installer is available.')
        _,version,asset=max(candidates)
        if not asset['browser_download_url'].startswith('https://github.com/'+repository+'/releases/download/'):raise ValueError('Unexpected installer address.')
        with LOCK:OPS_UPDATE_RELEASE.update(checking=False,version=version,url=asset['browser_download_url'],checked=time.time(),error=None)
    except Exception as e:
        with LOCK:OPS_UPDATE_RELEASE.update(checking=False,error=str(e))

def computer_self(handler,c,u,d):
    app=d.get('app');device=d.get('device');version=d.get('version')
    if app not in ('pos','office','ops') or not re.fullmatch('[a-f0-9]{32}',str(device)) or not re.fullmatch(r'\d+\.\d+\.\d+',str(version)):raise Problem('Invalid desktop identity.')
    meta=d.get('computer')
    if not isinstance(meta,dict) or not re.fullmatch('[a-f0-9]{32}',str(meta.get('id',''))):raise Problem('Windows computer identity is unavailable. Contact your administrator.')
    computer_heartbeat(handler,app,d)
    row=c.execute('SELECT * FROM retail_computers WHERE id=?',(meta['id'],)).fetchone()
    terminal=c.execute('SELECT id,name,enabled FROM retail_terminals WHERE device=?',(device,)).fetchone() if app=='pos' else None
    result={'computer':{k:row[k] for k in ('id','name','hostname','role','registered','revision')},'terminal':stores_terminal_details(c,terminal)}
    return handler.send(computer_client_state(app,device,result))

def computer_link_terminal(c,ident,d,name,hostname):
    # First-time DESK enrollment may link an available terminal, never replace an existing binding.
    device=d.get('device')
    if d.get('app')!='pos' or not device:return
    member=c.execute("SELECT 1 FROM retail_computer_apps WHERE computer=? AND app='pos' AND device=?",(ident,device)).fetchone()
    if not member:raise Problem('Refresh this computer before registering its checkout.',409)
    current=c.execute('SELECT * FROM retail_terminals WHERE device=?',(device,)).fetchone()
    if current:return
    target=d.get('terminal')
    if target:
        row=c.execute('SELECT * FROM retail_terminals WHERE id=?',(target,)).fetchone()
        if not row or row['device'] or not row['enabled']:raise Problem('Choose an enabled, unassigned terminal.',409)
        c.execute('UPDATE retail_terminals SET device=?,hostname=?,revision=revision+1 WHERE id=?',(device,hostname,target))
    else:
        if len(name)>60 or c.execute('SELECT 1 FROM retail_terminals WHERE name=? COLLATE NOCASE',(name,)).fetchone():raise Problem('Choose the existing terminal or enter a unique name of 60 characters or fewer.',409)
        store=stores_profile(c,d.get('store_id') or 'thrift-mart')['id'];terminal_id=secrets.token_hex(16)
        c.execute('INSERT INTO retail_terminals VALUES(?,?,?,?,?,?,?)',(terminal_id,name,device,None,1,1,hostname))
        c.execute('INSERT INTO retail_terminal_stores VALUES(?,?)',(terminal_id,store))
