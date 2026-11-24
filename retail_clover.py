"""Additive Clover pilot settings and one-use, read-only desktop test approvals.

Embedded in server.py by prepare_web_assets.py. No Clover credentials or payments.
"""
CLOVER_PILOT_TICKETS = {}


def clover_pilot_init(c):
    c.execute('''CREATE TABLE IF NOT EXISTS retail_clover_pilot(
        terminal TEXT PRIMARY KEY REFERENCES retail_terminals(id),
        revision INTEGER NOT NULL, store_id TEXT NOT NULL, address TEXT NOT NULL,
        serial TEXT NOT NULL, merchant_id TEXT NOT NULL, updated_at TEXT NOT NULL,
        updated_by TEXT NOT NULL)''')


def clover_pilot_admin(c, u):
    row = c.execute('SELECT admin FROM users WHERE name=?', (u.get('name'),)).fetchone()
    if not u.get('admin') or not row or not row['admin']:
        raise Problem('An administrator must configure or test Clover.', 403)


def clover_pilot_terminal(c, d):
    if d.get('terminal'):
        row = c.execute('SELECT * FROM retail_terminals WHERE id=?', (pos_text(d['terminal'], 'a terminal identifier', 64),)).fetchone()
    else:
        row = stores_terminal(c, pos_text(d.get('device'), 'a registered device identifier', 64))
    terminal = stores_terminal_details(c, row)
    if not terminal or not terminal['enabled'] or devices_removed(c, terminal['id']):
        raise Problem('Select an enabled, registered terminal.', 409)
    return terminal


def clover_pilot_details(c, terminal):
    row = c.execute('SELECT * FROM retail_clover_pilot WHERE terminal=?', (terminal['id'],)).fetchone()
    return dict(terminal={k: terminal[k] for k in ('id', 'name', 'device', 'store_id', 'store_name')},
                settings=dict(row) if row else dict(revision=0, store_id=terminal['store_id'], address='', serial='', merchant_id=''),
                store_changed=bool(row and row['store_id'] != terminal['store_id']),
                authorized=False, payments_enabled=False, status='authorization_required')


def clover_pilot_get(c, u, query):
    clover_pilot_admin(c, u)
    d = {key: value[0] for key, value in query.items()}
    if d.get('terminal') or d.get('device'):
        return clover_pilot_details(c, clover_pilot_terminal(c, d))
    terminals = []
    for row in c.execute('SELECT * FROM retail_terminals WHERE enabled=1 ORDER BY name'):
        if not devices_removed(c, row['id']):
            terminal = stores_terminal_details(c, row)
            terminals.append({k: terminal[k] for k in ('id', 'name', 'device', 'store_id', 'store_name')})
    return {'terminals': terminals, 'payments_enabled': False}


