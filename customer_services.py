"""Embedded into server.py by prepare_web_assets.py for legacy update compatibility."""
import smtplib, ssl
from email.message import EmailMessage
from email.utils import formataddr

CUSTOMER_DEFAULTS={
 'receipt':{'address':'','phone':'','footer':'Thank you for shopping with us!','policy':'','logo':''},
 'email':{'enabled':False,'sender':'','sender_name':'CoastYouth Retail','reminder_hours':24,
          'confirmation_subject':'Your reservation at {store}',
          'confirmation_body':'Hello {customer},\n\nYour {type} reservation is confirmed for {start}.\n{address}\n\n{store}',
          'reminder_subject':'Reminder: your reservation at {store}',
          'reminder_body':'Hello {customer},\n\nThis is a reminder of your {type} reservation on {start}.\n{address}\n\nWe look forward to seeing you.\n{store}'},
 'display':{'enabled':False,'welcome':'Welcome to CoastYouth Retail','thanks':'Thank you! Have a wonderful day.'}}

def customer_init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS office_user_details(account TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customer_settings(kind TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reservation_contacts(job TEXT PRIMARY KEY,email TEXT NOT NULL,confirmations INTEGER NOT NULL,reminders INTEGER NOT NULL,revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS customer_delivery(id INTEGER PRIMARY KEY,job TEXT NOT NULL,kind TEXT NOT NULL,fingerprint TEXT NOT NULL,recipient TEXT NOT NULL,due REAL NOT NULL,status TEXT NOT NULL,body TEXT NOT NULL,error TEXT NOT NULL DEFAULT '',updated REAL NOT NULL,UNIQUE(job,kind,fingerprint));
CREATE TABLE IF NOT EXISTS reservation_message_versions(job TEXT PRIMARY KEY,signature TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS customer_displays(token_hash TEXT PRIMARY KEY,owner TEXT NOT NULL,connection TEXT NOT NULL,expires REAL NOT NULL,heartbeat REAL NOT NULL,cart TEXT,sale INTEGER);
''')

def customer_settings(c,kind):
    row=c.execute('SELECT * FROM customer_settings WHERE kind=?',(kind,)).fetchone()
    return dict(json.loads(row['body']) if row else CUSTOMER_DEFAULTS[kind],revision=row['revision'] if row else 0)

def customer_email(value):
    if not isinstance(value,str) or len(value)>254 or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+',value):raise Problem('Enter one valid email address.')
    return value.strip()

def customer_password():
    # Keep credentials out of the operational database and API responses.
    return os.environ.get('COASTYOUTH_GMAIL_APP_PASSWORD','').replace(' ','')

def customer_ready(c):
    s=customer_settings(c,'email')
    return bool(s['sender'] and customer_password())

def customer_text(value,label,limit=2000):
    if not isinstance(value,str) or len(value)>limit:raise Problem('Invalid '+label+'.')
    return value.strip()

def customer_fingerprint(job,contact):
    fields={k:job.get(k,'') for k in ('customer','type','start','end','address','status')}
    return hashlib.sha256(json.dumps([fields,contact['email']],sort_keys=True).encode()).hexdigest()

def customer_message(c,job,kind):
    settings=customer_settings(c,'email')
    fields={k:str(job.get(k,'')) for k in ('customer','type','start','end','address')}
    fields['store']=pos_settings(c)['store']
    def render(template):
        return re.sub(r'\{(customer|type|start|end|address|store)\}',lambda m:fields[m[1]],template)
    return {'subject':render(settings[kind+'_subject']).replace('\r',' ').replace('\n',' '),'text':render(settings[kind+'_body'])}

def customer_schedule(c,now=None):
    now=time.time() if now is None else now
    settings=customer_settings(c,'email')
    for contact in c.execute('SELECT * FROM reservation_contacts').fetchall():
        row=c.execute('SELECT body FROM jobs WHERE id=?',(contact['job'],)).fetchone()
        job=json.loads(row[0]) if row else None
        valid=job and not job.get('request') and job.get('status')=='Scheduled'
        try:start=dt.datetime.fromisoformat(job['start']).timestamp() if valid else 0
        except (ValueError,KeyError,TypeError):start=0
        signature=customer_fingerprint(job,contact) if valid else 'inactive'
        signature+=f":{contact['confirmations']}:{contact['reminders']}"
        version=c.execute('SELECT * FROM reservation_message_versions WHERE job=?',(contact['job'],)).fetchone()
        generation=version['generation'] if version else 0
        if not version or version['signature']!=signature:
            generation+=1
            c.execute('INSERT INTO reservation_message_versions VALUES(?,?,?) ON CONFLICT(job) DO UPDATE SET signature=excluded.signature,generation=excluded.generation',(contact['job'],signature,generation))
        fingerprint=hashlib.sha256(f'{signature}:{generation}'.encode()).hexdigest() if valid else ''
        c.execute("UPDATE customer_delivery SET status='canceled',error='Reservation or communication preference changed',updated=? WHERE job=? AND status IN ('pending','failed','blocked','uncertain') AND (fingerprint<>? OR due>=? OR ?=0)",(now,contact['job'],fingerprint,start,int(start>now)))
        for kind,enabled in [('confirmation',contact['confirmations']),('reminder',contact['reminders'])]:
            if not enabled or start<=now:
                c.execute("UPDATE customer_delivery SET status='canceled',updated=? WHERE job=? AND kind=? AND status IN ('pending','failed','blocked','uncertain')",(now,contact['job'],kind));continue
            due=now if kind=='confirmation' else start-settings['reminder_hours']*3600
            c.execute("INSERT OR IGNORE INTO customer_delivery(job,kind,fingerprint,recipient,due,status,body,updated) VALUES(?,?,?,?,?,'pending',?,?)",(contact['job'],kind,fingerprint,contact['email'],due,json.dumps(customer_message(c,job,kind)),now))
            c.execute("UPDATE customer_delivery SET body=? WHERE job=? AND kind=? AND fingerprint=? AND status='pending'",(json.dumps(customer_message(c,job,kind)),contact['job'],kind,fingerprint))
            if kind=='reminder':c.execute("UPDATE customer_delivery SET due=? WHERE job=? AND kind='reminder' AND fingerprint=? AND status='pending'",(due,contact['job'],fingerprint))

def customer_smtp(sender,password,recipient,subject,body,message_id,sender_name=""):
    message=EmailMessage();message['From']=formataddr((sender_name,sender));message['To']=recipient;message['Subject']=subject;message['Message-ID']=message_id;message.set_content(body)
    with smtplib.SMTP('smtp.gmail.com',587,timeout=20) as smtp:
        smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo();smtp.login(sender,password)
        smtp.send_message(message)

def customer_delivery_tick():
    # Claim under the shared lock, then send outside it so checkout stays responsive.
    with LOCK,connect() as c:
        if STOPPING or (UPDATE_FLOW and UPDATE_FLOW.get('phase') in ('installing','restarting')):return
        customer_schedule(c)
        settings=customer_settings(c,'email')
        if not settings['enabled'] or not customer_ready(c):return
        row=c.execute("SELECT * FROM customer_delivery WHERE status='pending' AND due<=? ORDER BY due,id LIMIT 1",(time.time(),)).fetchone()
        if not row:return
        ident=row['id'];payload=json.loads(row['body'])
        c.execute("UPDATE customer_delivery SET status='sending',updated=? WHERE id=?",(time.time(),ident))
    try:
        customer_smtp(settings['sender'],customer_password(),row['recipient'],payload['subject'],payload['text'],f'<coastyouth-reservation-{ident}-{row["fingerprint"][:16]}@{settings["sender"].split("@")[1]}>',settings['sender_name'])
        status,error='sent','Accepted by Gmail; inbox delivery is not guaranteed.'
    except smtplib.SMTPAuthenticationError:status,error='failed','Gmail authentication failed. Check the server app password and account policy.'
    except smtplib.SMTPRecipientsRefused:status,error='failed','Gmail refused the recipient address.'
    except Exception:status,error='uncertain','Delivery could not be confirmed. Check Gmail Sent before retrying to avoid duplicate mail.'
    with LOCK,connect() as c:c.execute('UPDATE customer_delivery SET status=?,error=?,updated=? WHERE id=?',(status,error,time.time(),ident))

def customer_worker():
    with LOCK,connect() as c:c.execute("UPDATE customer_delivery SET status='uncertain',error='Server restarted during delivery. Check Gmail Sent before retrying.' WHERE status='sending'")
    while not STOPPING:
        try:customer_delivery_tick()
        except Exception:pass
        time.sleep(10)

def customer_get(c,u,path,query):
    if path=='customer-settings':
        if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
        profile=stores_profile(c,query['store_id'][0]) if query.get('store_id') else None
        return dict(receipt=dict(profile['receipt'],revision=profile['revision']) if profile else customer_settings(c,'receipt'),email=customer_settings(c,'email'),display=customer_settings(c,'display'),gmail_ready=customer_ready(c),server_time=dt.datetime.now().astimezone().isoformat())
    if path=='reservation-messages':
        if not has_permission(u,'manage_pos') or not has_permission(u,'view_schedule'):raise Problem('POS settings and schedule permissions required.',403)
        customer_schedule(c)
        jobs=[]
        for r in c.execute('SELECT * FROM jobs ORDER BY id'):
            j=json.loads(r['body']);contact=c.execute('SELECT * FROM reservation_contacts WHERE job=?',(r['id'],)).fetchone()
            jobs.append(dict(id=r['id'],customer=j.get('customer',''),start=j.get('start',''),status=j.get('status',''),contact=dict(contact) if contact else None))
        return dict(jobs=jobs,deliveries=[dict(r,body=json.loads(r['body'])) for r in c.execute('SELECT * FROM customer_delivery ORDER BY id DESC LIMIT 100')],enabled=customer_settings(c,'email')['enabled'],gmail_ready=customer_ready(c))
    return None

def customer_post(handler,c,u,path,d,finish):
    if path=='customer-settings-save':
        if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
        kind=d.get('kind')
        if kind not in CUSTOMER_DEFAULTS:raise Problem('Choose receipt, email or display settings.')
        if kind=='email' and not u['admin']:raise Problem('Administrator access required for email delivery settings.',403)
        profile=stores_profile(c,d['store_id']) if kind=='receipt' and d.get('store_id') else None
        old=dict(profile['receipt'],revision=profile['revision']) if profile else customer_settings(c,kind)
        if d.get('revision')!=old['revision']:raise Problem('Settings changed. Reopen this screen before saving.',409)
        body={}
        for key,default in CUSTOMER_DEFAULTS[kind].items():
            value=d.get(key,default)
            if type(default) is bool:
                if type(value) is not bool:raise Problem('Choose '+key+'.')
                body[key]=value
            elif type(default) is int:body[key]=pos_int(value,key,1,168)
            else:body[key]=customer_text(value,key,280000 if key=='logo' else 2000)
        if kind=='receipt' and body['logo']:
            if not re.fullmatch(r'data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+',body['logo']):raise Problem('Choose a PNG or JPEG logo smaller than 200 KB.')
            raw=base64.b64decode(body['logo'].split(',')[1],validate=True)
            if len(raw)>200000 or not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):raise Problem('Invalid receipt logo.')
        if kind=='email':
            if body['sender']:body['sender']=customer_email(body['sender'])
            for key in ('confirmation_subject','reminder_subject','sender_name'):
                if '\n' in body[key] or '\r' in body[key] or len(body[key])>160:raise Problem('Use a single line for email names and subjects.')
            for key in ('confirmation_subject','confirmation_body','reminder_subject','reminder_body'):
                if not body[key]:raise Problem('Email templates cannot be blank.')
                if re.search(r'\{(?!customer\}|type\}|start\}|end\}|address\}|store\})[^}]*\}',body[key]):raise Problem('Use only the listed template fields.')
            if body['enabled'] and not (body['sender'] and customer_password()):raise Problem('Configure the Gmail app password on the server before enabling delivery.')
        if kind=='display' and (not body['welcome'] or not body['thanks']):raise Problem('Enter welcome and thank-you messages.')
        if profile:
            record={k:v for k,v in profile.items() if k not in ('id','revision')};record['receipt']=body
            c.execute('INSERT INTO retail_stores VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(profile['id'],profile['revision']+1,json.dumps(record)))
            return finish(dict(settings=dict(body,revision=profile['revision']+1)),'Changed store receipt branding')
        c.execute('INSERT INTO customer_settings VALUES(?,?,?) ON CONFLICT(kind) DO UPDATE SET revision=excluded.revision,body=excluded.body',(kind,old['revision']+1,json.dumps(body)))
        if kind=='display' and not body['enabled']:c.execute('DELETE FROM customer_displays')
        return finish(dict(settings=customer_settings(c,kind)),'Changed customer '+kind+' settings')
    if path in ('reservation-contact','reservation-preview','delivery-retry'):
        if not has_permission(u,'manage_pos') or not has_permission(u,'view_schedule'):raise Problem('POS settings and schedule permissions required.',403)
        if path=='delivery-retry':
            row=c.execute('SELECT * FROM customer_delivery WHERE id=?',(pos_int(d.get('id'),'message',1),)).fetchone()
            if not row or row['status'] not in ('failed','uncertain'):raise Problem('Only failed or uncertain messages may be retried.',409)
            if d.get('checked_sent') is not True:raise Problem('Check Gmail Sent before confirming a retry.')
            customer_schedule(c)
            current=c.execute('SELECT status FROM customer_delivery WHERE id=?',(row['id'],)).fetchone()[0]
            if current not in ('failed','uncertain'):raise Problem('The reservation changed; this message is no longer current.',409)
            c.execute("UPDATE customer_delivery SET status='pending',error='',updated=? WHERE id=?",(time.time(),row['id']))
            return finish({'ok':True},'Authorized reservation message retry')
        jid=pos_text(d.get('job'),'a reservation',64);row=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        if not row:raise Problem('Reservation no longer exists.',404)
        job=json.loads(row['body'])
        if path=='reservation-preview':
            kind=d.get('kind')
            if kind not in ('confirmation','reminder'):raise Problem('Choose a message type.')
            return finish(customer_message(c,job,kind),'Previewed reservation message')
        old=c.execute('SELECT * FROM reservation_contacts WHERE job=?',(jid,)).fetchone()
        if d.get('revision')!=(old['revision'] if old else 0):raise Problem('Communication preferences changed. Refresh first.',409)
        email=customer_email(d.get('email'))
        if any(type(d.get(k)) is not bool for k in ('confirmations','reminders')):raise Problem('Choose confirmation and reminder preferences.')
        c.execute('INSERT INTO reservation_contacts VALUES(?,?,?,?,?) ON CONFLICT(job) DO UPDATE SET email=excluded.email,confirmations=excluded.confirmations,reminders=excluded.reminders,revision=excluded.revision',(jid,email,int(d['confirmations']),int(d['reminders']),(old['revision'] if old else 0)+1))
        customer_schedule(c)
        return finish({'ok':True},'Changed reservation communication preferences '+jid)
    if path=='display-pair':
        if not customer_settings(c,'display')['enabled']:raise Problem('Enable the customer display in OFFICE first.')
        token=secrets.token_urlsafe(32);key=hashlib.sha256(token.encode()).hexdigest();connection=connection_key(handler)
        c.execute('DELETE FROM customer_displays WHERE owner=? AND connection=?',(u['receipt_owner'],connection))
        c.execute('INSERT INTO customer_displays VALUES(?,?,?,?,?,NULL,NULL)',(key,u['receipt_owner'],connection,time.time()+43200,time.time()))
        return finish({'token':token,'path':'/customer-display#'+token},'Paired customer checkout display')
    if path=='display-state':
        token=d.get('token','');key=hashlib.sha256(str(token).encode()).hexdigest();row=c.execute('SELECT * FROM customer_displays WHERE token_hash=? AND owner=? AND connection=?',(key,u['receipt_owner'],connection_key(handler))).fetchone()
        if not row or row['expires']<time.time():raise Problem('Customer display pairing expired. Pair again.',404)
        cart=d.get('cart');sale=d.get('sale')
        if cart and not c.execute('SELECT 1 FROM pos_carts WHERE id=? AND owner=?',(cart,u['receipt_owner'])).fetchone():raise Problem('Sale not available.',403)
        if sale and not c.execute('SELECT 1 FROM pos_sales WHERE id=? AND owner=?',(sale,u['receipt_owner'])).fetchone():raise Problem('Receipt not available.',403)
        c.execute('UPDATE customer_displays SET cart=?,sale=?,heartbeat=? WHERE token_hash=?',(cart,sale,time.time(),key))
        return handler.send({'ok':True})
    return None

def customer_display(c,token):
    key=hashlib.sha256(token.encode()).hexdigest();row=c.execute('SELECT * FROM customer_displays WHERE token_hash=?',(key,)).fetchone()
    if not row or row['expires']<time.time() or not customer_settings(c,'display')['enabled']:raise Problem('Display pairing expired or disabled.',404)
    settings=customer_settings(c,'display');result={'state':'idle','welcome':settings['welcome'],'thanks':settings['thanks'],'store':pos_settings(c)['store']}
    if time.time()-row['heartbeat']>30:return result
    if row['sale']:
        sale=c.execute('SELECT body FROM pos_sales WHERE id=?',(row['sale'],)).fetchone()
        if sale:
            data=json.loads(sale[0]);at=dt.datetime.fromisoformat(data['at']).timestamp()
            if time.time()-at<20:result.update(state='paid',total=data['total'],change=data.get('change',0))
        return result
    cart=c.execute("SELECT * FROM pos_carts WHERE id=? AND status='open'",(row['cart'],)).fetchone()
    if cart:
        data=pos_cart(cart)
        if not data.get('held'):
            result.update(state='sale',lines=[dict(name=l['name'],quantity=l['quantity'],subtotal=l['subtotal'],weight_milli=l.get('weight_milli'),price_per_lb=l.get('price_per_lb')) for l in data['lines']],subtotal=data['subtotal'],tax=data['tax'],total=data['total'])
            result['donation_prompt']='Would you like to round up or add a donation? Please tell your cashier.' if thrift_settings(c)['donations'] and not any(l.get('donation') for l in data['lines']) else ''
            if data.get('adjustment'):result['adjustment']={k:data['adjustment'][k] for k in ('mode','amount')}
    return result
