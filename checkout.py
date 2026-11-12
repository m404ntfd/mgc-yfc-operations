"""Store checkout choices and receipt delivery. Embedded by prepare_web_assets."""
def checkout_init(c):
    c.execute('CREATE TABLE IF NOT EXISTS retail_checkout_settings(store TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL)')

def checkout_settings(c,store):
    row=c.execute('SELECT * FROM retail_checkout_settings WHERE store=?',(store,)).fetchone()
    body=json.loads(row['body']) if row else {'presets':[], 'reasons':[{'id':'customer-change','name':'Customer changed their mind'},{'id':'entry-error','name':'Incorrect item or entry'},{'id':'unable-to-pay','name':'Customer unable to pay'}]}
    return dict(body,store_id=store,revision=row['revision'] if row else 0)

def checkout_get(c,u,path,query):
    if path=='checkout-payment-status':
        request=query.get('request',[''])[0]
        if not re.fullmatch('[0-9a-f]{32}',request):raise Problem('Invalid payment reference.')
        row=c.execute('SELECT * FROM pos_operations WHERE id=? AND owner=?',(request,u.get('receipt_owner'))).fetchone()
        if not row:return {'confirmed':False}
        action,_=json.loads(row['payload'])
        if action not in ('cash','credit'):raise Problem('This reference is not a payment.',400)
        return {'confirmed':True,'result':json.loads(row['result'])}
    if path not in ('checkout-settings','today-receipts'):return None
    store,_=stores_context(c,u,{k:v[0] for k,v in query.items()})
    if path=='checkout-settings':return {'settings':checkout_settings(c,store)}
    today=dt.datetime.now().astimezone().date()
    sales=[]
    # Filter before applying a limit: yesterday's receipts must not hide today's.
    for row in c.execute('SELECT * FROM pos_sales ORDER BY id DESC'):
        if row['owner']!=u.get('receipt_owner') and not has_permission(u,'view_pos_sales'):continue
        sale=json.loads(row['body'])
        if stores_id(sale)!=store:continue
        try:day=dt.datetime.fromisoformat(sale['at']).astimezone().date()
        except (KeyError,ValueError,TypeError):continue
        if day==today:sales.append(dict(sale,id=row['id']))
    return {'sales':sales,'date':str(today)}

def checkout_post(c,u,path,d,finish):
    if path=='checkout-settings-save':
        if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
        store=pos_text(d.get('store_id'),'a store',80);stores_profile(c,store)
        old=checkout_settings(c,store)
        if d.get('revision')!=old['revision']:raise Problem('Checkout choices changed. Reopen this screen.',409)
        result={}
        for key in ('presets','reasons'):
            values=d.get(key)
            if not isinstance(values,list) or len(values)>100:raise Problem('Use no more than 100 '+key+'.')
            clean=[];ids=set()
            for value in values:
                if not isinstance(value,dict):raise Problem('Invalid checkout choice.')
                ident=pos_text(value.get('id'),'a choice identifier',80)
                if ident in ids:raise Problem('Duplicate checkout choice.')
                ids.add(ident);item={'id':ident,'name':pos_text(value.get('name'),'a choice name',100)}
                if key=='presets':
                    if value.get('mode') not in ('discount','surcharge') or value.get('scope') not in ('item','transaction') or value.get('kind') not in ('fixed','percent'):raise Problem('Choose the adjustment type, target and value type.')
                    item.update(mode=value['mode'],scope=value['scope'],kind=value['kind'],value=pos_int(value.get('value'),'adjustment value',1,10000 if value['kind']=='percent' else 10000000))
                clean.append(item)
            result[key]=clean
        c.execute('INSERT INTO retail_checkout_settings VALUES(?,?,?) ON CONFLICT(store) DO UPDATE SET revision=excluded.revision,body=excluded.body',(store,old['revision']+1,json.dumps(result)))
        return finish({'settings':checkout_settings(c,store)},'Store checkout choices updated')
    if path=='email-receipt':
        row=c.execute('SELECT * FROM pos_sales WHERE id=?',(pos_int(d.get('sale'),'receipt',1),)).fetchone()
        if not row or (row['owner']!=u.get('receipt_owner') and not has_permission(u,'view_pos_sales')):raise Problem('Receipt not found.',404)
        sale=json.loads(row['body']);store,_=stores_context(c,u,d)
        if stores_id(sale)!=store:raise Problem('Choose a receipt from this store.',403)
        recipient=customer_email(d.get('email'))
        if not recipient:raise Problem('Enter the customer email address.')
        config=customer_settings(c,'email')
        if not config['enabled'] or not customer_ready(c):raise Problem('Configure and enable Gmail in OFFICE before emailing receipts.',409)
        design=sale.get('receipt_design',{})
        money=lambda n:'${:,.2f}'.format(n/100)
        lines=[sale['settings']['store'],design.get('address',''),design.get('phone',''),'Receipt #'+str(row['id']),sale['at'],'Cashier: '+sale['cashier'],'']
        lines += [str(x['quantity'])+' × '+x['name']+'  '+money(x['subtotal']) for x in sale['lines']]
        lines += ['', 'Subtotal: '+money(sale['subtotal']),'Tax: '+money(sale['tax']),'Total: '+money(sale['total'])]
        if sale.get('store_credit'):lines.append('Store credit: '+money(sale['store_credit']))
        if sale['method']!='store_credit':lines += ['Cash rounding: '+money(sale.get('cash_rounding',0)),'Cash received: '+money(sale['tender']),'Change: '+money(sale['change'])]
        lines += [design.get('policy',''),design.get('footer','')]
        body={'subject':sale['settings']['store']+' · Receipt #'+str(row['id']),'text':'\n'.join(lines)}
        now=time.time()
        ident=c.execute('INSERT INTO customer_delivery(job,kind,fingerprint,recipient,due,status,body,updated) VALUES(?,?,?,?,?,?,?,?)',('sale:'+str(row['id']),'receipt',d['request'],recipient,now,'pending',json.dumps(body),now)).lastrowid
        return finish({'queued':True,'delivery':ident},'Receipt email queued #'+str(row['id']))

def checkout_preset(c,cart,d):
    if not d.get('preset'):return d
    choices=checkout_settings(c,stores_id(cart))
    if d.get('settings_revision')!=choices['revision']:raise Problem('Checkout buttons changed. Reopen Discounts/Surcharges.',409)
    preset=next((x for x in choices['presets'] if x['id']==d['preset']),None)
    if not preset:raise Problem('This adjustment is no longer available.',409)
    index=d.get('index')
    if (preset['scope']=='item')!=(index is not None):raise Problem('Choose the correct adjustment target.')
    return dict(d,mode=preset['mode'],amount=preset['value'] if preset['kind']=='fixed' else 0,percent_bps=preset['value'] if preset['kind']=='percent' else None,reason=preset['name'])

def retail_cash_due(settings,due):
    return ((due+2)//5)*5 if settings.get('cash_rounding')=='nearest5' and settings.get('cash_rounding_basis')=='total' else due
