"""Additive catalog configuration and snapshotted line taxes."""
def catalog_init(c):
    c.execute('CREATE TABLE IF NOT EXISTS retail_catalog_options(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,body TEXT NOT NULL)')

def catalog_options(c,discover=True):
    row=c.execute('SELECT * FROM retail_catalog_options WHERE id=1').fetchone()
    body=json.loads(row['body']) if row else {}
    categories=list(body.get('categories',[]))
    for r in (c.execute('SELECT body FROM pos_products') if discover else []):
        key=json.loads(r[0]).get('category','')
        if key and key not in categories:categories.append(key)
    routes=c.execute('SELECT body FROM retail_print_routes WHERE id=1').fetchone()
    body.setdefault('printing',sorted({r['category'] for r in json.loads(routes[0])}) if routes else [])
    body.setdefault('taxes',[]);body.setdefault('revenue_centers',[]);body.setdefault('departments',[]);body.setdefault('sub_departments',[])
    known={x['key'] for x in body['sub_departments']}
    for key in categories:
        if key not in known:
            body['sub_departments'].append(dict(id='legacy-'+hashlib.sha256(key.encode()).hexdigest()[:32],key=key,name=key,department_id=''))
            known.add(key)
    body['categories']=[x['key'] for x in body['sub_departments']]
    return dict(body,revision=row['revision'] if row else 0)

def catalog_key(c,value):
    """Resolve a newly entered display name without rewriting historical product keys."""
    options=catalog_options(c,False)
    sub=next((x for x in options['sub_departments'] if x['key']==value),None)
    if sub is None:sub=next((x for x in options['sub_departments'] if x['name'].casefold()==value.casefold()),None)
    return sub['key'] if sub else value

def catalog_classification(c,key,options=None):
    options=options or catalog_options(c,False)
    sub=next((x for x in options['sub_departments'] if x['key']==key),dict(id='legacy-'+hashlib.sha256(key.encode()).hexdigest()[:32],name=key))
    department=next((x for x in options['departments'] if x['id']==sub.get('department_id')), {})
    center=next((x for x in options['revenue_centers'] if x['id']==department.get('revenue_center_id')), {})
    return dict(sub_department_id=sub.get('id',''),sub_department=sub.get('name',key),department_id=department.get('id',''),department=department.get('name','Unassigned'),revenue_center_id=center.get('id',''),revenue_center=center.get('name','Unassigned'))

def catalog_hierarchy(old,body,key,values):
    if not isinstance(values,list) or len(values)>200:raise Problem('Use up to 200 entries.')
    previous={x['id']:x for x in old[key]};clean=[];ids=set();names=set();keys=set()
    for entry in values:
        if not isinstance(entry,dict):raise Problem('Invalid classification entry.')
        ident=entry.get('id');name=pos_text(entry.get('name'),'a name',60)
        if not isinstance(ident,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,64}',ident) or ident in ids:raise Problem('Use unique classification identifiers.')
        if name.casefold() in names:raise Problem('Names must be unique within this setup screen.')
        ids.add(ident);names.add(name.casefold());item=dict(id=ident,name=name)
        if key=='departments':
            parent=entry.get('revenue_center_id')
            if not isinstance(parent,str) or parent not in {x['id'] for x in body['revenue_centers']}:raise Problem('Select a Revenue Center for every Department.')
            item['revenue_center_id']=parent
        elif key=='sub_departments':
            # The original category key is immutable: eligibility rules and existing products keep their links.
            item['key']=previous[ident]['key'] if ident in previous else name
            if item['key'] in keys:raise Problem('This Sub Department already exists. Edit the existing entry.')
            keys.add(item['key']);parent=entry.get('department_id','')
            if not isinstance(parent,str) or (parent not in {x['id'] for x in body['departments']} and not (not parent and ident in previous and not previous[ident].get('department_id'))):raise Problem('Select a Department for every new Sub Department.')
            item['department_id']=parent
        clean.append(item)
    if key=='sub_departments':
        for entry in clean:
            if any(other['id']!=entry['id'] and other['key'].casefold()==entry['name'].casefold() for other in clean):raise Problem('This name is already linked to another Sub Department. Choose a different name.')
    body[key]=clean

def catalog_removal_check(c,old,body):
    """Setup deletion never removes or reassigns operational records."""
    removed_centers={x['id'] for x in old['revenue_centers']}-{x['id'] for x in body['revenue_centers']}
    removed_departments={x['id'] for x in old['departments']}-{x['id'] for x in body['departments']}
    removed_subs={x['key'] for x in old['sub_departments']}-{x['key'] for x in body['sub_departments']}
    removed_printing=set(old['printing'])-set(body['printing'])
    removed_taxes={x['id'] for x in old['taxes']}-{x['id'] for x in body['taxes']}
    if any(x['revenue_center_id'] in removed_centers for x in body['departments']):raise Problem('This Revenue Center is assigned to a Department. Reassign its Departments before deleting it.')
    if any(x.get('department_id') in removed_departments for x in body['sub_departments']):raise Problem('This Department is assigned to a Sub Department. Reassign its Sub Departments before deleting it.')
    if removed_subs:
        if any(json.loads(r[0]).get('category') in removed_subs for r in c.execute('SELECT body FROM pos_products')):raise Problem('This Sub Department is assigned to a product. Reassign its products before deleting it.')
        if any(removed_subs.intersection(t.get('categories',[])) for t in thrift_settings(c)['tags']):raise Problem('This Sub Department is used by a color-tag rule. Update that rule before deleting it.')
        if any(removed_subs.intersection(json.loads(r[0]).get('categories',[])) for r in c.execute('SELECT body FROM thrift_vouchers')):raise Problem('This Sub Department is used by an assistance voucher and must be retained.')
    if removed_printing or removed_taxes:
        for row in c.execute('SELECT body FROM retail_product_rules'):
            rule=json.loads(row[0])
            if rule.get('print_category') in removed_printing:raise Problem('This printing category is assigned to a product. Reassign its products before deleting or renaming it.')
            if removed_taxes.intersection(rule.get('tax_ids',[])):raise Problem('This tax is assigned to a product. Reassign its products before deleting it.')
        routes=c.execute('SELECT body FROM retail_print_routes WHERE id=1').fetchone()
        if routes and any(r['category'] in removed_printing for r in json.loads(routes[0])):raise Problem('This printing category has a printer route. Remove or change its route before deleting or renaming it.')

