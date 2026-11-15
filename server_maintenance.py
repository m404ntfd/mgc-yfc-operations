"""Once-daily shared-server updates; no desktop push or employee countdown."""

MAINTENANCE_MESSAGE='YFC OPERATIONS SERVER UPDATES & RESTARTS AT 4:00AM. SAVE ALL WORK AND EXIT APPLICATIONS UNTIL 04:05. APPLICATIONS WILL BE OFFLINE DURING THIS TIME'
MAINTENANCE_APPLYING=False

def maintenance_now(now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:raise ValueError('Use a timezone-aware clock.')
    now=now.astimezone(dt.timezone.utc)
    # US Central DST transitions, including the repeated hour in November.
    march=dt.datetime(now.year,3,8,8,tzinfo=dt.timezone.utc)
    march+=dt.timedelta(days=(6-march.weekday())%7)
    november=dt.datetime(now.year,11,1,7,tzinfo=dt.timezone.utc)
    november+=dt.timedelta(days=(6-november.weekday())%7)
    return now.astimezone(dt.timezone(dt.timedelta(hours=-5 if march<=now<november else -6)))

def maintenance_status(now=None):
    current=maintenance_now(now);minute=current.hour*60+current.minute
    return {'time':current.isoformat(),'timezone':'America/Chicago','banner':230<=minute<=241,
            'message':MAINTENANCE_MESSAGE,'server_version':updater.current(),'applying':MAINTENANCE_APPLYING}

def maintenance_check(server,now=None):
    global RESTART,MAINTENANCE_APPLYING
    current=maintenance_now(now)
    if current.hour!=4 or current.minute>=5 or os.environ.get('DISPATCH_LAUNCHER')!='1':return False
    path=DATA/'daily-maintenance.json'
    with LOCK:
        if STOPPING or RESTART or flow_active():return False
        if path.exists():
            try:
                if json.loads(path.read_text()).get('day')==str(current.date()):return False
            except (OSError,ValueError):return False  # damaged state must never trigger repeated restarts
        state={'day':str(current.date()),'started':current.isoformat(),'status':'checking'}
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(state));os.replace(temp,path)
    try:
        release=updater.check()
        if not release['available']:
            state['status']='current';path.write_text(json.dumps(state));return False
        updater.stage(release['latest'])
        with LOCK:
            if STOPPING or RESTART or flow_active():return False
            # All HTTP writes use LOCK. Drain their commits before freezing new writes.
            MAINTENANCE_APPLYING=True
            with connect() as c:
                c.execute('INSERT INTO audit VALUES(?,?,?,?)',(current.isoformat(),'System','Scheduled 04:00 server update',release['latest']))
                c.commit()
            state.update(status='restarting',version=release['latest']);path.write_text(json.dumps(state))
            RESTART=True
        server.shutdown()
        return True
    except Exception as exc:
        with LOCK:
            MAINTENANCE_APPLYING=False
            state.update(status='failed',error=str(exc));path.write_text(json.dumps(state))
        return False

def maintenance_worker(server):
    while not STOPPING and not RESTART:
        try:maintenance_check(server)
        except Exception as exc:
            # An unavailable state folder must not take down the server or cause a forced restart.
            print('Scheduled server update could not start: '+str(exc),flush=True)
        time.sleep(15)
