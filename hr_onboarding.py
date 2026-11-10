"""Invitation-only HR workflow. Sensitive payloads encrypted separately from operational data."""
from cryptography.fernet import Fernet, InvalidToken
HR_REFERENCE_FORMS=[] # prepared HR reference forms
HR_SESSIONS={}
HR_EMPLOYERS=['Mississippi Gulf Coast Youth for Christ','Thrift Mart (Mississippi Gulf Coast Youth for Christ dba Thrift Mart)']
HR_STEPS={'background':'Background check disclosure and authorization','i9':'Form I-9','w4':'Federal Form W-4','ms':'Mississippi withholding','deposit':'Direct deposit authorization'}
HR_CONSENT_VERSION='2026-11-09-v2'
HR_CONSENT='You may use electronic records for this onboarding process or ask HR for paper forms. You need an internet connection, a current browser, access to your email, and a PDF reader that can save or print documents. Open the document preview before consenting. At the final step you may download and retain your completed and signed records. Contact HR using the help bubble or the listed contact to request paper copies without a fee, update your contact details, or withdraw consent for future electronic records. Withdrawal does not invalidate records already submitted. Each document has its own required signature and certification; this consent does not sign employment, tax, background-check, or banking forms for you. Keep your invitation and password private. Do not put Social Security or bank account numbers in help messages.'

def hr_init(c):
    c.executescript("""
CREATE TABLE IF NOT EXISTS hr_credentials(id INTEGER PRIMARY KEY CHECK(id=1),body BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS hr_settings(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hr_enrollments(id TEXT PRIMARY KEY,account TEXT UNIQUE NOT NULL,token_hash TEXT UNIQUE NOT NULL,expires REAL NOT NULL,revision INTEGER NOT NULL,status TEXT NOT NULL,body BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS hr_templates(id TEXT PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,edition TEXT NOT NULL,active INTEGER NOT NULL,mime TEXT NOT NULL,body BLOB NOT NULL,digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hr_documents(id TEXT PRIMARY KEY,enrollment TEXT NOT NULL,kind TEXT NOT NULL,template TEXT NOT NULL,at REAL NOT NULL,body BLOB NOT NULL,digest TEXT NOT NULL,status TEXT NOT NULL,review_note TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS hr_messages(id INTEGER PRIMARY KEY,enrollment TEXT NOT NULL,at REAL NOT NULL,actor TEXT NOT NULL,body BLOB NOT NULL,resolved INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS hr_events(id INTEGER PRIMARY KEY,enrollment TEXT NOT NULL,at REAL NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hr_completion_notifications(id TEXT PRIMARY KEY,enrollment TEXT NOT NULL,at REAL NOT NULL,active INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS hr_notification_reads(notification TEXT NOT NULL,account TEXT NOT NULL,at REAL NOT NULL,PRIMARY KEY(notification,account));
CREATE TABLE IF NOT EXISTS hr_mail(id TEXT PRIMARY KEY,enrollment TEXT NOT NULL,body BLOB NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL DEFAULT '');
CREATE TRIGGER IF NOT EXISTS hr_events_no_update BEFORE UPDATE ON hr_events BEGIN SELECT RAISE(ABORT,'HR audit is immutable'); END;
CREATE TRIGGER IF NOT EXISTS hr_events_no_delete BEFORE DELETE ON hr_events BEGIN SELECT RAISE(ABORT,'HR audit is immutable'); END;
CREATE TRIGGER IF NOT EXISTS hr_docs_content BEFORE UPDATE OF body,digest,template,enrollment,kind,at ON hr_documents BEGIN SELECT RAISE(ABORT,'Submitted document is immutable'); END;
""")
    hr_browser_init(c)

def hr_cipher():
    path=DATA/'hr-encryption.key'
    if not path.exists():
        with connect() as c:
            if c.execute('SELECT 1 FROM hr_enrollments UNION ALL SELECT 1 FROM hr_templates UNION ALL SELECT 1 FROM hr_credentials LIMIT 1').fetchone():raise Problem('HR encryption key is missing. Restore it from the verified backup; do not create a replacement.',503)
        try:
            with path.open('xb') as f:f.write(Fernet.generate_key())
            try:os.chmod(path,0o600)
            except OSError:pass
        except FileExistsError:pass
    return Fernet(path.read_bytes())

