"""Additive catalog configuration and snapshotted line taxes."""
def catalog_init(c):
    c.execute('CREATE TABLE IF NOT EXISTS retail_catalog_options(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,body TEXT NOT NULL)')

def catalog_options(c):
    row=c.execute('SELECT * FROM retail_catalog_options WHERE id=1').fetchone()
    if row:return dict(json.loads(row['body']),revision=row['revision'])
    categories=sorted({json.loads(r[0]).get('category','') for r in c.execute('SELECT body FROM pos_products')}-{''})
    routes=c.execute('SELECT body FROM retail_print_routes WHERE id=1').fetchone()
    printing=sorted({r['category'] for r in json.loads(routes[0])}) if routes else []
    return dict(revision=0,categories=categories,printing=printing,taxes=[])

def catalog_save(c,u,d):
    if not has_permission(u,'manage_pos'):raise Problem('Manage POS permission required.',403)
    old=catalog_options(c)
    if d.get('revision')!=old['revision']:raise Problem('Catalog options changed. Reload before saving.',409)
    body={}
    for key in ('categories','printing'):
        values=d.get(key)
        if not isinstance(values,list) or len(values)>200:raise Problem('Use up to 200 options.')
        body[key]=list(dict.fromkeys(pos_text(x,key,60) for x in values))
    taxes=d.get('taxes')
    if not isinstance(taxes,list) or len(taxes)>50:raise Problem('Use up to 50 taxes.')
    body['taxes']=[];seen=set()
    for tax in taxes:
        ident=pos_text(tax.get('id'),'tax ID',64)
        if ident in seen or ident=='legacy':raise Problem('Duplicate or reserved tax ID.')
        seen.add(ident);store=tax.get('store_id','thrift-mart');stores_profile(c,store)
        body['taxes'].append(dict(id=ident,name=pos_text(tax.get('name'),'tax name',60),bps=pos_int(tax.get('bps'),'tax percentage',0,10000),store_id=store))
    c.execute('INSERT INTO retail_catalog_options VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',(old['revision']+1,json.dumps(body)))
    return catalog_options(c)

def catalog_validate(c,rule,clean,body):
    if 'tax_ids' not in rule:return
    ids=rule['tax_ids'];options=catalog_options(c)
    if not isinstance(ids,list) or len(ids)>10 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):raise Problem('Select valid taxes.')
    available={t['id'] for t in options['taxes'] if t['store_id']==clean['store_id']}
    if any(x not in available|{'legacy'} for x in ids) or ('legacy' in ids and len(ids)>1):raise Problem('Select taxes configured for this store.')
    if body['category'] not in options['categories']:raise Problem('Select a configured item category.')
    if clean['print_category'] and clean['print_category'] not in options['printing']:raise Problem('Select a configured printing category.')
    clean['tax_ids']=ids;body['taxable']=bool(ids)

def catalog_rates(c,product,legacy):
    ids=product['rules'].get('tax_ids')
    if ids is None or ids==['legacy']:return None
    rates={t['id']:t for t in catalog_options(c)['taxes']}
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
    for item in line.get('components') or [line]:
        row=c.execute('SELECT * FROM pos_products WHERE id=?',(item.get('product'),)).fetchone()
        if row:
            rates=catalog_rates(c,retail_product(c,row),legacy)
            if rates is not None:item['tax_rates']=rates
        catalog_tax(item,legacy)
    catalog_tax(line,legacy)
    return line
