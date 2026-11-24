"""Shared, expiring online pickup pause. Existing dispatch records stay untouched."""

def online_requests_init(c):
    c.execute('''CREATE TABLE IF NOT EXISTS online_request_settings(
        id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL,
        paused_until REAL NOT NULL, changed_at REAL NOT NULL, actor TEXT NOT NULL)''')
    c.execute("INSERT OR IGNORE INTO online_request_settings VALUES(1,0,0,0,'')")


def online_requests_status(c):
    row=c.execute('SELECT * FROM online_request_settings WHERE id=1').fetchone()
    now=time.time();until=row['paused_until'] if row else 0
    paused=until>now
    return dict(service='coastyouth-online-requests',supported=True,paused=paused,
                status='paused' if paused else 'active',paused_until=until if paused else None,
                server_now=now,revision=row['revision'] if row else 0)


def online_requests_change(c,u,d):
    if not has_permission(u,'review_requests'):
        raise Problem('Review and approve requests permission is required to pause online requests.',403)
    current=online_requests_status(c)
    if type(d.get('revision')) is not int or d['revision']!=current['revision']:
        raise Problem('Online request availability changed. Refresh and try again.',409)
    resume=d.get('resume') is True
    hours=d.get('hours')
    if resume:
        if hours is not None:raise Problem('Choose either resume or a pause duration.')
    elif type(hours) is not int or hours not in (8,12,24) or 'resume' in d:
        raise Problem('Choose 8, 12, or 24 hours.')
    now=time.time();until=0 if resume else now+hours*3600
    c.execute('UPDATE online_request_settings SET revision=revision+1,paused_until=?,changed_at=?,actor=? WHERE id=1',
              (until,now,u['name']))
    details=json.dumps(dict(hours=None if resume else hours,paused_until=until,previous_until=current['paused_until']))
    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().astimezone().isoformat(timespec='seconds'),
              u['name'],'Resumed online requests' if resume else 'Paused online requests',details))
    return online_requests_status(c)


def online_requests_guard(c,u,d):
    # The website's existing integration account is deliberately submission-only.
    # Recognize it as well as the explicit marker, including older website builds.
    grants={key for key,value in u.get('grants',{}).items() if value}
    online=d.get('online_request') is True or (not u['admin'] and grants=={'submit_requests'})
    if d.get('id') or not online:return
    status=online_requests_status(c)
    if status['paused']:
        raise Problem('Online donation pickup requests are temporarily paused. Please try again when requests reopen.',
                      423,code='online_requests_paused',availability=status)