def hr_pack(value):return hr_cipher().encrypt(json.dumps(value).encode())
def hr_unpack(value):
    try:return json.loads(hr_cipher().decrypt(value))
    except InvalidToken:raise Problem('HR data cannot be opened with this server key. Restore the matching backup key.',503)

def hr_email_secret(c):
    value=os.environ.get('COASTYOUTH_HR_GMAIL_APP_PASSWORD','').replace(' ','')
    if value:return value
    row=c.execute('SELECT body FROM hr_credentials WHERE id=1').fetchone()
    return hr_unpack(row['body']) if row else ''

def hr_sync_contact(c,r,b):
    target=c.execute('SELECT profile_id FROM receipt_profiles WHERE name=?',(r['account'],)).fetchone()
    row=c.execute('SELECT * FROM office_user_details WHERE account=?',(target[0],)).fetchone()
    body=json.loads(row['body']) if row else {};revision=row['revision'] if row else 0
    body.update(email=b['email'],phone=b['phone'],address1=b.get('address',''),city=b.get('city',''),region='MS',postal=b.get('zip',''),country='US')
    c.execute('INSERT INTO office_user_details VALUES(?,?,?) ON CONFLICT(account) DO UPDATE SET revision=excluded.revision,body=excluded.body',(target[0],revision+1,json.dumps(body)))

def hr_settings(c):
    r=c.execute('SELECT * FROM hr_settings WHERE id=1').fetchone()
    return dict(json.loads(r['body']) if r else dict(contact='',sender='',sender_name='CoastYouth HR',enabled=False,subject='Your onboarding invitation',welcome='Welcome! Complete each section at your own pace. Use the help bubble whenever you need assistance.',email_body='Hello {first},\n\nPlease complete your onboarding for {employer}.\nUsername: {username}\nTemporary password: {password}\nPrivate onboarding link: {link}\n\nChoose a new password when you first sign in. The link expires in seven days. Use the help bubble for assistance.\n\nHR'),revision=r['revision'] if r else 0)

def hr_secure(h):
    if h.external_scheme()!='https' and not (h.client_address[0] in ('127.0.0.1','::1') and not h.headers.get('X-Forwarded-Proto')):raise Problem('Open HR using the secure https://operations.coastyfc.com address.',403)

def hr_admin(h):
    hr_secure(h);u=h.user()
    if not has_permission(u,'manage_hr'):raise Problem('HR permission required.',403)
    return u

def hr_event(c,ident,actor,action,detail=''):
    c.execute('INSERT INTO hr_events(enrollment,at,actor,action,detail) VALUES(?,?,?,?,?)',(ident,time.time(),actor,action,detail))

def hr_row(c,ident):
    r=c.execute('SELECT * FROM hr_enrollments WHERE id=?',(ident,)).fetchone()
    if not r:raise Problem('Onboarding record not found.',404)
    return r

def hr_auth(h,c):
    hr_secure(h);cookies=SimpleCookie();cookies.load(h.headers.get('Cookie',''));token=cookies.get('hr_session');s=HR_SESSIONS.get(token.value if token else '')
    if not s or s['expires']<time.time():raise Problem('Open your invitation and sign in again.',401)
    r=hr_row(c,s['id'])
    if r['status']=='revoked' or s['token_hash']!=r['token_hash']:raise Problem('This invitation was replaced or revoked.',401)
    s["last_seen"]=time.time()
    s.setdefault("last_active",time.time())
    s["name"]=r["account"]
    return r

