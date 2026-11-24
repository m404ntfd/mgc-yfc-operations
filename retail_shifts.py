"""Terminal-wide register shifts, independent of employee timecards and cash counts.

Only unpaid carts may be voided. Their complete pre-close snapshots live in an
append-only ledger; paid receipts are never edited. All callers hold server LOCK.
"""
from zoneinfo import ZoneInfo

def shifts_clock():return time.time()

def shifts_init(c):
    c.executescript('''
CREATE TABLE IF NOT EXISTS retail_shift_settings(store TEXT PRIMARY KEY,revision INTEGER NOT NULL,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS retail_register_shifts(id INTEGER PRIMARY KEY AUTOINCREMENT,terminal TEXT NOT NULL,store TEXT NOT NULL,business_date TEXT NOT NULL,opened REAL NOT NULL,deadline REAL NOT NULL,closed REAL,processed REAL,actor TEXT,reason TEXT,body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS retail_register_shift_terminal ON retail_register_shifts(terminal,closed,deadline);
CREATE TABLE IF NOT EXISTS retail_shift_carts(cart TEXT PRIMARY KEY,shift INTEGER NOT NULL REFERENCES retail_register_shifts(id));
CREATE TABLE IF NOT EXISTS retail_shift_events(kind TEXT NOT NULL,reference TEXT NOT NULL,shift INTEGER NOT NULL REFERENCES retail_register_shifts(id),at REAL NOT NULL,body TEXT NOT NULL,PRIMARY KEY(kind,reference));
CREATE INDEX IF NOT EXISTS retail_shift_event_shift ON retail_shift_events(shift);
CREATE TRIGGER IF NOT EXISTS retail_register_shifts_closed BEFORE UPDATE ON retail_register_shifts WHEN OLD.closed IS NOT NULL BEGIN SELECT RAISE(ABORT,'Closed register shifts are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_register_shifts_no_delete BEFORE DELETE ON retail_register_shifts BEGIN SELECT RAISE(ABORT,'Register shift history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_shift_events_no_update BEFORE UPDATE ON retail_shift_events BEGIN SELECT RAISE(ABORT,'Register shift events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retail_shift_events_no_delete BEFORE DELETE ON retail_shift_events BEGIN SELECT RAISE(ABORT,'Register shift events are immutable'); END;
''')

def shifts_settings(c,store):
    stores_profile(c,store)
    row=c.execute('SELECT * FROM retail_shift_settings WHERE store=?',(store,)).fetchone()
    return dict({'cutoff':'23:59:59','print_format':'letter'},**(json.loads(row['body']) if row else {}),store_id=store,revision=row['revision'] if row else 0,timezone='America/Chicago')

def shifts_period(stamp,cutoff):
    zone=ZoneInfo('America/Chicago');local=dt.datetime.fromtimestamp(stamp,zone)
    clock=dt.time.fromisoformat(cutoff)
    def boundary(day):
        naive=dt.datetime.combine(day,clock)
        choices=[dt.datetime.fromtimestamp(naive.replace(tzinfo=zone,fold=fold).timestamp(),zone) for fold in (0,1)]
        valid=[x for x in choices if x.replace(tzinfo=None)==naive]
        return max(valid,key=lambda x:x.timestamp()) if valid else min((x for x in choices if x.replace(tzinfo=None)>naive),key=lambda x:x.timestamp())
    end=boundary(local.date())
    # Use the second occurrence of a repeated closing time. A nonexistent spring
    # time moves forward by the DST gap. UTC timestamps make comparisons precise.
    if stamp>=end.timestamp():
        end=boundary(local.date()+dt.timedelta(days=1))
    return str(end.date()),end.timestamp()

def shifts_terminal_for_cart(c,cart):
    row=None
    if cart.get('terminal_id'):row=c.execute('SELECT * FROM retail_terminals WHERE id=?',(cart['terminal_id'],)).fetchone()
    elif cart.get('device'):row=c.execute('SELECT * FROM retail_terminals WHERE device=?',(cart['device'],)).fetchone()
    elif cart.get('terminal'):
        rows=c.execute('SELECT * FROM retail_terminals WHERE name=?',(cart['terminal'],)).fetchall()
        if len(rows)==1:row=rows[0]
    return stores_terminal_details(c,row)

