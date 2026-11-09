"""Store separation and optional programs. Embedded for legacy server updates.

Legacy records have an implicit thrift-mart scope; no historical row is rewritten.
Currency is integer cents and entered pounds are integer thousandths.
"""
def stores_init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS retail_stores(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS retail_terminal_stores(terminal TEXT PRIMARY KEY,store TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS retail_programs(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS retail_point_allocations(point INTEGER NOT NULL,store TEXT NOT NULL,amount INTEGER NOT NULL,PRIMARY KEY(point,store));
CREATE TABLE IF NOT EXISTS retail_reward_sources(sale INTEGER NOT NULL,store TEXT NOT NULL,earned INTEGER NOT NULL,redeemed INTEGER NOT NULL,PRIMARY KEY(sale,store));
CREATE TRIGGER IF NOT EXISTS retail_point_allocations_no_update BEFORE UPDATE ON retail_point_allocations BEGIN SELECT RAISE(ABORT,'Reward allocations are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_point_allocations_no_delete BEFORE DELETE ON retail_point_allocations BEGIN SELECT RAISE(ABORT,'Reward allocations are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_reward_sources_no_update BEFORE UPDATE ON retail_reward_sources BEGIN SELECT RAISE(ABORT,'Reward sources are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_reward_sources_no_delete BEFORE DELETE ON retail_reward_sources BEGIN SELECT RAISE(ABORT,'Reward sources are immutable'); END;
CREATE TABLE IF NOT EXISTS retail_members(customer INTEGER PRIMARY KEY,card TEXT UNIQUE,birthday TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS retail_birthdays(customer INTEGER NOT NULL,store TEXT NOT NULL,year INTEGER NOT NULL,sale INTEGER NOT NULL,PRIMARY KEY(customer,store,year));
CREATE TABLE IF NOT EXISTS retail_gifts(account INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,store TEXT NOT NULL,sale INTEGER NOT NULL,amount INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS retail_drawers(id INTEGER PRIMARY KEY,terminal TEXT NOT NULL,store TEXT NOT NULL,opened TEXT NOT NULL,actor TEXT NOT NULL,opening INTEGER NOT NULL,closed TEXT,body TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS retail_drawer_open ON retail_drawers(terminal) WHERE closed IS NULL;
CREATE TABLE IF NOT EXISTS retail_drawer_events(id INTEGER PRIMARY KEY,drawer INTEGER NOT NULL,at TEXT NOT NULL,actor TEXT NOT NULL,amount INTEGER NOT NULL,reason TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS retail_drawer_events_no_update BEFORE UPDATE ON retail_drawer_events BEGIN SELECT RAISE(ABORT,'Cash history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_drawer_events_no_delete BEFORE DELETE ON retail_drawer_events BEGIN SELECT RAISE(ABORT,'Cash history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_drawer_closed_update BEFORE UPDATE ON retail_drawers WHEN OLD.closed IS NOT NULL BEGIN SELECT RAISE(ABORT,'Closed cash counts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_drawer_no_delete BEFORE DELETE ON retail_drawers BEGIN SELECT RAISE(ABORT,'Cash counts are immutable'); END;
''')

def stores_programs(c):
    row=c.execute('SELECT * FROM retail_programs WHERE id=1').fetchone()
    defaults=dict(drawers=False,gifts=False,membership=False,birthdays=False,birthday_cents=500,loyalty_scope='shared')
    return dict(defaults,**(json.loads(row['body']) if row else {}),revision=row['revision'] if row else 0)

def stores_id(body):return body.get('store_id','thrift-mart')

def stores_profile(c,ident='thrift-mart'):
    row=c.execute('SELECT * FROM retail_stores WHERE id=?',(ident,)).fetchone()
    if row:return dict(json.loads(row['body']),id=ident,revision=row['revision'])
    if ident not in ('thrift-mart','binopoly'):raise Problem('Store not found.',404)
    legacy=pos_settings(c)
    return dict(id=ident,revision=0,name=(legacy.get('store') or 'Thrift Mart') if ident=='thrift-mart' else 'Binopoly',tax_bps=legacy['tax_bps'] if ident=='thrift-mart' else None,receipt=customer_settings(c,'receipt') if ident=='thrift-mart' else dict(CUSTOMER_DEFAULTS['receipt']))

def stores_list(c):
    ids=['thrift-mart','binopoly']+[r[0] for r in c.execute("SELECT id FROM retail_stores WHERE id NOT IN ('thrift-mart','binopoly') ORDER BY id")]
    return [stores_profile(c,i) for i in ids]

def stores_terminal(c,device):
    r=c.execute('SELECT t.*,s.store AS store_id FROM retail_terminals t LEFT JOIN retail_terminal_stores s ON s.terminal=t.id WHERE t.device=?',(device or '',)).fetchone()
    return dict(r,store_id=r['store_id'] or 'thrift-mart') if r else None

def stores_context(c,u,d):
    terminal=stores_terminal(c,d.get('device'))
    if terminal:
        if not terminal['enabled']:raise Problem('This terminal is disabled.',403)
        return terminal['store_id'],terminal
    ident=d.get('store_id') or 'thrift-mart'
    stores_profile(c,ident)
    if ident!='thrift-mart' and not has_permission(u,'manage_pos'):raise Problem('Register this computer to a store in OFFICE first.',403)
    return ident,None

def stores_settings(c,ident):
    p=stores_profile(c,ident)
    return dict(pos_settings(c),store=p['name'],tax_bps=p['tax_bps'],store_id=ident)

def stores_point_balance(c,customer,store,exclude=None):
    total=0
    for r in c.execute('SELECT p.id,p.amount,s.body FROM thrift_points p LEFT JOIN pos_sales s ON s.id=p.sale WHERE p.customer=?',(customer,)):
        if r['id']==exclude:continue
        parts=c.execute('SELECT store,amount FROM retail_point_allocations WHERE point=?',(r['id'],)).fetchall()
        if parts:total+=sum(p['amount'] for p in parts if p['store']==store)
        elif stores_id(json.loads(r['body']) if r['body'] else {})==store:total+=r['amount']
    return total

def stores_points(c,customer,store):
    if stores_programs(c)['loyalty_scope']=='shared':return c.execute('SELECT COALESCE(SUM(amount),0) FROM thrift_points WHERE customer=?',(customer,)).fetchone()[0]
    return stores_point_balance(c,customer,store)

def stores_reward_allocate(c,sale,ident):
    point=c.execute('SELECT id FROM thrift_points WHERE sale=? AND refund IS NULL',(ident,)).fetchone()
    if not point:return
    store=stores_id(sale);earned=sale.get('loyalty_earned',0);redeemed=sale.get('reward',{}).get('points',0)
    sources={store:[earned,0]};remaining=redeemed
    candidates=[store]+[s['id'] for s in stores_list(c) if s['id']!=store] if stores_programs(c)['loyalty_scope']=='shared' else [store]
    for sid in candidates:
        take=min(remaining,max(0,stores_point_balance(c,sale['customer'],sid,point[0])))
        if take:sources.setdefault(sid,[0,0])[1]+=take;remaining-=take
    if remaining:raise Problem('Reward sources changed. Remove and reapply the reward.',409)
    for sid,(earn,spend) in sources.items():
        c.execute('INSERT INTO retail_reward_sources VALUES(?,?,?,?)',(ident,sid,earn,spend))
        c.execute('INSERT INTO retail_point_allocations VALUES(?,?,?)',(point[0],sid,earn-spend))

def stores_reward_refund(c,result,refund):
    point=c.execute('SELECT id,amount FROM thrift_points WHERE refund=?',(refund,)).fetchone()
    sources=c.execute('SELECT * FROM retail_reward_sources WHERE sale=? ORDER BY store',(result['sale'],)).fetchall()
    if not point or not sources:return
    sale=json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(result['sale'],)).fetchone()[0])
    returned=sum(r['subtotal'] for r in retail_refund_state(c,result['sale']))
    merchandise=sum(l['subtotal'] for l in sale['lines'] if not l.get('donation') and not l.get('gift_certificate'))
    earned=sale.get('loyalty_earned',0);redeemed=sale.get('reward',{}).get('points',0)
    reversal=earned-min(earned,max(0,merchandise-returned)//sale.get('loyalty_earn_cents',100))
    restored=redeemed if returned>=merchandise else redeemed*returned//max(1,merchandise)
    shares=retail_allocate(restored,[s['redeemed'] for s in sources]) if restored else [0]*len(sources)
    total=0
    for source,share in zip(sources,shares):
        target=share-(reversal if source['store']==stores_id(sale) else 0)
        prior=c.execute('SELECT COALESCE(SUM(a.amount),0) FROM retail_point_allocations a JOIN thrift_points p ON p.id=a.point WHERE p.sale=? AND p.refund IS NOT NULL AND p.id<>? AND a.store=?',(result['sale'],point[0],source['store'])).fetchone()[0]
        amount=target-prior;total+=amount
        c.execute('INSERT INTO retail_point_allocations VALUES(?,?,?)',(point[0],source['store'],amount))
    if total!=point['amount']:raise Problem('Reward return allocations need review.',409)

def stores_weight(value):
    if not isinstance(value,str) or not re.fullmatch(r'(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,3})?',value):raise Problem('Enter pounds with up to three decimal places.')
    whole,_,fraction=value.partition('.')
    return pos_int(int(whole)*1000+int((fraction+'000')[:3]),'weight in pounds',1,9999999)

def stores_weight_line(c,cart,d):
    ident=pos_text(d.get('product'),'an item identifier',32);row=c.execute('SELECT * FROM pos_products WHERE id=?',(ident,)).fetchone()
    if not row:raise Problem('Product not found.',404)
    p=retail_product(c,row);rule=p['rules']
    if rule.get('store_id','thrift-mart')!=stores_id(cart):raise Problem('This product belongs to another store.')
    if not rule.get('sold_by_weight'):return None
    if d.get('quantity')!=1 or d.get('choices') or d.get('open_price') is not None:raise Problem('Weighed items use one entered weight and their configured price per pound.')
    if not retail_available(rule):raise Problem('Product is not available.',409)
    weight=stores_weight(d.get('weight'));rate=p['display_price'];amount=(weight*rate+500)//1000
    if not 1<=amount<=10000000:raise Problem('The calculated price must be between $0.01 and $100,000.')
    return dict(pickup_slip=rule.get('pickup_slip',False),product=ident,name=p['name'],category=p['category'],taxable=p['taxable'],price=amount,quantity=1,subtotal=amount,tax=(amount*cart['settings']['tax_bps']+5000)//10000 if p['taxable'] else 0,weight_milli=weight,weight_unit='lb',price_per_lb=rate,weight_source='manual',modifiers=[],print_category=rule.get('print_category',''))

def stores_drawer(c,ident):
    row=c.execute('SELECT * FROM retail_drawers WHERE id=?',(ident,)).fetchone()
    if not row:raise Problem('Cash drawer not found.',404)
    d=dict(row);d.update(json.loads(d.pop('body')))
    if d['closed']:return d
    sales=[json.loads(r[0]) for r in c.execute('SELECT body FROM pos_sales')]
    refunds=[json.loads(r[0]) for r in c.execute('SELECT body FROM retail_refunds')]
    d['cash_sales']=sum(s.get('cash_paid',s['tender']-s['change']) for s in sales if s.get('drawer_id')==ident)
    d['cash_refunds']=sum(r['cash'] for r in refunds if r.get('drawer_id')==ident)
    d['movements']=sum(r[0] for r in c.execute('SELECT amount FROM retail_drawer_events WHERE drawer=?',(ident,)))
    d['expected']=d['opening']+d['cash_sales']-d['cash_refunds']+d['movements']
    return d

def stores_donations(sales):
    eligible=[s for s in sales if any(not l.get('donation') and not l.get('gift_certificate') for l in s['lines'])]
    giving=[s for s in eligible if any(l.get('donation') and l['subtotal']>0 for l in s['lines'])]
    total=sum(l['subtotal'] for s in sales for l in s['lines'] if l.get('donation'))
    return dict(total=total,transactions=len(eligible),donors=len(giving),participation=round(100*len(giving)/len(eligible),1) if eligible else None,average=(total+len(giving)//2)//len(giving) if giving else None,per_thousand=(total*1000+len(eligible)//2)//len(eligible) if eligible else None)

def stores_get(c,u,path,q):
    if path=='stores':return dict(stores=stores_list(c),programs=stores_programs(c),terminals=retail_config(c)['terminals'],assignments=dict(c.execute('SELECT terminal,store FROM retail_terminal_stores').fetchall()))
    if path=='programs':return dict(programs=stores_programs(c))
    if path=='membership-scan':
        if not stores_programs(c)['membership']:raise Problem('Membership cards are disabled in OFFICE.')
        r=c.execute('SELECT customer FROM retail_members WHERE card=?',(q.get('code',[''])[0].strip(),)).fetchone()
        if not r:raise Problem('Membership card not found.',404)
        return dict(customer=thrift_customer(c,r[0],q.get('store_id',['thrift-mart'])[0]))
    if path=='member':
        thrift_require(u,'manage_pos')
        ident=pos_int(int(q.get('id',['0'])[0]),'customer',1)
        thrift_customer(c,ident)
        r=c.execute('SELECT * FROM retail_members WHERE customer=?',(ident,)).fetchone()
        return dict(member=dict(r) if r else dict(customer=ident,card='',birthday=''),previous=dict(r) if r else None)
    if path=='drawers':
        thrift_require(u,'view_pos_sales')
        return dict(enabled=stores_programs(c)['drawers'],drawers=[stores_drawer(c,r[0]) for r in c.execute('SELECT id FROM retail_drawers ORDER BY id DESC LIMIT 200')])
    if path=='gifts':
        pos_credit_access(u,True)
        return dict(enabled=stores_programs(c)['gifts'],gifts=[dict(r,balance=pos_credit_account(c,r['account'])['balance']) for r in c.execute('SELECT * FROM retail_gifts ORDER BY account DESC')])
    return None

def stores_post(c,u,path,d,finish):
    if path=='store-save':
        thrift_require(u,'manage_pos');ident=pos_text(d.get('id'),'store ID',40);old=stores_profile(c,ident)
        if d.get('revision')!=old['revision']:raise Problem('Store settings changed. Reopen before saving.',409)
        tax=pos_int(d.get('tax_bps'),'tax rate',0,10000)
        if d.get('confirmed') is not True:raise Problem('Confirm this store’s tax rate.')
        receipt=d.get('receipt',{})
        clean={k:customer_text(receipt.get(k,''),k) for k in ('address','phone','footer','policy')}
        logo=receipt.get('logo','')
        if logo and (not isinstance(logo,str) or len(logo)>280000 or not re.fullmatch(r'data:image/(png|jpeg);base64,[A-Za-z0-9+/=]+',logo)):raise Problem('Use a PNG or JPEG logo up to 200 KB.')
        if logo:
            try:raw=base64.b64decode(logo.split(',')[1],validate=True)
            except (ValueError,TypeError):raise Problem('Invalid receipt logo.')
            if len(raw)>200000 or not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):raise Problem('Invalid receipt logo.')
        clean['logo']=logo
        body=dict(name=pos_text(d.get('name'),'store name'),tax_bps=tax,receipt=clean)
        c.execute('INSERT INTO retail_stores VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(ident,old['revision']+1,json.dumps(body)))
        return finish(dict(store=stores_profile(c,ident)),'Store profile saved: '+ident)
    if path=='store-terminal':
        thrift_require(u,'manage_pos');ident=pos_text(d.get('terminal'),'terminal');store=stores_profile(c,d.get('store_id'))['id']
        terminal=c.execute('SELECT * FROM retail_terminals WHERE id=?',(ident,)).fetchone()
        if not terminal:raise Problem('Register this terminal first.')
        current=c.execute('SELECT store FROM retail_terminal_stores WHERE terminal=?',(ident,)).fetchone();current=current[0] if current else 'thrift-mart'
        if d.get('previous')!=current:raise Problem('Assignment changed. Reopen before saving.',409)
        if c.execute('SELECT 1 FROM retail_drawers WHERE terminal=? AND closed IS NULL',(ident,)).fetchone():raise Problem('Close this terminal’s cash drawer before reassigning it.')
        if any(json.loads(r[0]).get('terminal')==terminal['name'] for r in c.execute("SELECT body FROM pos_carts WHERE status='open'")):raise Problem('Complete or cancel this terminal’s saved sales before reassigning it.')
        c.execute('INSERT INTO retail_terminal_stores VALUES(?,?) ON CONFLICT(terminal) DO UPDATE SET store=excluded.store',(ident,store))
        return finish(dict(ok=True),'Terminal store assigned')
    if path=='programs-save':
        thrift_require(u,'manage_pos');old=stores_programs(c)
        if d.get('revision')!=old['revision']:raise Problem('Program settings changed. Reopen before saving.',409)
        body={}
        for k in ('drawers','gifts','membership','birthdays'):
            if type(d.get(k)) is not bool:raise Problem('Choose '+k+' status.')
            body[k]=d[k]
        if not body['drawers'] and c.execute('SELECT 1 FROM retail_drawers WHERE closed IS NULL').fetchone():raise Problem('Close open cash drawers before disabling reconciliation.')
        if d.get('loyalty_scope') not in ('shared','store'):raise Problem('Choose loyalty scope.')
        body.update(loyalty_scope=d['loyalty_scope'],birthday_cents=pos_int(d.get('birthday_cents'),'birthday reward',1,100000))
        if body['loyalty_scope']!=old['loyalty_scope'] and any(json.loads(r[0]).get('reward') for r in c.execute("SELECT body FROM pos_carts WHERE status='open'")):raise Problem('Complete or remove rewards on saved sales before changing loyalty scope.')
        c.execute('INSERT INTO retail_programs VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(old['revision']+1,json.dumps(body)))
        return finish(dict(programs=stores_programs(c)),'Optional retail programs saved')
    if path=='member-save':
        thrift_require(u,'manage_pos');customer=pos_int(d.get('customer'),'customer',1);thrift_customer(c,customer)
        settings=stores_programs(c);card=d.get('card','').strip();birthday=d.get('birthday','')
        if card and (not settings['membership'] or not re.fullmatch(r'[0-9]{8,20}',card)):raise Problem('Enable membership cards and enter an 8–20 digit card number.')
        if birthday:
            if not settings['birthdays']:raise Problem('Birthday rewards are disabled.')
            try:dt.date.fromisoformat('2000-'+birthday)
            except (ValueError,TypeError):raise Problem('Enter birthday as MM-DD. No birth year is needed.')
        old=c.execute('SELECT * FROM retail_members WHERE customer=?',(customer,)).fetchone()
        if d.get('previous')!=(dict(old) if old else None):raise Problem('Member details changed. Reopen before saving.',409)
        if card and c.execute('SELECT 1 FROM retail_members WHERE card=? AND customer<>?',(card,customer)).fetchone():raise Problem('This card belongs to another customer.')
        c.execute('INSERT INTO retail_members VALUES(?,?,?) ON CONFLICT(customer) DO UPDATE SET card=excluded.card,birthday=excluded.birthday',(customer,card or None,birthday))
        return finish(dict(ok=True),'Membership details saved')
    if path in ('drawer-open','drawer-move','drawer-close'):
        thrift_require(u,'manage_pos')
        if not stores_programs(c)['drawers']:raise Problem('Cash-drawer reconciliation is disabled in OFFICE.')
        now=dt.datetime.now().astimezone().isoformat(timespec='seconds')
        if path=='drawer-open':
            t=c.execute('SELECT * FROM retail_terminals WHERE id=?',(d.get('terminal'),)).fetchone()
            if not t or not t['enabled']:raise Problem('Choose an enabled terminal.')
            if c.execute('SELECT 1 FROM retail_drawers WHERE terminal=? AND closed IS NULL',(t['id'],)).fetchone():raise Problem('This terminal already has an open drawer.',409)
            s=c.execute('SELECT store FROM retail_terminal_stores WHERE terminal=?',(t['id'],)).fetchone()
            ident=c.execute('INSERT INTO retail_drawers(terminal,store,opened,actor,opening,body) VALUES(?,?,?,?,?,?)',(t['id'],s[0] if s else 'thrift-mart',now,u['name'],pos_int(d.get('opening'),'opening cash'),json.dumps(dict(terminal_name=t['name'])))).lastrowid
        else:
            ident=pos_int(d.get('id'),'drawer',1);drawer=stores_drawer(c,ident)
            if drawer['closed']:raise Problem('This drawer is already closed.',409)
            reason=pos_text(d.get('reason'),'cash movement or count note',300)
            if path=='drawer-move':
                amount=pos_int(d.get('amount'),'cash movement',1)
                if d.get('direction') not in ('in','out'):raise Problem('Choose cash in or cash out.')
                amount*=1 if d['direction']=='in' else -1
                if drawer['expected']+amount<0:raise Problem('Cash out exceeds expected drawer cash.')
                c.execute('INSERT INTO retail_drawer_events(drawer,at,actor,amount,reason) VALUES(?,?,?,?,?)',(ident,now,u['name'],amount,reason))
            else:
                counted=pos_int(d.get('counted'),'counted cash')
                if d.get('expected')!=drawer['expected']:raise Problem('Drawer activity changed. Refresh before closing.',409)
                body={k:v for k,v in drawer.items() if k not in ('id','terminal','store','opened','actor','opening','closed')}
                body.update(counted=counted,variance=counted-drawer['expected'],closed_by=u['name'],note=reason)
                c.execute('UPDATE retail_drawers SET closed=?,body=? WHERE id=?',(now,json.dumps(body),ident))
        return finish(dict(drawer=stores_drawer(c,ident)),'Cash drawer '+path)
    raise Problem('Unknown store action.')

def stores_cart_action(c,u,cart,path,d,finish):
    settings=stores_programs(c)
    if cart.get('reward') or cart.get('adjustment'):raise Problem('Remove existing rewards or adjustments first.')
    if path=='gift-add':
        if not settings['gifts']:raise Problem('Gift certificate sales are disabled in OFFICE.')
        if len(cart['lines'])>=100:raise Problem('Maximum 100 lines per cart.')
        amount=pos_int(d.get('amount'),'gift certificate value',1,1000000)
        code='GC'+secrets.token_hex(8).upper()
        cart['lines'].append(dict(name='Gift certificate '+code,category='Gift certificates',quantity=1,price=amount,subtotal=amount,tax=0,taxable=False,gift_certificate=code))
    elif path=='birthday-reward':
        if not settings['birthdays'] or not cart.get('customer'):raise Problem('Enable birthday rewards and select a customer first.')
        today=dt.date.today();member=c.execute('SELECT birthday FROM retail_members WHERE customer=?',(cart['customer'],)).fetchone()
        if not member or member[0]!=today.strftime('%m-%d'):raise Problem('This reward is available on the customer’s birthday.')
        scope='shared' if settings['loyalty_scope']=='shared' else stores_id(cart)
        if c.execute("SELECT 1 FROM retail_birthdays WHERE customer=? AND year=? AND (?='shared' OR store=? OR store='shared')",(cart['customer'],today.year,scope,scope)).fetchone():raise Problem('This year’s birthday reward has already been used.')
        targets=[l for l in cart['lines'] if not l.get('donation') and not l.get('gift_certificate') and not l.get('components') and not l.get('tag',{}).get('discount') and not l.get('promotion')]
        amount=min(settings['birthday_cents'],sum(l['subtotal'] for l in targets))
        if amount<=0:raise Problem('Add eligible full-price merchandise before applying the birthday reward.')
        cart['reward_original']=json.loads(json.dumps(cart['lines']))
        for line,part in zip(targets,retail_allocate(amount,[l['subtotal'] for l in targets])):
            line['subtotal']-=part;line['tax']=(line['subtotal']*cart['settings']['tax_bps']+5000)//10000 if line['taxable'] else 0
        cart['reward']=dict(points=0,amount=amount,birthday=True,scope=scope,year=today.year,loyalty_scope=settings['loyalty_scope'])
    retail_save_cart(c,cart)
    retail_event(c,cart['id'],u['name'],path,{})
    return finish(dict(cart=cart),'Optional retail sale updated')

def stores_sale_prepare(c,cart,path):
    p=stores_programs(c)
    gifts=any(l.get('gift_certificate') for l in cart['lines'])
    if gifts and (not p['gifts'] or path!='cash'):raise Problem('Gift certificates require cash payment and must be enabled in OFFICE.')
    if gifts and (cart.get('reward') or cart.get('adjustment')):raise Problem('Gift certificates cannot be discounted.')
    reward=cart.get('reward',{})
    if reward and reward.get('loyalty_scope',p['loyalty_scope'])!=p['loyalty_scope']:raise Problem('Loyalty scope changed. Remove and reapply the reward.')
    if reward.get('birthday'):
        member=c.execute('SELECT birthday FROM retail_members WHERE customer=?',(cart['customer'],)).fetchone()
        today=dt.date.today()
        if not p['birthdays'] or not member or member[0]!=today.strftime('%m-%d') or reward['year']!=today.year:raise Problem('Birthday reward is no longer eligible. Remove it before payment.')
        if c.execute("SELECT 1 FROM retail_birthdays WHERE customer=? AND year=? AND (?='shared' OR store=? OR store='shared')",(cart['customer'],today.year,reward['scope'],reward['scope'])).fetchone():raise Problem('Birthday reward already redeemed.',409)
    if p['drawers']:
        terminal=cart.get('terminal_id')
        row=c.execute('SELECT id FROM retail_drawers WHERE terminal=? AND closed IS NULL',(terminal,)).fetchone()
        if not row:raise Problem('Open this register’s cash drawer before completing sales.')
        cart['drawer_id']=row[0]

def stores_sale_saved(c,sale,ident):
    stores_reward_allocate(c,sale,ident)
    for line in sale['lines']:
        if not line.get('gift_certificate'):continue
        code=line['gift_certificate'];amount=line['subtotal']
        account=c.execute("INSERT INTO pos_credit_accounts(name,kind,contact) VALUES(?,'customer',?)",('Gift certificate '+code,code)).lastrowid
        c.execute('INSERT INTO retail_gifts VALUES(?,?,?,?,?)',(account,code,stores_id(sale),ident,amount))
        c.execute('INSERT INTO pos_credit_ledger(account,amount,balance,at,actor,reason,sale) VALUES(?,?,?,?,?,?,?)',(account,amount,amount,sale['at'],sale['cashier'],'Gift certificate purchased',ident))
    r=sale.get('reward',{})
    if r.get('birthday'):c.execute('INSERT INTO retail_birthdays VALUES(?,?,?,?)',(sale['customer'],r['scope'],r['year'],ident))

def stores_credit_check(c,account,cart):
    gift=c.execute('SELECT * FROM retail_gifts WHERE account=?',(account['id'],)).fetchone()
    if gift and gift['store']!=stores_id(cart):raise Problem('This gift certificate can only be redeemed at its issuing store.')
    if any(l.get('gift_certificate') for l in cart['lines']):raise Problem('Gift certificates cannot be purchased with store credit.')
    # Legacy account and assistance balances belong to Thrift Mart.
    if not gift and stores_id(cart)!='thrift-mart':raise Problem('This legacy store-credit account belongs to Thrift Mart.')

def stores_refund_drawer(c,result,d):
    if not result['cash'] or not stores_programs(c)['drawers']:return
    sale=json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(result['sale'],)).fetchone()[0])
    rows=c.execute('SELECT id FROM retail_drawers WHERE store=? AND closed IS NULL',(stores_id(sale),)).fetchall()
    ident=d.get('drawer_id') or (rows[0][0] if len(rows)==1 else None)
    if ident not in [r[0] for r in rows]:raise Problem('Choose an open cash drawer in the original store for this refund.')
    result['drawer_id']=ident