def hr_summary(c,r,details=False):
    b=hr_unpack(r['body']);docs=[dict(x) for x in c.execute('SELECT id,kind,template,at,digest,status,review_note FROM hr_documents WHERE enrollment=? ORDER BY at',(r['id'],))]
    for doc in docs:
        signature=c.execute('SELECT body FROM hr_browser_signatures WHERE document=?',(doc['id'],)).fetchone()
        if signature:
            e=hr_unpack(signature[0]);config=c.execute('SELECT body FROM hr_browser_forms WHERE id=?',(e['form'],)).fetchone();roles={f['role'] for f in json.loads(config[0])['fields']} if config else set();doc.update(browser_form=e['form'],signer_role=e['role'],has_employer_fields='employer' in roles)
    latest={d['kind']:d for d in docs};messages=[dict(x,body=hr_unpack(x['body'])) for x in c.execute('SELECT * FROM hr_messages WHERE enrollment=? ORDER BY id',(r['id'],))]
    out=dict(id=r['id'],account=r['account'],revision=r['revision'],status=r['status'],expires=r['expires'],profile=b,documents=docs,steps=[dict(id=k,title=v,status=latest.get(k,{}).get('status','not_started')) for k,v in HR_STEPS.items()],help_open=sum(1 for m in messages if m['actor']=='employee' and not m['resolved']))
    if details:out.update(messages=messages,audit=[dict(x) for x in c.execute('SELECT * FROM hr_events WHERE enrollment=? ORDER BY id',(r['id'],))])
    return out

def hr_completion_sync(c,ident):
    r=hr_row(c,ident);summary=hr_summary(c,r);b=summary['profile']
    c.execute('UPDATE hr_completion_notifications SET active=0 WHERE enrollment=?',(ident,))
    if r['status'] in ('revoked','complete') or not b.get('password_changed') or not b.get('consent') or b.get('paper_requested') or not b.get('profile_complete'):return
    if any(s['status'] not in ('submitted','accepted') for s in summary['steps']):return
    # Employer signatures don't create a second employee-completion alert.
    latest={}
    for d in summary['documents']:
        if d.get('signer_role')!='employer':latest[d['kind']]=d['id']
    notice=hashlib.sha256((ident+json.dumps(latest,sort_keys=True)).encode()).hexdigest()
    c.execute('INSERT INTO hr_completion_notifications VALUES(?,?,?,1) ON CONFLICT(id) DO UPDATE SET active=1',(notice,ident,time.time()))

def hr_notifications(c,u):
    # Also picks up employees who submitted before this feature was installed.
    for r in c.execute("SELECT id FROM hr_enrollments WHERE status NOT IN ('revoked','complete')").fetchall():hr_completion_sync(c,r['id'])
    rows=[]
    for n in c.execute('SELECT n.* FROM hr_completion_notifications n LEFT JOIN hr_notification_reads r ON r.notification=n.id AND r.account=? WHERE n.active=1 AND r.notification IS NULL ORDER BY n.at DESC',(u['name'],)):
        b=hr_unpack(hr_row(c,n['enrollment'])['body']);rows.append(dict(id=n['id'],enrollment=n['enrollment'],at=n['at'],name=' '.join(b.get(k,'') for k in ('first','last')),employer=b['employer']))
    c.commit();return rows