def shifts_open(c,terminal,stamp=None,store=None):
    stamp=shifts_clock() if stamp is None else stamp;store=store or terminal['store_id']
    settings=shifts_settings(c,store);day,deadline=shifts_period(stamp,settings['cutoff'])
    row=c.execute('SELECT * FROM retail_register_shifts WHERE terminal=? AND store=? AND closed IS NULL AND opened<=? AND deadline>? ORDER BY id DESC',(terminal['id'],store,stamp,stamp)).fetchone()
    if row:return dict(row)
    profile=stores_profile(c,store)
    body=dict(terminal_name=terminal['name'],store_name=profile['name'],logo=profile['receipt'].get('logo',''),cutoff=settings['cutoff'],timezone=settings['timezone'])
    ident=c.execute('INSERT INTO retail_register_shifts(terminal,store,business_date,opened,deadline,body) VALUES(?,?,?,?,?,?)',(terminal['id'],store,day,stamp,deadline,json.dumps(body))).lastrowid
    return dict(c.execute('SELECT * FROM retail_register_shifts WHERE id=?',(ident,)).fetchone())

def shifts_attach(c,ident,cart,stamp=None):
    if cart.get('training'):return
    terminal=shifts_terminal_for_cart(c,cart)
    if not terminal:return  # Never invent a terminal for legacy unregistered carts.
    shift=shifts_open(c,terminal,stamp,stores_id(cart))
    c.execute('INSERT OR IGNORE INTO retail_shift_carts VALUES(?,?)',(ident,shift['id']))

def shifts_event(c,shift,kind,reference,body,stamp=None):
    row=c.execute('SELECT closed FROM retail_register_shifts WHERE id=?',(shift,)).fetchone()
    if not row or row[0] is not None:raise Problem('This register shift has ended. Start a new transaction.',409)
    c.execute('INSERT INTO retail_shift_events VALUES(?,?,?,?,?)',(kind,str(reference),shift,shifts_clock() if stamp is None else stamp,json.dumps(body)))

def shifts_rehome(c,cart,terminal):
    if cart.get('training') or not terminal:return
    shift=shifts_open(c,terminal)
    previous=c.execute('SELECT shift FROM retail_shift_carts WHERE cart=?',(cart['id'],)).fetchone()
    if previous and previous[0]!=shift['id']:
        retail_event(c,cart['id'],'System','register-shift-transfer',dict(previous_shift=previous[0],shift=shift['id']))
    c.execute('INSERT INTO retail_shift_carts VALUES(?,?) ON CONFLICT(cart) DO UPDATE SET shift=excluded.shift',(cart['id'],shift['id']))
    cart.update(terminal_id=terminal['id'],terminal=terminal['name'])

def shifts_cart_event(c,cart,kind,reference,body,stamp=None):
    if cart.get('training'):return
    row=c.execute('SELECT shift FROM retail_shift_carts WHERE cart=?',(cart['id'],)).fetchone()
    if row:shifts_event(c,row[0],kind,reference,body,stamp)

def shifts_terminal_event(c,device,kind,reference,body):
    terminal=stores_terminal(c,device)
    if not terminal:return
    shift=shifts_open(c,terminal)
    shifts_event(c,shift['id'],kind,reference,body)

def shifts_unpaid(c,terminal):
    rows=[]
    for row in c.execute("SELECT * FROM pos_carts WHERE status='open'"):
        body=json.loads(row['body'])
        if body.get('training'):continue
        match=shifts_terminal_for_cart(c,body)
        if match and match['id']==terminal:
            name=c.execute('SELECT name FROM receipt_profiles WHERE profile_id=?',(row['owner'],)).fetchone()
            rows.append(dict(id=row['id'],owner=row['owner'],cashier=name[0] if name else 'Former employee',held=bool(body.get('held')),total=body['total'],items=len(body['lines']),revision=row['revision']))
    return rows

