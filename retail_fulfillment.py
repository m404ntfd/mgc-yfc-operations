"""Paid-sale follow-up, reusing sold slips and the existing dispatch save rules."""
def fulfillment_init(c):
    c.execute('CREATE TABLE IF NOT EXISTS retail_sale_followups(sale INTEGER PRIMARY KEY REFERENCES pos_sales(id),revision INTEGER NOT NULL,step TEXT NOT NULL,appointment TEXT)')

def fulfillment_sale(c,u,ident):
    ident=pos_int(ident,'receipt number',1)
    row=c.execute('SELECT * FROM pos_sales WHERE id=?',(ident,)).fetchone()
    if not row or (row['owner']!=u.get('receipt_owner') and not has_permission(u,'view_pos_sales')):raise Problem('Receipt not found or not available to this user.',404)
    return dict(id=ident,**json.loads(row['body']))

def fulfillment_saved(c,sale,ident):
    if any(l.get('pickup_slip') for l in sale['lines']):
        c.execute("INSERT OR IGNORE INTO retail_sale_followups VALUES(?,1,'pickup',NULL)",(ident,))

def fulfillment_context(c,u,ident):
    sale=fulfillment_sale(c,u,ident)
    row=c.execute('SELECT * FROM retail_sale_followups WHERE sale=?',(ident,)).fetchone()
    slip=c.execute('SELECT * FROM thrift_pickups WHERE sale=?',(ident,)).fetchone()
    return dict(sale=sale,followup=dict(row) if row else None,pickup=dict(sale=ident,revision=slip['revision'],**json.loads(slip['body'])) if slip else None,can_schedule=has_permission(u,'view_schedule') and has_permission(u,'create_appointments'))

def fulfillment_get(c,u,path,q):
    if path=='pickup-followup':return fulfillment_context(c,u,int(q.get('sale',['0'])[0]))
    if path=='pickup-pending':
        return dict(pending=[dict(r) for r in c.execute("SELECT f.* FROM retail_sale_followups f JOIN pos_sales s ON s.id=f.sale WHERE s.owner=? AND f.step<>'done' ORDER BY f.sale",(u.get('receipt_owner'),))])
    return None

def fulfillment_post(c,u,d,finish):
    ident=pos_int(d.get('sale'),'receipt number',1);context=fulfillment_context(c,u,ident);f=context['followup']
    if not f:raise Problem('No pickup follow-up is needed for this receipt.')
    if d.get('revision')!=f['revision']:raise Problem('Follow-up changed. Reopen it to continue.',409)
    action=d.get('action');transitions={('pickup','skip'):'done',('pickup','slip'):'slip',('slip','printed'):'delivery',('delivery','skip'):'done',('scheduling','skip'):'done',('delivery','schedule'):'scheduling'}
    step=transitions.get((f['step'],action))
    if not step:raise Problem('This follow-up step has already changed. Reopen it.',409)
    if action=='printed' and not context['pickup']:raise Problem('Save the sold slip before confirming it printed.')
    if action=='schedule' and not context['can_schedule']:raise Problem('View schedule and Create appointments permissions are required. The saved slip is available for an authorized scheduler.',403)
    c.execute('UPDATE retail_sale_followups SET step=?,revision=revision+1 WHERE sale=?',(step,ident))
    cart=c.execute('SELECT cart FROM pos_sales WHERE id=?',(ident,)).fetchone()[0]
    retail_event(c,cart,u['name'],'pickup-followup-'+action,{})
    return finish(fulfillment_context(c,u,ident),'Paid sale pickup follow-up: '+action)

def fulfillment_delivery_prepare(c,u,d):
    ident=pos_int(d.get('retail_sale'),'receipt number',1)
    context=fulfillment_context(c,u,ident);f=context['followup']
    if not context['can_schedule']:raise Problem('View schedule and Create appointments permissions required.',403)
    if not f or not context['pickup']:raise Problem('Save and print the sold slip before scheduling delivery.')
    if d.get('id') or d.get('type')!='Delivery':raise Problem('This follow-up creates a new delivery only.')
    if f['appointment']:
        if not c.execute('SELECT 1 FROM jobs WHERE id=?',(f['appointment'],)).fetchone():raise Problem('The linked appointment was removed. Ask a manager to review the sold slip.',409)
        return f
    if f['step']!='scheduling':raise Problem('Choose delivery from the paid sale follow-up first.',409)
    return f

def fulfillment_delivery_saved(c,u,ident,jid):
    f=c.execute('SELECT * FROM retail_sale_followups WHERE sale=?',(ident,)).fetchone()
    if not f or f['appointment']:raise Problem('This receipt already has a linked delivery.',409)
    slip=c.execute('SELECT * FROM thrift_pickups WHERE sale=?',(ident,)).fetchone()
    if not slip:raise Problem('Sold slip no longer exists.',409)
    body=json.loads(slip['body']);body.update(status='awaiting_delivery',dispatch_reference=jid,updated_by=u['name'],updated_at=dt.datetime.now().astimezone().isoformat())
    c.execute('UPDATE thrift_pickups SET revision=revision+1,body=? WHERE sale=?',(json.dumps(body),ident))
    c.execute("UPDATE retail_sale_followups SET revision=revision+1,step='done',appointment=? WHERE sale=?",(jid,ident))