def hr_employee_file(h,c,u,q):
    r=hr_row(c,q.get('id',[''])[0]);b=hr_unpack(r['body']);all_versions=q.get('versions',['latest'])[0]=='all'
    docs=c.execute('SELECT * FROM hr_documents WHERE enrollment=? ORDER BY at,id',(r['id'],)).fetchall()
    if not all_versions:
        latest={d['kind']:d for d in docs};docs=[latest[k] for k in HR_STEPS if k in latest]
    if not docs:raise Problem('No employee documents have been submitted yet.')
    Reader,Writer,_,Canvas=hr_pdf_libraries();writer=Writer();cover=io.BytesIO();canvas=Canvas(cover,pagesize=(612,792))
    def line(text,size=11):
        nonlocal y
        if y<55:canvas.showPage();y=750
        canvas.setFont('Helvetica',size)
        for part in __import__('textwrap').wrap(str(text),85):canvas.drawString(36,y,part);y-=17
    y=750;line('CoastYouth Retail - Confidential employee file',17);y-=10
    line('Employee: '+' '.join(b.get(k,'') for k in ('first','middle','last')));line('Employer: '+b['employer']);line('Prepared: '+dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
    line('Included: '+('All submitted versions (including prior corrections)' if all_versions else 'Latest submitted version of each form'))
    line('Onboarding status: '+r['status']);line('Submitted documents may still need HR review or employer completion.');y-=12
    missing=[HR_STEPS[k] for k in HR_STEPS if not any(d['kind']==k for d in docs)]
    if missing:line('Not yet submitted: '+', '.join(missing));y-=8
    pages=[]
    for d in docs:
        payload=hr_unpack(d['body']);raw=base64.b64decode(payload['file'])
        if hashlib.sha256(raw).hexdigest()!=d['digest']:raise Problem('Document integrity check failed. No employee file was exported.',503)
        line(HR_STEPS[d['kind']]+' - '+d['status'].replace('_',' '))
        if payload['mime']=='application/pdf':reader=Reader(io.BytesIO(raw))
        else:
            from PIL import Image
            image=Image.open(io.BytesIO(raw)).convert('RGB');buf=io.BytesIO();image.save(buf,format='PDF',resolution=150);reader=Reader(io.BytesIO(buf.getvalue()))
        pages.append(reader)
    canvas.save();writer.append(Reader(io.BytesIO(cover.getvalue())))
    for reader in pages:writer.append(reader)
    output=io.BytesIO();writer.write(output)
    hr_event(c,r['id'],u['name'],'Exported printable employee file','all versions' if all_versions else 'latest versions');c.commit()
    return h.send(output.getvalue(),kind='application/pdf',attachment=True)

def hr_reference_seed(c):
    for item in HR_REFERENCE_FORMS:
        ident='reference-'+item['kind']
        if not c.execute('SELECT 1 FROM hr_templates WHERE id=?',(ident,)).fetchone():
            c.execute('INSERT INTO hr_templates VALUES(?,?,?,?,0,?,?,?)',(ident,item['kind'],item['title'],item['edition'],item['mime'],hr_pack({'file':item['file']}),hashlib.sha256(base64.b64decode(item['file'])).hexdigest()))
    c.commit()

def hr_get(h,c,path,q):
    if path.startswith('browser-'):return hr_browser_get(h,c,path,q)
    if path=='activity':
        hr_auth(h,c);cookies=SimpleCookie(h.headers.get('Cookie',''));session=HR_SESSIONS[cookies['hr_session'].value]
        session['last_active']=time.time()
        return h.send({'pending_update':flow_active()})
    if path=='completed-file':
        r=hr_auth(h,c);summary=hr_summary(c,r)
        if not summary['profile'].get('profile_complete') or any(s['status'] not in ('submitted','accepted') for s in summary['steps']):raise Problem('Finish your onboarding steps before downloading the completed packet.')
        return hr_employee_file(h,c,dict(name=r['account']),{'id':[r['id']]})
    if path=='state':
        r=hr_auth(h,c);settings=hr_settings(c);result=hr_summary(c,r,True)
        return h.send(dict(result,settings={k:settings[k] for k in ('contact','welcome')},consent_text=HR_CONSENT,consent_version=HR_CONSENT_VERSION,templates=[dict(x) for x in c.execute('SELECT t.id,t.kind,t.title,t.edition,(SELECT f.id FROM hr_browser_forms f WHERE f.template=t.id AND f.active=1) AS browser_form FROM hr_templates t WHERE t.active=1')]))
    if path in ('document','template'):
        ident=q.get('id',[''])[0];employee=None
        try:u=hr_admin(h)
        except Problem:employee=hr_auth(h,c);u=None
        if path=='document':
            r=c.execute('SELECT * FROM hr_documents WHERE id=?',(ident,)).fetchone()
            if not r or (employee and r['enrollment']!=employee['id']):raise Problem('Document not found.',404)
            hr_event(c,r['enrollment'],u['name'] if u else 'employee','Downloaded document',ident);c.commit();payload=hr_unpack(r['body']);raw=base64.b64decode(payload['file'])
            if hashlib.sha256(raw).hexdigest()!=r['digest']:raise Problem('Document integrity check failed. Contact the administrator to restore the verified backup.',503)
            return h.send(raw,kind=payload['mime'],attachment=True)
        r=c.execute('SELECT * FROM hr_templates WHERE id=?',(ident,)).fetchone()
        if not r or (employee and not r['active'] and not c.execute('SELECT 1 FROM hr_documents WHERE enrollment=? AND template=?',(employee['id'],ident)).fetchone()):raise Problem('Template not available.',404)
        return h.send(base64.b64decode(hr_unpack(r['body'])['file']),kind=r['mime'],attachment=True)
    u=hr_admin(h)
    if path=='notifications':return h.send(hr_notifications(c,u))
    if path=='employee-file':return hr_employee_file(h,c,u,q)
    if path=='dashboard':hr_reference_seed(c);hr_source_seed(c)
    if path=='dashboard':return h.send(dict(notifications=hr_notifications(c,u),employers=HR_EMPLOYERS,settings=hr_settings(c),steps=HR_STEPS,templates=[dict(x) for x in c.execute('SELECT id,kind,title,edition,active,digest FROM hr_templates')],employees=[hr_summary(c,r) for r in c.execute('SELECT * FROM hr_enrollments ORDER BY rowid DESC')],mail=[dict(x) for x in c.execute('SELECT id,enrollment,status,error FROM hr_mail ORDER BY rowid DESC LIMIT 100')],email_ready=bool(hr_email_secret(c))))
    if path=='employee':return h.send(hr_summary(c,hr_row(c,q.get('id',[''])[0]),True))
    raise Problem('HR page not found.',404)

def hr_file(d,template=False):
    try:raw=base64.b64decode(d.get('file',''),validate=True)
    except Exception:raise Problem('Choose a valid file.')
    if not raw or len(raw)>3000000:raise Problem('Choose a file up to 3 MB.')
    mime='application/pdf' if raw.startswith(b'%PDF-') else 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else None
    if template and raw.startswith(b'PK'):mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if not mime:raise Problem('Use PDF, PNG or JPEG'+(' (or DOCX for a blank template).' if template else '.'))
    return raw,mime

def hr_post(h,c,path,d):
    hr_secure(h)
    if path.startswith('browser-'):return hr_browser_post(h,c,path,d)
    if path=='login':
        key='hr:'+h.client_address[0];attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-300]
        if len(attempts)>=10:raise Problem('Too many attempts. Wait five minutes.',429)
        ATTEMPTS[key]=attempts+[time.time()];digest=hashlib.sha256(str(d.get('token','')).encode()).hexdigest()
        r=c.execute('SELECT * FROM hr_enrollments WHERE token_hash=?',(digest,)).fetchone();u=c.execute('SELECT * FROM users WHERE name=?',(str(d.get('username','')),)).fetchone()
        if not r or not u or r['account']!=u['name'] or r['status']=='revoked' or r['expires']<time.time() or not hmac.compare_digest(u['hash'],password(str(d.get('password','')),u['salt'])):raise Problem('Invitation or sign-in details are invalid or expired.',401)
        token=secrets.token_urlsafe(32);HR_SESSIONS[token]=dict(id=r['id'],token_hash=digest,expires=time.time()+3600);ATTEMPTS.pop(key,None);hr_event(c,r['id'],'employee','Signed in');c.commit()
        return h.send({'ok':True},cookie='hr_session='+token+'; HttpOnly; SameSite=Strict; Path=/api/hr; Max-Age=3600')
    if path in ('password','consent','profile','upload','help','withdraw','logout'):
        r=hr_auth(h,c);b=hr_unpack(r['body']);ident=r['id']
        if r['status']=='complete' and path not in ('help','logout'):raise Problem('Onboarding is complete. Ask HR to arrange any corrections.',409)
        if path=='logout':
            cookies=SimpleCookie();cookies.load(h.headers.get('Cookie',''));HR_SESSIONS.pop(cookies['hr_session'].value,None);return h.send({'ok':True},cookie='hr_session=; HttpOnly; SameSite=Strict; Path=/api/hr; Max-Age=0')
        if path=='password':
            p=d.get('password','')
            if not valid_credential(p):raise Problem('Use a password of 8–256 characters.')
            old=c.execute('SELECT * FROM users WHERE name=?',(r['account'],)).fetchone()
            if hmac.compare_digest(old['hash'],password(p,old['salt'])):raise Problem('Choose a new password different from the temporary password.')
            salt=secrets.token_hex(16);c.execute('UPDATE users SET salt=?,hash=? WHERE name=?',(salt,password(p,salt),r['account']));b['password_changed']=True
        elif not b.get('password_changed'):raise Problem('Choose your new password first.',403)
        elif path=='consent':
            if d.get('version')!=HR_CONSENT_VERSION or d.get('agree') is not True or d.get('access_test') is not True:raise Problem('Open the test document and confirm electronic-record consent.')
            b['consent']=dict(version=HR_CONSENT_VERSION,text=HR_CONSENT,at=time.time(),name=pos_text(d.get('name'),'your full name'));b.pop('paper_requested',None)
        elif path=='withdraw':b['paper_requested']=True;hr_event(c,ident,'employee','Requested paper process / withdrew future electronic consent')
        elif path=='help':
            text=customer_text(d.get('message'),'help message',3000)
            if not text:raise Problem('Enter your question.')
            c.execute('INSERT INTO hr_messages(enrollment,at,actor,body) VALUES(?,?,?,?)',(ident,time.time(),'employee',hr_pack(text)))
        elif path=='profile':
            if not b.get('consent') or b.get('paper_requested'):raise Problem('Complete consent or contact HR for paper forms.')
            for k in ('first','middle','last','phone','address','city','zip'):b[k]=customer_text(d.get(k,''),k,150)
            digits=re.sub(r'\D','',b['phone'])
            if len(digits)==11 and digits.startswith('1'):digits=digits[1:]
            if len(digits)!=10 or digits[0] not in '23456789':raise Problem('Enter a 10-digit phone number including the area code, for example (228) 555-0100.')
            b['phone']='('+digits[:3]+') '+digits[3:6]+'-'+digits[6:]
            b['email']=customer_email(d.get('email'));b['state']='MS'
            if not b['first'] or not b['last']:raise Problem('Enter your first and last names.')
            b['profile_complete']=True;hr_sync_contact(c,r,b)
        elif path=='upload':
            if not b.get('consent') or b.get('paper_requested'):raise Problem('Complete consent or contact HR for paper forms.')
            kind=d.get('kind');template=c.execute('SELECT * FROM hr_templates WHERE id=? AND active=1 AND kind=?',(d.get('template'),kind)).fetchone()
            if kind not in HR_STEPS or not template:raise Problem('HR must approve a current template for this section.')
            if d.get('completed_signed') is not True:raise Problem('Confirm the document is completed and signed where required.')
            raw,mime=hr_file(d);doc=hashlib.sha256((ident+kind+template['id']).encode()+raw).hexdigest();payload=dict(file=base64.b64encode(raw).decode(),mime=mime,attestation='I confirm this is my completed document, signed where required.',name=pos_text(d.get('name'),'your full name'),consent=b['consent'])
            c.execute("INSERT OR IGNORE INTO hr_documents VALUES(?,?,?,?,?,?,?,'submitted','')",(doc,ident,kind,template['id'],time.time(),hr_pack(payload),hashlib.sha256(raw).hexdigest()));hr_event(c,ident,'employee','Submitted '+kind,doc)
        c.execute('UPDATE hr_enrollments SET body=?,revision=revision+1 WHERE id=?',(hr_pack(b),ident));hr_event(c,ident,'employee',path);hr_completion_sync(c,ident);c.commit();return h.send({'ok':True})
    u=hr_admin(h)
    if path=='notification-read':
        row=c.execute('SELECT id FROM hr_completion_notifications WHERE id=?',(d.get('notification'),)).fetchone()
        if not row:raise Problem('Notification not found.',404)
        c.execute('INSERT OR IGNORE INTO hr_notification_reads VALUES(?,?,?)',(row['id'],u['name'],time.time()));c.commit();return h.send({'ok':True})
    if path=='settings':
        old=hr_settings(c)
        if d.get('revision')!=old['revision']:raise Problem('HR settings changed. Reload.',409)
        body={k:customer_text(d.get(k,''),k,6000 if k=='email_body' else 1000) for k in ('contact','sender','sender_name','subject','welcome','email_body')}
        for k in ('contact','sender'):
            if body[k]:body[k]=customer_email(body[k])
        if d.get('app_password'):
            secret=customer_text(d['app_password'],'Gmail app password',100).replace(' ','')
            if len(secret)!=16 or not secret.isalpha():raise Problem('Enter the 16-letter Google app password, not your normal account password.')
            c.execute('INSERT INTO hr_credentials VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(hr_pack(secret),))
        body['enabled']=d.get('enabled') is True
        if body['enabled'] and (not body['contact'] or not body['sender'] or not hr_email_secret(c)):raise Problem('Set HR contact, sender, and the server HR Gmail app password before enabling email.')
        c.execute('INSERT INTO hr_settings VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(old['revision']+1,json.dumps(body)));hr_event(c,'',u['name'],'Changed HR settings')
    elif path=='template':
        if d.get('kind') not in HR_STEPS:raise Problem('Choose a section.')
        if d.get('reviewed') is not True:raise Problem('Confirm the form edition, instructions, disclosures and employer details have been reviewed.')
        raw,mime=hr_file(d,True);ident=secrets.token_hex(16);c.execute('UPDATE hr_templates SET active=0 WHERE kind=?',(d['kind'],));c.execute('INSERT INTO hr_templates VALUES(?,?,?,?,1,?,?,?)',(ident,d['kind'],pos_text(d.get('title'),'template title'),pos_text(d.get('edition'),'edition'),mime,hr_pack({'file':base64.b64encode(raw).decode()}),hashlib.sha256(raw).hexdigest()));hr_event(c,'',u['name'],'Approved template',ident)
    elif path=='invite':
        if not has_permission(u,'manage_users'):raise Problem('Add users permission is also required.',403)
        request=d.get('request')
        if not isinstance(request,str) or not re.fullmatch('[0-9a-f]{32}',request):raise Problem('Invitation request ID required.')
        if c.execute('SELECT 1 FROM hr_enrollments WHERE id=?',(request,)).fetchone():return h.send({'ok':True,'id':request,'already_created':True})
        first=pos_text(d.get('first'),'first name',80);last=pos_text(d.get('last'),'last name',80);email=customer_email(d.get('email'));employer=d.get('employer')
        if employer not in HR_EMPLOYERS:raise Problem('Select the employer.')
        username=pos_text(d.get('username'),'username',80);temp=secrets.token_urlsafe(14);h.add_user(c,username,temp,False)
        c.execute('INSERT INTO permissions VALUES(?,?,?)',(username,0,0));c.execute('INSERT INTO user_grants VALUES(?,?)',(username,json.dumps({k:False for k in PERMISSIONS})))
        token=secrets.token_urlsafe(32);body=dict(first=first,middle=customer_text(d.get('middle',''),'middle name',80),last=last,phone=customer_text(d.get('phone',''),'phone',60),email=email,employer=employer,state='MS',password_changed=False)
        c.execute("INSERT INTO hr_enrollments VALUES(?,?,?,?,0,'invited',?)",(request,username,hashlib.sha256(token.encode()).hexdigest(),time.time()+604800,hr_pack(body)));link='https://operations.coastyfc.com/onboarding#'+token
        hr_sync_contact(c,dict(account=username),body)
        settings=hr_settings(c);variables=dict(first=first,employer=employer,username=username,password=temp,link=link);text=settings['email_body']
        for k,v in variables.items():text=text.replace('{'+k+'}',v)
        c.execute("INSERT INTO hr_mail VALUES(?,?,?,'pending','')",(request,request,hr_pack(dict(recipient=email,subject=settings['subject'],text=text))));hr_event(c,request,u['name'],'Created invitation');c.commit();return h.send(dict(ok=True,id=request,link=link,username=username,temporary_password=temp,email_status='pending' if settings['enabled'] else 'disabled'))
    elif path=='reinvite':
        r=hr_row(c,d.get('id'))
        if r['status']=='complete':raise Problem('This employee has completed onboarding.')
        if d.get('revision')!=r['revision']:raise Problem('Employee status changed. Reopen this record.',409)
        if not has_permission(u,'manage_users'):raise Problem('User management permission required.',403)
        b=hr_unpack(r['body']);token=secrets.token_urlsafe(32);temp=secrets.token_urlsafe(14);salt=secrets.token_hex(16);b['password_changed']=False
        c.execute('UPDATE users SET salt=?,hash=? WHERE name=?',(salt,password(temp,salt),r['account']))
        c.execute("UPDATE hr_enrollments SET token_hash=?,expires=?,revision=revision+1,status='invited',body=? WHERE id=?",(hashlib.sha256(token.encode()).hexdigest(),time.time()+604800,hr_pack(b),r['id']))
        c.execute("UPDATE hr_mail SET status='canceled' WHERE enrollment=? AND status IN ('pending','uncertain')",(r['id'],))
        link='https://operations.coastyfc.com/onboarding#'+token;settings=hr_settings(c);text=settings['email_body']
        for k,v in dict(first=b['first'],employer=b['employer'],username=r['account'],password=temp,link=link).items():text=text.replace('{'+k+'}',v)
        c.execute("INSERT INTO hr_mail VALUES(?,?,?,'pending','')",(secrets.token_hex(16),r['id'],hr_pack(dict(recipient=b['email'],subject=settings['subject'],text=text))))
        hr_event(c,r['id'],u['name'],'Replaced invitation; previous link invalidated');c.commit();return h.send(dict(ok=True,link=link,username=r['account'],temporary_password=temp))
    elif path in ('review','reply','resolve','revoke','complete'):
        r=hr_row(c,d.get('id'));ident=r['id']
        if path=='review':
            doc=c.execute('SELECT * FROM hr_documents WHERE id=? AND enrollment=?',(d.get('document'),ident)).fetchone()
            if not doc:raise Problem('Document not found.',404)
            status=d.get('status')
            if status not in ('accepted','needs_correction'):raise Problem('Choose a review result.')
            note=customer_text(d.get('note',''),'review note',1000)
            if status=='needs_correction' and not note:raise Problem('Explain what needs correction.')
            if doc['kind']=='i9' and status=='accepted' and d.get('employer_verified') is not True:raise Problem('Confirm employer Section 2 and required document examination are complete. Employee upload alone is not I-9 verification.')
            signature=c.execute('SELECT body FROM hr_browser_signatures WHERE document=?',(doc['id'],)).fetchone()
            if doc['kind']=='i9' and status=='accepted' and signature and hr_unpack(signature[0])['role']!='employer':raise Problem('Complete and sign the employer section in OFFICE before accepting this I-9.')
            c.execute('UPDATE hr_documents SET status=?,review_note=? WHERE id=?',(status,note,doc['id']));hr_event(c,ident,u['name'],'Reviewed document: '+status,doc['id'])
        if path=='reply':
            text=customer_text(d.get('message'),'reply',3000)
            if not text:raise Problem('Enter a reply.')
            c.execute('INSERT INTO hr_messages(enrollment,at,actor,body) VALUES(?,?,?,?)',(ident,time.time(),u['name'],hr_pack(text)))
        if path=='resolve':c.execute("UPDATE hr_messages SET resolved=1 WHERE enrollment=? AND actor='employee'",(ident,))
        if path=='revoke' and r['status']=='complete':raise Problem('Use OFFICE account security to deactivate an active staff account.')
        if path=='revoke':c.execute("UPDATE hr_enrollments SET status='revoked',revision=revision+1 WHERE id=?",(ident,))
        if path=='complete':
            summary=hr_summary(c,r)
            if not summary['profile'].get('profile_complete') or any(s['status']!='accepted' for s in summary['steps']):raise Problem('Complete the employee profile and accept all required documents first.')
            c.execute("UPDATE hr_enrollments SET status='complete',revision=revision+1 WHERE id=?",(ident,))
        hr_event(c,ident,u['name'],path);hr_completion_sync(c,ident)
    else:raise Problem('HR action not found.',404)
    c.commit();return h.send({'ok':True})

def hr_mail_tick():
    with LOCK,connect() as c:
        settings=hr_settings(c);secret=hr_email_secret(c)
        if not settings['enabled'] or not secret:return
        row=c.execute("SELECT m.* FROM hr_mail m JOIN hr_enrollments e ON e.id=m.enrollment WHERE m.status='pending' AND e.status<>'revoked' AND e.expires>? ORDER BY m.rowid LIMIT 1",(time.time(),)).fetchone()
        if not row:return
        payload=hr_unpack(row['body']);c.execute("UPDATE hr_mail SET status='sending' WHERE id=?",(row['id'],));c.commit()
    try:customer_smtp(settings['sender'],secret,payload['recipient'],payload['subject'],payload['text'],'<hr-'+row['id']+'@'+settings['sender'].split('@')[1]+'>',settings['sender_name']);status='sent';error=''
    except Exception:status='uncertain';error='Delivery could not be confirmed. Check Gmail Sent before issuing a replacement invitation.'
    with LOCK,connect() as c:c.execute('UPDATE hr_mail SET status=?,error=? WHERE id=?',(status,error,row['id']))
