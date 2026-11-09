"""Additive thrift workflows, embedded in server.py for legacy updaters.

All amounts are integer cents. Existing sales and credit ledgers stay immutable.
"""
def thrift_init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS thrift_settings(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS thrift_customers(id INTEGER PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS thrift_points(id INTEGER PRIMARY KEY,customer INTEGER NOT NULL REFERENCES thrift_customers(id),amount INTEGER NOT NULL,sale INTEGER,refund INTEGER,reason TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS thrift_points_sale ON thrift_points(sale) WHERE refund IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS thrift_points_refund ON thrift_points(refund) WHERE refund IS NOT NULL;
CREATE TABLE IF NOT EXISTS thrift_vouchers(account INTEGER PRIMARY KEY REFERENCES pos_credit_accounts(id),body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS thrift_pickups(sale INTEGER PRIMARY KEY REFERENCES pos_sales(id),revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS thrift_intake(id INTEGER PRIMARY KEY,product TEXT UNIQUE NOT NULL REFERENCES pos_products(id),received TEXT NOT NULL,tag TEXT NOT NULL,status TEXT NOT NULL,sale INTEGER,actor TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS thrift_points_no_update BEFORE UPDATE ON thrift_points BEGIN SELECT RAISE(ABORT,'Reward history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS thrift_points_no_delete BEFORE DELETE ON thrift_points BEGIN SELECT RAISE(ABORT,'Reward history is immutable'); END;
''')

def thrift_settings(c):
    row=c.execute('SELECT * FROM thrift_settings WHERE id=1').fetchone()
    return dict(json.loads(row['body']),revision=row['revision']) if row else dict(revision=0,tags=[],donations=False,loyalty=False,earn_cents=100,reward_points=100,reward_cents=500,stack_tags=False)

def thrift_require(u,permission):
    if not has_permission(u,permission):raise Problem('Required permission: '+permission.replace('_',' '),403)

def thrift_customer(c,ident,store='thrift-mart'):
    row=c.execute('SELECT * FROM thrift_customers WHERE id=?',(ident,)).fetchone()
    if not row:raise Problem('Customer not found.',404)
    points=stores_points(c,ident,store)
    return dict(id=ident,revision=row['revision'],points=points,**json.loads(row['body']))

def thrift_date(value,label,optional=True):
    if not value and optional:return ''
    try:return dt.date.fromisoformat(value).isoformat()
    except (ValueError,TypeError):raise Problem('Enter a valid '+label+'.')

def thrift_get(c,u,path,q):
    if path=='thrift-config':return {'settings':thrift_settings(c)}
    if path=='thrift-intake':
        thrift_require(u,'manage_pos')
        return {'items':[dict(r,code=str(100000000+r['id']),item=json.loads(r['body'])) for r in c.execute('SELECT i.*,p.body FROM thrift_intake i JOIN pos_products p ON p.id=i.product ORDER BY i.id DESC LIMIT 200')]}
    if path=='thrift-scan':
        code=q.get('code',[''])[0]
        if not re.fullmatch('[0-9]{9}',code):raise Problem('Enter a valid intake barcode.')
        row=c.execute('SELECT * FROM thrift_intake WHERE id=?',(int(code)-100000000,)).fetchone()
        if not row or row['status']!='available':raise Problem('This donated item is not available.',409)
        return {'product':row['product']}
    if path=='thrift-customers':
        search=q.get('search',[''])[0].strip().casefold()
        if len(search)<2:raise Problem('Enter at least two characters to find a customer.')
        matches=[]
        for row in c.execute('SELECT id FROM thrift_customers ORDER BY id DESC'):
            item=thrift_customer(c,row[0],q.get('store_id',['thrift-mart'])[0])
            if search in (str(item['id'])+' '+item['name']+' '+item['contact']).casefold():matches.append(item)
            if len(matches)==50:break
        return {'customers':matches}
    if path=='thrift-pickups':
        thrift_require(u,'view_pos_sales')
        return {'pickups':[dict(sale=r['sale'],revision=r['revision'],**json.loads(r['body'])) for r in c.execute('SELECT * FROM thrift_pickups ORDER BY sale DESC') if json.loads(r['body'])['status'] not in ('collected','delivered','canceled')]}
    if path=='thrift-reports':
        thrift_require(u,'view_pos_sales')
        start=thrift_date(q.get('from',[''])[0],'start date',False);end=thrift_date(q.get('to',[''])[0],'end date',False)
        if end<start:raise Problem('End date must follow start date.')
        colors={};donations=0;voucher_used=0;loyalty_discount=0
        for row in c.execute('SELECT id,body FROM pos_sales'):
            s=json.loads(row['body'])
            if not start<=s['at'][:10]<=end or (q.get('store_id',[''])[0] and stores_id(s)!=q['store_id'][0]):continue
            donations+=sum(l['subtotal'] for l in s['lines'] if l.get('donation'))
            voucher_used+=s.get('voucher_paid',0);loyalty_discount+=s.get('reward',{}).get('amount',0)
            for l in s['lines']:
                if l.get('tag'):
                    v=colors.setdefault(l['tag']['name'],[0,0,0]);v[0]+=l['quantity'];v[1]+=l['subtotal'];v[2]+=l['tag']['discount']
        for row in c.execute('SELECT sale,body FROM retail_refunds'):
            r=json.loads(row['body'])
            if not start<=r['at'][:10]<=end:continue
            s=json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(row['sale'],)).fetchone()[0])
            if q.get('store_id',[''])[0] and stores_id(s)!=q['store_id'][0]:continue
            if s.get('voucher_paid'):voucher_used-=r['store_credit']
            for l in r['lines']:
                old=s['lines'][l['index']]
                if old.get('tag'):
                    v=colors.setdefault(old['tag']['name'],[0,0,0]);v[0]-=l['quantity'];v[1]-=l['subtotal'];v[2]-=l.get('tag_discount',old['tag']['discount']*l['quantity']//old['quantity'])
        vouchers=[]
        for r in c.execute('SELECT * FROM thrift_vouchers'):
            a=pos_credit_account(c,r['account']);vouchers.append(dict(code=a['code'],name=a['name'],balance=a['balance'],**json.loads(r['body'])))
        return {'from':start,'to':end,'colors':colors,'donations':donations,'voucher_used':voucher_used,'loyalty_discount':loyalty_discount,'vouchers':vouchers,'pickups':thrift_get(c,u,'thrift-pickups',{})['pickups'],'note':'Sales and returns use their posting dates. Voucher balances and outstanding pickups are current. Reward discounts are issued amounts before returns.'}
    return None

def thrift_post(c,u,path,d,finish):
    if path=='thrift-intake-create':
        thrift_require(u,'manage_pos')
        tag=pos_text(d.get('tag'),'a tag color',40)
        if not any(t['name']==tag for t in thrift_settings(c)['tags']):raise Problem('Choose a configured tag color.')
        item=dict(name=pos_text(d.get('name'),'an item name'),category=pos_text(d.get('category'),'a category',60),price=pos_int(d.get('price'),'price',1),taxable=d.get('taxable'))
        if type(item['taxable']) is not bool:raise Problem('Choose tax status.')
        product=secrets.token_hex(16);c.execute('INSERT INTO pos_products VALUES(?,?)',(product,json.dumps(item)))
        ident=c.execute("INSERT INTO thrift_intake(product,received,tag,status,actor) VALUES(?,?,?,'available',?)",(product,dt.date.today().isoformat(),tag,u['name'])).lastrowid
        return finish({'item':dict(id=ident,product=product,code=str(100000000+ident),tag=tag,**item)},'Donated item priced and tagged')
    if path=='thrift-intake-restock':
        thrift_require(u,'manage_pos');ident=pos_int(d.get('id'),'intake item',1);reason=pos_text(d.get('reason'),'restock reason',200)
        row=c.execute('SELECT * FROM thrift_intake WHERE id=?',(ident,)).fetchone()
        if not row or row['status']!='returned':raise Problem('Only a fully returned item can be restocked.',409)
        c.execute("UPDATE thrift_intake SET status='available',sale=NULL WHERE id=?",(ident,))
        retail_event(c,'intake:'+str(ident),u['name'],'intake-restock',{'reason':reason})
        return finish({'ok':True},'Returned donated item restocked')
    if path=='thrift-settings':
        thrift_require(u,'manage_pos');old=thrift_settings(c)
        if d.get('revision')!=old['revision']:raise Problem('Thrift settings changed. Reopen before saving.',409)
        if 'loyalty_scope' in d:
            programs=stores_programs(c)
            if d.get('program_revision')!=programs['revision']:raise Problem('Loyalty scope changed. Reopen settings.',409)
            if d['loyalty_scope'] not in ('shared','store'):raise Problem('Choose loyalty scope.')
            if d['loyalty_scope']!=programs['loyalty_scope'] and any(json.loads(r[0]).get('reward') for r in c.execute("SELECT body FROM pos_carts WHERE status='open'")):raise Problem('Complete or remove rewards on saved sales before changing scope.')
            programs['loyalty_scope']=d['loyalty_scope'];revision=programs.pop('revision')
            c.execute('INSERT INTO retail_programs VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(revision+1,json.dumps(programs)))
        body={}
        for key in ('donations','loyalty','stack_tags'):
            if type(d.get(key)) is not bool:raise Problem('Choose '+key+'.')
            body[key]=d[key]
        for key in ('earn_cents','reward_points','reward_cents'):body[key]=pos_int(d.get(key),key,1,1000000)
        tags=d.get('tags');body['tags']=[]
        if not isinstance(tags,list) or len(tags)>20:raise Problem('Use at most 20 tag colors.')
        names=set()
        for tag in tags:
            name=pos_text(tag.get('name'),'a tag name',40)
            if name.casefold() in names:raise Problem('Tag names must be unique.')
            names.add(name.casefold());color=tag.get('color','')
            if not isinstance(color,str) or not re.fullmatch('#[0-9a-fA-F]{6}',color):raise Problem('Choose a tag color.')
            start=thrift_date(tag.get('from'),'promotion start');end=thrift_date(tag.get('to'),'promotion end')
            if start and end and end<start:raise Problem('Promotion end must follow start.')
            cats=tag.get('categories',[])
            if not isinstance(cats,list) or len(cats)>100:raise Problem('Invalid categories.')
            days=tag.get('days',list(range(7)))
            if not isinstance(days,list) or any(type(x) is not int or x not in range(7) for x in days):raise Problem('Invalid weekdays.')
            body['tags'].append(dict(name=name,color=color,bps=pos_int(tag.get('bps'),'discount percent',0,10000),**{'from':start,'to':end},days=days,categories=[pos_text(x,'a category',60) for x in cats]))
        c.execute('INSERT INTO thrift_settings VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(old['revision']+1,json.dumps(body)))
        return finish({'settings':thrift_settings(c)},'Thrift settings saved')
    if path=='thrift-customer-save':
        ident=d.get('id');old=thrift_customer(c,pos_int(ident,'customer',1)) if ident else None
        if old and d.get('revision')!=old['revision']:raise Problem('Customer changed. Search again.',409)
        name=pos_text(d.get('name'),'a customer name');contact=d.get('contact','')
        if not isinstance(contact,str) or len(contact)>200:raise Problem('Contact is too long.')
        if type(d.get('marketing')) is not bool:raise Problem('Record the customer’s marketing consent separately.')
        body=dict(name=name,contact=contact.strip(),marketing=d['marketing'],consent_at=dt.datetime.now().astimezone().isoformat(),consent_by=u['name'])
        if old:c.execute('UPDATE thrift_customers SET body=?,revision=revision+1 WHERE id=?',(json.dumps(body),ident))
        else:ident=c.execute('INSERT INTO thrift_customers(revision,body) VALUES(1,?)',(json.dumps(body),)).lastrowid
        return finish({'customer':thrift_customer(c,ident)},'Customer preferences saved')
    if path=='thrift-voucher-issue':
        pos_credit_access(u,True)
        name=pos_text(d.get('name'),'recipient name');reason=pos_text(d.get('reason'),'funding/reference reason',300)
        amount=pos_int(d.get('amount'),'voucher amount',1);expiry=thrift_date(d.get('expires'),'expiry date',False)
        if expiry<dt.date.today().isoformat():raise Problem('Expiry must not be in the past.')
        cats=d.get('categories',[])
        if not isinstance(cats,list) or not cats:raise Problem('Specify eligible merchandise categories.')
        body=dict(expires=expiry,categories=[pos_text(x,'a category',60) for x in cats],reason=reason)
        ident=c.execute("INSERT INTO pos_credit_accounts(name,kind,contact) VALUES(?,'customer',?)",(name,'Assistance voucher')).lastrowid
        c.execute('INSERT INTO thrift_vouchers VALUES(?,?)',(ident,json.dumps(body)))
        c.execute('INSERT INTO pos_credit_ledger(account,amount,balance,at,actor,reason) VALUES(?,?,?,?,?,?)',(ident,amount,amount,dt.datetime.now().astimezone().isoformat(),u['name'],reason))
        return finish({'account':pos_credit_account(c,ident)},'Assistance voucher issued')
    if path=='thrift-pickup-save':
        ident=pos_int(d.get('sale'),'receipt number',1);fulfillment_sale(c,u,ident)
        s=c.execute('SELECT body,cart FROM pos_sales WHERE id=?',(ident,)).fetchone()
        if not s:raise Problem('Receipt not found.',404)
        old=c.execute('SELECT * FROM thrift_pickups WHERE sale=?',(ident,)).fetchone()
        if d.get('revision',0)!=(old['revision'] if old else 0):raise Problem('Pickup changed. Refresh before saving.',409)
        status=d.get('status')
        if status not in ('awaiting_pickup','awaiting_delivery','collected','delivered','canceled'):raise Problem('Choose fulfillment status.')
        body=dict(customer=pos_text(d.get('customer'),'a customer name'),contact=pos_text(d.get('contact'),'a contact',200),location=pos_text(d.get('location'),'a storage location',120),due=thrift_date(d.get('due'),'pickup date',False),status=status,notes=str(d.get('notes',''))[:500],dispatch_reference=str(d.get('dispatch_reference',''))[:120])
        body['updated_by']=u['name'];body['updated_at']=dt.datetime.now().astimezone().isoformat()
        revision=(old['revision'] if old else 0)+1
        c.execute('INSERT INTO thrift_pickups VALUES(?,?,?) ON CONFLICT(sale) DO UPDATE SET revision=excluded.revision,body=excluded.body',(ident,revision,json.dumps(body)))
        retail_event(c,s['cart'],u['name'],'sold-pickup',body)
        return finish({'pickup':dict(sale=ident,revision=revision,**body),'receipt':json.loads(s['body'])},'Sold-item fulfillment saved')
    raise Problem('Unknown thrift action.')

def thrift_tag(c,cart,d):
    if cart.get('reward') or cart.get('adjustment'):raise Problem('Remove the reward or restore original prices before changing tag discounts.')
    index=pos_int(d.get('index'),'line',0,len(cart['lines'])-1);line=cart['lines'][index]
    if line.get('donation') or line.get('gift_certificate') or line.get('components'):raise Problem('Tag discounts apply to individual merchandise lines, not donations or bundles.')
    settings=thrift_settings(c);name=d.get('tag','')
    tag=next((x for x in settings['tags'] if x['name']==name),None) if name else None
    if name and not tag:raise Problem('Tag color no longer exists. Reopen the tag selector.',409)
    base=line.pop('tag_original',None)
    if base:line.clear();line.update(base)
    if tag:
        today=dt.date.today();active=(not tag['from'] or today.isoformat()>=tag['from']) and (not tag['to'] or today.isoformat()<=tag['to']) and today.weekday() in tag['days']
        eligible=not tag['categories'] or line['category'] in tag['categories']
        rate=tag['bps'] if active and eligible and not line.get('promotion') else 0
        original=json.loads(json.dumps(line));discount=(line['subtotal']*rate+5000)//10000
        line['subtotal']-=discount;line['tax']=(line['subtotal']*cart['settings']['tax_bps']+5000)//10000 if line['taxable'] else 0
        line['tag']=dict(name=tag['name'],color=tag['color'],discount=discount,bps=rate);line['tag_original']=original

def thrift_cart_action(c,u,cart,path,d,finish):
    if path=='thrift-tag':thrift_tag(c,cart,d)
    elif path=='thrift-donation':
        if cart.get('adjustment') or cart.get('reward'):raise Problem('Restore discounts/rewards before changing donation amounts.')
        if not thrift_settings(c)['donations']:raise Problem('Donation prompts are disabled in OFFICE.')
        cart['lines']=[l for l in cart['lines'] if not l.get('donation')]
        amount=pos_int(d.get('amount'),'donation',0,100000)
        if d.get('roundup') is True:amount=(-sum(l['subtotal']+l['tax'] for l in cart['lines']))%100
        if amount:cart['lines'].append(dict(name='Voluntary donation',category='Donations',price=amount,quantity=1,subtotal=amount,tax=0,taxable=False,donation=True))
    elif path=='thrift-customer':
        if cart.get('reward'):raise Problem('Remove the reward before changing customers.')
        ident=d.get('customer');cart['customer']=thrift_customer(c,pos_int(ident,'customer',1))['id'] if ident else None
    elif path=='thrift-reward':
        if cart.get('reward'):
            cart['lines']=cart.pop('reward_original');cart.pop('reward')
        elif d.get('redeem') is True:
            settings=thrift_settings(c)
            if not settings['loyalty'] or not cart.get('customer'):raise Problem('Select a customer and enable loyalty in OFFICE.')
            if cart.get('adjustment'):raise Problem('Rewards cannot combine with manual discounts.')
            customer=thrift_customer(c,cart['customer'],stores_id(cart))
            if customer['points']<settings['reward_points']:raise Problem('Insufficient reward points.')
            targets=[l for l in cart['lines'] if not l.get('donation') and not l.get('gift_certificate') and (settings['stack_tags'] or not l.get('tag',{}).get('discount'))]
            if any(l.get('components') for l in targets):raise Problem('Rewards on bundles are not supported.')
            amount=min(settings['reward_cents'],sum(l['subtotal'] for l in targets))
            if amount<=0:raise Problem('No eligible merchandise for this reward.')
            cart['reward_original']=json.loads(json.dumps(cart['lines']))
            for l,part in zip(targets,retail_allocate(amount,[l['subtotal'] for l in targets])):
                l['subtotal']-=part;l['tax']=(l['subtotal']*cart['settings']['tax_bps']+5000)//10000 if l['taxable'] else 0
            cart['reward']=dict(points=settings['reward_points'],amount=amount,loyalty_scope=stores_programs(c)['loyalty_scope'])
    retail_save_cart(c,cart);retail_event(c,cart['id'],u['name'],path,{k:v for k,v in d.items() if k not in ('request',)})
    return finish({'cart':cart},'Thrift sale updated')

def thrift_voucher_check(c,account,cart,amount):
    row=c.execute('SELECT body FROM thrift_vouchers WHERE account=?',(account['id'],)).fetchone()
    if not row:return
    rule=json.loads(row[0])
    if dt.date.today().isoformat()>rule['expires']:raise Problem('This assistance voucher has expired.')
    # Keep restricted voucher receipts homogeneous so partial refunds cannot
    # convert cash for excluded merchandise into restricted voucher credit.
    if any(l.get('donation') or l['category'] not in rule['categories'] for l in cart['lines']):raise Problem('Use a separate sale for donations or items outside this voucher’s eligible categories.')
    cart['voucher_paid']=amount

def thrift_sale_prepare(c,cart,path):
    settings=thrift_settings(c)
    seen=set()
    for line in cart['lines']:
        if not line.get('intake'):continue
        row=c.execute('SELECT status FROM thrift_intake WHERE id=?',(line['intake'],)).fetchone()
        if line['intake'] in seen or not row or row['status']!='available':raise Problem('A donated item in this sale has already sold. Remove it before payment.',409)
        seen.add(line['intake'])
    if cart.get('reward'):
        if not cart['reward'].get('birthday') and not settings['loyalty']:raise Problem('Loyalty is disabled. Remove the reward before checkout.')
        if not cart['reward'].get('birthday') and thrift_customer(c,cart['customer'],stores_id(cart))['points']<cart['reward']['points']:raise Problem('Reward balance changed. Remove the reward and try again.',409)
    if cart.get('customer') and settings['loyalty']:
        cart['loyalty_earned']=sum(l['subtotal'] for l in cart['lines'] if not l.get('donation') and not l.get('gift_certificate'))//settings['earn_cents'] if path=='cash' else 0
        cart['loyalty_earn_cents']=settings['earn_cents']

def thrift_sale_saved(c,sale,ident):
    for line in sale['lines']:
        if line.get('intake'):c.execute("UPDATE thrift_intake SET status='sold',sale=? WHERE id=?",(ident,line['intake']))
    if sale.get('customer') and ('loyalty_earned' in sale or sale.get('reward')):
        c.execute('INSERT INTO thrift_points(customer,amount,sale,reason) VALUES(?,?,?,?)',(sale['customer'],sale.get('loyalty_earned',0)-sale.get('reward',{}).get('points',0),ident,'Sale earn/redeem'))

def thrift_refund_saved(c,result,refund):
    sale=json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(result['sale'],)).fetchone()[0])
    for line in result['lines']:
        original=sale['lines'][line['index']]
        if original.get('intake'):c.execute("UPDATE thrift_intake SET status='returned' WHERE id=? AND sale=? AND status='sold'",(original['intake'],result['sale']))
    if not sale.get('customer'):return
    history=retail_refund_state(c,result['sale']);returned=sum(r['subtotal'] for r in history)
    merchandise=sum(l['subtotal'] for l in sale['lines'] if not l.get('donation') and not l.get('gift_certificate'))
    earned=sale.get('loyalty_earned',0);redeemed=sale.get('reward',{}).get('points',0)
    # Recompute the cumulative refund entitlement; repeated partial returns
    # cannot earn additional points. A negative balance is a future-earn debt.
    reversal=earned-min(earned,max(0,merchandise-returned)//sale.get('loyalty_earn_cents',100))
    restored=redeemed if returned>=merchandise else redeemed*returned//max(1,merchandise)
    prior=c.execute('SELECT COALESCE(SUM(amount),0) FROM thrift_points WHERE sale=? AND refund IS NOT NULL',(result['sale'],)).fetchone()[0]
    c.execute('INSERT INTO thrift_points(customer,amount,sale,refund,reason) VALUES(?,?,?,?,?)',(sale['customer'],restored-reversal-prior,result['sale'],refund,'Return reward correction'))

def thrift_intake_line(c,cart,item):
    if not item.get('product'):return
    row=c.execute('SELECT * FROM thrift_intake WHERE product=?',(item['product'],)).fetchone()
    if not row:return
    if row['status']!='available' or item['quantity']!=1 or any(l.get('intake')==row['id'] for l in cart['lines']):raise Problem('A donated item can only be sold once, with quantity one.')
    item['intake']=row['id'];item['barcode']=str(100000000+row['id'])
    cart['lines'].append(item)
    thrift_tag(c,cart,{'index':len(cart['lines'])-1,'tag':row['tag']})
    cart['lines'].pop()