def clover_pilot_post(c, u, path, d):
    clover_pilot_admin(c, u)
    terminal = clover_pilot_terminal(c, d)
    old = clover_pilot_details(c, terminal)
    if type(d.get('revision')) is not int or d['revision'] != old['settings']['revision']:
        raise Problem('Clover settings changed. Reopen the setup screen before continuing.', 409)
    if path == 'clover-settings-save':
        import ipaddress
        try:
            address = ipaddress.IPv4Address(d.get('address', ''))
            if not any(address in ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
                raise ValueError()
        except (ValueError, TypeError):
            raise Problem('Enter the private local IPv4 address shown in REST Pay Display.') from None
        serial = d.get('serial', '')
        merchant = d.get('merchant_id', '')
        if not isinstance(serial, str) or not re.fullmatch('[A-Za-z0-9]{6,64}', serial):
            raise Problem('Enter the Clover serial number printed on the device.')
        if not isinstance(merchant, str) or (merchant and not re.fullmatch('[A-Za-z0-9]{6,64}', merchant)):
            raise Problem('Enter a valid Clover merchant ID, or leave it blank until confirmed.')
        if d.get('store_id') != terminal['store_id']:
            raise Problem('The terminal store changed. Reopen and confirm its Clover settings.', 409)
        duplicate = c.execute('SELECT terminal FROM retail_clover_pilot WHERE upper(serial)=upper(?) AND terminal<>?', (serial, terminal['id'])).fetchone()
        if duplicate:
            raise Problem('This Clover is already assigned to another terminal. Review that assignment first.', 409)
        now = dt.datetime.now().astimezone().isoformat(timespec='seconds')
        c.execute('''INSERT INTO retail_clover_pilot VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(terminal) DO UPDATE SET revision=excluded.revision,store_id=excluded.store_id,
            address=excluded.address,serial=excluded.serial,merchant_id=excluded.merchant_id,
            updated_at=excluded.updated_at,updated_by=excluded.updated_by''',
            (terminal['id'], d['revision']+1, terminal['store_id'], str(address), serial.upper(), merchant.upper(), now, u['name']))
        c.execute('INSERT INTO audit VALUES(?,?,?,?)', (now, u['name'], 'Saved connection-only Clover pilot for '+terminal['name'], 'No payment capability enabled'))
        c.commit()
        return dict(ok=True, **clover_pilot_details(c, terminal))
    if path != 'clover-test-approval':
        raise Problem('Unknown Clover setup action.', 404)
    if not old['settings']['revision'] or old['store_changed']:
        raise Problem('Save Clover settings for this terminal’s current store before testing.', 409)
    device, nonce = d.get('device'), d.get('nonce')
    if (device != terminal['device'] or not isinstance(device, str) or not re.fullmatch('[0-9a-f]{32}', device)
            or not isinstance(nonce, str) or not re.fullmatch('[0-9a-f]{64}', nonce)):
        raise Problem('Run this test in DESK on the selected registered computer.', 403)
    now = time.time()
    for key, value in list(CLOVER_PILOT_TICKETS.items()):
        if value['expires'] < now or value['device'] == device:
            CLOVER_PILOT_TICKETS.pop(key, None)
    if len(CLOVER_PILOT_TICKETS) >= 100:
        raise Problem('Too many pending connection tests. Try again shortly.', 429)
    token = secrets.token_hex(32)
    CLOVER_PILOT_TICKETS[hashlib.sha256(token.encode()).hexdigest()] = dict(
        expires=now+60, device=device, nonce=nonce, session=u, terminal=terminal['id'],
        terminal_revision=terminal['revision'], revision=d['revision'], store_id=terminal['store_id'])
    return {'token': token, 'purpose': 'clover-network-check-only'}


def clover_pilot_redeem(c, d):
    token = d.get('token')
    if not isinstance(token, str) or not re.fullmatch('[0-9a-f]{64}', token):
        raise Problem('Invalid Clover connection-test approval.', 403)
    key = hashlib.sha256(token.encode()).hexdigest()
    ticket = CLOVER_PILOT_TICKETS.get(key)
    if (not ticket or ticket['expires'] < time.time() or ticket['device'] != d.get('device')
            or ticket['nonce'] != d.get('nonce')):
        raise Problem('Clover test approval expired or belongs to another computer.', 403)
    CLOVER_PILOT_TICKETS.pop(key, None)
    u = ticket['session']
    if not any(session is u for session in SESSIONS.values()) or session_expired(u, time.time()):
        raise Problem('The approving administrator must still be signed in.', 403)
    clover_pilot_admin(c, u)
    terminal = clover_pilot_terminal(c, {'terminal': ticket['terminal']})
    details = clover_pilot_details(c, terminal)
    if (terminal['device'] != ticket['device'] or terminal['revision'] != ticket['terminal_revision']
            or terminal['store_id'] != ticket['store_id'] or details['store_changed']
            or details['settings']['revision'] != ticket['revision']):
        raise Problem('Terminal or Clover settings changed. Start a new connection check.', 409)
    c.execute('INSERT INTO audit VALUES(?,?,?,?)', (dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        u['name'], 'Authorized read-only Clover network check on '+terminal['name'], 'No charge or sale created'))
    c.commit()
    return dict(purpose='clover-network-check-only', device=ticket['device'], nonce=ticket['nonce'],
                terminal_id=terminal['id'], terminal_name=terminal['name'], store_name=terminal['store_name'],
                address=details['settings']['address'], serial=details['settings']['serial'])