def shifts_report(c,ident):
    row=c.execute('SELECT * FROM retail_register_shifts WHERE id=?',(ident,)).fetchone()
    if not row:raise Problem('Register shift not found.',404)
    result=dict(row);meta=json.loads(result.pop('body'));result.update(meta)
    events=[dict(kind=r['kind'],reference=r['reference'],at=r['at'],**json.loads(r['body'])) for r in c.execute('SELECT * FROM retail_shift_events WHERE shift=? ORDER BY at,kind,reference',(ident,))]
    sales=[e for e in events if e['kind']=='sale'];voids=[e for e in events if e['kind']=='void'];refunds=[e for e in events if e['kind']=='refund'];advances=[e for e in events if e['kind']=='advance']
    cash=sum(e['sale'].get('tender',0)-e['sale'].get('change',0) for e in sales)
    cash_refunds=sum(e['refund'].get('cash',0) for e in refunds)
    advances_total=sum(e['advance']['amount'] for e in advances)
    result.update(events=events,completed=len(sales),voided=len(voids),sales_total=sum(e['sale']['total'] for e in sales),tax=sum(e['sale']['tax'] for e in sales),cash_rounding=sum(e['sale'].get('cash_rounding',0) for e in sales),cash=cash,store_credit=sum(e['sale'].get('store_credit',0) for e in sales),cash_refunds=cash_refunds,credit_refunds=sum(e['refund'].get('store_credit',0) for e in refunds),advances=advances_total,net_cash=cash-cash_refunds-advances_total,users=sorted({e.get('cashier','') for e in events}-{''}))
    return result

def shifts_close(c,shift,actor,automatic=False,stamp=None):
    stamp=shifts_clock() if stamp is None else stamp
    if shift['closed'] is not None:return
    rows=c.execute("SELECT p.* FROM pos_carts p JOIN retail_shift_carts s ON s.cart=p.id WHERE s.shift=? AND p.status='open'",(shift['id'],)).fetchall()
    if not automatic and shifts_unpaid(c,shift['terminal']):raise Problem('Open transactions remain on this terminal. Use Find to complete or cancel them before ending the shift.',409)
    for row in rows:
        if c.execute('SELECT 1 FROM pos_sales WHERE cart=?',(row['id'],)).fetchone():raise Problem('A paid receipt still has an open cart. Ask an administrator to review it before closing.',409)
        cart=pos_cart(row)
        name=c.execute('SELECT name FROM receipt_profiles WHERE profile_id=?',(row['owner'],)).fetchone()
        reason='Automatic end of business day — unpaid transaction'
        shifts_cart_event(c,cart,'void',row['id'],dict(cashier=name[0] if name else 'Former employee',owner=row['owner'],reason=reason,total=0,collected=0,original=cart),shift['deadline'])
        c.execute("UPDATE pos_carts SET status='discarded',revision=revision+1 WHERE id=? AND status='open'",(row['id'],))
        c.execute("UPDATE retail_adjustments SET status='denied',decided_by='System',decision_reason=? WHERE cart=? AND status='pending'",(reason,row['id']))
        retail_event(c,row['id'],actor,'business-day-void',dict(shift=shift['id'],business_date=shift['business_date'],original_total=cart['total'],total=0,collected=0,reason=reason))
    closed=shift['deadline'] if automatic else stamp
    c.execute('UPDATE retail_register_shifts SET closed=?,processed=?,actor=?,reason=? WHERE id=? AND closed IS NULL',(closed,stamp,actor,'end-of-business-day' if automatic else 'manual',shift['id']))
    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.fromtimestamp(stamp,dt.timezone.utc).isoformat(),actor,'Register shift #'+str(shift['id'])+' closed ('+('automatic' if automatic else 'manual')+'); business date '+shift['business_date'],''))

def shifts_sweep(c,stamp=None):
    stamp=shifts_clock() if stamp is None else stamp
    # Adopt only still-open, attributable legacy carts, without rewriting them.
    for row in c.execute("SELECT p.* FROM pos_carts p LEFT JOIN retail_shift_carts s ON s.cart=p.id WHERE p.status='open' AND s.cart IS NULL ORDER BY p.updated").fetchall():
        shifts_attach(c,row['id'],json.loads(row['body']),row['updated'])
    for shift in c.execute('SELECT * FROM retail_register_shifts WHERE closed IS NULL AND deadline<=? ORDER BY deadline,id',(stamp,)).fetchall():
        shifts_close(c,shift,'System',True,stamp)

def shifts_tick():
    with LOCK,connect() as c:
        if STOPPING or RESTART or MAINTENANCE_APPLYING:return
        shifts_sweep(c)
        c.commit()

