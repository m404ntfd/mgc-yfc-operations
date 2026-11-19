"""Terminal printers, persistent limited customer displays and customer entry drafts."""

def devices_init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS retail_terminal_options(terminal TEXT PRIMARY KEY,revision INTEGER NOT NULL,printer TEXT NOT NULL,display_token TEXT NOT NULL UNIQUE,cart TEXT,sale TEXT,heartbeat REAL NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS retail_store_displays(store TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS retail_customer_requests(id TEXT PRIMARY KEY,terminal TEXT NOT NULL,owner TEXT NOT NULL,expires REAL NOT NULL,status TEXT NOT NULL,body TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS retail_removed_terminals(terminal TEXT PRIMARY KEY REFERENCES retail_terminals(id),at TEXT NOT NULL,actor TEXT NOT NULL,enabled INTEGER NOT NULL);
    ''')

def devices_removed(c,terminal):
    return c.execute('SELECT * FROM retail_removed_terminals WHERE terminal=?',(terminal,)).fetchone()

def devices_remove(c,u,d,finish):
    if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
    ident=pos_text(d.get('id'),'a terminal identifier',64)
    row=c.execute('SELECT * FROM retail_terminals WHERE id=?',(ident,)).fetchone()
    if not row:raise Problem('Terminal not found. Refresh the terminal list.',404)
    if d.get('revision')!=row['revision']:raise Problem('Terminal changed. Refresh the terminal list before removing it.',409)
    if devices_removed(c,row['id']):raise Problem('This terminal has already been removed.',409)
    if d.get('confirmed') is not True:raise Problem('Confirm removal of this terminal.')
    if c.execute('SELECT 1 FROM retail_drawers WHERE terminal=? AND closed IS NULL',(row['id'],)).fetchone():raise Problem('Close and reconcile this terminal’s cash drawer before removing it.',409)
    for record in c.execute("SELECT body FROM pos_carts WHERE status='open'"):
        cart=json.loads(record[0])
        linked=cart.get('terminal_id')==row['id'] or (row['device'] and cart.get('device')==row['device']) or (not cart.get('terminal_id') and cart.get('terminal')==row['name'])
        if linked:raise Problem('Complete or cancel this terminal’s open and saved sales before removing it.',409)
    # Keep the terminal and every historical relationship. Removal is an audited
    # registration state, not deletion of sales, settings, or computer inventory.
    c.execute('INSERT INTO retail_removed_terminals VALUES(?,?,?,?)',(row['id'],dt.datetime.now().astimezone().isoformat(timespec='seconds'),u['name'],row['enabled']))
    c.execute('UPDATE retail_terminals SET enabled=0,revision=revision+1 WHERE id=?',(row['id'],))
    return finish({'ok':True,'id':row['id'],'revision':row['revision']+1},'Removed terminal '+row['name']+' ('+row['id']+'); history retained') or True

def devices_restore(c,u,d,finish):
    if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
    ident=pos_text(d.get('id'),'a terminal identifier',64)
    row=c.execute('SELECT * FROM retail_terminals WHERE id=?',(ident,)).fetchone()
    removed=devices_removed(c,ident)
    if not row or not removed:raise Problem('Removed terminal not found. Refresh the terminal list.',409)
    if d.get('revision')!=row['revision']:raise Problem('Terminal changed. Refresh the terminal list before restoring it.',409)
    if d.get('confirmed') is not True:raise Problem('Confirm restoration of this terminal.')
    c.execute('UPDATE retail_terminals SET enabled=?,revision=revision+1 WHERE id=?',(removed['enabled'],row['id']))
    c.execute('DELETE FROM retail_removed_terminals WHERE terminal=?',(row['id'],))
    return finish({'ok':True,'id':row['id'],'revision':row['revision']+1},'Restored terminal '+row['name']+' ('+row['id']+')') or True

def devices_terminal(c,u,d,manage=False):
    if manage and not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
    if d.get('terminal'):
        if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
        row=c.execute('SELECT * FROM retail_terminals WHERE id=?',(d['terminal'],)).fetchone()
        terminal=stores_terminal_details(c,row)
    else:terminal=stores_terminal_details(c,stores_terminal(c,d.get('device')))
    if not terminal or not terminal['enabled']:raise Problem('Register this checkout with an enabled terminal first.',409)
    return terminal

def devices_options(c,terminal):
    row=c.execute('SELECT * FROM retail_terminal_options WHERE terminal=?',(terminal['id'],)).fetchone()
    return dict(row) if row else dict(terminal=terminal['id'],revision=0,printer='',display_token='',cart=None,sale=None,heartbeat=0)

def devices_display_settings(c,store):
    profile=stores_profile(c,store);row=c.execute('SELECT * FROM retail_store_displays WHERE store=?',(profile['id'],)).fetchone()
    body=json.loads(row['body']) if row else customer_settings(c,'display')
    return dict(body,revision=row['revision'] if row else 0,store_id=profile['id'],store=profile['name'],logo=profile['receipt'].get('logo',''))

def devices_get(c,u,path,q):
    d={k:v[0] for k,v in q.items()}
    if path=='terminal-options':
        terminal=devices_terminal(c,u,d);options=devices_options(c,terminal)
        return dict(terminal=terminal,revision=options['revision'],printer=options['printer'],display_path='/customer-display#'+options['display_token'] if options['display_token'] else '')
    if path=='store-display':
        if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
        return devices_display_settings(c,d.get('store_id','thrift-mart'))
    if path=='customer-entry':
        terminal=devices_terminal(c,u,d)
        row=c.execute('SELECT * FROM retail_customer_requests WHERE id=? AND owner=? AND terminal=?',(d.get('id'),u['receipt_owner'],terminal['id'])).fetchone()
        if not row or row['expires']<time.time():raise Problem('Customer entry expired. Start a new request.',404)
        return dict(id=row['id'],status=row['status'],details=json.loads(row['body']) if row['status']=='submitted' else {})
    return None

def devices_post(handler,c,u,path,d,finish):
    if path=='terminal-remove':return devices_remove(c,u,d,finish)
    if path=='terminal-restore':return devices_restore(c,u,d,finish)
    if path=='terminal-options-save':
        terminal=devices_terminal(c,u,d,True);old=devices_options(c,terminal)
        if d.get('revision')!=old['revision']:raise Problem('Terminal settings changed. Reopen them before saving.',409)
        printer=d.get('printer','')
        if not isinstance(printer,str) or len(printer)>200 or any(ord(x)<32 for x in printer):raise Problem('Choose a valid Windows receipt printer name.')
        token=secrets.token_urlsafe(32) if d.get('replace_display') or not old['display_token'] else old['display_token']
        c.execute('INSERT INTO retail_terminal_options(terminal,revision,printer,display_token) VALUES(?,?,?,?) ON CONFLICT(terminal) DO UPDATE SET revision=excluded.revision,printer=excluded.printer,display_token=excluded.display_token,cart=NULL,sale=NULL,heartbeat=0',(terminal['id'],old['revision']+1,printer,token))
        return finish({'ok':True},'Configured receipt printer and customer display for '+terminal['name']) or True
    if path=='store-display-save':
        if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
        old=devices_display_settings(c,d.get('store_id','thrift-mart'))
        if d.get('revision')!=old['revision']:raise Problem('Display settings changed. Reopen them before saving.',409)
        if type(d.get('enabled')) is not bool:raise Problem('Choose whether this store display is enabled.')
        body=dict(enabled=d['enabled'],welcome=pos_text(d.get('welcome'),'a welcome message',200),thanks=pos_text(d.get('thanks'),'a thank-you message',200))
        c.execute('INSERT INTO retail_store_displays VALUES(?,?,?) ON CONFLICT(store) DO UPDATE SET revision=excluded.revision,body=excluded.body',(old['store_id'],old['revision']+1,json.dumps(body)))
        return finish({'ok':True},'Configured customer display for '+old['store']) or True
    if path in ('customer-entry-start','customer-entry-close'):
        # Abandoned entry forms are drafts, not permanent customer records.
        c.execute("UPDATE retail_customer_requests SET status='expired',body='{}' WHERE expires<? AND status IN ('open','submitted')",(time.time(),))
        terminal=devices_terminal(c,u,d);options=devices_options(c,terminal)
        if not options['display_token'] or not devices_display_settings(c,terminal['store_id'])['enabled']:raise Problem('Enable this store’s customer display and assign its link in Terminal setup first.')
        if path=='customer-entry-close':
            c.execute("UPDATE retail_customer_requests SET status='closed',body='{}' WHERE id=? AND owner=? AND terminal=?",(d.get('id'),u['receipt_owner'],terminal['id']))
            return finish({'ok':True},'Closed customer entry') or True
        c.execute("UPDATE retail_customer_requests SET status='closed',body='{}' WHERE terminal=?",(terminal['id'],))
        ident=secrets.token_urlsafe(24)
        c.execute('INSERT INTO retail_customer_requests VALUES(?,?,?,?,?,?)',(ident,terminal['id'],u['receipt_owner'],time.time()+600,'open','{}'))
        return finish({'id':ident,'path':'/customer-display#'+options['display_token']},'Started customer entry on '+terminal['name']) or True
    return None

def devices_display_state(handler,c,u,d):
    token=d.get('token','');row=c.execute('SELECT * FROM retail_terminal_options WHERE display_token=?',(token,)).fetchone()
    if not row:return False
    terminal=devices_terminal(c,u,d)
    if row['terminal']!=terminal['id']:raise Problem('This customer display belongs to another register.',403)
    cart=d.get('cart');sale=d.get('sale')
    if cart:
        cr=c.execute('SELECT * FROM pos_carts WHERE id=? AND owner=?',(cart,u['receipt_owner'])).fetchone()
        if not cr or pos_cart(cr).get('terminal_id')!=terminal['id']:raise Problem('Transaction belongs to another register.',403)
    if sale:
        practice=str(sale).startswith('T');sr=c.execute('SELECT body FROM '+('retail_training_transactions' if practice else 'pos_sales')+' WHERE id=?',(str(sale)[1:] if practice else sale,)).fetchone()
        if not sr or json.loads(sr[0]).get('terminal_id')!=terminal['id']:raise Problem('Receipt belongs to another register.',403)
    customer_prompt_state(c,token,cart,d)
    c.execute('UPDATE retail_terminal_options SET cart=?,sale=?,heartbeat=? WHERE terminal=?',(cart,str(sale) if sale else None,time.time(),terminal['id']))
    c.commit();handler.send({'ok':True});return True

def devices_display(c,token):
    row=c.execute('SELECT * FROM retail_terminal_options WHERE display_token=?',(token,)).fetchone()
    if not row:return None
    terminal=stores_terminal_details(c,c.execute('SELECT * FROM retail_terminals WHERE id=?',(row['terminal'],)).fetchone())
    if not terminal or not terminal['enabled']:raise Problem('Display disabled.',404)
    settings=devices_display_settings(c,terminal['store_id'])
    if not settings['enabled']:raise Problem('Customer display is disabled for this store.',404)
    result=dict(state='idle',welcome=settings['welcome'],thanks=settings['thanks'],store=settings['store'],logo=settings['logo'],training=False)
    request=c.execute("SELECT * FROM retail_customer_requests WHERE terminal=? AND status IN ('open','submitted') AND expires>? ORDER BY expires DESC LIMIT 1",(terminal['id'],time.time())).fetchone()
    if request:
        result['entry']={'id':request['id'],'status':request['status']};return result
    if time.time()-row['heartbeat']>30:return result
    data=None
    if row['sale']:
        practice=row['sale'].startswith('T');sr=c.execute('SELECT body FROM '+('retail_training_transactions' if practice else 'pos_sales')+' WHERE id=?',(row['sale'][1:] if practice else row['sale'],)).fetchone()
        if sr:
            data=json.loads(sr[0])
            if stores_id(data)==terminal['store_id'] and time.time()-dt.datetime.fromisoformat(data['at']).timestamp()<20:result.update(state='paid',total=data['total'],change=data.get('change',0),training=bool(data.get('training')))
        return result
    cr=c.execute("SELECT * FROM pos_carts WHERE id=? AND status='open'",(row['cart'],)).fetchone()
    if cr:
        data=pos_cart(cr)
        if not data.get('held') and stores_id(data)==terminal['store_id']:
            result.update(state='sale',training=bool(data.get('training')),lines=[{k:l.get(k) for k in ('name','quantity','subtotal','weight_milli','price_per_lb')} for l in data['lines']],subtotal=data['subtotal'],tax=data['tax'],total=data['total'])
            if data.get('adjustment'):result['adjustment']={k:data['adjustment'][k] for k in ('mode','amount')}
            result['roundup']=customer_prompt(c,token,data)
    return result

def devices_customer_submit(c,token,d):
    row=c.execute('SELECT * FROM retail_terminal_options WHERE display_token=?',(token,)).fetchone()
    if not row:raise Problem('Display unavailable.',404)
    request=c.execute("SELECT * FROM retail_customer_requests WHERE id=? AND terminal=? AND expires>?",(d.get('id'),row['terminal'],time.time())).fetchone()
    if not request or request['status'] not in ('open','submitted'):raise Problem('This entry request expired or was closed.',409)
    if request['status']=='submitted':return {'ok':True}
    settings=devices_display(c,token)
    if not settings:raise Problem('Display unavailable.',404)
    name=pos_text(d.get('name'),'your name',120);phone=d.get('phone','').strip();email=d.get('email','').strip()
    if phone:
        digits=re.sub(r'\D','',phone)
        if len(digits)==11 and digits[0]=='1':digits=digits[1:]
        if len(digits)!=10:raise Problem('Enter a phone number including the area code.')
        phone='('+digits[:3]+') '+digits[3:6]+'-'+digits[6:]
    if email:email=customer_email(email)
    if type(d.get('marketing',False)) is not bool:raise Problem('Choose a contact preference.')
    details=dict(name=name,phone=phone,email=email,contact=' · '.join(x for x in (phone,email) if x),marketing=d.get('marketing',False))
    if len(details['contact'])>200:raise Problem('Contact details are too long.')
    c.execute("UPDATE retail_customer_requests SET status='submitted',body=? WHERE id=?",(json.dumps(details),request['id']));c.commit()
    return {'ok':True}
