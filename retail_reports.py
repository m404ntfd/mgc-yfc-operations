"""Read-only reporting, embedded in the legacy server update."""
def retail_reports(c,u,q):
    kind=q.get('kind',['dashboard'])[0]
    def local_epoch(value):
        try:return dt.datetime.fromisoformat(value).timestamp()
        except (TypeError,ValueError):raise Problem('Choose valid report dates.')
    start=local_epoch(q.get('start',[''])[0]);end=local_epoch(q.get('end',[''])[0])
    q=dict(q,start=[dt.datetime.fromtimestamp(start).astimezone().isoformat()],end=[dt.datetime.fromtimestamp(end).astimezone().isoformat()])
    if start is None or end is None or not 0<end-start<=366*86400:raise Problem('Choose a date range of up to 366 days.')
    labor=any(has_permission(u,p) for p in ('edit_time_cards','add_time_cards','export_payroll'))
    if kind in ('labor','time-entries','schedule'):
        if kind=='schedule':
            if not has_permission(u,'manage_staff_schedule'):raise Problem('Scheduling permission required.',403)
            rows=[dict(r) for r in c.execute('SELECT s.*,p.name FROM work_shifts s LEFT JOIN receipt_profiles p ON p.profile_id=s.account WHERE s.start<? AND s.end>? ORDER BY s.start,p.name',(end,start))]
            return {'title':'Employee schedule','columns':['Employee','Start','End','Job','Location','Notes'],'rows':[[r['name'],work_local(r['start']),work_local(r['end']),r['job'],r['location'],r['notes']] for r in rows]}
        if not labor:raise Problem('Time card or payroll permission required.',403)
        if kind=='time-entries':
            rows=[dict(r) for r in c.execute('SELECT w.*,p.name FROM work_periods w LEFT JOIN receipt_profiles p ON p.profile_id=w.account WHERE w.start<? AND (w.end IS NULL OR w.end>?) ORDER BY w.start',(end,start))]
            return {'title':'Time entries','columns':['Employee','Clock in','Clock out','Break minutes in range','Status'],'rows':[[r['name'],work_local(r['start']),work_local(r['end']) if r['end'] else '',round(sum(max(0,min(end,time.time(),b['end'] or time.time())-max(start,b['start'])) for b in c.execute('SELECT * FROM work_breaks WHERE period=?',(r['id'],)))/60,2),'Open' if r['end'] is None else 'Closed'] for r in rows]}
        rows=[]
        for r in c.execute('SELECT profile_id,name FROM receipt_profiles ORDER BY name'):
            gross,worked=work_hours(c,r['profile_id'],(start,end),int(time.time()))
            if gross:rows.append([r['name'],round(gross/3600,2),round((gross-worked)/3600,2),round(worked/3600,2)])
        return {'title':'Labor hours','columns':['Employee','Gross hours','Break hours','Worked hours'],'rows':rows,'note':'Actual recorded breaks are deducted. Open entries are calculated through now. Wage cost and labor percentage are unavailable until wage history is recorded.'}
    if not has_permission(u,'view_pos_sales'):raise Problem('Sales report permission required.',403)
    report=retail_workflow_get(c,u,'sale-report',q);sales=report['sales'];refunds=report['refunds']
    def money(n):return f'{n/100:.2f}'
    def stamp(v):return dt.datetime.fromtimestamp(retail_epoch(v,'date'))
    def table(title,columns,rows,note=''):return dict(title=title,columns=columns,rows=rows,note=note)
    def merchandise(s):return sum(l['subtotal'] for l in s['lines'] if not l.get('donation'))
    if kind=='dashboard':
        items={};categories={};employees={};buckets={}
        def add(group,key,value):group[key]=group.get(key,0)+value
        for s in sales:
            add(employees,s['cashier'],merchandise(s));add(buckets,stamp(s['at']).strftime('%Y-%m-%d' if end-start>172800 else '%Y-%m-%d %H:00'),merchandise(s))
            for l in s['lines']:
                if not l.get('donation'):add(items,l['name'],l['subtotal']);add(categories,l['category'],l['subtotal'])
        for r in refunds:
            original=c.execute('SELECT body FROM pos_sales WHERE id=?',(r['sale'],)).fetchone();name=json.loads(original[0])['cashier'] if original else 'Unknown'
            add(employees,name,-r['subtotal']);add(buckets,stamp(r['at']).strftime('%Y-%m-%d' if end-start>172800 else '%Y-%m-%d %H:00'),-r['subtotal'])
            for l in r['lines']:add(items,l['name'],-l['subtotal']);add(categories,l['category'],-l['subtotal'])
        gross=sum(l.get('tag_original',l)['subtotal'] for s in sales for l in (s.get('reward_original') or s.get('original_lines') or s['lines']) if not l.get('donation'))
        net=sum(merchandise(s) for s in sales)-sum(r['subtotal'] for r in refunds)
        working=[r[0] for r in c.execute('SELECT p.name FROM work_periods w LEFT JOIN receipt_profiles p ON p.profile_id=w.account WHERE w.end IS NULL')] if labor else None
        previous=dict(q,start=[dt.datetime.fromtimestamp(start-(end-start)).astimezone().isoformat()],end=[dt.datetime.fromtimestamp(start).astimezone().isoformat()])
        prev=retail_workflow_get(c,u,'sale-report',previous)
        prior_net=sum(merchandise(s) for s in prev['sales'])-sum(r['subtotal'] for r in prev['refunds'])
        return dict(store=pos_settings(c)['store'],gross=gross,net=net,transactions=len(sales),average=round(net/len(sales)) if sales else None,prior_net=prior_net,items=items,categories=categories,employees=employees,buckets=buckets,working=working,labor_percent=None,note='Net sales exclude tax and voluntary donations and deduct refunds posted in this period. Comparison is the preceding equal-length period. Employee returns are attributed to the original cashier.')
    if kind=='pricing' or kind=='tax-assignment' or kind=='hierarchy':
        rows=[retail_product(c,r) for r in c.execute('SELECT * FROM pos_products ORDER BY rowid')]
        return table({'pricing':'Pricing','tax-assignment':'Tax assignment','hierarchy':'Reporting hierarchy'}[kind],['Product','Category','Price','Taxable','Active'],[[r['name'],r['category'],'Open price' if r.get('rules',{}).get('open_priced') else money(r['price']),r['taxable'],r.get('rules',{}).get('active',True)] for r in rows],'Current catalog configuration; not a reconstruction of historical prices.')
    if kind=='modifiers':
        rows=[]
        for sale in sales:
            for line in sale['lines']:
                for m in line.get('modifiers',[]):rows.append([sale['id'],line['name'],m['group'],m['name'],line['quantity'],money(m['price'])])
        return table('Products and modifiers',['Receipt','Product','Choice group','Choice','Sold quantity','Unit add-on price'],rows,'Completed sales before returns. Add-on prices are already included in product sales, not additional revenue.')
    if kind=='accounts':
        if not has_permission(u,'manage_store_credit'):raise Problem('Store-credit management permission required.',403)
        return table('Account information',['Account','Name','Type','Current balance'],[[a['code'],a['name'],a['kind'],money(a['balance'])] for a in (pos_credit_account(c,r[0]) for r in c.execute('SELECT id FROM pos_credit_accounts'))],'Balances are current; the date range does not change current balances.')
    if kind=='reservations':
        if not has_permission(u,'view_schedule'):raise Problem('Reservation permission required.',403)
        rows=[]
        for r in c.execute('SELECT id,body FROM jobs'):
            j=json.loads(r['body'])
            try:at=local_epoch(j.get('start',''))
            except Problem:continue
            if at and start<=at<end:rows.append([r['id'],j.get('customer'),j.get('type'),j.get('start'),j.get('status')])
        return table('Reservation schedule',['ID','Customer','Type','Start','Status'],rows,'Reservation appointments; merchandise orders are not linked to reservations.')
    if kind=='tabs':
        return table('Open and held sales',['Sale','Employee','Updated','Total','Held'],[[r['id'],r['name'],dt.datetime.fromtimestamp(r['updated']).isoformat(),money(json.loads(r['body'])['total']),json.loads(r['body']).get('held',False)] for r in c.execute("SELECT a.*,p.name FROM pos_carts a LEFT JOIN receipt_profiles p ON p.profile_id=a.owner WHERE a.status='open'")],'Current open sales, regardless of selected date range.')
    if kind in ('transactions','sales','tax-audit'):
        return table({'transactions':'Transaction log','sales':'Sales report','tax-audit':'Tax audit'}[kind],['Type','Receipt','Time','Employee','Subtotal','Tax','Total'],[['Sale',s['id'],s['at'],s['cashier'],money(s['subtotal']),money(s['tax']),money(s['total'])] for s in sales]+[['Refund',r['sale'],r['at'],r['cashier'],money(-r['subtotal']),money(-r['tax']),money(-r['total'])] for r in refunds])
    if kind=='adjustments' or kind=='journal':
        rows=[]
        for r in c.execute('SELECT * FROM retail_sale_events ORDER BY id'):
            if kind=='adjustments' and not r['action'].startswith('adjustment-'):continue
            if start<=retail_epoch(r['at'],'event time')<end:rows.append([r['at'],r['actor'],r['cart'],r['action'],r['body']])
        return table('Sales journal' if kind=='journal' else 'Adjustments log',['Time','Employee','Sale','Action','Detail'],rows,'Recorded sale events; historical events not captured by earlier versions cannot be reconstructed.')
    groups={}
    for sign,records in ((1,sales),(-1,refunds)):
        for s in records:
            original=s if sign==1 else json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(s['sale'],)).fetchone()[0])
            if kind in ('cash','drawer','shift'):
                key=(original.get('terminal') or 'Not recorded',s['cashier']);v=groups.setdefault(key,[0,0]);v[0]+=sign*(s['tender']-s['change'] if sign==1 else s['cash']);v[1]+=sign*s.get('store_credit',0)
            else:
                for l in s['lines']:
                    if l.get('donation'):continue
                    key=(s['cashier'],stamp(s['at']).strftime('%Y-%m-%d' if end-start>172800 else '%Y-%m-%d %H:00')) if kind=='employee-time' else (l['name'],stamp(s['at']).strftime('%H:00')) if kind=='products-hour' else (stamp(s['at']).strftime('%Y-%m-%d'),stamp(s['at']).strftime('%H:00')) if kind=='seven-day' else (l['name'],l['category'])
                    v=groups.setdefault(key,[0,0]);v[0]+=sign*l['quantity'];v[1]+=sign*l['subtotal']
    if kind in ('cash','drawer','shift'):return table({'cash':'Cash summary','drawer':'Drawer summary','shift':'Shift summary'}[kind],['Terminal','Employee','Net cash','Net store credit'],[[*k,money(v[0]),money(v[1])] for k,v in sorted(groups.items())],'Calculated from recorded payments and refunds. No physical drawer counts or cash-session reconciliation are recorded.')
    if kind not in ('employee-time','products-hour','seven-day','products'):raise Problem('Report not available.',404)
    columns={'employee-time':['Employee','Hour'],'products-hour':['Product','Hour'],'seven-day':['Day','Hour'],'products':['Product','Category']}[kind]
    return table({'employee-time':'Employee sales by time','products-hour':'Products sold by hour','seven-day':'Revenue by day and hour','products':'Products sold'}[kind],columns+['Net quantity','Net sales'],[[*k,v[0],money(v[1])] for k,v in sorted(groups.items())],'Refunds use their posting date; totals exclude tax. Product names reflect saved receipts.')
