"""Practice checkout records are never inserted into sales or financial ledgers.

Embedded into server.py for compatibility with the existing update package.
"""

def training_init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS retail_training_modes(device TEXT PRIMARY KEY, enabled INTEGER NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS retail_training_transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, cart TEXT UNIQUE, store TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS retail_training_customers(id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT NOT NULL, body TEXT NOT NULL);
    ''')


def training_device(u,d):
    device=d.get('device')
    if device:
        if not isinstance(device,str) or not re.fullmatch('[0-9a-f]{32}',device):raise Problem('Invalid terminal identity.')
        return device
    return 'user:'+str(u.get('receipt_owner',''))


def training_state(c,u,d):
    device=training_device(u,d)
    row=c.execute('SELECT * FROM retail_training_modes WHERE device=?',(device,)).fetchone()
    return {'enabled':bool(row and row['enabled']),'revision':row['revision'] if row else 0,'device':device}


def training_get(c,u,path,q):
    d={k:v[0] for k,v in q.items()}
    if path=='training-state':return training_state(c,u,d)
    if path not in ('training-report','training-receipts'):return None
    receipts=path=='training-receipts'
    if not receipts and not has_permission(u,'view_pos_sales'):raise Problem('Sales report permission required.',403)
    if receipts and (not has_permission(u,'use_pos') or not training_state(c,u,d)['enabled']):raise Problem('Open training mode to view practice receipts.',403)
    store=d.get('store_id','');start=d.get('from','');end=d.get('to','')
    try:
        if start:dt.date.fromisoformat(start)
        if end:dt.date.fromisoformat(end)
    except ValueError:raise Problem('Choose valid report dates.')
    if start and end and end<start:raise Problem('End date must follow start date.')
    rows=[]
    for r in c.execute('SELECT * FROM retail_training_transactions ORDER BY id DESC'):
        body=json.loads(r['body'])
        if receipts and (r['kind']!='sale' or body.get('device')!=training_device(u,d)):continue
        if receipts and not has_permission(u,'view_pos_sales') and body.get('owner')!=u.get('receipt_owner'):continue
        if store and r['store']!=store:continue
        day=r['at'][:10]
        if start and day<start or end and day>end:continue
        rows.append(dict(id='T'+str(r['id']),kind=r['kind'],**body))
    return {'transactions':rows,'training':True,'count':len(rows),'total':sum(r.get('total',r.get('amount',0)) for r in rows if r['kind']!='canceled')}


def training_record(c,u,body,kind,cart=None):
    body=dict(body,training=True,cashier=u['name'],owner=u['receipt_owner'],at=dt.datetime.now().astimezone().isoformat(timespec='seconds'))
    ident=c.execute('INSERT INTO retail_training_transactions(cart,store,actor,at,kind,body) VALUES(?,?,?,?,?,?)',
        (cart,stores_id(body),u['name'],body['at'],kind,json.dumps(body))).lastrowid
    return dict(body,id='T'+str(ident))


def training_post(c,u,path,d,finish):
    state=training_state(c,u,d)
    if path=='training-mode':
        if type(d.get('enabled')) is not bool:raise Problem('Choose the training status.')
        if d.get('revision')!=state['revision']:raise Problem('Training status changed. Refresh before switching.',409)
        for r in c.execute("SELECT * FROM pos_carts WHERE status='open'"):
            cart=pos_cart(r)
            matches=cart.get('device')==state['device'] or (not cart.get('device') and r['owner']==u.get('receipt_owner'))
            if matches and cart['lines'] and not cart.get('held'):raise Problem('Finish, save with Pay later, or cancel the current transaction before changing training mode.',409)
        revision=state['revision']+1
        c.execute('INSERT INTO retail_training_modes VALUES(?,?,?,?) ON CONFLICT(device) DO UPDATE SET enabled=excluded.enabled,revision=excluded.revision,actor=excluded.actor',
            (state['device'],int(d['enabled']),revision,u['name']))
        return finish({'enabled':d['enabled'],'revision':revision,'device':state['device']},'Training mode '+('enabled' if d['enabled'] else 'disabled')) or True
    if not state['enabled']:return None
    if path=='cash-advance':
        context=stores_advance_context(c,u,d.get('device'))
        if d.get('terminal')!=context['terminal'] or d.get('store_id')!=context['store_id'] or d.get('drawer_id')!=context['drawer_id']:
            raise Problem('The terminal, store or drawer changed. Reopen Cash Advance before proceeding.',409)
        person=c.execute('SELECT name FROM receipt_profiles WHERE profile_id=?',(d.get('employee'),)).fetchone()
        if not person or d['employee']==u['receipt_owner']:raise Problem('Choose another employee.')
        if d.get('confirmed') is not True:raise Problem('Confirm the practice advance.')
        amount=pos_int(d.get('amount'),'cash advance amount',1)
        advance=training_record(c,u,dict(context,amount=amount,reason=pos_text(d.get('reason'),'a reason',300),employee_name=person['name'],actor_name=u['name'],drawer=None,device=state['device']),'cash-advance')
        return finish({'advance':advance},'TRAINING cash advance '+advance['id']) or True
    if path=='thrift-customer-save':
        if d.get('id'):raise Problem('Training cannot edit an existing customer.')
        name=pos_text(d.get('name'),'a customer name');contact=d.get('contact','')
        if not isinstance(contact,str) or len(contact)>200:raise Problem('Contact is too long.')
        body={'name':name,'contact':contact,'marketing':bool(d.get('marketing')),'training':True,'revision':1}
        ident=c.execute('INSERT INTO retail_training_customers(device,body) VALUES(?,?)',(state['device'],json.dumps(body))).lastrowid
        return finish({'customer':dict(body,id=-ident,points=0)},'TRAINING customer created') or True
    allowed={'new','add','remove','quantity','discard','hold','resume','adjustment-request','thrift-tag','thrift-donation','thrift-customer','thrift-reward','gift-add','birthday-reward','cash','credit','display-pair','display-state','customer-entry-start','customer-entry-close'}
    if path not in allowed:raise Problem('This action changes live records. Leave training mode first.',409)
    return None


def training_cart_guard(c,u,cart,path,d):
    state=training_state(c,u,d)
    if bool(cart.get('training'))!=state['enabled']:raise Problem('This transaction belongs to '+('training' if cart.get('training') else 'live')+' mode. Switch modes before reopening it.',409)
    if cart.get('training') and cart.get('device')!=state['device']:raise Problem('Open practice transactions on their original training register.',403)


def training_payment(c,u,cart,path,d,finish):
    if not cart.get('training'):return None
    if path not in ('cash','credit'):raise Problem('Card processing is unavailable in training mode.',409)
    if not cart['lines'] or cart['total']<0:raise Problem('Add an item before checkout.')
    sale={k:v for k,v in cart.items() if k not in ('id','revision','status')}
    amount=0
    if path=='credit':
        if not has_permission(u,'use_store_credit'):raise Problem('Redeem store credit permission required.',403)
        account=pos_credit_account(c,pos_int(d.get('account'),'account',1))
        if not account['active']:raise Problem('Account is inactive.',409)
        if d.get('account_revision')!=account['revision']:raise Problem('Balance changed. Refresh the account.',409)
        amount=pos_int(d.get('amount'),'practice credit',1,min(account['balance'],cart['total']))
        stores_credit_check(c,account,cart);thrift_voucher_check(c,account,cart,amount)
        sale.update(store_credit=amount,credit_account=account['code'],credit_name=account['name'],credit_balance=account['balance']-amount)
    remaining=cart['total']-amount
    tender=pos_int(d.get('tender'),'cash received',retail_cash_due(cart['settings'],remaining),20000000 if remaining else 0)
    sale.update(**retail_cash_change(cart['settings'],tender,remaining))
    sale.update(method='cash' if path=='cash' else 'store_credit_cash' if remaining else 'store_credit',tender=tender,receipt_design=stores_profile(c,stores_id(cart))['receipt'])
    sale=training_record(c,u,sale,'sale',cart['id'])
    c.execute("UPDATE pos_carts SET status='training-paid',revision=revision+1 WHERE id=?",(cart['id'],))
    # Deliberately do not call financial/inventory/loyalty/fulfillment hooks.
    return finish({'sale':sale},'TRAINING payment '+sale['id']+' (no money collected)')