def shifts_get(c,u,path,q):
    if path not in ('shift-status','shift-watch','shift-settings','shift-history','shift-report'):return None
    d={k:v[0] for k,v in q.items()}
    if path=='shift-settings':
        thrift_require(u,'manage_pos');return shifts_settings(c,d.get('store_id') or 'thrift-mart')
    if path=='shift-history':
        thrift_require(u,'view_pos_sales');store=d.get('store_id') or 'thrift-mart';stores_profile(c,store)
        start=d.get('from') or str(dt.date.today()-dt.timedelta(days=30));end=d.get('to') or str(dt.date.today())
        try:
            if dt.date.fromisoformat(start)>dt.date.fromisoformat(end):raise ValueError()
        except ValueError:raise Problem('Choose a valid report date range.')
        rows=c.execute('SELECT * FROM retail_register_shifts WHERE store=? AND business_date BETWEEN ? AND ? ORDER BY id DESC LIMIT 501',(store,start,end)).fetchall()
        return dict(shifts=[dict({k:r[k] for k in r.keys() if k!='body'},**json.loads(r['body'])) for r in rows[:500]],more=len(rows)>500)
    if path=='shift-report':
        try:ident=int(d.get('id',''))
        except ValueError:raise Problem('Choose a register shift.')
        report=shifts_report(c,ident)
        if not has_permission(u,'view_pos_sales'):
            terminal=devices_terminal(c,u,d)
            if report['terminal']!=terminal['id']:raise Problem('This shift belongs to another terminal.',403)
        return report
    terminal=devices_terminal(c,u,d)
    current=c.execute('SELECT id FROM retail_register_shifts WHERE terminal=? AND closed IS NULL ORDER BY id DESC',(terminal['id'],)).fetchone()
    last=c.execute('SELECT id FROM retail_register_shifts WHERE terminal=? AND closed IS NOT NULL ORDER BY id DESC',(terminal['id'],)).fetchone()
    if path=='shift-watch':
        closed=dict(c.execute('SELECT id,business_date,reason,closed FROM retail_register_shifts WHERE id=?',(last[0],)).fetchone()) if last else None
        cart=c.execute('SELECT status FROM pos_carts WHERE id=? AND owner=?',(d.get('cart',''),u.get('receipt_owner'))).fetchone()
        return dict(last=closed,cart_status=cart[0] if cart else None)
    return dict(terminal=terminal,settings=shifts_settings(c,terminal['store_id']),current=shifts_report(c,current[0]) if current else None,last=shifts_report(c,last[0]) if last else None,open=shifts_unpaid(c,terminal['id']))

def shifts_post(c,u,path,d,finish):
    if path=='shift-settings-save':
        thrift_require(u,'manage_pos');store=d.get('store_id') or 'thrift-mart';old=shifts_settings(c,store)
        if d.get('revision')!=old['revision']:raise Problem('Shift settings changed. Reopen before saving.',409)
        cutoff=d.get('cutoff')
        if not isinstance(cutoff,str) or not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d:[0-5]\d',cutoff):raise Problem('Choose an end-of-business-day time, including seconds.')
        if d.get('print_format') not in ('letter','receipt'):raise Problem('Choose Letter or receipt paper.')
        c.execute('INSERT INTO retail_shift_settings VALUES(?,?,?) ON CONFLICT(store) DO UPDATE SET revision=excluded.revision,body=excluded.body',(store,old['revision']+1,json.dumps(dict(cutoff=cutoff,print_format=d['print_format']))))
        return finish(shifts_settings(c,store),'Register shift settings saved; open shifts keep their scheduled closing time') or True
    if path=='shift-end':
        terminal=devices_terminal(c,u,d)
        if training_state(c,u,d)['enabled']:raise Problem('Exit training mode before closing a live register shift.',409)
        if d.get('confirmed') is not True:raise Problem('Confirm ending the shift for all cashiers on this terminal.')
        ident=pos_int(d.get('shift'),'shift',1)
        shift=c.execute('SELECT * FROM retail_register_shifts WHERE id=? AND terminal=?',(ident,terminal['id'])).fetchone()
        if not shift:raise Problem('Refresh the terminal shift before closing it.',409)
        if shift['closed'] is None:shifts_close(c,shift,u['name'])
        return finish(dict(report=shifts_report(c,ident)),'Terminal end shift confirmed #'+str(ident)) or True
    return None
