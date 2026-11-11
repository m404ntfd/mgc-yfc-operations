"""Giving foundation. Embedded in server.py; no payment or email network calls."""
GIVING_PERMISSIONS = {
 'view_giving':'View donors and giving history',
 'manage_donors':'Create and edit donor profiles',
 'record_gifts':'Record gifts received outside this application',
 'adjust_gifts':'Void or correct incorrect gift records',
 'manage_giving_plans':'Manage monthly giving drafts',
 'giving_statements':'Preview and print donor statements',
 'giving_settings':'Manage giving and statement settings',
}

def giving_init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS giving_donors(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS giving_donor_history(donor TEXT NOT NULL,revision INTEGER NOT NULL,at TEXT NOT NULL,actor TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(donor,revision));
CREATE TRIGGER IF NOT EXISTS giving_donor_history_no_update BEFORE UPDATE ON giving_donor_history BEGIN SELECT RAISE(ABORT,'Donor history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_donor_history_no_delete BEFORE DELETE ON giving_donor_history BEGIN SELECT RAISE(ABORT,'Donor history is immutable'); END;
CREATE TABLE IF NOT EXISTS giving_gifts(id TEXT PRIMARY KEY,donor TEXT NOT NULL,day TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS giving_gifts_donor_day ON giving_gifts(donor,day);
CREATE TABLE IF NOT EXISTS giving_voids(gift TEXT PRIMARY KEY,reason TEXT NOT NULL,actor TEXT NOT NULL,at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS giving_gift_replacements(
    original TEXT PRIMARY KEY NOT NULL REFERENCES giving_voids(gift),
    replacement TEXT UNIQUE NOT NULL REFERENCES giving_gifts(id),
    CHECK(original<>replacement)
);
CREATE TRIGGER IF NOT EXISTS giving_gift_replacements_no_update BEFORE UPDATE ON giving_gift_replacements BEGIN SELECT RAISE(ABORT,'Gift replacement history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_gift_replacements_no_delete BEFORE DELETE ON giving_gift_replacements BEGIN SELECT RAISE(ABORT,'Gift replacement history is immutable'); END;
CREATE TABLE IF NOT EXISTS giving_plans(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS giving_settings(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS giving_requests(id TEXT PRIMARY KEY,actor TEXT NOT NULL,payload TEXT NOT NULL,result TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS giving_statements(id TEXT PRIMARY KEY,donor TEXT NOT NULL,period TEXT NOT NULL,created_at TEXT NOT NULL,actor TEXT NOT NULL,body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS giving_statements_donor ON giving_statements(donor,created_at);
CREATE TRIGGER IF NOT EXISTS giving_statements_no_update BEFORE UPDATE ON giving_statements BEGIN SELECT RAISE(ABORT,'Saved statements are immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_statements_no_delete BEFORE DELETE ON giving_statements BEGIN SELECT RAISE(ABORT,'Saved statements are immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_gifts_no_update BEFORE UPDATE ON giving_gifts BEGIN SELECT RAISE(ABORT,'Gift history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_gifts_no_delete BEFORE DELETE ON giving_gifts BEGIN SELECT RAISE(ABORT,'Gift history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_voids_no_update BEFORE UPDATE ON giving_voids BEGIN SELECT RAISE(ABORT,'Void history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS giving_voids_no_delete BEFORE DELETE ON giving_voids BEGIN SELECT RAISE(ABORT,'Void history is immutable'); END;
''')

def giving_require(u,permission='view_giving'):
    if not has_permission(u,'view_giving') or not has_permission(u,permission):
        raise Problem('Giving permission required.',403)

def giving_text(d,key,limit=200,required=False):
    value=d.get(key,'')
    if not isinstance(value,str) or len(value)>limit:raise Problem('Invalid '+key+'.')
    value=value.strip()
    if required and not value:raise Problem(key+' is required.')
    return value

def giving_amount(d,key='amount',minimum=1):
    value=d.get(key)
    if type(value) is not int or not minimum<=value<=100000000:raise Problem('Enter a valid amount in whole cents.')
    return value

def giving_day(d,key):
    value=giving_text(d,key,10,True)
    try:
        parsed=dt.date.fromisoformat(value)
        if parsed.isoformat()!=value:raise ValueError()
    except ValueError:raise Problem('Enter a valid '+key+' (YYYY-MM-DD).')
    return value

def giving_profile(c,ident):
    row=c.execute('SELECT * FROM giving_donors WHERE id=?',(ident,)).fetchone()
    if not row:raise Problem('Donor not found.',404)
    return dict(json.loads(row['body']),id=row['id'],revision=row['revision'])

def giving_config(c):
    row=c.execute('SELECT * FROM giving_settings WHERE id=1').fetchone()
    defaults={'organization':'Mississippi Gulf Coast Youth for Christ','ein':'','address':'',
      'monthly_message':'Thank you for investing in young people on the Gulf Coast.',
      'annual_message':'Thank you for your generosity throughout the year.'}
    return dict(json.loads(row['body']) if row else defaults,revision=row['revision'] if row else 0)

def giving_get(c,u,path,q):
    giving_require(u)
    if path=='donor':
        return {'donor':giving_profile(c,q.get('id',[''])[0])}
    if path=='donor_history':
        giving_require(u,'manage_donors')
        donor=giving_profile(c,q.get('donor',[''])[0])
        rows=c.execute('SELECT * FROM giving_donor_history WHERE donor=? ORDER BY revision DESC',(donor['id'],))
        return {'history':[dict(json.loads(r['body']),revision=r['revision'],at=r['at'],actor=r['actor']) for r in rows]}
    if path=='donors':
        search=giving_text({'search':q.get('search',[''])[0]},'search',254).casefold()
        try:
            limit_text=q.get('limit',['50'])[0];offset_text=q.get('offset',['0'])[0]
            if not re.fullmatch(r'[0-9]{1,7}',limit_text) or not re.fullmatch(r'[0-9]{1,7}',offset_text):raise ValueError()
            limit=int(limit_text);offset=int(offset_text)
            if not 1<=limit<=100:raise ValueError()
        except (ValueError,TypeError):raise Problem('Choose a limit from 1 to 100 and a nonnegative offset.')
        donors=[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM giving_donors')]
        donors=[d for d in donors if not search or any(search in d.get(k,'').casefold() for k in ('name','email','address'))]
        donors.sort(key=lambda d:(d['name'].casefold(),d['id']))
        return {'donors':donors[offset:offset+limit],'total':len(donors),'limit':limit,'offset':offset}
    if path in ('statement_history','statement_snapshot'):
        giving_require(u,'giving_statements')
        if path=='statement_snapshot':
            row=c.execute('SELECT body FROM giving_statements WHERE id=?',(q.get('id',[''])[0],)).fetchone()
            if not row:raise Problem('Saved statement not found.',404)
            return json.loads(row['body'])
        donor=giving_profile(c,q.get('donor',[''])[0])
        return {'statements':[dict(id=r['id'],period=r['period'],created_at=r['created_at'],actor=r['actor'],total=json.loads(r['body'])['total']) for r in c.execute('SELECT * FROM giving_statements WHERE donor=? ORDER BY created_at DESC,id DESC',(donor['id'],))]}
    if path=='overview':
        donors=[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM giving_donors')]
        gifts=[dict(json.loads(r['body']),id=r['id'],voided=bool(r['voided']),
          replaces=r['original'],replacement=r['replacement'],
          correction={'reason':r['void_reason'],'actor':r['void_actor'],'at':r['void_at']} if r['voided'] else None)
          for r in c.execute('''SELECT g.*,v.gift AS voided,v.reason AS void_reason,v.actor AS void_actor,v.at AS void_at,
              outgoing.replacement,incoming.original
          FROM giving_gifts g
          LEFT JOIN giving_voids v ON v.gift=g.id
          LEFT JOIN giving_gift_replacements outgoing ON outgoing.original=g.id
          LEFT JOIN giving_gift_replacements incoming ON incoming.replacement=g.id
          ORDER BY g.day DESC,g.id''')]
        plans=[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM giving_plans')]
        return {'donors':sorted(donors,key=lambda x:x['name'].casefold()),'gifts':gifts,'plans':plans,
          'processing':'not_connected','delivery':'not_configured','settings':giving_config(c) if has_permission(u,'giving_settings') else None}
    if path=='statement':
        giving_require(u,'giving_statements')
        donor=giving_profile(c,q.get('donor',[''])[0]);period=q.get('period',[''])[0]
        if not re.fullmatch(r'\d{4}(-\d{2})?',period):raise Problem('Choose a year or month.')
        try:
            start=dt.date.fromisoformat(period+'-01' if len(period)==7 else period+'-01-01')
            end=dt.date(start.year+1,1,1) if len(period)==4 or start.month==12 else dt.date(start.year,start.month+1,1)
        except ValueError:raise Problem('Choose a valid statement period.')
        rows=c.execute("""
            SELECT g.* FROM giving_gifts g LEFT JOIN giving_voids v ON v.gift=g.id
            WHERE g.donor=? AND g.day>=? AND g.day<? AND v.gift IS NULL
            ORDER BY g.day,g.id
        """,(donor['id'],f'{start.year:04d}-01-01',end.isoformat())).fetchall()
        first_day=start.isoformat()
        gifts=[dict(json.loads(r['body']),id=r['id']) for r in rows if r['day']>=first_day]
        ytd=sum(r['amount'] for r in rows)
        settings=giving_config(c)
        return {'donor':donor,'period':period,'gifts':gifts,'total':sum(g['amount'] for g in gifts),'ytd':ytd,'settings':settings,'message':settings['monthly_message' if len(period)==7 else 'annual_message'],'preview':True}
    raise Problem('Giving endpoint not found.',404)

def giving_void(c,u,ident,reason,now):
    if not c.execute('SELECT 1 FROM giving_gifts WHERE id=?',(ident,)).fetchone():
        raise Problem('Gift not found.',404)
    if c.execute('SELECT 1 FROM giving_voids WHERE gift=?',(ident,)).fetchone():
        raise Problem('Gift already voided.',409)
    c.execute('INSERT INTO giving_voids VALUES(?,?,?,?)',(ident,reason,u['name'],now))

def giving_post(c,u,path,d):
    permissions={'donor':'manage_donors','gift':'record_gifts','void':'adjust_gifts','replace_gift':'adjust_gifts','plan':'manage_giving_plans','settings':'giving_settings','statement_snapshot':'giving_statements'}
    if path not in permissions:raise Problem('Giving endpoint not found.',404)
    giving_require(u,permissions[path])
    if path=='replace_gift':giving_require(u,'record_gifts')
    allowed={'donor':{'id','revision','name','email','address','delivery'},'gift':{'donor','day','amount','method','reference','fund','benefit','benefit_value'},'void':{'gift','reason'},'plan':{'id','revision','donor','amount','start','billing_day','fund','status'},'settings':{'revision','organization','ein','address','monthly_message','annual_message'}}
    allowed['replace_gift']=allowed['gift']|allowed['void']
    allowed['statement_snapshot']={'donor','period'}
    if set(d)-allowed[path]-{'request'}:raise Problem('Unsupported fields. Do not enter card data here.')
    request=giving_text(d,'request',32,True)
    if not re.fullmatch('[0-9a-f]{32}',request):raise Problem('A unique request is required.')
    actor=u.get('receipt_owner') or u['name'];payload=json.dumps([path,d],sort_keys=True)
    c.execute('BEGIN IMMEDIATE')
    old=c.execute('SELECT * FROM giving_requests WHERE id=?',(request,)).fetchone()
    if old:
        if old['actor']!=actor or old['payload']!=payload:raise Problem('Request already used for another action.',409)
        c.commit()
        return json.loads(old['result'])
    now=dt.datetime.now().astimezone().isoformat(timespec='seconds');ident=giving_text(d,'id',32) or secrets.token_hex(16)
    if not re.fullmatch('[0-9a-f]{32}',ident):raise Problem('Invalid record identifier.')
    if path=='statement_snapshot':
        donor=giving_text(d,'donor',32,True);period=giving_text(d,'period',7,True)
        body=giving_get(c,u,'statement',{'donor':[donor],'period':[period]})
        body.update(id=ident,created_at=now,actor=u['name'],preview=False,saved=True,delivery='not_sent')
        c.execute('INSERT INTO giving_statements VALUES(?,?,?,?,?,?)',(ident,donor,period,now,u['name'],json.dumps(body)))
    elif path=='donor':
        if type(d.get('revision',0)) is not int or d.get('revision',0)<0:raise Problem('Invalid donor revision.')
        previous=giving_profile(c,ident) if d.get('id') else None
        body={k:giving_text(d,k,limit,k=='name') for k,limit in [('name',150),('email',254),('address',500),('delivery',10)]}
        if body['email']:customer_email(body['email'])
        if body['delivery'] not in ('email','print'):raise Problem('Choose email or print delivery.')
        if body['delivery']=='email' and not body['email']:raise Problem('An email address is required for email statements.')
        table='giving_donors'
    elif path=='plan':
        donor=giving_profile(c,giving_text(d,'donor',32,True))
        body={'donor':donor['id'],'amount':giving_amount(d),'start':giving_day(d,'start'),'billing_day':d.get('billing_day'),'fund':giving_text(d,'fund',100,True),'status':giving_text(d,'status',20,True)}
        if type(body['billing_day']) is not int or not 1<=body['billing_day']<=28:raise Problem('Choose a billing day from 1 to 28.')
        if body['status'] not in ('draft','cancelled'):raise Problem('Live recurring charges are not connected. Save a draft only.')
        table='giving_plans'
    elif path=='settings':
        body={k:giving_text(d,k,limit,k=='organization') for k,limit in [('organization',200),('ein',20),('address',500),('monthly_message',2000),('annual_message',2000)]}
        table='giving_settings';ident=1
    elif path in ('gift','replace_gift'):
        donor=giving_profile(c,giving_text(d,'donor',32,True));amount=giving_amount(d);day=giving_day(d,'day')
        if day>dt.date.today().isoformat():raise Problem('Received gifts cannot have a future date.')
        method=giving_text(d,'method',30,True)
        if method not in ('cash','check','external_card','external_bank'):raise Problem('Choose a supported received-payment method.')
        benefit=giving_text(d,'benefit',500);value=giving_amount(d,'benefit_value',0)
        if value>amount or (value>0 and not benefit):raise Problem('Describe goods or services and enter a value no greater than the payment.')
        body={'donor':donor['id'],'donor_name':donor['name'],'day':day,'amount':amount,'method':method,'reference':giving_text(d,'reference',200,True),'fund':giving_text(d,'fund',100,True),'benefit':benefit,'benefit_value':value,'actor':u['name'],'at':now}
        c.execute('INSERT INTO giving_gifts VALUES(?,?,?,?,?)',(ident,donor['id'],day,amount,json.dumps(body)))
        if path=='replace_gift':
            original=giving_text(d,'gift',32,True)
            reason=giving_text(d,'reason',500,True)
            giving_void(c,u,original,reason,now)
            c.execute('INSERT INTO giving_gift_replacements VALUES(?,?)',(original,ident))
    else:
        ident=giving_text(d,'gift',32,True)
        giving_void(c,u,ident,giving_text(d,'reason',500,True),now)
    if path in ('donor','plan','settings'):
        old=c.execute('SELECT revision FROM '+table+' WHERE id=?',(ident,)).fetchone();revision=old['revision'] if old else 0
        if d.get('revision',0)!=revision:raise Problem('This record changed. Reload before saving.',409)
        c.execute('INSERT INTO '+table+' VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(ident,revision+1,json.dumps(body)))
        if path=='donor':
            history={'before':previous,'after':dict(body,id=ident,revision=revision+1)}
            c.execute('INSERT INTO giving_donor_history VALUES(?,?,?,?,?)',(ident,revision+1,now,u['name'],json.dumps(history)))
    result={'id':ident,'ok':True}
    c.execute('INSERT INTO giving_requests VALUES(?,?,?,?)',(request,actor,payload,json.dumps(result)))
    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(now,u['name'],'Giving '+path, str(ident)))
    c.commit()
    return result