def catalog_save(c,u,d):
    if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
    old=catalog_options(c)
    if d.get('revision')!=old['revision']:raise Problem('Setup changed in another screen. Close and reopen this screen before saving.',409)
    section=d.get('section','legacy')
    if section not in ('legacy','taxes','printing','revenue_centers','departments','sub_departments'):raise Problem('Unknown catalog setup section.')
    body={k:v for k,v in old.items() if k!='revision'}
    if section in ('revenue_centers','departments','sub_departments'):
        catalog_hierarchy(old,body,section,d.get(section))
    if section=='legacy':
        values=d.get('categories')
        if not isinstance(values,list) or len(values)>200:raise Problem('Use up to 200 Sub Departments.')
        for value in values:
            key=pos_text(value,'Sub Department',60)
            if key not in {x['key'] for x in body['sub_departments']}:
                body['sub_departments'].append(dict(id='legacy-'+hashlib.sha256(key.encode()).hexdigest()[:32],key=key,name=key,department_id=''))
    if section in ('legacy','printing'):
        values=d.get('printing')
        if not isinstance(values,list) or len(values)>200:raise Problem('Use up to 200 printing categories.')
        body['printing']=list(dict.fromkeys(pos_text(x,'printing category',60) for x in values))
    if section in ('legacy','taxes'):
        taxes=d.get('taxes')
        if not isinstance(taxes,list) or len(taxes)>50:raise Problem('Use up to 50 taxes.')
        body['taxes']=[];seen=set()
        for tax in taxes:
            if not isinstance(tax,dict):raise Problem('Invalid tax.')
            ident=pos_text(tax.get('id'),'tax ID',64)
            if ident in seen or ident=='legacy':raise Problem('Duplicate or reserved tax ID.')
            seen.add(ident);store=tax.get('store_id','thrift-mart');stores_profile(c,store)
            body['taxes'].append(dict(id=ident,name=pos_text(tax.get('name'),'tax name',60),bps=pos_int(tax.get('bps'),'tax percentage',0,10000),store_id=store))
    catalog_removal_check(c,old,body)
    body['categories']=[x['key'] for x in body['sub_departments']]
    c.execute('INSERT INTO retail_catalog_options VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(old['revision']+1,json.dumps(body)))
    return catalog_options(c)

def catalog_validate(c,rule,clean,body):
    if 'tax_ids' not in rule:return
    ids=rule['tax_ids'];options=catalog_options(c)
    if not isinstance(ids,list) or len(ids)>10 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):raise Problem('Select valid taxes.')
    available={t['id'] for t in options['taxes'] if t['store_id']==clean['store_id']}
    if any(x not in available|{'legacy'} for x in ids) or ('legacy' in ids and len(ids)>1):raise Problem('Select taxes configured for this store.')
    if body['category'] not in options['categories']:raise Problem('Select a configured Sub Department.')
    if clean['print_category'] and clean['print_category'] not in options['printing']:raise Problem('Select a configured printing category.')
    clean['tax_ids']=ids;body['taxable']=bool(ids)

def catalog_rates(c,product,legacy):
    ids=product['rules'].get('tax_ids')
    if ids is None or ids==['legacy']:return None
    rates={t['id']:t for t in catalog_options(c,False)['taxes']}
    if any(x not in rates for x in ids):raise Problem('A product tax was removed. Review this item in OFFICE.',409)
    return [dict(id=x,name=rates[x]['name'],bps=rates[x]['bps']) for x in ids]

def catalog_tax(line,legacy):
    if line.get('components'):
        line['tax']=sum(catalog_tax(x,legacy) for x in line['components']);return line['tax']
    if 'tax_rates' in line:
        line['tax_details']=[dict(t,amount=(line['subtotal']*t['bps']+5000)//10000) for t in line['tax_rates']]
        line['tax']=sum(t['amount'] for t in line['tax_details'])
    else:line['tax']=(line['subtotal']*legacy+5000)//10000 if line['taxable'] else 0
    return line['tax']

def catalog_stamp(c,line,legacy):
    options=catalog_options(c,False);line['reporting']=catalog_classification(c,line.get('category',''),options)
    for item in line.get('components') or [line]:
        row=c.execute('SELECT * FROM pos_products WHERE id=?',(item.get('product'),)).fetchone()
        if row:
            item['reporting']=catalog_classification(c,json.loads(row['body']).get('category',''),options)
            rates=catalog_rates(c,retail_product(c,row),legacy)
            if rates is not None:item['tax_rates']=rates
        catalog_tax(item,legacy)
    catalog_tax(line,legacy)
    return line
