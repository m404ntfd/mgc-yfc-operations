"""MGC YFC Operations Server: trusted-local-network scheduling server. Python 3.11+."""
import datetime as dt
import hashlib, hmac, json, os, secrets, socket, sqlite3, threading, time
import updater
import tempfile, zipfile, base64, re, queue, math
from contextlib import contextmanager, closing
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs,urlencode
from urllib.request import Request,urlopen

try:
    import requests
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
    from py_vapid import Vapid
    from pywebpush import webpush as WebPush, WebPushException
except ImportError:
    WebPush = None

WEB_ASSETS={} # prepared by prepare_web_assets.py

def web_asset(key):
    value=WEB_ASSETS.get(key)
    if value:return base64.b64decode(value)
    if key=='gif':return base64.b64decode(''.join(part.read_text() for part in sorted((ROOT/'assets').glob('plug-*.b64'))))
    return base64.b64decode(json.loads((ROOT/'assets/home-icons.json').read_text())[key])

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('DISPATCH_DATA', ROOT/'data'))
DATA.mkdir(parents=True, exist_ok=True)
DB=DATA/'schedule.db'
LOCK=threading.RLock()
SESSIONS={}
MOBILE_MEDIA={}
ATTEMPTS={}
CLOCK_SESSIONS={}
RESTART=False
STOPPING=False
STARTED=time.time()
UPDATE_STATUS={'available':False}
def check_release_status():
    result=updater.check()
    UPDATE_STATUS['available']=bool(result.get('available'))
    return result

def monitor_release_status():
    while True:
        try: check_release_status()
        except Exception: pass  # GitHub failure does not mean the store server is offline.
        time.sleep(3600)


@contextmanager
def connect():
    c=sqlite3.connect(DB, timeout=15)
    c.row_factory=sqlite3.Row
    try:
        with c: yield c
    finally: c.close()

# The worker is served from the app root. It never caches application pages or data.
PUSH_WORKER = b"""
self.addEventListener('push', event => {
  event.waitUntil(self.registration.showNotification('YFC Operations', {
    body: 'You have a new message.',
    icon: '/app-icon-192.png',
    tag: 'yfc-message'
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async () => {
    const destination = new URL('/#comms', self.location.origin);
    const windows = await clients.matchAll({type: 'window', includeUncontrolled: true});
    const app = windows.find(client => ['/', '/mobile', '/mobile/'].includes(new URL(client.url).pathname));
    if (app) {
      await app.focus();
      app.postMessage({type: 'open-comms'});
    } else {
      await clients.openWindow(destination.href);
    }
  })());
});
"""

PUSH_QUEUE = queue.Queue(maxsize=128)


def push_supported(handler):
    host = handler.headers.get('Host', '')
    return (handler.external_scheme() == 'https' or
            re.fullmatch(r'(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?', host, re.I))


def push_key(c, *, create=False):
    if WebPush is None:
        return None
    row = c.execute('SELECT private_key FROM comm_push_key WHERE id=1').fetchone()
    if row:
        return Vapid.from_string(row[0])
    if create:
        key = Vapid()
        key.generate_keys()
        der = key.private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
        c.execute('INSERT INTO comm_push_key VALUES(1,?)', (base64.urlsafe_b64encode(der).decode(),))
        c.commit()
        return key
    return None


def push_device(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{32}', value))


def push_subscription(value):
    """Only send HTTPS requests to known browser push providers."""
    if not isinstance(value, dict) or not isinstance(value.get('keys'), dict):
        raise Problem('Invalid notification subscription.')
    endpoint = value.get('endpoint')
    if not isinstance(endpoint, str) or not re.fullmatch(r'https://[!-~]{1,2000}', endpoint):
        raise Problem('Invalid push endpoint.')
    try:
        url = urlsplit(endpoint)
        host = url.hostname or ''
    except ValueError:
        raise Problem('Invalid push endpoint.')
    allowed = (host in ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'push.services.mozilla.com')
               or host.endswith(('.push.apple.com', '.notify.windows.com')))
    if not allowed or url.netloc.lower() != host or not url.path or url.fragment:
        raise Problem('This browser push service is not supported.')
    keys = {}
    for name, length in (('auth', 16), ('p256dh', 65)):
        key = value['keys'].get(name)
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', key):
            raise Problem('Invalid notification subscription key.')
        try:
            decoded = base64.urlsafe_b64decode(key + '=' * (-len(key) % 4))
        except ValueError:
            raise Problem('Invalid notification subscription key.')
        if len(decoded) != length or (name == 'p256dh' and decoded[0] != 4):
            raise Problem('Invalid notification subscription key.')
        keys[name] = key
    return {'endpoint': endpoint, 'keys': keys}


def push_settings(handler, c, account, query):
    if not push_supported(handler) or WebPush is None:
        return handler.send({'available': False, 'reason': 'runtime' if WebPush is None else 'https'})
    key = push_key(c, create=True)
    public = key.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    device = query.get('device', [''])[0]
    enabled = c.execute('SELECT 1 FROM comm_push_devices WHERE device=? AND account=?', (device, account)).fetchone()
    return handler.send({'available': True, 'enabled': bool(enabled),
                         'publicKey': base64.urlsafe_b64encode(public).decode().rstrip('=')})


def push_update(handler, c, account, d):
    device, enabled = d.get('device'), d.get('enabled')
    if not push_device(device) or type(enabled) is not bool:
        raise Problem('Invalid notification settings.')
    if not enabled:
        c.execute('DELETE FROM comm_push_devices WHERE device=? AND account=?', (device, account))
    else:
        if not push_supported(handler) or not push_key(c):
            raise Problem('Push notifications are unavailable at this address.', 403)
        subscription = push_subscription(d.get('subscription'))
        count = c.execute('SELECT COUNT(*) FROM comm_push_devices WHERE account=? AND device!=?',
                          (account, device)).fetchone()[0]
        if count >= 12:
            raise Problem('This account has reached its device limit. Turn off notifications on an existing device first.')
        c.execute('INSERT OR REPLACE INTO comm_push_devices VALUES(?,?,?,?)',
                  (device, account, subscription['endpoint'], json.dumps(subscription)))
    c.commit()
    return handler.send({'enabled': enabled})


def push_deliver(session, thread, message, author):
    with LOCK, connect() as c:
        key = push_key(c)
        if not key:
            return
        devices = c.execute("""SELECT d.* FROM comm_members a
            JOIN comm_push_devices d ON d.account=a.account
            JOIN receipt_profiles p ON p.profile_id=d.account JOIN users u ON u.name=p.name
            WHERE a.thread=? AND a.account!=? AND a.seen<?""", (thread, author, message)).fetchall()
        devices = [d for d in devices if comm_preferences(c, d['account'])['alerts']]
    for device in devices:
        # Check again before sending so sign-out and preference changes take effect.
        with LOCK, connect() as c:
            current = c.execute("""SELECT 1 FROM comm_push_devices d JOIN comm_members a ON a.account=d.account
                WHERE d.device=? AND d.account=? AND d.subscription=? AND a.thread=? AND a.seen<?
                AND NOT EXISTS(SELECT 1 FROM comm_hidden_groups h WHERE h.account=a.account AND h.thread=a.thread)
                AND NOT EXISTS(SELECT 1 FROM comm_hidden_messages h WHERE h.account=a.account AND h.message=?)""",
                                (device['device'], device['account'], device['subscription'], thread, message, message)).fetchone()
            if not current or not comm_preferences(c, device['account'])['alerts']:
                continue
        try:
            WebPush(subscription_info=json.loads(device['subscription']), data='{}', vapid_private_key=key,
                    vapid_claims={'sub': 'https://operations.coastyfc.com'}, ttl=300,
                    timeout=5, requests_session=session, headers={'Topic': 'yfc-message'})
        except WebPushException as error:
            status = error.response.status_code if error.response is not None else 0
            if status in (404, 410):
                with LOCK, connect() as c:
                    c.execute('DELETE FROM comm_push_devices WHERE device=? AND subscription=?',
                              (device['device'], device['subscription']))
            else:
                print(f'Web Push provider rejected a notification (status {status}).')
        except Exception:
            print('Unable to reach a Web Push provider.')


def push_worker():
    class PushSession(requests.Session):
        def post(self, url, *args, **kwargs):
            # Keep validation effective even if the push provider redirects.
            return super().post(url, *args, **{**kwargs, 'allow_redirects': False})

    with PushSession() as session:
        while True:
            thread, message, author, queued_at = PUSH_QUEUE.get()
            try:
                if time.monotonic() - queued_at < 300:
                    push_deliver(session, thread, message, author)
            except Exception:
                print('Unable to process a Web Push notification.')
            finally:
                PUSH_QUEUE.task_done()


def can_review_requests(u):
    return has_permission(u,'manage_staff_schedule')


def request_review_scope(u):
    if u['admin']:
        return 'SELECT profile_id FROM receipt_profiles', ()
    if not can_review_requests(u):
        return 'SELECT profile_id FROM receipt_profiles WHERE 0', ()
    # Roles override individual grants, as in Handler.user().
    return ('''SELECT p.profile_id FROM receipt_profiles p JOIN users u ON u.name=p.name
        LEFT JOIN user_roles a ON a.name=u.name LEFT JOIN permission_roles r ON r.id=a.role_id
        LEFT JOIN user_grants g ON g.name=u.name
        WHERE p.profile_id=? OR (u.admin=0 AND
              COALESCE(json_extract(COALESCE(r.body,g.body,'{}'),'$.manage_staff_schedule'),0)=0)''',
        (u['receipt_owner'],))


def can_review_request(c,u,account):
    scope,args=request_review_scope(u)
    return c.execute(f'SELECT ? IN ({scope})',(account,*args)).fetchone()[0]


def user_identity(c,account,name):
    row=c.execute('SELECT username,first,middle,last FROM user_identity WHERE account=?',(account,)).fetchone()
    return dict(row) if row else dict(username=name,first='',middle='',last='')


def find_login_user(c,username):
    return c.execute("""SELECT u.* FROM users u LEFT JOIN receipt_profiles p ON p.name=u.name
        LEFT JOIN user_identity i ON i.account=p.profile_id
        WHERE COALESCE(i.username,u.name)=? COLLATE NOCASE""",(username,)).fetchone()


def check_username_available(c,username,account=None):
    identity=c.execute('SELECT account FROM user_identity WHERE username=?',(username,)).fetchone()
    reserved=c.execute('SELECT u.name,p.profile_id FROM users u LEFT JOIN receipt_profiles p ON p.name=u.name WHERE u.name=?',
                       (username,)).fetchone()
    if (identity and identity['account']!=account) or (reserved and (account is None or reserved['profile_id']!=account)):
        raise Problem('That username is already in use.',409)


def identity_target(c,u,name):
    if not has_permission(u,'rename_users'): raise Problem('Edit user names permission required.',403)
    row=c.execute('SELECT u.name,u.admin,p.profile_id FROM users u JOIN receipt_profiles p ON p.name=u.name WHERE u.name=?',
                  (name,)).fetchone()
    if not row: raise Problem('User not found.',404)
    if row['admin'] and not u['admin']: raise Problem('Only an administrator can edit this account.',403)
    return row


def profile_get(handler,c,u,path):
    account=u['receipt_owner']
    if path=='identity':
        return handler.send(user_identity(c,account,u['name']))
    if path=='mine':
        row=c.execute("""SELECT account,approved IS NOT NULL AS approved,pending_revision,status
                         FROM user_profile_photos WHERE account=?""",(account,)).fetchone()
        return handler.send(dict(row) if row else {'approved':False,'pending_revision':None,'status':'none'})
    if path=='queue':
        if not can_review_requests(u): raise Problem('Profile photo approval permission required.',403)
        scope,args=request_review_scope(u)
        rows=c.execute(f"""SELECT p.account,u.name,p.pending_revision FROM user_profile_photos p
            JOIN receipt_profiles r ON r.profile_id=p.account JOIN users u ON u.name=r.name
            WHERE p.pending_revision IS NOT NULL AND p.account IN ({scope}) ORDER BY u.name""",args)
        return handler.send({'requests':[{**dict(row),'own':row['account']==account} for row in rows]})
    parts=path.split('/')
    if len(parts)==2 and parts[0]=='photo':
        target=parts[1]
        row=c.execute("""SELECT p.approved FROM user_profile_photos p JOIN receipt_profiles r ON r.profile_id=p.account
            JOIN users u ON u.name=r.name WHERE p.account=?""",(target,)).fetchone()
        if row and row[0]: return handler.send(row[0],kind='image/jpeg')
    if len(parts)==3 and parts[0]=='pending' and (parts[1]==account or can_review_request(c,u,parts[1])):
        row=c.execute('SELECT pending FROM user_profile_photos WHERE account=? AND pending_revision=?',tuple(parts[1:])).fetchone()
        if row and row[0]: return handler.send(row[0],kind='image/jpeg')
    raise Problem('Profile photo not found.',404)


def profile_post(handler,c,u,path,d):
    account=u['receipt_owner']
    if path=='upload':
        encoded=d.get('image')
        if not isinstance(encoded,str) or len(encoded)>400000:
            raise Problem('Choose a profile photo smaller than 300 KB.')
        try: raw=base64.b64decode(encoded,validate=True)
        except ValueError: raise Problem('Invalid profile photo.')
        if not 16<=len(raw)<=300000 or not raw.startswith(b'\xff\xd8\xff') or not raw.endswith(b'\xff\xd9'):
            raise Problem('Choose a valid JPEG profile photo.')
        revision=secrets.token_hex(12)
        if u['admin']:
            c.execute("""INSERT INTO user_profile_photos(account,approved,approved_revision,status) VALUES(?,?,?,'approved')
                ON CONFLICT(account) DO UPDATE SET approved=excluded.approved,approved_revision=excluded.approved_revision,
                pending=NULL,pending_revision=NULL,status='approved'""",(account,raw,revision))
        else:
            c.execute("""INSERT INTO user_profile_photos(account,pending,pending_revision,status) VALUES(?,?,?,'pending')
                ON CONFLICT(account) DO UPDATE SET pending=excluded.pending,pending_revision=excluded.pending_revision,status='pending'""",(account,raw,revision))
    elif path=='review':
        target,revision,decision=d.get('account'),d.get('revision'),d.get('decision')
        if not isinstance(target,str) or not isinstance(revision,str) or decision not in ('approve','reject'):
            raise Problem('Invalid review decision.')
        if not can_review_request(c,u,target): raise Problem('This request requires an administrator or an authorized manager.',403)
        if decision=='approve':
            query="""UPDATE user_profile_photos SET approved=pending,approved_revision=pending_revision,pending=NULL,pending_revision=NULL,status='approved'
                     WHERE account=? AND pending_revision=?"""
        else:
            query="""UPDATE user_profile_photos SET pending=NULL,pending_revision=NULL,status='rejected'
                     WHERE account=? AND pending_revision=?"""
        if not c.execute(query,(target,revision)).rowcount:
            raise Problem('This request has changed or was already reviewed. Refresh the list.',409)
        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),
                  u['name'],f'Profile photo review: {decision}',target))
    else:
        raise Problem('Not found.',404)
    c.commit()
    return handler.send({'ok':True})


def init_comms(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS user_identity(
            account TEXT PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            first TEXT NOT NULL, middle TEXT NOT NULL, last TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_profile_photos (
            account TEXT PRIMARY KEY, approved BLOB, pending BLOB,
            pending_revision TEXT, status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comm_push_key (id INTEGER PRIMARY KEY, private_key TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS comm_push_devices (
            device TEXT PRIMARY KEY, account TEXT NOT NULL, endpoint TEXT UNIQUE NOT NULL, subscription TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS comm_push_account ON comm_push_devices(account);
        CREATE TABLE IF NOT EXISTS comm_threads (
            id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT, direct_key TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS comm_members (
            thread INTEGER NOT NULL, account TEXT NOT NULL, seen INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (thread, account)
        );
        CREATE INDEX IF NOT EXISTS comm_member_account ON comm_members(account, thread);
        CREATE TABLE IF NOT EXISTS comm_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, thread INTEGER NOT NULL, author TEXT NOT NULL,
            author_name TEXT NOT NULL, sent REAL NOT NULL, text TEXT NOT NULL, filename TEXT
        );
        CREATE INDEX IF NOT EXISTS comm_message_thread ON comm_messages(thread, id);
        CREATE TABLE IF NOT EXISTS comm_files (id INTEGER PRIMARY KEY, data BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS comm_saved (
            account TEXT NOT NULL, message INTEGER NOT NULL, PRIMARY KEY (account, message)
        );
        CREATE TABLE IF NOT EXISTS comm_hidden_groups (
            account TEXT NOT NULL, thread INTEGER NOT NULL, PRIMARY KEY(account,thread)
        );
        CREATE TABLE IF NOT EXISTS comm_hidden_messages (
            account TEXT NOT NULL, message INTEGER NOT NULL, PRIMARY KEY(account,message)
        );
        CREATE TABLE IF NOT EXISTS comm_prefs (
            account TEXT PRIMARY KEY, body TEXT NOT NULL
        );
    """)

    if not any(row[1]=='approved_revision' for row in c.execute('PRAGMA table_info(user_profile_photos)')):
        c.execute("ALTER TABLE user_profile_photos ADD COLUMN approved_revision TEXT")


COMM_DEFAULTS = dict(direct=True, order='recent', dm='all', group='all', alerts=True)
COMM_MESSAGES = """SELECT m.*, COALESCE(u.name,m.author_name) AS sender,
    EXISTS(SELECT 1 FROM user_profile_photos f WHERE f.account=p.profile_id AND u.name IS NOT NULL AND f.approved IS NOT NULL) AS photo,
    EXISTS(SELECT 1 FROM comm_saved s WHERE s.account=? AND s.message=m.id) AS saved
    FROM comm_messages m LEFT JOIN receipt_profiles p ON p.profile_id=m.author
    LEFT JOIN users u ON u.name=p.name"""


def comm_preferences(c, account):
    row = c.execute('SELECT body FROM comm_prefs WHERE account=?', (account,)).fetchone()
    return {**COMM_DEFAULTS, **(json.loads(row[0]) if row else {})}


def comm_number(value, default=0):
    if isinstance(value, int) and not isinstance(value, bool) and 0 < value <= 2**63-1:
        return value
    if isinstance(value, str) and re.fullmatch(r'[0-9]{1,18}', value):
        return int(value)
    return default


def comm_member(c, thread, account):
    row = c.execute('SELECT * FROM comm_threads t JOIN comm_members a ON a.thread=t.id WHERE t.id=? AND a.account=?',
                    (thread, account)).fetchone()
    if not row:
        raise Problem('Conversation not found.', 404)
    return row


def comm_directory(c, account):
    return [dict(row) for row in c.execute("""SELECT p.profile_id AS id, u.name,
        EXISTS(SELECT 1 FROM user_profile_photos f WHERE f.account=p.profile_id AND f.approved IS NOT NULL) AS photo
        FROM users u JOIN receipt_profiles p ON p.name=u.name
        WHERE p.profile_id!=? ORDER BY u.name COLLATE NOCASE""", (account,))]


def comm_get(handler, c, u, path, query):
    account = u['receipt_owner']
    if not account:
        raise Problem('Account not found.', 403)
    if path == 'push':
        return push_settings(handler, c, account, query)
    if path == 'status':
        rows = c.execute("""SELECT a.thread AS id, COUNT(*) AS unread, MAX(m.id) AS latest
            FROM comm_members a JOIN comm_messages m ON m.thread=a.thread AND m.id>a.seen
            WHERE a.account=? AND m.author!=?
              AND NOT EXISTS(SELECT 1 FROM comm_hidden_groups h WHERE h.account=a.account AND h.thread=a.thread)
              AND NOT EXISTS(SELECT 1 FROM comm_hidden_messages h WHERE h.account=a.account AND h.message=m.id)
            GROUP BY a.thread""", (account, account))
        review=can_review_requests(u)
        scope,args=request_review_scope(u)
        pending=c.execute(f'SELECT COUNT(*) FROM user_profile_photos WHERE pending_revision IS NOT NULL AND account IN ({scope})',
                          args).fetchone()[0] if review else 0
        photo=c.execute('SELECT approved_revision,approved IS NOT NULL,pending_revision IS NOT NULL FROM user_profile_photos WHERE account=?',
                        (account,)).fetchone()
        schedule_review=review
        schedule_pending=c.execute(f"""SELECT COUNT(*) FROM work_requests q JOIN receipt_profiles p ON p.profile_id=q.account
            JOIN users u ON u.name=p.name WHERE q.status='pending' AND q.account IN ({scope})""",args).fetchone()[0] if schedule_review else 0
        return handler.send({'schedule_review':schedule_review,'pending_schedule':schedule_pending,'profile_account':account,'profile_photo_revision':(photo[0] or 'existing') if photo and photo[1] else None,'profile_photo_pending':bool(photo and photo[2]),'unread': [dict(r) for r in rows], 'alerts': comm_preferences(c, account)['alerts'],
                             'photo_review':review,'pending_photos':pending})
    if path == 'inbox':
        threads = [dict(r) for r in c.execute("""SELECT t.id,t.kind,t.title,a.seen,
            EXISTS(SELECT 1 FROM comm_hidden_groups h WHERE h.account=a.account AND h.thread=t.id) AS hidden,
            COALESCE((SELECT MAX(m.id) FROM comm_messages m WHERE m.thread=t.id),0) AS latest
            FROM comm_threads t JOIN comm_members a ON a.thread=t.id WHERE a.account=?
            ORDER BY latest DESC,t.id DESC""", (account,))]
        for thread in threads:
            members = c.execute("""SELECT u.name,a.account FROM comm_members a
                JOIN receipt_profiles p ON p.profile_id=a.account JOIN users u ON u.name=p.name
                WHERE a.thread=? AND a.account!=? ORDER BY u.name COLLATE NOCASE""", (thread['id'], account))
            people = members.fetchall()
            thread['members'] = [r['name'] for r in people]
            if thread['kind'] == 'group' and has_permission(u,'manage_comms_groups'):
                thread['member_ids'] = [r['account'] for r in people]
            if thread['kind'] == 'dm':
                thread['title'] = next(iter(thread['members']), 'Former user')
        return handler.send({'threads': threads, 'team': comm_directory(c, account),
                             'preferences': comm_preferences(c, account), 'account': account,
                             'manage_groups': has_permission(u,'manage_comms_groups')})
    if path == 'messages':
        thread = comm_number(query.get('thread', [''])[0])
        before = comm_number(query.get('before', [''])[0], 2**63-1)
        comm_member(c, thread, account)
        rows = c.execute(COMM_MESSAGES + ''' WHERE m.thread=? AND m.id<?
                         AND NOT EXISTS(SELECT 1 FROM comm_hidden_messages h WHERE h.account=? AND h.message=m.id)
                         ORDER BY m.id DESC LIMIT 101''', (account, thread, before, account)).fetchall()
        return handler.send({'messages': [dict(r) for r in reversed(rows[:100])], 'older': len(rows)>100})
    if path in ('saved', 'files'):
        condition = ('EXISTS(SELECT 1 FROM comm_saved s WHERE s.account=a.account AND s.message=m.id)'
                     if path == 'saved' else 'm.filename IS NOT NULL')
        rows = c.execute(COMM_MESSAGES + ' JOIN comm_members a ON a.thread=m.thread WHERE a.account=? AND '
                         + condition + ''' AND NOT EXISTS(SELECT 1 FROM comm_hidden_messages h
                         WHERE h.account=a.account AND h.message=m.id) ORDER BY m.id DESC''', (account, account))
        return handler.send({'messages': [dict(r) for r in rows]})
    if path.startswith('file/'):
        row = c.execute("""SELECT f.data FROM comm_files f JOIN comm_messages m ON m.id=f.id
            JOIN comm_members a ON a.thread=m.thread WHERE f.id=? AND a.account=?
            AND NOT EXISTS(SELECT 1 FROM comm_hidden_messages h WHERE h.account=a.account AND h.message=m.id)""",
                        (comm_number(path[5:]), account)).fetchone()
        if not row:
            raise Problem('File not found.', 404)
        return handler.send(row[0], kind='application/octet-stream', attachment=True)
    raise Problem('Not found.', 404)


def comm_post(handler, c, u, path, d):
    account = u['receipt_owner']
    if not account:
        raise Problem('Account not found.', 403)
    if path == 'push':
        return push_update(handler, c, account, d)
    if path == 'preferences':
        if (set(d) != set(COMM_DEFAULTS) or type(d['direct']) is not bool or type(d['alerts']) is not bool
                or d['order'] not in ('recent', 'unread') or any(d[k] not in ('all', 'unread') for k in ('dm', 'group'))):
            raise Problem('Choose valid communication preferences.')
        c.execute('INSERT OR REPLACE INTO comm_prefs VALUES(?,?)', (account, json.dumps(d)))
        c.commit()
        return handler.send(d)
    if path in ('create','manage-group'):
        kind, members, title = d.get('kind'), d.get('members'), d.get('title', '')
        if path=='manage-group' or kind=='group':
            if not has_permission(u,'manage_comms_groups'):
                raise Problem('Create and manage groups permission required.',403)
            kind='group'
        if kind not in ('dm', 'group') or not isinstance(members, list) or not 1 <= len(members) <= 50:
            raise Problem('Select members for this conversation.')
        if any(not isinstance(m, str) for m in members) or len(set(members)) != len(members):
            raise Problem('Select distinct team members.')
        if not set(members) <= {r['id'] for r in comm_directory(c, account)}:
            raise Problem('Select current team members.')
        direct_key = None
        if kind == 'dm':
            if len(members) != 1:
                raise Problem('Choose one recipient.')
            direct_key = ':'.join(sorted([account, *members]))
            row = c.execute('SELECT id FROM comm_threads WHERE direct_key=?', (direct_key,)).fetchone()
            if row:
                return handler.send({'id': row[0]})
            if not comm_preferences(c, members[0])['direct']:
                raise Problem('This person has turned off direct messages.', 403)
            title = None
        elif not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
            raise Problem('Enter a group name (1–80 characters).')
        else:
            title = title.strip()
        if path=='manage-group':
            thread=comm_number(d.get('thread'))
            if comm_member(c,thread,account)['kind']!='group':
                raise Problem('Group not found.',404)
            c.execute('UPDATE comm_threads SET title=? WHERE id=?',(title,thread))
            current={r[0] for r in c.execute('SELECT account FROM comm_members WHERE thread=? AND account!=?',(thread,account))}
            removed=current-set(members)
            c.executemany('DELETE FROM comm_members WHERE thread=? AND account=?',[(thread,p) for p in removed])
            latest=c.execute('SELECT COALESCE(MAX(id),0) FROM comm_messages WHERE thread=?',(thread,)).fetchone()[0]
            c.executemany('INSERT INTO comm_members(thread,account,seen) VALUES(?,?,?)',
                          [(thread,p,latest) for p in members if p not in current])
            c.commit()
            return handler.send({'id':thread})
        thread = c.execute('INSERT INTO comm_threads(kind,title,direct_key) VALUES(?,?,?)',
                           (kind, title, direct_key)).lastrowid
        c.executemany('INSERT INTO comm_members(thread,account) VALUES(?,?)',
                      [(thread, member) for member in [account, *members]])
        c.commit()
        return handler.send({'id': thread})
    if path=='hide-group':
        thread=comm_number(d.get('thread'))
        hidden=d.get('hidden')
        if type(hidden) is not bool: raise Problem('Choose whether to hide the group.')
        if comm_member(c,thread,account)['kind']!='group': raise Problem('Group not found.',404)
        if hidden:
            c.execute('INSERT OR IGNORE INTO comm_hidden_groups VALUES(?,?)',(account,thread))
        else:
            c.execute('DELETE FROM comm_hidden_groups WHERE account=? AND thread=?',(account,thread))
        c.commit()
        return handler.send({'ok':True})
    if path=='delete-message':
        message=comm_number(d.get('id'))
        row=c.execute('SELECT thread FROM comm_messages WHERE id=?',(message,)).fetchone()
        if comm_member(c,row['thread'] if row else 0,account)['kind']!='dm':
            raise Problem('Only direct messages can be deleted from your view.',403)
        c.execute('INSERT OR IGNORE INTO comm_hidden_messages VALUES(?,?)',(account,message))
        c.execute('DELETE FROM comm_saved WHERE account=? AND message=?',(account,message))
        c.commit()
        return handler.send({'ok':True})
    if path == 'save':
        message, save = comm_number(d.get('id')), d.get('save')
        if type(save) is not bool:
            raise Problem('Choose whether to save the message.')
        row = c.execute('SELECT thread FROM comm_messages WHERE id=?', (message,)).fetchone()
        comm_member(c, row[0] if row else 0, account)
        c.execute('INSERT OR IGNORE INTO comm_saved VALUES(?,?)' if save else
                  'DELETE FROM comm_saved WHERE account=? AND message=?', (account, message))
        c.commit()
        return handler.send({'ok': True})
    if path not in ('send', 'read'):
        raise Problem('Not found.', 404)
    thread = comm_number(d.get('thread'))
    membership = comm_member(c, thread, account)
    if path == 'read':
        last = comm_number(d.get('id'))
        if last and c.execute('SELECT 1 FROM comm_messages WHERE id=? AND thread=?', (last, thread)).fetchone():
            c.execute('UPDATE comm_members SET seen=MAX(seen,?) WHERE thread=? AND account=?', (last, thread, account))
        c.commit()
        return handler.send({'ok': True})
    if membership['kind'] == 'dm':
        recipient = c.execute("""SELECT a.account FROM comm_members a JOIN receipt_profiles p ON p.profile_id=a.account
            JOIN users u ON u.name=p.name WHERE a.thread=? AND a.account!=?""", (thread, account)).fetchone()
        if not recipient or not comm_preferences(c, recipient[0])['direct']:
            raise Problem('This person is unavailable for direct messages.', 403)
    text, filename, attachment = d.get('text', ''), d.get('filename'), None
    if not isinstance(text, str) or len(text) > 5000:
        raise Problem('Messages can contain up to 5,000 characters.')
    if filename is not None:
        if not isinstance(filename, str) or not 1 <= len(filename) <= 200 or any(
                ch in '/\\' or ord(ch)<32 or ord(ch)==127 for ch in filename):
            raise Problem('Choose a file with a valid name.')
        try:
            attachment = base64.b64decode(d.get('file', ''), validate=True)
        except (ValueError, TypeError):
            raise Problem('Invalid attachment.')
        if not 1 <= len(attachment) <= 3000000:
            raise Problem('Attachments must be 3 MB or smaller.')
    if not text.strip() and attachment is None:
        raise Problem('Enter a message or attach a file.')
    message = c.execute('INSERT INTO comm_messages(thread,author,author_name,sent,text,filename) VALUES(?,?,?,?,?,?)',
                        (thread, account, u['name'], time.time(), text.strip(), filename)).lastrowid
    if attachment is not None:
        c.execute('INSERT INTO comm_files VALUES(?,?)', (message, attachment))
    c.commit()
    if WebPush is not None:
        try:
            PUSH_QUEUE.put_nowait((thread, message, account, time.monotonic()))
        except queue.Full:
            print('Web Push queue full. The message is available in Communications Hub.')
    return handler.send({'id': message})


def init_workforce(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS work_job_definitions(name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS work_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT NOT NULL, kind TEXT NOT NULL, details TEXT NOT NULL,
            notes TEXT NOT NULL, status TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT,
            reviewer TEXT, reviewed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS work_request_account ON work_requests(account,status);
        CREATE TABLE IF NOT EXISTS work_clock_pins(account TEXT PRIMARY KEY, pin_hash TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS work_pin_security(
            id INTEGER PRIMARY KEY CHECK(id=1), salt TEXT NOT NULL, window INTEGER NOT NULL, failures INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS work_time_card_audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT, period INTEGER NOT NULL, employee TEXT NOT NULL,
            actor TEXT NOT NULL, at TEXT NOT NULL, reason TEXT NOT NULL, before TEXT NOT NULL, after TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS work_audit_no_update BEFORE UPDATE ON work_time_card_audit
            BEGIN SELECT RAISE(ABORT,'Time card audit entries cannot be changed'); END;
        CREATE TRIGGER IF NOT EXISTS work_audit_no_replace BEFORE INSERT ON work_time_card_audit
            WHEN EXISTS(SELECT 1 FROM work_time_card_audit WHERE id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Time card audit entries cannot be replaced'); END;
        CREATE TRIGGER IF NOT EXISTS work_audit_no_delete BEFORE DELETE ON work_time_card_audit
            BEGIN SELECT RAISE(ABORT,'Time card audit entries cannot be deleted'); END;
        CREATE TABLE IF NOT EXISTS work_assignments(account TEXT PRIMARY KEY,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS work_shifts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT NOT NULL, start INTEGER NOT NULL,
            end INTEGER NOT NULL CHECK(end>start), location TEXT NOT NULL, notes TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS work_shift_account ON work_shifts(account,start);
        CREATE TABLE IF NOT EXISTS work_periods(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT NOT NULL, start INTEGER NOT NULL,
            end INTEGER CHECK(end>=start), site_in TEXT, site_out TEXT
        );
        CREATE INDEX IF NOT EXISTS work_period_account ON work_periods(account,start);
        CREATE UNIQUE INDEX IF NOT EXISTS work_one_open ON work_periods(account) WHERE end IS NULL;
        CREATE TABLE IF NOT EXISTS work_breaks(
            id INTEGER PRIMARY KEY AUTOINCREMENT, period INTEGER NOT NULL, start INTEGER NOT NULL,
            end INTEGER CHECK(end>=start)
        );
        CREATE INDEX IF NOT EXISTS work_break_period ON work_breaks(period);
        CREATE UNIQUE INDEX IF NOT EXISTS work_one_open_break ON work_breaks(period) WHERE end IS NULL;
        CREATE TABLE IF NOT EXISTS work_sites(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE COLLATE NOCASE,
            latitude REAL NOT NULL, longitude REAL NOT NULL, radius REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS work_clock_settings(
            id INTEGER PRIMARY KEY CHECK(id=1), require_location INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO work_clock_settings VALUES(1,1);
    """)
    if not any(row[1]=='job' for row in c.execute('PRAGMA table_info(work_shifts)')):
        c.execute("ALTER TABLE work_shifts ADD COLUMN job TEXT NOT NULL DEFAULT ''")
    if not any(row[1]=='address' for row in c.execute('PRAGMA table_info(work_sites)')):
        c.execute("ALTER TABLE work_sites ADD COLUMN address TEXT NOT NULL DEFAULT ''")
    # Carry existing assignments and historical shifts into the shared job catalogue.
    for row in c.execute('SELECT body FROM work_assignments').fetchall():
        for job in json.loads(row['body']).get('jobs',[]):
            c.execute('INSERT OR IGNORE INTO work_job_definitions VALUES(?)',(job,))
    c.execute("INSERT OR IGNORE INTO work_job_definitions SELECT DISTINCT job FROM work_shifts WHERE job!=''")




def work_geocode(address):
    address=address.strip()
    if not 5<=len(address)<=240 or not address.isprintable():
        raise Problem('Enter a street address with a city and state or ZIP code.')
    params=urlencode({'address':address,'benchmark':'Public_AR_Current','format':'json'})
    request=Request('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?'+params,
                    headers={'User-Agent':'MGC-YFC-Operations','Accept':'application/json'})
    try:
        with urlopen(request,timeout=8) as response:
            data=json.loads(response.read(262145))
        matches=[]
        for row in data['result']['addressMatches'][:8]:
            coordinates=row['coordinates']
            lat,lon=float(coordinates['y']),float(coordinates['x'])
            label=row['matchedAddress']
            if -90<=lat<=90 and -180<=lon<=180 and isinstance(label,str):
                matches.append(dict(address=label[:240],latitude=lat,longitude=lon))
        return matches
    except (OSError,ValueError,TypeError,KeyError):
        raise Problem('Address lookup is unavailable. Try again or enter the coordinates manually.',424)


def clock_pin_hash(c, pin):
    row=c.execute('SELECT salt FROM work_pin_security WHERE id=1').fetchone()
    if not row:
        salt=secrets.token_hex(16)
        c.execute('INSERT INTO work_pin_security VALUES(1,?,0,0)',(salt,))
    else:
        salt=row['salt']
    return password(pin,salt)


def clock_pin_cookie(handler):
    cookies=SimpleCookie()
    cookies.load(handler.headers.get('Cookie',''))
    value=cookies.get('clock_session')
    return value.value if value else ''


def clock_pin_user(handler,c):
    token=clock_pin_cookie(handler)
    session=CLOCK_SESSIONS.get(token)
    if session and session[1]>time.time():
        row=c.execute("""SELECT u.name,p.profile_id FROM receipt_profiles p JOIN users u ON u.name=p.name
            JOIN work_clock_pins pin ON pin.account=p.profile_id
            LEFT JOIN account_lockouts l ON l.name=u.name
            WHERE p.profile_id=? AND l.locked_at IS NULL AND pin.pin_hash=?""",(session[0],session[2])).fetchone()
        if row:
            return dict(name=row['name'],receipt_owner=row['profile_id'],admin=False)
    CLOCK_SESSIONS.pop(token,None)
    raise Problem('Enter your Time Clock PIN again.',401)


def clock_pin_login(handler,c,d):
    if handler.external_scheme()!='https' and handler.client_address[0] not in ('127.0.0.1','::1'):
        raise Problem('Use the secure staff address for PIN access.',403)
    pin=d.get('pin')
    if not isinstance(pin,str) or not re.fullmatch(r'[0-9]{6}',pin):
        raise Problem('Enter your six-digit Time Clock PIN.')
    now=int(time.time())
    state=c.execute('SELECT window,failures FROM work_pin_security WHERE id=1').fetchone()
    window,failures=(state['window'],state['failures']) if state and now-state['window']<300 else (now,0)
    if failures>=8:
        raise Problem('Too many PIN attempts. Try again in a few minutes, or sign in with your username.',429)
    digest=clock_pin_hash(c,pin)
    row=c.execute("""SELECT pin.account FROM work_clock_pins pin JOIN receipt_profiles p ON p.profile_id=pin.account
        JOIN users u ON u.name=p.name LEFT JOIN account_lockouts l ON l.name=u.name
        WHERE pin.pin_hash=? AND l.locked_at IS NULL""",(digest,)).fetchone()
    if not row:
        c.execute('UPDATE work_pin_security SET window=?,failures=? WHERE id=1',(window,failures+1))
        c.commit()
        raise Problem('That Time Clock PIN could not be used.',403)
    CLOCK_SESSIONS.pop(clock_pin_cookie(handler),None)
    for token,session in list(CLOCK_SESSIONS.items()):
        if session[1]<=now or session[0]==row['account']:
            del CLOCK_SESSIONS[token]
    token=secrets.token_urlsafe(32)
    CLOCK_SESSIONS[token]=(row['account'],now+180,digest)
    return handler.send({'ok':True},cookie=f'clock_session={token}; HttpOnly; SameSite=Strict; Path=/api/workforce/quick; Max-Age=180')


def work_bounds(day, length=1):
    return tuple(int(dt.datetime.combine(day+dt.timedelta(days=offset),dt.time()).timestamp())
                 for offset in (0,length))


def work_week(value, today):
    if value:
        try:
            day=dt.date.fromisoformat(value)
            if not 1970<=day.year<=2100: raise ValueError()
        except ValueError:
            raise Problem('Choose a valid schedule date.')
    else:
        day=today
    return day-dt.timedelta(days=(day.weekday()+1)%7)


def work_local(timestamp):
    return dt.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M')


def work_time(value):
    if not isinstance(value,str):
        raise Problem('Enter a start and end date and time.')
    try:
        parsed=dt.datetime.strptime(value,'%Y-%m-%dT%H:%M')
        if not 1970<=parsed.year<=2100: raise ValueError()
        timestamp=int(parsed.timestamp())
        if dt.datetime.fromtimestamp(timestamp)!=parsed: raise ValueError()
        return timestamp
    except (ValueError,OverflowError,OSError):
        raise Problem('Choose a valid date and time in the server time zone.')


def work_hours(c, account, bounds, now):
    first,last=bounds
    last=min(last,now)
    if first>=last:
        return 0,0
    periods=c.execute("""SELECT id,start,end FROM work_periods
        WHERE account=? AND start<? AND (end IS NULL OR end>?)""",(account,last,first)).fetchall()
    gross=breaks=0
    for period in periods:
        end=min(last,period['end'] if period['end'] is not None else last)
        start=max(first,period['start'])
        gross+=max(0,end-start)
        for pause in c.execute('SELECT start,end FROM work_breaks WHERE period=? AND start<? AND (end IS NULL OR end>?)',
                               (period['id'],end,start)):
            breaks+=max(0,min(end,pause['end'] if pause['end'] is not None else end)-max(start,pause['start']))
    return gross,max(0,gross-breaks)


def work_open(c, account):
    period=c.execute('SELECT id,start FROM work_periods WHERE account=? AND end IS NULL',(account,)).fetchone()
    pause=c.execute('SELECT id,start FROM work_breaks WHERE period=? AND end IS NULL',
                    (period['id'],)).fetchone() if period else None
    return period,pause


def work_assignment(c,account):
    row=c.execute('SELECT body FROM work_assignments WHERE account=?',(account,)).fetchone()
    if not row:
        return dict(jobs=[],sites=[],primary_job='',primary_site=None,require_location=False)
    return json.loads(row['body'])


def work_assigned_sites(c,assignment):
    ids=set(assignment['sites'])
    return [dict(row) for row in c.execute('SELECT * FROM work_sites ORDER BY name') if row['id'] in ids]


def work_assignment_target(c,name):
    if not isinstance(name,str): raise Problem('Choose a current employee.')
    row=c.execute('SELECT profile_id FROM receipt_profiles WHERE name=?',(name,)).fetchone()
    if not row: raise Problem('Employee not found.',404)
    return row[0]


def work_save_assignment(c,d):
    account=work_assignment_target(c,d.get('name'))
    jobs,sites=d.get('jobs'),d.get('sites')
    job,site=d.get('primary_job'),d.get('primary_site')
    required=d.get('require_location')
    if (not isinstance(jobs,list) or len(jobs)>30 or any(not isinstance(j,str) or not 1<=len(j.strip())<=80 for j in jobs)
            or not isinstance(sites,list) or len(sites)>50 or any(type(i) is not int for i in sites)
            or type(required) is not bool):
        raise Problem('Choose valid jobs, work sites and location settings.')
    jobs=list(dict.fromkeys(j.strip() for j in jobs))
    sites=list(dict.fromkeys(sites))
    if (not set(sites)<={r[0] for r in c.execute('SELECT id FROM work_sites')}
            or (bool(jobs) and job not in jobs) or (not jobs and job!='')
            or (bool(sites) and (type(site) is not int or site not in sites)) or (not sites and site is not None)):
        raise Problem('Choose a primary job and site from the assigned options.')
    if required and not sites: raise Problem('Assign at least one work site to require location checks.')
    for assigned_job in jobs:
        c.execute('INSERT OR IGNORE INTO work_job_definitions VALUES(?)',(assigned_job,))
    body=dict(jobs=jobs,sites=sites,primary_job=job,primary_site=site,require_location=required)
    c.execute('INSERT OR REPLACE INTO work_assignments VALUES(?,?)',(account,json.dumps(body)))


def work_shifts(c, week, account=None):
    first,last=work_bounds(week,7)
    args=(last,first)
    query="""SELECT s.*,u.name FROM work_shifts s JOIN receipt_profiles p ON p.profile_id=s.account
             JOIN users u ON u.name=p.name WHERE s.start<? AND s.end>?"""
    if account is not None:
        query+=' AND s.account=?'
        args+= (account,)
    return [{**dict(row),'start':work_local(row['start']),'end':work_local(row['end']),
             'week_seconds':min(last,row['end'])-max(first,row['start'])}
            for row in c.execute(query+' ORDER BY s.start,u.name,s.id',args)]


WORK_DAYS=('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')


def work_request_rows(c,account=None,reviewer=None):
    sql="""SELECT q.*,u.name FROM work_requests q JOIN receipt_profiles p ON p.profile_id=q.account
             JOIN users u ON u.name=p.name"""
    args=()
    if account is not None:
        sql+=' WHERE q.account=?'
        args=(account,)
    elif reviewer is not None:
        scope,args=request_review_scope(reviewer)
        sql+=f' WHERE q.account IN ({scope})'
    rows=c.execute(sql+" ORDER BY (q.status='pending') DESC,q.id DESC",args)
    return [{**dict(row),'details':json.loads(row['details'])} for row in rows]


def work_week_absences(c,week,status="approved"):
    end=week+dt.timedelta(days=6)
    rows=c.execute("""SELECT q.account,q.kind,q.details FROM work_requests q
        JOIN receipt_profiles p ON p.profile_id=q.account JOIN users u ON u.name=p.name
        WHERE q.status=? AND q.start_date<=? AND (q.end_date IS NULL OR q.end_date>=?)""",
                   (status,end.isoformat(),week.isoformat()))
    cells=[]
    for row in rows:
        details=json.loads(row['details'])
        for i in range(7):
            day=(week+dt.timedelta(days=i)).isoformat()
            if row['kind']=='time-off':
                if details['start']<=day<=details['end']:
                    cells.append(dict(account=row['account'],day=day,kind='time-off',**(
                        dict(start=details['from_time'],end=details['until_time']) if details.get('from_time') else {})))
            elif day>=details['effective']:
                for block in details['blocks']:
                    if block['day']==(i+6)%7:
                        cells.append(dict(account=row['account'],day=day,kind='availability',**{
                            'start':block['start'],'end':block['end']}))
    return cells


def work_submit_request(c,u,d):
    account=u['receipt_owner']
    kind,notes=d.get('kind'),d.get('notes','')
    if not isinstance(notes,str) or len(notes)>500: raise Problem('Use up to 500 characters for the note.')
    today=dt.date.today()
    if kind=='availability':
        raw=d.get('blocks')
        if not isinstance(raw,list) or len(raw)>28: raise Problem('Add up to 28 weekly unavailable periods.')
        blocks=[]
        for block in raw:
            if not isinstance(block,dict): raise Problem('Choose valid days and times.')
            day,start,end=block.get('day'),block.get('start'),block.get('end')
            if type(day) is not int or not 0<=day<7: raise Problem('Choose a day for each unavailable period.')
            if start==end=='':
                pass
            elif not all(isinstance(t,str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',t) for t in (start,end)) or start>=end:
                raise Problem('Enter an end time after the start time. Split overnight periods across two days.')
            blocks.append(dict(day=day,start=start,end=end))
        first,last=today.isoformat(),None
        details=dict(effective=first,blocks=blocks)
        c.execute("UPDATE work_requests SET status='withdrawn' WHERE account=? AND kind='availability' AND status='pending'",
                  (account,))
    elif kind=='time-off':
        try:
            start,end=(dt.date.fromisoformat(d[key]) for key in ('start','end'))
            if start<today or not 0<=(end-start).days<366: raise ValueError()
        except (TypeError,ValueError,KeyError):
            raise Problem('Choose a current or future date range of up to 366 days.')
        first,last=start.isoformat(),end.isoformat()
        details=dict(start=first,end=last)
        begin,finish=d.get('from_time',''),d.get('until_time','')
        if begin or finish:
            if (first!=last or not all(isinstance(t,str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',t) for t in (begin,finish)) or begin>=finish):
                raise Problem('For partial-day time off, choose one day and an end time after the start.')
            details.update(from_time=begin,until_time=finish)
    else:
        raise Problem('Choose availability or time off.')
    request=c.execute("""INSERT INTO work_requests(account,kind,details,notes,status,start_date,end_date)
                 VALUES(?,?,?,?,'pending',?,?)""",(account,kind,json.dumps(details),notes.strip(),first,last))
    if u['admin']:
        row=c.execute('SELECT * FROM work_requests WHERE id=?',(request.lastrowid,)).fetchone()
        work_set_request_decision(c,row,'approved',u['name'])


def work_review_request(c,u,d):
    if not can_review_requests(u): raise Problem('This request requires an administrator or an authorized manager.',403)
    ident,decision=d.get('id'),d.get('decision')
    if type(ident) is not int or not 0<ident<2**63 or decision not in ('approved','declined'):
        raise Problem('Choose a valid review decision.')
    row=c.execute("SELECT * FROM work_requests WHERE id=? AND status='pending'",(ident,)).fetchone()
    if not row: raise Problem('This request has already been reviewed or withdrawn.',409)
    if not can_review_request(c,u,row['account']): raise Problem('This request requires an administrator or an authorized manager.',403)
    work_set_request_decision(c,row,decision,u['name'])


def work_set_request_decision(c,row,decision,reviewer):
    if row['kind']=='availability' and decision=='approved':
        c.execute("""UPDATE work_requests SET status='superseded' WHERE account=? AND kind='availability'
                     AND status='approved'""",(row['account'],))
    c.execute('UPDATE work_requests SET status=?,reviewer=?,reviewed_at=? WHERE id=?',
              (decision,reviewer,dt.datetime.now().isoformat(timespec='seconds'),row['id']))


DEFAULT_PAYROLL_BREAK_HOURS=5.5


def work_payroll_preview(c,start_value,break_after=DEFAULT_PAYROLL_BREAK_HOURS,*,period='sunday'):
    if period not in ('sunday','quickbooks'):
        raise Problem('Choose a payroll period option.')
    try:
        start=dt.date.fromisoformat(start_value)
        end=start+dt.timedelta(days=6)
        if not 2000<=start.year<=2100 or end>=dt.date.today():
            raise ValueError()
    except (TypeError,ValueError,OverflowError):
        raise Problem('Choose the start of a completed seven-day pay period.')
    if period=='sunday' and start.weekday()!=6:
        raise Problem('Choose the Sunday that starts the pay period.')
    try:
        break_threshold=float(break_after)
        if not 0<=break_threshold<=48: raise ValueError()
    except (TypeError,ValueError):
        raise Problem('Choose a break review threshold from 0 to 48 hours.')
    first,last=work_bounds(start,7)
    periods=c.execute("""SELECT w.*,u.name,
        EXISTS(SELECT 1 FROM work_breaks b WHERE b.period=w.id) AS has_break,
        EXISTS(SELECT 1 FROM work_breaks b WHERE b.period=w.id AND b.end IS NULL) AS open_break
        FROM work_periods w LEFT JOIN receipt_profiles p ON p.profile_id=w.account
        LEFT JOIN users u ON u.name=p.name WHERE w.start<? AND (w.end IS NULL OR w.end>?)
        ORDER BY w.start,w.id""",(last,first)).fetchall()
    shifts=c.execute("""SELECT s.account,s.start,s.end,u.name FROM work_shifts s
        JOIN receipt_profiles p ON p.profile_id=s.account JOIN users u ON u.name=p.name
        WHERE s.start<? AND s.end>? ORDER BY s.start,s.id""",(last,first)).fetchall()
    entries,by_account,unlinked={},{},set()
    def employee(row):
        return entries.setdefault(row['account'],dict(account=row['account'],name=row['name'],
                                  gross=0,net=0,open_punch=False,issues=[]))
    for period in periods:
        if not period['name']:
            unlinked.add(period['account'])
            continue
        item=employee(period)
        by_account.setdefault(period['account'],[]).append(period)
        at=work_local(period['start'])
        if period['end'] is None:
            item['open_punch']=True
            item['issues'].append(dict(kind='missing-clock-out',at=at))
        if period['open_break']:
            item['issues'].append(dict(kind='missing-break-end',at=at))
        if (period['end'] is not None and not period['has_break'] and period['end']>period['start']
                and period['end']-period['start']>=break_threshold*3600):
            item['issues'].append(dict(kind='no-break-recorded',at=at))
    for shift in shifts:
        item=employee(shift)
        if not any(p['start']<min(shift['end'],last) and
                   (p['end'] if p['end'] is not None else last)>max(first,shift['start'])
                   for p in by_account.get(shift['account'],[])):
            item['issues'].append(dict(kind='missing-clock-in',at=work_local(shift['start'])))
    for item in entries.values():
        item['has_punches']=item['account'] in by_account
        item['gross'],item['net']=work_hours(c,item['account'],(first,last),last)
        item['issues'].sort(key=lambda issue:(issue['at'],issue['kind']))
    employees=sorted(entries.values(),key=lambda item:(item['name'].casefold(),item['account']))
    return dict(start=start.isoformat(),end=end.isoformat(),employees=employees,unlinked=len(unlinked))


def work_card_time(timestamp):
    return dt.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%S') if timestamp is not None else ''


def work_card_timestamp(value,optional=False):
    if value=='' and optional:
        return None
    if not isinstance(value,str): raise Problem('Enter a valid date and time.')
    try:
        local=dt.datetime.fromisoformat(value)
        if local.tzinfo or local.microsecond or not 2000<=local.year<=2100: raise ValueError()
        stamp=int(local.timestamp())
        if dt.datetime.fromtimestamp(stamp)!=local or stamp>int(time.time()): raise ValueError()
        return stamp
    except (ValueError,OverflowError,OSError):
        raise Problem('Choose a valid date and time at or before the current server time.')


def work_card_snapshot(c,period):
    return dict(start=period['start'],end=period['end'],
                breaks=[dict(row) for row in c.execute('SELECT id,start,end FROM work_breaks WHERE period=? ORDER BY id',
                                                       (period['id'],))])


def work_card_revision(card):
    return hashlib.sha256(json.dumps(card,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def work_card_display(card):
    return dict(start=work_card_time(card['start']),end=work_card_time(card['end']),
                breaks=[dict(id=b['id'],start=work_card_time(b['start']),end=work_card_time(b['end'])) for b in card['breaks']])


def work_time_cards(c,week,account=None):
    first,last=work_bounds(week,7)
    rows=c.execute("""SELECT w.*,u.name FROM work_periods w LEFT JOIN receipt_profiles p ON p.profile_id=w.account
        LEFT JOIN users u ON u.name=p.name WHERE w.start<? AND (w.end IS NULL OR w.end>?)
        ORDER BY u.name COLLATE NOCASE,w.start,w.id""",(last,first)).fetchall()
    cards=[]
    for row in rows:
        if account is not None and row["account"]!=account: continue
        card=work_card_snapshot(c,row)
        cards.append(dict(id=row['id'],name=row['name'] or 'Former employee',
                          revision=work_card_revision(card),**work_card_display(card)))
    return cards


def work_edit_time_card(c,u,d):
    if not has_permission(u,'edit_time_cards'): raise Problem('Edit time cards permission required.',403)
    ident,reason=d.get('id'),d.get('reason')
    if type(ident) is not int or not 0<ident<2**63:
        raise Problem('Choose a time card.')
    if not isinstance(reason,str) or not 1<=len(reason.strip())<=500:
        raise Problem('Enter a reason of up to 500 characters.')
    period=c.execute("""SELECT w.*,u.name FROM work_periods w LEFT JOIN receipt_profiles p ON p.profile_id=w.account
        LEFT JOIN users u ON u.name=p.name WHERE w.id=?""",(ident,)).fetchone()
    if not period: raise Problem('Time card not found.',404)
    before=work_card_snapshot(c,period)
    if d.get('revision')!=work_card_revision(before):
        raise Problem('The time card changed. Reload it before saving.',409)
    raw_breaks=d.get('breaks')
    if not isinstance(raw_breaks,list) or len(raw_breaks)!=len(before['breaks']):
        raise Problem('Edit the existing break entries.')
    # Keep unchanged server timestamps, including ambiguous times during a clock change.
    displayed=work_card_display(before)
    def parse_change(value,key,original,display):
        shown=display[key]
        if value==shown or (shown.endswith(':00') and value==shown[:-3]):
            return original[key]
        return work_card_timestamp(value,key=='end')
    start=parse_change(d.get('start'),'start',before,displayed)
    end=parse_change(d.get('end'),'end',before,displayed)
    if end is not None and end<start: raise Problem('Clock-out must be at or after clock-in.')
    if c.execute("""SELECT 1 FROM work_periods WHERE account=? AND id!=?
                    AND (end IS NULL OR end>?) AND (? IS NULL OR start<?)""",
                 (period['account'],ident,start,end,end)).fetchone():
        raise Problem('This correction overlaps another time card.',409)
    corrected=[]
    for raw,old,shown in zip(raw_breaks,before['breaks'],displayed['breaks']):
        if not isinstance(raw,dict) or type(raw.get('id')) is not int or raw['id']!=old['id']:
            raise Problem('Edit the existing break entries.')
        bs=parse_change(raw.get('start'),'start',old,shown)
        be=parse_change(raw.get('end'),'end',old,shown)
        if bs<start or (be is not None and be<bs) or (end is not None and (be is None or be>end)):
            raise Problem('Each break must start and end within the time card.')
        corrected.append(dict(id=old['id'],start=bs,end=be))
    ordered=sorted(corrected,key=lambda b:b['start'])
    for left,right in zip(ordered,ordered[1:]):
        if left['end'] is None or left['end']>right['start']:
            raise Problem('Break entries cannot overlap.')
    after=dict(start=start,end=end,breaks=corrected)
    if before==after:
        raise Problem('Change at least one punch before saving.')
    c.execute('UPDATE work_periods SET start=?,end=? WHERE id=?',(start,end,ident))
    # Close an existing open break before opening a different one to satisfy the unique index.
    for item in sorted(corrected,key=lambda b:b['end'] is None):
        c.execute('UPDATE work_breaks SET start=?,end=? WHERE id=? AND period=?',
                  (item['start'],item['end'],item['id'],ident))
    c.execute("""INSERT INTO work_time_card_audit(period,employee,actor,at,reason,before,after)
                 VALUES(?,?,?,?,?,?,?)""",(ident,period['name'] or 'Former employee',u['name'],
                 dt.datetime.now().astimezone().isoformat(timespec='seconds'),reason.strip(),
                 json.dumps(work_card_display(before)),json.dumps(work_card_display(after))))


def work_add_time_card(c,u,d):
    if not has_permission(u,'add_time_cards'): raise Problem('Add time cards permission required.',403)
    account,reason=d.get('account'),d.get('reason')
    if not isinstance(account,str):
        raise Problem('Choose an employee.')
    person=c.execute('SELECT u.name FROM users u JOIN receipt_profiles p ON p.name=u.name WHERE p.profile_id=?',
                     (account,)).fetchone()
    if not person: raise Problem('Choose a current employee.')
    if not isinstance(reason,str) or not 1<=len(reason.strip())<=500:
        raise Problem('Enter a reason of up to 500 characters.')
    start,end=work_card_timestamp(d.get('start')),work_card_timestamp(d.get('end'))
    if end<=start: raise Problem('Clock-out must be after clock-in.')
    if c.execute("""SELECT 1 FROM work_periods WHERE account=? AND start<? AND (end IS NULL OR end>?)""",
                 (account,end,start)).fetchone():
        raise Problem('This entry overlaps another time card.',409)
    raw=d.get('breaks',[])
    if not isinstance(raw,list) or len(raw)>20 or any(not isinstance(item,dict) for item in raw):
        raise Problem('Add up to 20 valid break periods.')
    breaks=sorted((work_card_timestamp(item.get('start')),work_card_timestamp(item.get('end'))) for item in raw)
    previous=start
    for first,last in breaks:
        if not previous<=first<last<=end:
            raise Problem('Breaks must be within the time card and cannot overlap.')
        previous=last
    period=c.execute('INSERT INTO work_periods(account,start,end) VALUES(?,?,?)',(account,start,end)).lastrowid
    saved=[]
    for first,last in breaks:
        ident=c.execute('INSERT INTO work_breaks(period,start,end) VALUES(?,?,?)',(period,first,last)).lastrowid
        saved.append(dict(id=ident,start=first,end=last))
    c.execute("""INSERT INTO work_time_card_audit(period,employee,actor,at,reason,before,after)
                 VALUES(?,?,?,?,?,?,?)""",(period,person['name'],u['name'],
                 dt.datetime.now().astimezone().isoformat(timespec='seconds'),reason.strip(),'null',
                 json.dumps(work_card_display(dict(start=start,end=end,breaks=saved)))))



def work_dispatch(c,u,week):
    if not has_permission(u,'view_schedule'): return []
    first,last=week.isoformat(),(week+dt.timedelta(days=7)).isoformat()
    events=[]
    for row in c.execute('SELECT body FROM jobs'):
        job=json.loads(row['body'])
        if (job.get('request') or job.get('status') in ('Canceled','Cancelled') or
                job.get('type') not in ('Pickup','Delivery')): continue
        start=job.get('start','')
        if first<=start<last:
            events.append(dict(start=start,type=job['type']))
    return sorted(events,key=lambda event:event['start'])


def work_copy_week(c,d):
    try:
        source,target=(dt.date.fromisoformat(d[key]) for key in ('source','target'))
        if source.weekday()!=6 or target.weekday()!=6 or source==target: raise ValueError()
        if not all(2000<=day.year<=2100 for day in (source,target)): raise ValueError()
    except (TypeError,ValueError,KeyError):
        raise Problem('Choose different Sunday start dates for the source and destination weeks.')
    # Serialize conflict checks and inserts; a failed copy leaves every destination shift intact.
    c.execute('BEGIN IMMEDIATE')
    first,last=work_bounds(source,7)
    rows=c.execute("""SELECT s.* FROM work_shifts s JOIN receipt_profiles p ON p.profile_id=s.account
        JOIN users u ON u.name=p.name WHERE s.start>=? AND s.start<? ORDER BY s.start,s.id""",(first,last)).fetchall()
    if not rows: raise Problem('The source week has no shifts starting in it.')
    offset=target-source
    copied=[]
    for row in rows:
        # Preserve local wall times when the offset crosses daylight saving time.
        start=work_time((dt.datetime.fromtimestamp(row['start'])+offset).isoformat(timespec='minutes'))
        end=work_time((dt.datetime.fromtimestamp(row['end'])+offset).isoformat(timespec='minutes'))
        if not 0<end-start<=48*3600: raise Problem('A copied shift has invalid hours at the destination.')
        assignment=work_assignment(c,row['account'])
        locations=work_assigned_sites(c,assignment)
        if ((assignment['jobs'] and row['job'] not in assignment['jobs']) or
            (locations and row['location'] not in {site['name'] for site in locations})):
            raise Problem('An employee’s assignments changed. Update the source shifts before copying.',409)
        if c.execute('SELECT 1 FROM work_shifts WHERE account=? AND start<? AND end>?',
                     (row['account'],end,start)).fetchone():
            raise Problem('Copy stopped: a destination shift overlaps. No shifts were copied.',409)
        c.execute('INSERT INTO work_shifts(account,start,end,location,notes,job) VALUES(?,?,?,?,?,?)',
                  (row['account'],start,end,row['location'],row['notes'],row['job']))
        copied.append(row['id'])
    return dict(ok=True,copied=len(copied))

def work_get(handler,c,u,path,query,clock_only=False):
    account=u['receipt_owner']
    if not account: raise Problem('Staff account required.',403)
    now=int(time.time())
    today=dt.date.fromtimestamp(now)
    week=work_week(query.get('week',[''])[0],today)
    if path=='my-time-cards':
        return handler.send({'cards':work_time_cards(c,week,account)})
    if path=='time-cards':
        edit,add=has_permission(u,'edit_time_cards'),has_permission(u,'add_time_cards')
        if not (edit or add): raise Problem('Time card permission required.',403)
        people=[dict(row) for row in c.execute("""SELECT p.profile_id AS id,u.name FROM users u
                 JOIN receipt_profiles p ON p.name=u.name ORDER BY u.name""")] if add else []
        return handler.send({'cards':work_time_cards(c,week),'people':people})
    if path=='time-card-audit':
        if not u['admin']: raise Problem('Administrator access required.',403)
        before=comm_number(query.get('before',[''])[0],2**63-1)
        rows=c.execute('SELECT * FROM work_time_card_audit WHERE id<? ORDER BY id DESC LIMIT 51',(before,)).fetchall()
        return handler.send({'entries':[{**dict(row),'before':json.loads(row['before']),'after':json.loads(row['after'])}
                                        for row in rows[:50]],'more':len(rows)>50})
    if path=='payroll':
        if not has_permission(u,'export_payroll'): raise Problem('Payroll export permission required.',403)
        return handler.send(work_payroll_preview(c,query.get('start',[''])[0],
                                                 query.get('break_after',[DEFAULT_PAYROLL_BREAK_HOURS])[0],
                                                 period=query.get('period',['sunday'])[0]))
    if path=='overview':
        gross,worked=work_hours(c,account,work_bounds(today),now)
        week_gross,week_worked=work_hours(c,account,work_bounds(week,7),now)
        period,pause=work_open(c,account)
        state='break' if pause else 'working' if period else 'out'
        assignment=work_assignment(c,account)
        return handler.send(dict(week=week.isoformat(),today=today.isoformat(),now=now,
            day_end=work_bounds(today)[1],week_end=work_bounds(week,7)[1],week_start=work_bounds(week,7)[0],
            clock=dict(state=state,since=work_local(period['start']) if period else None,
                       gross=gross,worked=worked,week_gross=week_gross,week_worked=week_worked),
            require_location=assignment['require_location'],sites_ready=bool(work_assigned_sites(c,assignment)),
            manage_schedule=has_permission(u,'manage_staff_schedule'),edit_time_cards=has_permission(u,'edit_time_cards'),add_time_cards=has_permission(u,'add_time_cards'),export_payroll=has_permission(u,'export_payroll'),manage_review=can_review_requests(u),manage_sites=has_permission(u,'manage_work_sites'),
            shifts=[] if clock_only else work_shifts(c,week,account)))
    if path=='team':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        people=[dict(row) for row in c.execute("""SELECT p.profile_id AS id,u.name FROM users u
                    JOIN receipt_profiles p ON p.name=u.name ORDER BY u.name""")]
        for person in people:
            assignment=work_assignment(c,person['id'])
            locations=work_assigned_sites(c,assignment)
            person.update(jobs=assignment['jobs'],primary_job=assignment['primary_job'],locations=[site['name'] for site in locations],
                          primary_location=next((site['name'] for site in locations if site['id']==assignment['primary_site']),''))
        return handler.send(dict(people=people,shifts=work_shifts(c,week),absences=work_week_absences(c,week),
            pending_absences=work_week_absences(c,week,'pending'),dispatch=work_dispatch(c,u,week),
            jobs=[r['name'] for r in c.execute('SELECT name FROM work_job_definitions ORDER BY name')]))
    if path=='requests':
        return handler.send({'requests':work_request_rows(c,account)})
    if path=='review-requests':
        if not can_review_requests(u): raise Problem('This request requires an administrator or an authorized manager.',403)
        return handler.send({'requests':work_request_rows(c,reviewer=u),'account':account})
    if path=='jobs':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        return handler.send({'jobs':[r['name'] for r in c.execute('SELECT name FROM work_job_definitions ORDER BY name')]})
    if path=='assignment':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        target=work_assignment_target(c,query.get('name',[''])[0])
        return handler.send({'assignment':work_assignment(c,target),'sites':[dict(row) for row in c.execute('SELECT id,name FROM work_sites ORDER BY name')]})
    if path=='sites':
        if not has_permission(u,'manage_work_sites'): raise Problem('Work site management permission required.',403)
        return handler.send(dict(sites=[dict(row) for row in c.execute('SELECT * FROM work_sites ORDER BY name')]))
    raise Problem('Not found.',404)


def work_number(value, low, high):
    if type(value) not in (int,float) or not low<=value<=high:
        raise Problem('Enter valid location coordinates, accuracy and radius.')
    return float(value)


def work_check_location(c,account,position):
    assignment=work_assignment(c,account)
    if not assignment['require_location']:
        return None
    sites=work_assigned_sites(c,assignment)
    if not sites:
        raise Problem('A manager must assign you a work site before you can clock in or out.',409)
    if not isinstance(position,dict):
        raise Problem('Allow location access to clock in or out at a work site.',403)
    lat=work_number(position.get('latitude'),-90,90)
    lon=work_number(position.get('longitude'),-180,180)
    accuracy=work_number(position.get('accuracy'),0,100000)
    matched=[]
    for site in sites:
        lat1,lat2=math.radians(lat),math.radians(site['latitude'])
        a=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(site['longitude']-lon)/2)**2
        distance=12742000*math.asin(math.sqrt(min(1,a)))
        if distance+accuracy<=site['radius']:
            matched.append((distance,site['name']))
    if not matched:
        raise Problem('Your location is outside an approved work site or too imprecise. Move closer and try again.',403)
    return min(matched)[1]


def work_post(handler,c,u,path,d,clock_only=False):
    account=u['receipt_owner']
    if not account: raise Problem('Staff account required.',403)
    if path in ('edit-time-card','add-time-card'):
        if path=='add-time-card': work_add_time_card(c,u,d)
        else: work_edit_time_card(c,u,d)
        c.commit()
        return handler.send({'ok':True})
    if path in ('request','withdraw-request','review-request'):
        if path=='request': work_submit_request(c,u,d)
        elif path=='review-request': work_review_request(c,u,d)
        else:
            ident=d.get('id')
            if type(ident) is not int or not 0<ident<2**63: raise Problem('Invalid request.')
            if not c.execute("UPDATE work_requests SET status='withdrawn' WHERE id=? AND account=? AND status='pending'",
                             (ident,account)).rowcount:
                raise Problem('Only your pending requests can be withdrawn.',409)
        c.commit()
        return handler.send({'ok':True})
    if path=='punch':
        action=d.get('action')
        period,pause=work_open(c,account)
        allowed=('in',) if not period else ('out','end_break') if pause else ('out','start_break')
        if action not in allowed: raise Problem('This punch is no longer available. Refresh and check your clock status.',409)
        site=work_check_location(c,account,d.get('position')) if action in ('in','out') else None
        now=int(time.time())
        if (period and now<period['start']) or (pause and now<pause['start']):
            raise Problem('The server clock changed. Ask a manager to check it before punching again.',409)
        if action=='in':
            c.execute('INSERT INTO work_periods(account,start,site_in) VALUES(?,?,?)',(account,now,site))
        elif action=='start_break':
            c.execute('INSERT INTO work_breaks(period,start) VALUES(?,?)',(period['id'],now))
        else:
            if pause: c.execute('UPDATE work_breaks SET end=? WHERE id=?',(now,pause['id']))
            if action=='out': c.execute('UPDATE work_periods SET end=?,site_out=? WHERE id=?',(now,site,period['id']))
        c.commit()
        if clock_only:
            CLOCK_SESSIONS.pop(clock_pin_cookie(handler),None)
            return handler.send({'ok':True},cookie='clock_session=; HttpOnly; SameSite=Strict; Path=/api/workforce/quick; Max-Age=0')
        return handler.send({'ok':True})
    if path=='copy-week':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        result=work_copy_week(c,d)
        c.commit()
        return handler.send(result)
    if path=='jobs':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        jobs=d.get('jobs')
        if not isinstance(jobs,list) or len(jobs)>200 or any(not isinstance(j,str) or not 1<=len(j.strip())<=80 for j in jobs):
            raise Problem('Enter up to 200 job names, with up to 80 characters each.')
        jobs=list(dict.fromkeys(j.strip() for j in jobs))
        used={job for r in c.execute('SELECT body FROM work_assignments') for job in json.loads(r['body'])['jobs']}
        used.update(r['job'] for r in c.execute("SELECT DISTINCT job FROM work_shifts WHERE job!=''"))
        if not used<=set(jobs): raise Problem('Jobs used by an employee or saved shift cannot be removed.',409)
        c.execute('DELETE FROM work_job_definitions')
        c.executemany('INSERT INTO work_job_definitions VALUES(?)',[(job,) for job in jobs])
        c.commit()
        return handler.send({'ok':True})
    if path=='assignment':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        work_save_assignment(c,d)
        c.commit()
        return handler.send({'ok':True})
    if path=='shift':
        if not has_permission(u,'manage_staff_schedule'): raise Problem('Schedule management permission required.',403)
        ident=d.get('id')
        if ident is not None and (type(ident) is not int or not 0<ident<2**63): raise Problem('Invalid shift.')
        if ident is not None:
            old=c.execute('SELECT * FROM work_shifts WHERE id=?',(ident,)).fetchone()
            if not old or d.get('revision')!=old['revision']: raise Problem('This shift changed. Refresh the schedule and try again.',409)
        if d.get('remove') is True:
            if ident is None: raise Problem('Choose a shift to remove.')
            c.execute('DELETE FROM work_shifts WHERE id=?',(ident,))
        else:
            employee=d.get('account')
            if not isinstance(employee,str) or not c.execute("""SELECT 1 FROM receipt_profiles p JOIN users u
                    ON u.name=p.name WHERE p.profile_id=?""",(employee,)).fetchone():
                raise Problem('Choose a current employee.')
            start,end=work_time(d.get('start')),work_time(d.get('end'))
            if not 0<end-start<=48*3600: raise Problem('End the shift after it starts and within 48 hours.')
            if c.execute('SELECT 1 FROM work_shifts WHERE account=? AND start<? AND end>? AND id!=?',
                         (employee,end,start,ident or 0)).fetchone():
                raise Problem('This employee already has a shift during those hours.',409)
            assignment=work_assignment(c,employee)
            locations=work_assigned_sites(c,assignment)
            primary=next((site['name'] for site in locations if site['id']==assignment['primary_site']),'')
            location,job,notes=d.get('location',primary),d.get('job',assignment['primary_job']),d.get('notes','')
            if not isinstance(job,str) or len(job)>80:
                raise Problem('Use up to 80 characters for the job.')
            job=job.strip()
            if assignment['jobs'] and job not in assignment['jobs'] and not (ident and old['account']==employee and job==old['job']):
                raise Problem('Choose one of the employee’s assigned jobs.')
            if not isinstance(location,str) or not isinstance(notes,str) or len(location)>100 or len(notes)>500:
                raise Problem('Use up to 100 characters for location and 500 for notes.')
            location=location.strip()
            if locations and location not in {site['name'] for site in locations} and not (ident and old['account']==employee and location==old['location']):
                raise Problem('Choose one of the employee’s assigned work sites.')
            fields=(employee,start,end,location,notes.strip(),job)
            if ident:
                c.execute('UPDATE work_shifts SET account=?,start=?,end=?,location=?,notes=?,job=?,revision=revision+1 WHERE id=?',
                          fields+(ident,))
            else:
                c.execute('INSERT INTO work_shifts(account,start,end,location,notes,job) VALUES(?,?,?,?,?,?)',fields)
        c.commit()
        return handler.send({'ok':True})
    if path=='site':
        if not has_permission(u,'manage_work_sites'): raise Problem('Work site management permission required.',403)
        ident=d.get('id')
        if ident is not None and (type(ident) is not int or not 0<ident<2**63): raise Problem('Invalid work site.')
        if ident and not c.execute('SELECT 1 FROM work_sites WHERE id=?',(ident,)).fetchone():
            raise Problem('Work site not found.',404)
        if d.get('remove') is True:
            if ident is None: raise Problem('Choose a work site to remove.')
            if c.execute("SELECT 1 FROM work_assignments a, json_each(a.body,'$.sites') s WHERE s.value=?",(ident,)).fetchone():
                raise Problem('Remove this site from employee assignments before deleting it.',409)
            c.execute('DELETE FROM work_sites WHERE id=?',(ident,))
        else:
            name=d.get('name')
            if not isinstance(name,str) or not 1<=len(name.strip())<=80: raise Problem('Enter a work site name.')
            address=d.get('address','')
            if not isinstance(address,str) or len(address)>240:
                raise Problem('Use up to 240 characters for the work site address.')
            fields=(name.strip(),work_number(d.get('latitude'),-90,90),
                    work_number(d.get('longitude'),-180,180),work_number(d.get('radius'),30,2000),address.strip())
            if ident: c.execute('UPDATE work_sites SET name=?,latitude=?,longitude=?,radius=?,address=? WHERE id=?',fields+(ident,))
            else: c.execute('INSERT INTO work_sites(name,latitude,longitude,radius,address) VALUES(?,?,?,?,?)',fields)
        c.commit()
        return handler.send({'ok':True})
    raise Problem('Not found.',404)



def init():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY COLLATE NOCASE, salt TEXT, hash TEXT, admin INTEGER);
CREATE TABLE IF NOT EXISTS permissions(name TEXT PRIMARY KEY COLLATE NOCASE, can_create INTEGER NOT NULL DEFAULT 1, see_requests INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS photos(job TEXT, position INTEGER, body BLOB, PRIMARY KEY(job,position));
CREATE TABLE IF NOT EXISTS vehicles(name TEXT PRIMARY KEY COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, revision INTEGER, body TEXT);
CREATE TABLE IF NOT EXISTS update_notices(id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT, actor TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS daily_home(name TEXT COLLATE NOCASE, day TEXT, section TEXT, PRIMARY KEY(name,day));
CREATE TABLE IF NOT EXISTS landing_preferences(name TEXT PRIMARY KEY COLLATE NOCASE, section TEXT);
CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, actor TEXT, area TEXT);
CREATE TABLE IF NOT EXISTS login_security(id INTEGER PRIMARY KEY CHECK(id=1), max_attempts INTEGER NOT NULL);
INSERT OR IGNORE INTO login_security VALUES(1,5);
CREATE TABLE IF NOT EXISTS account_lockouts(name TEXT PRIMARY KEY COLLATE NOCASE, failures INTEGER NOT NULL DEFAULT 0, locked_at TEXT);
CREATE TABLE IF NOT EXISTS receipt_categories(code TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, at REAL, actor TEXT, category TEXT, filename TEXT, mime TEXT, body BLOB, source TEXT);
CREATE TABLE IF NOT EXISTS audit(at TEXT, actor TEXT, action TEXT, job TEXT);''')
        init_comms(c)
        init_workforce(c)
        if 'chosen_on' not in {r[1] for r in c.execute('PRAGMA table_info(landing_preferences)')}:
            c.execute('ALTER TABLE landing_preferences ADD COLUMN chosen_on TEXT')
        c.execute('CREATE TABLE IF NOT EXISTS local_admin_sessions(token_hash TEXT PRIMARY KEY,name TEXT COLLATE NOCASE,version TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS permission_roles(id INTEGER PRIMARY KEY,name TEXT UNIQUE COLLATE NOCASE,body TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS user_roles(name TEXT PRIMARY KEY COLLATE NOCASE,role_id INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS page_colors(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS sharing_settings(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS receipt_profiles(name TEXT PRIMARY KEY COLLATE NOCASE,profile_id TEXT UNIQUE)')
        for person in c.execute('SELECT name FROM users').fetchall():c.execute('INSERT OR IGNORE INTO receipt_profiles VALUES(?,?)',(person['name'],secrets.token_hex(16)))
        c.execute("""UPDATE user_profile_photos SET approved=pending,approved_revision=pending_revision,
                     pending=NULL,pending_revision=NULL,status='approved'
                     WHERE pending_revision IS NOT NULL AND account IN (
                       SELECT p.profile_id FROM receipt_profiles p JOIN users u ON u.name=p.name WHERE u.admin=1)""")
        pending_admin_requests=c.execute("""SELECT q.*,u.name FROM work_requests q
            JOIN receipt_profiles p ON p.profile_id=q.account JOIN users u ON u.name=p.name
            WHERE u.admin=1 AND q.status='pending' ORDER BY q.id""").fetchall()
        for request in pending_admin_requests:
            work_set_request_decision(c,request,'approved',request['name'])
        c.execute('CREATE TABLE IF NOT EXISTS receipt_details(receipt_id TEXT PRIMARY KEY,reimbursement INTEGER NOT NULL DEFAULT 0,guest_assigned INTEGER NOT NULL DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS receipt_ownership(receipt_id TEXT PRIMARY KEY,profile_id TEXT)')
        c.execute("INSERT OR IGNORE INTO receipt_ownership SELECT r.id,p.profile_id FROM receipts r LEFT JOIN receipt_profiles p ON p.name=r.actor AND r.actor!='Guest'")
        c.execute("CREATE TABLE IF NOT EXISTS appearance_preferences(name TEXT PRIMARY KEY COLLATE NOCASE, mode TEXT NOT NULL)")
        c.execute('CREATE TABLE IF NOT EXISTS journal_archives(file TEXT PRIMARY KEY, sha256 TEXT NOT NULL, records INTEGER NOT NULL, archived_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS user_grants(name TEXT PRIMARY KEY COLLATE NOCASE, body TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS app_migrations(name TEXT PRIMARY KEY)')
        if not c.execute("SELECT 1 FROM app_migrations WHERE name='schedule-view-default-v1'").fetchone():
            for row in c.execute('SELECT name,body FROM user_grants').fetchall():
                grants=json.loads(row['body']);grants['view_schedule']=True
                c.execute('UPDATE user_grants SET body=? WHERE name=?',(json.dumps(grants),row['name']))
            c.execute("INSERT INTO app_migrations VALUES('schedule-view-default-v1')")


PERMISSIONS={
 'send_pages':'Page an associate to an area', 'receive_pages':'Use device as paging speaker',
 'show_vehicle_filter':'Show vehicle filter on main dashboard', 'show_search':'Show search bar on main dashboard',
 'submit_receipts':'Submit receipts and appear in guest receipt assignment',
 'view_all_receipts':'View all users’ receipts (manager/accounting)',
 'view_reports':'Open and print schedule/request reports',
 'view_schedule':'View schedule, search and filter', 'create_appointments':'Create pickups and deliveries',
 'edit_appointments':'Edit appointment details', 'delete_appointments':'Remove appointments',
 'update_status':'Set Scheduled / In Progress / Completed', 'cancel_appointments':'Cancel existing appointments',
 'submit_requests':'Submit pickup and delivery requests', 'review_requests':'Review and approve requests',
 'see_requests':'Show flashing Pending Requests button', 'call_contacts':'Show customer call button',
 'text_contacts':'Show On Our Way text button', 'navigate':'Show navigation button',
 'manage_roles':'Create and edit permission roles',
 'manage_comms_groups':'Create and manage groups',
 'manage_staff_schedule':'Create and edit staff shifts', 'edit_time_cards':'Edit time cards', 'add_time_cards':'Add time cards', 'export_payroll':'View and export payroll', 'manage_work_sites':'Manage time clock work sites and geofencing',
 'manage_vehicles':'Add vehicles', 'manage_users':'Add/remove employees and edit permissions',
 'rename_users':'Edit user names', 'unlock_users':'Unlock employee accounts after failed logins',
 'reset_passwords':'Reset employee passwords/passcodes', 'change_own_password':'Change own password/passcode',
 'view_audit':'View recent changes', 'backup_settings':'Manage backup settings',
 'create_backups':'Create backups', 'check_updates':'Check server updates',
 'configure_updates':'Change update repository', 'install_updates':'Install server updates',
 'view_server':'View server status', 'restart_server':'Restart server'}
ROUTE_PERMISSIONS={'/api/admin/lockouts':'unlock_users','/api/admin/unlock-user':'unlock_users','/api/paging/send':'send_pages',
 'send_pages':'Page an associate to an area', 'receive_pages':'Use device as paging speaker',
 'show_vehicle_filter':'Show vehicle filter on main dashboard', 'show_search':'Show search bar on main dashboard',
 'submit_receipts':'Submit receipts and appear in guest receipt assignment',
 'view_all_receipts':'View all users’ receipts (manager/accounting)',
 'view_reports':'Open and print schedule/request reports','/api/admin/users':'manage_users','/api/admin/permissions':'manage_users',
 '/api/user':'manage_users','/api/admin/remove-user':'manage_users','/api/admin/password':'reset_passwords',
 '/api/account/password':'change_own_password','/api/vehicle':'manage_vehicles',
 '/api/admin/backup-settings':'backup_settings','/api/admin/backup-now':'create_backups',
 '/api/admin/backup':'create_backups','/api/admin/status':'view_server','/api/admin/restart':'restart_server',
 '/api/updates':'check_updates','/api/update-check':'check_updates','/api/update-config':'configure_updates',
 '/api/update-install':'install_updates','/api/audit':'view_audit'}
DEFAULT_PAGE_COLORS={name:{'header':color,'light':'#faf6f5','dark':'#101821'} for name,color in {'dispatch':'#b51f2b','paging':'#7a1520','receipts':'#067a06','print':'#073ea6','settings':'#000000','signin':'#ffffff'}.items()}

def permission_groups():
    dispatch={'view_reports','view_schedule','create_appointments','edit_appointments','delete_appointments','update_status','cancel_appointments','submit_requests','review_requests','see_requests','call_contacts','text_contacts','navigate','manage_vehicles','show_vehicle_filter','show_search'}
    paging={'send_pages','receive_pages'};receipts={'submit_receipts','view_all_receipts'}
    workforce={'manage_staff_schedule','manage_work_sites','edit_time_cards','add_time_cards','export_payroll'}
    return {'Application Settings':[k for k in PERMISSIONS if k not in dispatch|paging|receipts|workforce],'Thrift Mart Dispatch':[k for k in PERMISSIONS if k in dispatch],'Store Associate Paging':[k for k in PERMISSIONS if k in paging],'Receipts & Accounting':[k for k in PERMISSIONS if k in receipts],'Print with a Purpose':[],'Scheduling & Time Clock':[k for k in PERMISSIONS if k in workforce]}

def has_permission(u,key): return bool(u['admin'] or u.get('grants',{}).get(key,False))
def route_allowed(u,path): return has_permission(u,ROUTE_PERMISSIONS.get(path,''))

def section_options(u):
    options=[]
    if has_permission(u,'view_schedule'): options.append({'id':'dispatch','label':'Thrift Mart Dispatch'})
    if has_permission(u,'send_pages') or has_permission(u,'receive_pages'): options.append({'id':'paging','label':'Store Associate Paging'})
    options.append({'id':'receipts','label':'Receipts & Accounting'})
    options.append({'id':'print','label':'Print with a Purpose'})
    return options

def session_expired(session, now):
    if session.get('local_admin'):return session.get('version')!=updater.current()
    if now >= session['expires']: return True
    login_day = session.get('login_day', dt.date.fromtimestamp(now).isoformat())
    return dt.date.fromtimestamp(now).isoformat() != login_day and now-session.get('last_active',0) >= 300

def valid_credential(p): return 8<=len(p)<=256 or (len(p)==4 and all(c in '0123456789' for c in p))
def password(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(s),200000).hex()
def backup():
    folder=DATA/'backups'; folder.mkdir(exist_ok=True)
    target=folder/(dt.date.today().isoformat()+'.db')
    if not target.exists():
        with connect() as src, closing(sqlite3.connect(target)) as dest: src.backup(dest)
        for old in sorted(folder.glob('*.db'))[:-30]: old.unlink()

def backup_config():
    p=DATA/'backup-settings.json'
    if p.exists(): return json.loads(p.read_text())
    base=os.environ.get('OneDriveCommercial') or os.environ.get('OneDriveConsumer') or os.environ.get('OneDrive')
    return {'enabled':False,'folder':str(Path(base)/'Thrift Mart Dispatch Backups') if base else ''}

def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def journal_folder():
    cfg=backup_config()
    folder=Path(cfg.get('folder',''))
    if not cfg.get('folder') or not folder.is_absolute():raise ValueError('Configure the server backup folder first.')
    return folder/'Dispatch Journal'

@contextmanager
def open_journal(row):
    name=row['file']
    if Path(name).name!=name or not name.endswith('.db'):raise ValueError('Invalid Dispatch Journal filename.')
    path=journal_folder()/name
    if not path.is_file() or file_digest(path)!=row['sha256']:raise ValueError('Dispatch Journal unavailable or damaged: '+name+'. Check OneDrive before continuing.')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Dispatch Journal integrity check failed: '+name)
        yield c

def all_report_jobs(c):
    jobs={}
    for archive in c.execute('SELECT * FROM journal_archives ORDER BY archived_at'):
        with open_journal(archive) as journal:
            for row in journal.execute('SELECT * FROM jobs'):jobs[row['id']]=dict(json.loads(row['body']),id=row['id'])
    for row in c.execute('SELECT * FROM jobs'):jobs[row['id']]=dict(json.loads(row['body']),id=row['id'])
    return list(jobs.values())

def merge_journals(snapshot):
    # Make every complete backup independently restorable, including journal history.
    with closing(sqlite3.connect(snapshot)) as c:
        c.row_factory=sqlite3.Row
        for archive in c.execute('SELECT * FROM journal_archives ORDER BY archived_at DESC').fetchall():
            with open_journal(archive) as j:
                for row in j.execute('SELECT * FROM jobs'):c.execute('INSERT OR IGNORE INTO jobs VALUES(?,?,?)',tuple(row))
                for row in j.execute('SELECT * FROM photos'):c.execute('INSERT OR IGNORE INTO photos VALUES(?,?,?)',tuple(row))
                for row in j.execute('SELECT * FROM audit'):
                    if not c.execute('SELECT 1 FROM audit WHERE at=? AND actor=? AND action=? AND job=?',tuple(row)).fetchone():c.execute('INSERT INTO audit VALUES(?,?,?,?)',tuple(row))
        c.execute('DELETE FROM journal_archives');c.commit()
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup database integrity check failed.')
        counts={'Pickup':0,'Delivery':0,'other':0,'total':0,'photos':c.execute('SELECT COUNT(*) FROM photos').fetchone()[0]}
        for row in c.execute('SELECT body FROM jobs'):
            kind=json.loads(row[0]).get('type');counts[kind if kind in ('Pickup','Delivery') else 'other']+=1;counts['total']+=1
        return counts

def verify_backup_archive(path,expected_digest):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Backup ZIP integrity check failed.')
        digest=hashlib.sha256(z.read('schedule.db')).hexdigest()
        manifest=json.loads(z.read('manifest.json'))
        if digest!=expected_digest or manifest.get('database_sha256')!=digest:raise ValueError('Saved backup does not match the database snapshot.')
        return manifest

def archive_dispatch(today=None):
    try:
        count=_archive_dispatch(today)
        (DATA/'journal-status.json').write_text(json.dumps({'at':dt.datetime.now().isoformat(),'archived':count,'error':None}))
        return count
    except Exception as e:
        (DATA/'journal-status.json').write_text(json.dumps({'at':dt.datetime.now().isoformat(),'error':str(e)}))
        raise

def _archive_dispatch(today=None):
    # The shared lock prevents an appointment changing between copy, verify and removal.
    with LOCK:
        cfg=backup_config()
        if not cfg.get('enabled') or not cfg.get('journal_enabled',True):return 0
        cutoff=(today or dt.date.today())-dt.timedelta(days=int(cfg.get('journal_days',30)))
        with connect() as c:
            selected=[]
            for row in c.execute('SELECT * FROM jobs'):
                job=json.loads(row['body'])
                if job.get('type') not in ('Pickup','Delivery'):continue
                try:
                    event=dt.date.fromisoformat((job.get('end') or job.get('start') or '')[:10])
                    last=c.execute('SELECT MAX(at) FROM audit WHERE job=?',(row['id'],)).fetchone()[0]
                    modified=dt.date.fromisoformat(last[:10]) if last else event
                except ValueError:continue
                if event>=cutoff:continue
                selected.append(tuple(row))
            if not selected:return 0
        # A fresh, complete and verified fallback must exist before any local removal.
        complete_backup()
        folder=journal_folder();folder.mkdir(parents=True,exist_ok=True)
        target=folder/('Dispatch-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(6)+'.db')
        partial=target.with_suffix('.partial')
        try:
            with connect() as source, closing(sqlite3.connect(partial)) as dest:
                dest.executescript('CREATE TABLE jobs(id TEXT PRIMARY KEY,revision INTEGER,body TEXT); CREATE TABLE photos(job TEXT,position INTEGER,body BLOB,PRIMARY KEY(job,position)); CREATE TABLE audit(at TEXT,actor TEXT,action TEXT,job TEXT);')
                for row in selected:
                    dest.execute('INSERT INTO jobs VALUES(?,?,?)',row)
                    dest.executemany('INSERT INTO photos VALUES(?,?,?)',[tuple(r) for r in source.execute('SELECT * FROM photos WHERE job=?',(row[0],))])
                    dest.executemany('INSERT INTO audit VALUES(?,?,?,?)',[tuple(r) for r in source.execute('SELECT * FROM audit WHERE job=?',(row[0],))])
                dest.commit()
                if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Journal integrity check failed.')
            digest=file_digest(partial)
            os.replace(partial,target)
            record={'file':target.name,'sha256':digest}
            with open_journal(record) as saved, connect() as source:
                for row in selected:
                    current=source.execute('SELECT * FROM jobs WHERE id=?',(row[0],)).fetchone()
                    copy=saved.execute('SELECT * FROM jobs WHERE id=?',(row[0],)).fetchone()
                    if not current or tuple(current)!=row or not copy or tuple(copy)!=row:raise ValueError('Dispatch record changed during archiving; local data retained.')
                    for table,order in [('photos','position'),('audit','rowid')]:
                        query=f'SELECT * FROM {table} WHERE job=? ORDER BY {order}'
                        if [tuple(r) for r in source.execute(query,(row[0],))]!=[tuple(r) for r in saved.execute(query,(row[0],))]:raise ValueError('Journal attachments or history failed verification.')
                source.execute('INSERT INTO journal_archives VALUES(?,?,?,?)',(target.name,digest,len(selected),dt.datetime.now().isoformat()))
                for row in selected:
                    source.execute('DELETE FROM photos WHERE job=?',(row[0],))
                    source.execute('DELETE FROM audit WHERE job=?',(row[0],))
                    source.execute('DELETE FROM jobs WHERE id=?',(row[0],))
            # Reclaim the pages only after the verified archive and DB transaction succeed.
            with closing(sqlite3.connect(DB)) as c:c.execute('VACUUM')
            return len(selected)
        finally:partial.unlink(missing_ok=True)

def complete_backup():
    with LOCK:return _complete_backup()

def _complete_backup():
    cfg=backup_config()
    if not cfg.get('folder'): raise ValueError('Set up a OneDrive backup folder in Settings first.')
    folder=Path(cfg['folder'])
    if not folder.is_absolute(): raise ValueError('The backup folder must be an absolute path on the server computer.')
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/('Thrift-Mart-Dispatch-Backup-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.zip')
    partial=target.with_suffix('.partial')
    try:
        with tempfile.TemporaryDirectory(dir=DATA) as temp:
            snapshot=Path(temp)/'schedule.db'
            with connect() as src, closing(sqlite3.connect(snapshot)) as dst: src.backup(dst)
            counts=merge_journals(snapshot);digest=file_digest(snapshot)
            with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(snapshot,'schedule.db')
                for name in ('updates.json','backup-settings.json'):
                    if (DATA/name).exists(): z.write(DATA/name,name)
                z.writestr('manifest.json',json.dumps({'application':'thrift-mart-dispatch','format':1,'version':updater.current(),'created':dt.datetime.now().isoformat(),'database_sha256':digest,'verified_counts':counts,'includes_dispatch_journal':True}))
            verify_backup_archive(partial,digest)
            os.replace(partial,target)
            verify_backup_archive(target,digest)
        # Keep the latest 90 complete archives in the configured folder.
        for old in sorted(folder.glob('Thrift-Mart-Dispatch-Backup-*.zip'),key=lambda p:p.stat().st_mtime)[:-90]:old.unlink()
        (DATA/'backup-status.json').write_text(json.dumps({'file':str(target),'at':dt.datetime.now().isoformat(timespec='seconds'),'saved_at':time.time(),'error':None,'verified':True,'counts':counts,'database_sha256':digest,'cloud_sync':'Check OneDrive sync status on the host computer'}))
        return str(target)
    except Exception as e:
        partial.unlink(missing_ok=True)
        previous=DATA/'backup-status.json'
        try:status=json.loads(previous.read_text()) if previous.exists() else {}
        except ValueError:status={}
        status['error']=str(e);status['failed_at']=dt.datetime.now().isoformat(timespec='seconds');previous.write_text(json.dumps(status))
        raise

def background():
    while True:
        try:
            with LOCK:
                backup()
                status=DATA/'backup-status.json'
                last=json.loads(status.read_text()).get('saved_at',0) if status.exists() else 0
                if backup_config().get('enabled') and time.time()-last>=3600:
                    complete_backup();archive_dispatch()
        except Exception as e: print('Backup failed:',e)
        time.sleep(60)

# Keep a process-wide lock, also used by the offline restore utility.
def hold_data_lock():
    f=(DATA/'server.lock').open('a+b');f.seek(0);f.write(b'0');f.flush();f.seek(0)
    try:
        if os.name=='nt':
            import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        f.close();raise SystemExit('Another server or restore process is using this data folder.')
    return f

FAVICON_SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><g fill="none" stroke="white" stroke-width="50"><ellipse cx="154" cy="290" rx="118" ry="118"/><ellipse cx="268" cy="386" rx="104" ry="104"/><ellipse cx="260" cy="152" rx="128" ry="128"/></g><g fill="none" stroke="#ea4520" stroke-width="34"><ellipse cx="154" cy="290" rx="112" ry="112"/><ellipse cx="268" cy="386" rx="98" ry="98"/><ellipse cx="260" cy="152" rx="122" ry="122"/></g><rect x="278" y="216" width="216" height="276" rx="9" fill="#b8c7d2" stroke="white" stroke-width="8"/><path fill="#8fa5b5" d="M430 228h50v252h-50z"/><path fill="#667e90" d="M305 204h159v26H305z"/><g fill="#286584"><rect x="306" y="248" width="25" height="29"/><rect x="350" y="248" width="25" height="29"/><rect x="394" y="248" width="25" height="29"/><rect x="438" y="248" width="25" height="29"/><rect x="306" y="295" width="25" height="29"/><rect x="350" y="295" width="25" height="29"/><rect x="394" y="295" width="25" height="29"/><rect x="438" y="295" width="25" height="29"/><rect x="306" y="342" width="25" height="29"/><rect x="350" y="342" width="25" height="29"/><rect x="394" y="342" width="25" height="29"/><rect x="438" y="342" width="25" height="29"/><rect x="306" y="389" width="25" height="29"/><rect x="350" y="389" width="25" height="29"/><rect x="394" y="389" width="25" height="29"/><rect x="438" y="389" width="25" height="29"/></g><path fill="#334c60" d="M365 437h46v43h-46z"/><rect x="270" y="480" width="231" height="21" rx="5" fill="#536e82"/></svg>'

class Problem(Exception):
    def __init__(self,message,status=400,**details): self.message=message; self.status=status; self.details=details

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): pass
    def external_scheme(self):
        # Only a connector on this server may describe the browser's TLS connection.
        # Keep Host unchanged: never trust X-Forwarded-Host for origin validation.
        if self.client_address[0] in ('127.0.0.1','::1') and self.headers.get('X-Forwarded-Proto')=='https':
            return 'https'
        return 'http'

    def send(self,data,status=200,cookie=None,kind='application/json',attachment=False):
        raw=json.dumps(data).encode() if kind=='application/json' else data
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data: blob: https://tile.openstreetmap.org; media-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        if attachment: self.send_header('Content-Disposition','attachment')
        if cookie: self.send_header('Set-Cookie',cookie+('; Secure' if self.external_scheme()=='https' else ''))
        self.end_headers(); self.wfile.write(raw)
    def user(self):
        cookie=SimpleCookie(); cookie.load(self.headers.get('Cookie',''))
        token=cookie.get('session'); token=token.value if token else ''
        session=SESSIONS.get(token)
        local_control=os.environ.get('DISPATCH_CONTROL_TOKEN','')
        trusted_local=self.client_address[0] in ('127.0.0.1','::1') and local_control and hmac.compare_digest(self.headers.get('X-Local-Control',''),local_control)
        if trusted_local and token:
            with connect() as c:
                row=c.execute('SELECT s.name,s.version FROM local_admin_sessions s JOIN users u ON u.name=s.name WHERE s.token_hash=? AND u.admin=1',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if row and row['version']==updater.current():session={'name':row['name'],'admin':True,'local_admin':True,'version':row['version']};SESSIONS[token]=session
            elif session and session.get('local_admin'):session=None
        elif session and session.get('local_admin'):session=None
        if not session or session_expired(session, time.time()):
            SESSIONS.pop(token, None)
            raise Problem('Please sign in again.',401)
        if self.headers.get('X-Dispatch-Activity')=='1':session['last_active']=time.time()
        with connect() as c:
            permission=c.execute('SELECT * FROM permissions WHERE name=?',(session['name'],)).fetchone()
            profile=c.execute('SELECT profile_id FROM receipt_profiles WHERE name=?',(session['name'],)).fetchone()
            session['receipt_owner']=profile['profile_id'] if profile else None
        with connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS user_grants(name TEXT PRIMARY KEY COLLATE NOCASE, body TEXT)')
            saved=c.execute('SELECT body FROM user_grants WHERE name=?',(session['name'],)).fetchone()
        session['can_create']=bool(session['admin'] or not permission or permission['can_create'])
        session['see_requests']=bool(session['can_create'] and (permission['see_requests'] if permission else session['admin']))
        defaults={key:False for key in PERMISSIONS}
        defaults.update({key:True for key in ('view_schedule','submit_requests','cancel_appointments','call_contacts','text_contacts','navigate','change_own_password')})
        for key in ('create_appointments','edit_appointments','delete_appointments','update_status','review_requests'): defaults[key]=session['can_create']
        defaults['see_requests']=session['see_requests'];defaults['view_reports']=session['can_create']
        defaults['submit_receipts']=True
        with connect() as c:role=c.execute('SELECT r.body FROM permission_roles r JOIN user_roles a ON a.role_id=r.id WHERE a.name=?',(session['name'],)).fetchone()
        session['grants']=json.loads(role['body']) if role else json.loads(saved['body']) if saved else defaults
        session['grants'].setdefault('submit_receipts',True)
        for key in ('view_schedule','show_vehicle_filter','show_search'): session['grants'].setdefault(key,True)
        session['can_create']=has_permission(session,'create_appointments')
        session['see_requests']=has_permission(session,'see_requests')
        return session
    def serve_mobile_media(self,head_only=False):
        path=urlsplit(self.path).path
        if path not in ('/media/mobile-intro.mp4','/media/mobile-intro.webm'):return False
        extension=path.rsplit('.',1)[1]
        if extension not in MOBILE_MEDIA:
            html=(ROOT/'static/index.html').read_text(encoding='utf-8')
            match=re.search(r'<script[^>]*id="splashMedia"[^>]*>(.*?)</script>',html,re.S)
            MOBILE_MEDIA[extension]=base64.b64decode(json.loads(match.group(1))['mobile'+extension].split(',',1)[1])
        raw=MOBILE_MEDIA[extension];total=len(raw);start=0;end=total-1;status=200
        etag='"'+hashlib.sha256(raw).hexdigest()+'"'
        requested=self.headers.get('Range') if not head_only else None
        if self.headers.get('If-Range') not in (None,etag):requested=None
        if requested:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested.strip())
            try:
                if not match or not any(match.groups()):raise ValueError()
                first,last=match.groups()
                if first:start=int(first);end=min(int(last),total-1) if last else total-1
                else:
                    count=int(last)
                    if count<=0:raise ValueError()
                    start=max(0,total-count)
                if start>=total or start>end:raise ValueError()
                status=206
            except (ValueError,OverflowError):
                self.send_response(416);self.send_header('Content-Range','bytes */'+str(total));self.send_header('Content-Length','0');self.end_headers();return True
        self.send_response(status);self.send_header('Content-Type','video/'+extension);self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1));self.send_header('Cache-Control','no-store');self.send_header('ETag',etag)
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{total}')
        self.end_headers()
        if not head_only:
            try:self.wfile.write(raw[start:end+1])
            except (BrokenPipeError,ConnectionResetError):pass
        return True
    def do_HEAD(self):
        if not self.serve_mobile_media(True):self.send_error(404)
    def do_GET(self):
        try:
            request=urlsplit(self.path)
            if request.path=='/api/workforce/geocode':
                with LOCK:
                    user=self.user()
                    if not has_permission(user,'manage_work_sites'):
                        raise Problem('Work site management permission required.',403)
                address=parse_qs(request.query).get('address',[''])[0]
                return self.send({'matches':work_geocode(address)})

            if self.serve_mobile_media():return
            if self.path=='/offline.gif':return self.send(web_asset('gif'),kind='image/gif')
            if self.path in ('/app-icon-180.png','/app-icon-192.png','/app-icon-512.png'):return self.send(web_asset(self.path.split('-')[-1].split('.')[0]),kind='image/png')
            if self.path=='/push-worker.js':return self.send(PUSH_WORKER,kind='text/javascript; charset=utf-8')
            if self.path=='/manifest.webmanifest':return self.send(json.dumps({'name':'MGC YFC Operations','short_name':'YFC Operations','start_url':'/','scope':'/','display':'standalone','background_color':'#101821','theme_color':'#073ea6','icons':[{'src':'/app-icon-'+str(size)+'.png','sizes':str(size)+'x'+str(size),'type':'image/png','purpose':'any'} for size in (192,512)]}).encode(),kind='application/manifest+json')
            if self.path in ('/favicon.svg','/favicon.ico'):
                return self.send(FAVICON_SVG.encode(),kind='image/svg+xml')
            if self.path in ('/','/mobile','/mobile/','/app.js','/style.css'):
                filename={'/':'index.html','/mobile':'index.html','/mobile/':'index.html','/app.js':'app.js','/style.css':'style.css'}[self.path]
                kind={'/':'text/html; charset=utf-8','/mobile':'text/html; charset=utf-8','/mobile/':'text/html; charset=utf-8','/app.js':'text/javascript','/style.css':'text/css'}[self.path]
                body=(ROOT/'static'/filename).read_bytes()
                if filename=='index.html':body=body.replace(b'</head>',b'<link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" sizes="180x180" href="/app-icon-180.png"><link rel="manifest" href="/manifest.webmanifest"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="YFC Operations"></head>')
                return self.send(body,kind=kind)
            with LOCK, connect() as c:
                if self.path=='/api/page-colors':
                    row=c.execute('SELECT body FROM page_colors WHERE id=1').fetchone()
                    return self.send({'pages':json.loads(row['body']) if row else DEFAULT_PAGE_COLORS,'defaults':DEFAULT_PAGE_COLORS})
                if self.path=='/api/sharing':
                    row=c.execute('SELECT body FROM sharing_settings WHERE id=1').fetchone()
                    return self.send(json.loads(row['body']) if row else {'mobile':{'text':True,'email':True,'native':True},'desktop':{'text':True,'email':True,'native':False}})
                if self.path=='/api/connection-status':
                    return self.send({'online':True,'update_available':UPDATE_STATUS['available']})
                if self.path=='/api/session':
                    setup=not c.execute('SELECT 1 FROM users').fetchone()
                    try: u=self.user()
                    except Problem: u=None
                    return self.send({'application':'thrift-mart-dispatch','name':'MGC YFC Operations Server','version':updater.current(),'setup':setup,'user':u and {'name':u['name'],'admin':u['admin'],'can_create':u['can_create'],'see_requests':u['see_requests'],'grants':u['grants']},'local':self.client_address[0] in ('127.0.0.1','::1')})
                if self.path=='/api/receipt-users':
                    people=[]
                    for row in c.execute('SELECT u.name,u.admin,p.profile_id,g.body FROM users u JOIN receipt_profiles p ON p.name=u.name LEFT JOIN user_grants g ON g.name=u.name ORDER BY u.name'):
                        assigned=c.execute('SELECT r.body FROM permission_roles r JOIN user_roles a ON a.role_id=r.id WHERE a.name=?',(row['name'],)).fetchone()
                        grants=json.loads(assigned['body']) if assigned else json.loads(row['body']) if row['body'] else {}
                        if row['admin'] or grants.get('submit_receipts',True):people.append({'id':row['profile_id'],'name':row['name']})
                    return self.send({'users':people})
                if self.path=='/api/receipt-categories':
                    return self.send({'categories':[r[0] for r in c.execute('SELECT code FROM receipt_categories ORDER BY code')]})
                if urlsplit(self.path).path=='/api/workforce/quick':
                    return work_get(self,c,clock_pin_user(self,c),'overview',{},clock_only=True)
                u=self.user()
                request=urlsplit(self.path)
                if request.path=='/api/admin/user-identity':
                    target=identity_target(c,u,parse_qs(request.query).get('name',[''])[0])
                    return self.send(user_identity(c,target['profile_id'],target['name']))
                if request.path.startswith('/api/profile/'):
                    return profile_get(self,c,u,request.path[len('/api/profile/'):])
                if request.path.startswith('/api/workforce/'):
                    return work_get(self,c,u,request.path[len('/api/workforce/'):],parse_qs(request.query))
                if request.path.startswith('/api/comms/'):
                    return comm_get(self,c,u,request.path[len('/api/comms/'):],parse_qs(request.query))
                if self.path.startswith('/api/receipt-file/'):
                    row=c.execute('SELECT r.body,r.mime,o.profile_id AS owner FROM receipts r LEFT JOIN receipt_ownership o ON o.receipt_id=r.id WHERE r.id=?',(self.path.rsplit('/',1)[1],)).fetchone()
                    if not row or not (has_permission(u,'view_all_receipts') or row['owner'] and row['owner']==u.get('receipt_owner')):raise Problem('Receipt not found.',404)
                    return self.send(bytes(row['body']),kind=row['mime'])
                if urlsplit(self.path).path=='/api/receipts':
                    query=parse_qs(urlsplit(self.path).query);value=lambda key:query.get(key,[''])[0]
                    all_users=value('scope')=='all'
                    if all_users and not has_permission(u,'view_all_receipts'):raise Problem('All-receipt access required.',403)
                    clauses=[];args=[]
                    if not all_users:clauses.append('id IN (SELECT receipt_id FROM receipt_ownership WHERE profile_id=?)');args.append(u.get('receipt_owner'))
                    if value('search'):
                        clauses.append('(instr(lower(filename),lower(?))>0 OR instr(lower(category),lower(?))>0 OR instr(lower(actor),lower(?))>0)');args.extend([value('search')[:200]]*3)
                    if value('category'):clauses.append('category=?');args.append(value('category'))
                    for key,op,days in [('from','>=',0),('to','<',1)]:
                        if value(key):
                            try:stamp=dt.datetime.combine(dt.date.fromisoformat(value(key))+dt.timedelta(days=days),dt.time()).timestamp()
                            except ValueError:raise Problem('Choose valid receipt dates.')
                            clauses.append('at'+op+'?');args.append(stamp)
                    where=' WHERE '+' AND '.join(clauses) if clauses else ''
                    try:offset=max(0,int(value('offset') or 0))
                    except ValueError:raise Problem('Invalid page.')
                    count=c.execute('SELECT COUNT(*) FROM receipts'+where,args).fetchone()[0]
                    rows=c.execute('SELECT id,at,actor,category,filename,COALESCE((SELECT reimbursement FROM receipt_details WHERE receipt_id=receipts.id),0) AS reimbursement_required,COALESCE((SELECT guest_assigned FROM receipt_details WHERE receipt_id=receipts.id),0) AS guest_assigned FROM receipts'+where+' ORDER BY at DESC,id LIMIT 100 OFFSET ?',args+[offset]).fetchall()
                    return self.send({'receipts':[dict(r) for r in rows],'total':count,'offset':offset,'can_view_all':has_permission(u,'view_all_receipts')})
                if self.path=='/api/admin/receipts':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    return self.send({'receipts':[dict(r) for r in c.execute('SELECT id,at,actor,category,filename,COALESCE((SELECT reimbursement FROM receipt_details WHERE receipt_id=receipts.id),0) AS reimbursement_required,COALESCE((SELECT guest_assigned FROM receipt_details WHERE receipt_id=receipts.id),0) AS guest_assigned FROM receipts ORDER BY at DESC LIMIT 200')]})
                if self.path.startswith('/api/admin/receipt-file/'):
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    r=c.execute('SELECT body,mime FROM receipts WHERE id=?',(self.path.rsplit('/',1)[1],)).fetchone()
                    if not r: raise Problem('Receipt not found.',404)
                    return self.send(r['body'],kind=r['mime'])
                if self.path=='/api/admin/login-security':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    return self.send({'max_attempts':c.execute('SELECT max_attempts FROM login_security WHERE id=1').fetchone()[0]})
                if self.path=='/api/admin/lockouts':
                    if not has_permission(u,'unlock_users'): raise Problem('Unlock users permission required.',403)
                    return self.send({'users':[dict(r) for r in c.execute('SELECT l.name,l.failures,l.locked_at FROM account_lockouts l JOIN users u ON u.name=l.name WHERE l.locked_at IS NOT NULL ORDER BY l.name')]})
                if self.path=='/api/roles':
                    if not (has_permission(u,'manage_users') or has_permission(u,'manage_roles')):raise Problem('Employee or role management permission required.',403)
                    return self.send({'permissions':PERMISSIONS,'groups':permission_groups(),'roles':[{'id':r['id'],'name':r['name'],'grants':json.loads(r['body'])} for r in c.execute('SELECT * FROM permission_roles ORDER BY name')],'assignments':{r['name']:r['role_id'] for r in c.execute('SELECT * FROM user_roles')},'can_edit':has_permission(u,'manage_roles'),'can_assign':has_permission(u,'manage_users'),'grantable':[key for key in PERMISSIONS if has_permission(u,key)]})
                if self.path=='/api/admin/permission-catalog':
                    if not has_permission(u,'manage_users'): raise Problem('Administrator access required.',403)
                    return self.send({'permissions':PERMISSIONS,'users':[{'name':r['name'],'grants':json.loads(r['body'])} for r in c.execute('SELECT * FROM user_grants')]})
                if self.path=='/api/admin/users':
                    if not any(has_permission(u, permission) for permission in ('manage_users','reset_passwords','rename_users','manage_staff_schedule')):
                        raise Problem('Administrator access required.',403)
                    return self.send({'users':[dict(r) for r in c.execute('SELECT users.name,admin,COALESCE(permissions.can_create,1) AS can_create,COALESCE(permissions.see_requests,admin) AS see_requests FROM users LEFT JOIN permissions ON users.name=permissions.name ORDER BY users.name')]})
                if self.path=='/api/admin/backup-settings':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    p=DATA/'backup-status.json'
                    return self.send({'config':backup_config(),'status':json.loads(p.read_text()) if p.exists() else None,'journal':{'status':json.loads((DATA/'journal-status.json').read_text()) if (DATA/'journal-status.json').exists() else None,'archives':c.execute('SELECT COUNT(*) FROM journal_archives').fetchone()[0],'records':c.execute('SELECT COALESCE(SUM(records),0) FROM journal_archives').fetchone()[0]}})
                if self.path=='/api/admin/status':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    return self.send({'name':'MGC YFC Operations Server','version':updater.current(),'uptime_minutes':int((time.time()-STARTED)/60),'time':dt.datetime.now().isoformat(timespec='seconds'),'jobs':c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],'vehicles':c.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0],'users':c.execute('SELECT COUNT(*) FROM users').fetchone()[0]})
                if self.path=='/api/updates' and route_allowed(u,self.path):
                    last=DATA/'last-update.json'
                    return self.send({'current':updater.current(),'repository':updater.repo(),'launcher':os.environ.get('DISPATCH_LAUNCHER')=='1','last':json.loads(last.read_text()) if last.exists() else None})
                if self.path.startswith('/api/photo/'):
                    parts=self.path.split('/')
                    if len(parts)!=5: raise Problem('Not found',404)
                    row=c.execute('SELECT body FROM jobs WHERE id=?',(parts[3],)).fetchone()
                    if not row: raise Problem('Not found',404)
                    job=json.loads(row['body'])
                    if not has_permission(u,'view_schedule') or (job.get('request') and not u['can_create'] and job.get('requestedBy')!=u['name']): raise Problem('Permission required.',403)
                    photo=c.execute('SELECT body FROM photos WHERE job=? AND position=?',(parts[3],int(parts[4]))).fetchone()
                    if not photo: raise Problem('Not found',404)
                    return self.send(bytes(photo['body']),kind='image/jpeg')
                if self.path=='/api/account/appearance':
                    row=c.execute('SELECT mode FROM appearance_preferences WHERE name=?',(u['name'],)).fetchone()
                    return self.send({'mode':row['mode'] if row else 'system'})
                if self.path=='/api/account/landing':
                    preference=c.execute('SELECT section,chosen_on FROM landing_preferences WHERE name=?',(u['name'],)).fetchone()
                    today=dt.date.today().isoformat();options=section_options(u)
                    section=preference['section'] if preference and preference['chosen_on']==today and preference['section'] in {o['id'] for o in options} else None
                    home=c.execute('SELECT section FROM daily_home WHERE name=? AND day=?',(u['name'],today)).fetchone()
                    return self.send({'section':section,'home_section':section,'date':today,'options':options})
                if self.path=='/api/paging':
                    if not has_permission(u,'send_pages') and not has_permission(u,'receive_pages'): raise Problem('Paging permission required.',403)
                    return self.send({'pages':[dict(r) for r in c.execute('SELECT * FROM pages WHERE at>? ORDER BY id',(time.time()-60,))],'latest':c.execute('SELECT COALESCE(MAX(id),0) FROM pages').fetchone()[0]})
                if self.path=='/api/reports':
                    if not has_permission(u,'view_reports'): raise Problem('Reports permission required.',403)
                    try: jobs=all_report_jobs(c)
                    except Exception as e:raise Problem('Historical reports unavailable: '+str(e),503)
                    return self.send({'jobs':[j for j in jobs if not j.get('request') or u['can_create'] or j.get('requestedBy')==u['name']]})
                if self.path=='/api/state':
                    if not has_permission(u,'view_schedule'): raise Problem('Schedule access required.',403)
                    pending_counts={}
                    for row in c.execute('SELECT body FROM jobs'):
                        request=json.loads(row['body'])
                        if request.get('request') and request.get('status')!='Canceled':
                            date=request.get('start','')[:10]
                            counts=pending_counts.setdefault(date,{'Pickup':0,'Delivery':0})
                            if request.get('type') in counts: counts[request['type']]+=1
                    notice=c.execute('SELECT * FROM update_notices ORDER BY id DESC LIMIT 1').fetchone()
                    return self.send({'updateNotice':dict(notice) if notice else None,'pendingCounts':pending_counts,'jobs':[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM jobs') if not json.loads(r['body']).get('request')], 'requests':[dict(json.loads(r['body']),id=r['id'],revision=r['revision']) for r in c.execute('SELECT * FROM jobs') if json.loads(r['body']).get('request') and (u['can_create'] or json.loads(r['body']).get('requestedBy')==u['name'])], 'permissions':{'can_create':u['can_create'],'see_requests':u['see_requests'],'grants':u['grants']}, 'vehicles':[r[0] for r in c.execute('SELECT name FROM vehicles ORDER BY name')], 'users':[dict(r) for r in c.execute('SELECT users.name,admin,COALESCE(permissions.can_create,1) AS can_create,COALESCE(permissions.see_requests,admin) AS see_requests FROM users LEFT JOIN permissions ON users.name=permissions.name ORDER BY users.name')]})
                if self.path=='/api/audit' and route_allowed(u,self.path):
                    return self.send([dict(r) for r in c.execute('SELECT * FROM audit ORDER BY rowid DESC LIMIT 100')])
                raise Problem('Not found',404)
        except Problem as e: self.send({'error':e.message,**e.details},e.status)
    def do_POST(self):
        global RESTART, STOPPING
        try:
            if self.headers.get('X-Dispatch')!='1': raise Problem('Invalid request.',403)
            origin=self.headers.get('Origin')
            if origin and origin!=self.external_scheme()+'://'+self.headers.get('Host',''): raise Problem('Invalid origin.',403)
            n=int(self.headers.get('Content-Length','0'))
            if n>4500000: raise Problem('Request too large.')
            d=json.loads(self.rfile.read(n))
            if not isinstance(d,dict): raise Problem('Invalid request.')
            with LOCK, connect() as c:
                if RESTART or STOPPING: raise Problem('Update is restarting the server. Please wait and sign in again.',503)
                if self.path=='/api/local/stop':
                    expected=os.environ.get('DISPATCH_CONTROL_TOKEN','')
                    if self.client_address[0] not in ('127.0.0.1','::1') or not expected or not hmac.compare_digest(str(d.get('token','')),expected): raise Problem('Local server controller required.',403)
                    STOPPING=True
                    self.send({'ok':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                if self.path=='/api/workforce/quick/login':
                    return clock_pin_login(self,c,d)
                if self.path=='/api/workforce/quick/close':
                    CLOCK_SESSIONS.pop(clock_pin_cookie(self),None)
                    return self.send({'ok':True},cookie='clock_session=; HttpOnly; SameSite=Strict; Path=/api/workforce/quick; Max-Age=0')
                if self.path=='/api/workforce/quick/punch':
                    clock_user=clock_pin_user(self,c)
                    return work_post(self,c,clock_user,'punch',d,clock_only=True)
                if self.path in ('/api/setup','/api/login'):
                    name=str(d.get('name','')).strip(); p=str(d.get('password',''))
                    if self.path=='/api/setup':
                        if self.client_address[0] not in ('127.0.0.1','::1') or self.headers.get('X-Forwarded-Proto') or self.headers.get('CF-Connecting-IP'): raise Problem('Create the first account on the server computer.',403)
                        if c.execute('SELECT 1 FROM users').fetchone(): raise Problem('Already set up.',409)
                        self.add_user(c,name,p,True)
                    r=find_login_user(c,name)
                    if not r:
                        key=self.client_address[0]; attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-300]
                        if len(attempts)>=15: raise Problem('Too many attempts. Wait five minutes.',429)
                        ATTEMPTS[key]=attempts+[time.time()]
                        raise Problem('Incorrect name or password.',401)
                    lockout=c.execute('SELECT * FROM account_lockouts WHERE name=?',(r['name'],)).fetchone()
                    if lockout and lockout['locked_at']: raise Problem('Account locked. Ask an administrator or authorized employee to unlock it.',423,attempts_remaining=0)
                    if not hmac.compare_digest(r['hash'],password(p,r['salt'])):
                        failures=(lockout['failures'] if lockout else 0)+1
                        limit=c.execute('SELECT max_attempts FROM login_security WHERE id=1').fetchone()[0]
                        locked_at=dt.datetime.now().astimezone().isoformat(timespec='seconds') if failures>=limit else None
                        c.execute('INSERT OR REPLACE INTO account_lockouts VALUES(?,?,?)',(r['name'],failures,locked_at))
                        if locked_at: c.execute('INSERT INTO audit VALUES(?,?,?,?)',(locked_at,r['name'],'Account locked after failed login attempts',''))
                        c.commit() # Persist failures even though the response below raises an error.
                        if locked_at: raise Problem('Account locked. Ask an administrator or authorized employee to unlock it.',423,attempts_remaining=0)
                        raise Problem('Incorrect name or password.',401,attempts_remaining=max(0,limit-failures))
                    c.execute('DELETE FROM account_lockouts WHERE name=?',(r['name'],))
                    local_admin=bool(d.get('local_admin'))
                    if local_admin:
                        control=os.environ.get('DISPATCH_CONTROL_TOKEN','')
                        if not r['admin'] or self.client_address[0] not in ('127.0.0.1','::1') or not control or not hmac.compare_digest(str(d.get('local_control_token','')),control):raise Problem('Local server administration required.',403)
                    token=secrets.token_urlsafe(32); SESSIONS[token]={'name':r['name'],'admin':bool(r['admin']),'expires':time.time()+86400,'login_day':dt.date.today().isoformat(),'last_active':time.time()}
                    if local_admin:
                        c.execute('INSERT INTO local_admin_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),r['name'],updater.current()))
                        SESSIONS[token].update(local_admin=True,version=updater.current())
                    return self.send({'ok':True},cookie=f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={315360000 if local_admin else 86400}')
                if self.path=='/api/receipt-submit':
                    # This is intentionally public. Never grants a session or schedule access.
                    category=d.get('category'); ident=d.get('id'); filename=d.get('filename')
                    if not isinstance(ident,str) or len(ident)!=32 or any(x not in '0123456789abcdef' for x in ident): raise Problem('Invalid submission ID.')
                    source=hashlib.sha256(self.client_address[0].encode()).hexdigest()
                    if c.execute('SELECT 1 FROM receipts WHERE id=?',(ident,)).fetchone():
                        return self.send({'ok':True,'id':ident,'email_pending':True})
                    if c.execute('SELECT COUNT(*) FROM receipts WHERE source=? AND at>?',(source,time.time()-300)).fetchone()[0]>=10: raise Problem('Please wait five minutes before submitting more receipts.',429)
                    if not isinstance(category,str) or not c.execute('SELECT 1 FROM receipt_categories WHERE code=?',(category,)).fetchone(): raise Problem('Select a configured category or code.')
                    if not isinstance(filename,str) or not 1<=len(filename)<=200: raise Problem('Choose a receipt file.')
                    try: body=base64.b64decode(d.get('body',''),validate=True)
                    except (ValueError,TypeError): raise Problem('Invalid receipt file.')
                    if not 1<=len(body)<=3000000: raise Problem('Receipt files must be 3 MB or smaller.')
                    mime=None
                    if body.startswith(b'\xff\xd8\xff'): mime='image/jpeg'
                    elif body.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png'
                    elif body.startswith(b'%PDF-'): mime='application/pdf'
                    elif len(body)>12 and body[4:8]==b'ftyp' and body[8:12] in (b'heic',b'heix',b'hevc',b'hevx',b'mif1'): mime='image/heic'
                    elif len(body)>12 and body[:4]==b'RIFF' and body[8:12]==b'WEBP': mime='image/webp'
                    if not mime: raise Problem('Choose a JPEG, PNG, HEIC, WebP or PDF receipt.')
                    try:
                        uploader=self.user();owner=uploader['receipt_owner'];actor=uploader['name']
                    except Problem:
                        if d.get('account_upload'):raise Problem('Sign in again before saving this receipt to your profile.',401)
                        target=c.execute('SELECT u.name,u.admin,p.profile_id,g.body FROM users u JOIN receipt_profiles p ON p.name=u.name LEFT JOIN user_grants g ON g.name=u.name WHERE p.profile_id=?',(str(d.get('assignee','')),)).fetchone()
                        if not target:raise Problem('Select a current user for this receipt.')
                        assigned=c.execute('SELECT r.body FROM permission_roles r JOIN user_roles a ON a.role_id=r.id WHERE a.name=?',(target['name'],)).fetchone()
                        grants=json.loads(assigned['body']) if assigned else json.loads(target['body']) if target['body'] else {}
                        if not target['admin'] and not grants.get('submit_receipts',True):raise Problem('This user cannot submit receipts.')
                        owner=target['profile_id'];actor=target['name'];uploader=None
                    if uploader and not has_permission(uploader,'submit_receipts'):raise Problem('Receipt submission permission required.',403)
                    reimbursement=d.get('reimbursement_required',False)
                    if not isinstance(reimbursement,bool):raise Problem('Choose whether reimbursement is required.')
                    c.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?)',(ident,time.time(),actor,category,filename,mime,body,source))
                    c.execute('INSERT INTO receipt_ownership VALUES(?,?)',(ident,owner))
                    c.execute('INSERT INTO receipt_details VALUES(?,?,?)',(ident,int(reimbursement),int(uploader is None)))
                    return self.send({'ok':True,'id':ident,'email_pending':True})
                u=self.user()
                if self.path.startswith('/api/profile/'):
                    return profile_post(self,c,u,self.path[len('/api/profile/'):],d)
                if self.path.startswith('/api/workforce/'):
                    return work_post(self,c,u,self.path[len('/api/workforce/'):],d)
                if self.path.startswith('/api/comms/'):
                    return comm_post(self,c,u,self.path[len('/api/comms/'):],d)
                if self.path=='/api/page-colors':
                    if not u['admin']:raise Problem('Administrator access required.',403)
                    pages=d.get('pages')
                    if not isinstance(pages,dict) or set(pages)!=set(DEFAULT_PAGE_COLORS) or any(not isinstance(v,dict) or set(v)!={'header','light','dark'} or any(not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color) for color in v.values()) for v in pages.values()):raise Problem('Use six-digit hex colors for every page.')
                    pages={name:{key:value.lower() for key,value in colors.items()} for name,colors in pages.items()}
                    c.execute('INSERT OR REPLACE INTO page_colors VALUES(1,?)',(json.dumps(pages),))
                    return self.send({'pages':pages,'defaults':DEFAULT_PAGE_COLORS})
                if self.path=='/api/sharing':
                    if not u['admin']:raise Problem('Administrator access required.',403)
                    if set(d)!={'mobile','desktop'} or any(not isinstance(d[k],dict) or set(d[k])!={'text','email','native'} or any(not isinstance(v,bool) for v in d[k].values()) for k in d):raise Problem('Invalid sharing options.')
                    c.execute('INSERT OR REPLACE INTO sharing_settings VALUES(1,?)',(json.dumps(d),))
                    return self.send(d)
                if self.path=='/api/account/activity':
                    u['last_active']=time.time()
                    return self.send({'ok':True})
                if self.path=='/api/account/appearance':
                    mode=d.get('mode')
                    if mode not in ('light','dark','system'):raise Problem('Choose Light, Dark or Use system settings.')
                    c.execute('INSERT OR REPLACE INTO appearance_preferences VALUES(?,?)',(u['name'],mode))
                    return self.send({'mode':mode})
                if self.path=='/api/repository-unlock':
                    if not (has_permission(u,'check_updates') or has_permission(u,'configure_updates')):raise Problem('Update settings permission required.',403)
                    name=str(d.get('name','')).strip()
                    key='repo:'+self.client_address[0]
                    attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-300]
                    if len(attempts)>=5:raise Problem('Too many attempts. Wait five minutes.',429)
                    ATTEMPTS[key]=attempts+[time.time()]
                    row=find_login_user(c,name)
                    locked=c.execute('SELECT locked_at FROM account_lockouts WHERE name=?',(row['name'],)).fetchone() if row else None
                    if not row or not row['admin'] or (locked and locked['locked_at']) or not hmac.compare_digest(row['hash'],password(str(d.get('password','')),row['salt'])):
                        raise Problem('Valid administrator credentials are required.',403)
                    ATTEMPTS.pop(key,None)
                    u['repository_unlock']={'until':time.time()+300,'administrator':row['name']}
                    return self.send({'ok':True,'expires_in':300})
                if self.path=='/api/update-config':
                    approval=u.pop('repository_unlock',None)
                    if not approval or approval['until']<time.time():raise Problem('Unlock repository settings with administrator credentials first.',403)
                    admin=c.execute('SELECT admin FROM users WHERE name=?',(approval['administrator'],)).fetchone()
                    if not admin or not admin['admin']:raise Problem('Administrator approval is no longer valid.',403)
                    try:updater.configure(str(d.get('repository','')).strip())
                    except ValueError as e:raise Problem(str(e))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),approval['administrator'],'Update repository changed by '+u['name'],''))
                    return self.send({'ok':True})
                if self.path in ROUTE_PERMISSIONS and not route_allowed(u,self.path): raise Problem('Administrator or delegated permission required.',403)
                if self.path=='/api/admin/receipt-categories':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    categories=d.get('categories')
                    if not isinstance(categories,list) or len(categories)>200 or any(not isinstance(x,str) or not 1<=len(x.strip())<=100 for x in categories): raise Problem('Enter up to 200 categories, each 1–100 characters.')
                    categories=list(dict.fromkeys(x.strip() for x in categories))
                    c.execute('DELETE FROM receipt_categories')
                    c.executemany('INSERT INTO receipt_categories VALUES(?)',[(x,) for x in categories])
                    return self.send({'ok':True})
                if self.path=='/api/admin/login-security':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    limit=d.get('max_attempts')
                    if type(limit) is not int or not 1<=limit<=100: raise Problem('Enter a whole number from 1 to 100.')
                    c.execute('UPDATE login_security SET max_attempts=? WHERE id=1',(limit,))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Login attempt limit changed to '+str(limit),''))
                    return self.send({'ok':True})
                if self.path=='/api/admin/unlock-user':
                    target=c.execute('SELECT name FROM users WHERE name=?',(str(d.get('name','')).strip(),)).fetchone()
                    if not target: raise Problem('Employee not found.',404)
                    if target['name'].casefold()==u['name'].casefold(): raise Problem('Ask another authorized employee to unlock your account.',403)
                    c.execute('DELETE FROM account_lockouts WHERE name=?',(target['name'],))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Account unlocked: '+target['name'],''))
                    return self.send({'ok':True})
                if self.path=='/api/admin/notify-update':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    c.execute('INSERT INTO update_notices(version,actor,at) VALUES(?,?,?)',(updater.current(),u['name'],dt.datetime.now().astimezone().isoformat(timespec='seconds')))
                    c.execute('DELETE FROM update_notices WHERE id NOT IN (SELECT id FROM update_notices ORDER BY id DESC LIMIT 10)')
                    return self.send({'ok':True})
                if self.path=='/api/account/landing':
                    section=d.get('section')
                    if section not in {o['id'] for o in section_options(u)}: raise Problem('Choose an available section.',403)
                    if section=='paging' and not has_permission(u,'send_pages') and not has_permission(u,'receive_pages'): raise Problem('Paging permission required.',403)
                    previous=c.execute('SELECT section,chosen_on FROM landing_preferences WHERE name=?',(u['name'],)).fetchone()
                    home=previous['section'] if previous and previous['chosen_on']==dt.date.today().isoformat() else section
                    c.execute('INSERT OR REPLACE INTO daily_home VALUES(?,?,?)',(u['name'],dt.date.today().isoformat(),section))
                    c.execute('INSERT OR REPLACE INTO landing_preferences(name,section,chosen_on) VALUES(?,?,?)',(u['name'],section,dt.date.today().isoformat()))
                    return self.send({'ok':True})
                if self.path=='/api/paging/send':
                    area=str(d.get('area','')).strip()
                    if not 1<=len(area)<=100: raise Problem('Enter an area (up to 100 characters).')
                    if c.execute('SELECT 1 FROM pages WHERE actor=? AND at>?',(u['name'],time.time()-10)).fetchone(): raise Problem('Please wait ten seconds before paging again.',429)
                    c.execute('INSERT INTO pages(at,actor,area) VALUES(?,?,?)',(time.time(),u['name'],area))
                    c.execute('DELETE FROM pages WHERE at<?',(time.time()-86400,))
                    return self.send({'ok':True})
                if self.path=='/api/logout':
                    if push_device(d.get('pushDevice')):
                        c.execute('DELETE FROM comm_push_devices WHERE device=? AND account=?',
                                  (d['pushDevice'],u['receipt_owner']))
                        c.commit()
                    if u.get('local_admin'):c.execute('DELETE FROM local_admin_sessions WHERE token_hash=?',(hashlib.sha256(SimpleCookie(self.headers.get('Cookie',''))['session'].value.encode()).hexdigest(),))
                    for k,v in list(SESSIONS.items()):
                        if v is u: del SESSIONS[k]
                    return self.send({'ok':True},cookie='session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if self.path=='/api/roles':
                    if not has_permission(u,'manage_roles'):raise Problem('Role management permission required.',403)
                    name=str(d.get('name','')).strip();grants=d.get('grants');ident=d.get('id')
                    if not 1<=len(name)<=80 or not isinstance(grants,dict) or any(k not in PERMISSIONS or not isinstance(v,bool) for k,v in grants.items()):raise Problem('Enter a role name and valid permissions.')
                    old=c.execute('SELECT body FROM permission_roles WHERE id=?',(ident,)).fetchone() if ident is not None else None
                    if ident is not None and not old:raise Problem('Role not found.',404)
                    previous=json.loads(old['body']) if old else {}
                    if not u['admin'] and any(v and not previous.get(k) and not has_permission(u,k) for k,v in grants.items()):raise Problem('You may only grant permissions you have.',403)
                    body=json.dumps({k:bool(grants.get(k,False)) for k in PERMISSIONS})
                    if old:c.execute('UPDATE permission_roles SET name=?,body=? WHERE id=?',(name,body,ident))
                    else:ident=c.execute('INSERT INTO permission_roles(name,body) VALUES(?,?)',(name,body)).lastrowid
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Saved role: '+name,''))
                    return self.send({'ok':True,'id':ident})
                if self.path=='/api/admin/user-role':
                    if not has_permission(u,'manage_users'):raise Problem('Employee management permission required.',403)
                    target=c.execute('SELECT name,admin FROM users WHERE name=?',(str(d.get('name','')),)).fetchone()
                    if not target:raise Problem('Employee not found.',404)
                    if target['admin']:raise Problem('Administrators retain all permissions; roles apply to employee accounts.',403)
                    ident=d.get('role_id')
                    if ident is None:
                        if not u['admin']:raise Problem('An administrator must restore individual permissions.',403)
                        c.execute('DELETE FROM user_roles WHERE name=?',(target['name'],))
                    else:
                        role=c.execute('SELECT name,body FROM permission_roles WHERE id=?',(ident,)).fetchone()
                        if not role:raise Problem('Role not found.',404)
                        if not u['admin'] and any(v and not has_permission(u,k) for k,v in json.loads(role['body']).items()):raise Problem('You may only assign roles within your own permissions.',403)
                        c.execute('INSERT OR REPLACE INTO user_roles VALUES(?,?)',(target['name'],ident))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Assigned role for: '+target['name'],''))
                    return self.send({'ok':True})
                if self.path=='/api/admin/permissions':
                    if not u['admin']: raise Problem('Administrator access required.',403)
                    target=c.execute('SELECT * FROM users WHERE name=?',(str(d.get('name','')),)).fetchone()
                    if not target: raise Problem('User not found.',404)
                    if c.execute('SELECT 1 FROM user_roles WHERE name=?',(target['name'],)).fetchone():raise Problem('Edit the assigned role, or select Individual permissions first.',409)
                    if 'grants' in d:
                        if not isinstance(d['grants'],dict) or any(k not in PERMISSIONS or not isinstance(v,bool) for k,v in d['grants'].items()): raise Problem('Invalid permission list.')
                        grants={k:bool(d['grants'].get(k,k=='view_schedule')) for k in PERMISSIONS}
                        c.execute('INSERT OR REPLACE INTO user_grants VALUES(?,?)',(target['name'],json.dumps(grants)))
                    create=bool(target['admin'] or d.get('can_create') is True)
                    see=bool(create and d.get('see_requests') is True)
                    c.execute('INSERT OR REPLACE INTO permissions VALUES(?,?,?)',(target['name'],int(create),int(see)))
                    return self.send({'ok':True})
                if self.path in ('/api/admin/password','/api/account/password'):
                    if self.path=='/api/admin/password' and not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    name=u['name'] if self.path=='/api/account/password' else str(d.get('name','')).strip()
                    if self.path=='/api/account/password':
                        account=c.execute('SELECT * FROM users WHERE name=?',(u['name'],)).fetchone()
                        if not hmac.compare_digest(account['hash'],password(str(d.get('current','')),account['salt'])): raise Problem('Current password or passcode is incorrect.',403)
                    new_password=str(d.get('password',''))
                    if not valid_credential(new_password): raise Problem('Use an 8–256 character password or exactly 4 digits.')
                    if new_password!=d.get('confirm'): raise Problem('The passwords do not match.')
                    target=c.execute('SELECT name FROM users WHERE name=?',(name,)).fetchone()
                    if not target: raise Problem('User not found.',404)
                    salt=secrets.token_hex(16)
                    c.execute('UPDATE users SET salt=?,hash=? WHERE name=?',(salt,password(new_password,salt),target['name']))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Password changed for: '+target['name'],''))
                    c.commit()
                    c.execute('DELETE FROM local_admin_sessions WHERE name=?',(target['name'],))
                    for token,session in list(SESSIONS.items()):
                        if session['name']==target['name']: del SESSIONS[token]
                    return self.send({'ok':True,'signed_out':u['name']==target['name']})
                elif self.path in ('/api/admin/backup-settings','/api/admin/backup-now'):
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    if self.path=='/api/admin/backup-settings':
                        folder=str(d.get('folder','')).strip()
                        enabled=d.get('enabled') is True
                        if enabled and (not folder or not Path(folder).is_absolute()): raise Problem('Enter the full OneDrive folder path on the SERVER computer.')
                        if folder:
                            candidate=Path(folder).resolve()
                            if candidate==ROOT or candidate==DATA or ROOT in candidate.parents: raise Problem('Choose a OneDrive folder outside the program folder.')
                        if folder!=backup_config().get('folder','') and c.execute('SELECT 1 FROM journal_archives').fetchone():raise Problem('Dispatch Journal exists. Keep the current backup folder until the journal has been migrated and verified.')
                        days=d.get('journal_days',backup_config().get('journal_days',30))
                        if type(days) is not int or not 1<=days<=3650:raise Problem('Journal retention must be 1–3650 days.')
                        cfg={'folder':folder,'enabled':enabled,'journal_enabled':d.get('journal_enabled',True) is True,'journal_days':days}
                        tmp=DATA/'backup-settings.tmp';tmp.write_text(json.dumps(cfg));os.replace(tmp,DATA/'backup-settings.json')
                    else:
                        try: return self.send({'ok':True,'backup':complete_backup()})
                        except Exception as e: raise Problem('Backup failed: '+str(e))
                elif self.path in ('/api/admin/backup','/api/admin/restart'):
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    if self.path=='/api/admin/backup':
                        folder=DATA/'manual-backups'; folder.mkdir(exist_ok=True)
                        target=folder/(dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.db')
                        with connect() as src, closing(sqlite3.connect(target)) as dst: src.backup(dst)
                        return self.send({'ok':True,'backup':str(target)})
                    if os.environ.get('DISPATCH_LAUNCHER_PROTOCOL')!='2': raise Problem('Install the full version 0.3.0 server package and use its launcher to enable remote restart.')
                    RESTART=76
                    self.send({'ok':True,'restarting':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                elif self.path.startswith('/api/update-'):
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    try:
                        if self.path=='/api/update-config': updater.configure(str(d.get('repository','')).strip())
                        elif self.path=='/api/update-check':
                            result=check_release_status(); result.pop('asset',None); return self.send(result)
                        elif self.path=='/api/update-install':
                            if os.environ.get('DISPATCH_LAUNCHER')!='1': raise ValueError('Restart using Start-Store-Dispatch.bat to enable installation.')
                            updater.stage(str(d.get('version','')))
                            RESTART=True
                            self.send({'ok':True,'restarting':True})
                            threading.Thread(target=self.server.shutdown,daemon=True).start()
                            return
                        else: raise Problem('Not found',404)
                    except ValueError as e: raise Problem(str(e))
                elif self.path=='/api/user':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    self.add_user(c,str(d.get('name','')).strip(),str(d.get('password','')),False)
                elif self.path=='/api/admin/clock-pin':
                    if not has_permission(u,'reset_passwords'): raise Problem('Password reset permission required.',403)
                    name,pin=d.get('name'),d.get('pin')
                    if not isinstance(name,str) or not isinstance(pin,str) or (pin and not re.fullmatch(r'[0-9]{6}',pin)):
                        raise Problem('Enter a six-digit Time Clock PIN.')
                    target=c.execute('SELECT p.profile_id,u.admin FROM users u JOIN receipt_profiles p ON p.name=u.name WHERE u.name=?',
                                     (name,)).fetchone()
                    if not target: raise Problem('User not found.',404)
                    if target['admin'] and not u['admin']: raise Problem('Only an administrator can manage this PIN.',403)
                    account=target['profile_id']
                    if pin:
                        digest=clock_pin_hash(c,pin)
                        if c.execute('SELECT 1 FROM work_clock_pins WHERE pin_hash=? AND account!=?',(digest,account)).fetchone():
                            raise Problem('That PIN is in use. Choose another PIN.',409)
                        c.execute('INSERT INTO work_clock_pins VALUES(?,?) ON CONFLICT(account) DO UPDATE SET pin_hash=excluded.pin_hash',
                                  (account,digest))
                    else:
                        c.execute('DELETE FROM work_clock_pins WHERE account=?',(account,))
                    c.commit()
                    for token,session in list(CLOCK_SESSIONS.items()):
                        if session[0]==account: del CLOCK_SESSIONS[token]
                elif self.path=='/api/admin/user-identity':
                    name=d.get('name')
                    if not isinstance(name,str): raise Problem('Choose a user.')
                    target=identity_target(c,u,name)
                    fields=[d.get(key) for key in ('username','first','middle','last')]
                    if any(not isinstance(value,str) for value in fields): raise Problem('Enter valid profile names.')
                    username,first,middle,last=[value.strip() for value in fields]
                    if not username or any(len(value)>80 or (value and not value.isprintable()) for value in (username,first,middle,last)):
                        raise Problem('A login username is required. Names can contain up to 80 characters.')
                    check_username_available(c,username,target['profile_id'])
                    c.execute("""INSERT INTO user_identity VALUES(?,?,?,?,?) ON CONFLICT(account) DO UPDATE SET
                        username=excluded.username,first=excluded.first,middle=excluded.middle,last=excluded.last""",
                              (target['profile_id'],username,first,middle,last))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),
                              u['name'],'Updated login and legal name fields for '+target['name'],''))
                elif self.path=='/api/admin/rename-user':
                    if not has_permission(u,'rename_users'):
                        raise Problem('Edit user names permission required.',403)
                    previous,new_name=d.get('name'),d.get('new_name')
                    if not isinstance(previous,str) or not isinstance(new_name,str):
                        raise Problem('Enter a valid user name.')
                    new_name=new_name.strip()
                    if not 1<=len(new_name)<=80 or not new_name.isprintable() or new_name.casefold()=='guest':
                        raise Problem('Enter a user name of 1–80 characters. Guest is reserved.')
                    target=c.execute('SELECT name,admin FROM users WHERE name=?',(previous,)).fetchone()
                    if not target: raise Problem('User not found.',404)
                    if target['admin'] and not u['admin']:
                        raise Problem('Only an administrator can rename an administrator account.',403)
                    old_name=target['name']
                    if old_name!=new_name:
                        check_username_available(c,new_name,work_assignment_target(c,old_name))
                        # Move the account's name keys together. Its profile ID and credentials stay the same.
                        for table in ('users','permissions','daily_home','landing_preferences','account_lockouts',
                                      'local_admin_sessions','user_roles','receipt_profiles','appearance_preferences','user_grants'):
                            c.execute(f'UPDATE {table} SET name=? WHERE name=?',(new_name,old_name))
                        for row in c.execute('SELECT id,body FROM jobs').fetchall():
                            job=json.loads(row['body'])
                            changed=False
                            if job.get('requestedBy')==old_name:
                                job['requestedBy']=new_name
                                changed=True
                            names=job.get('staffNames')
                            if isinstance(names,list) and old_name in names:
                                job['staffNames']=[new_name if name==old_name else name for name in names]
                                job['staff']=', '.join(job['staffNames'])
                                changed=True
                            elif not names and job.get('staff')==old_name:
                                job['staff']=new_name
                                changed=True
                            if changed:
                                c.execute('UPDATE jobs SET body=?,revision=revision+1 WHERE id=?',(json.dumps(job),row['id']))
                        actor=u['name']
                        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),actor,
                                  f'Renamed user: {old_name} → {new_name}',''))
                        c.commit()
                        for session in SESSIONS.values():
                            if session['name']==old_name: session['name']=new_name
                    return self.send({'name':new_name,'signed_in_name':u['name']})
                elif self.path=='/api/admin/remove-user':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    target=c.execute('SELECT name,admin FROM users WHERE name=?',(str(d.get('name','')).strip(),)).fetchone()
                    if not target: raise Problem('Employee not found.',404)
                    if target['admin']: raise Problem('Administrator accounts cannot be removed here.',403)
                    c.execute('DELETE FROM users WHERE name=?',(target['name'],))
                    c.execute('DELETE FROM comm_push_devices WHERE account=(SELECT profile_id FROM receipt_profiles WHERE name=?)',(target['name'],))
                    c.execute('DELETE FROM work_assignments WHERE account=(SELECT profile_id FROM receipt_profiles WHERE name=?)',(target['name'],))
                    c.execute('DELETE FROM work_clock_pins WHERE account=(SELECT profile_id FROM receipt_profiles WHERE name=?)',(target['name'],))
                    c.execute('DELETE FROM user_identity WHERE account=(SELECT profile_id FROM receipt_profiles WHERE name=?)',(target['name'],))
                    c.execute('DELETE FROM user_profile_photos WHERE account=(SELECT profile_id FROM receipt_profiles WHERE name=?)',(target['name'],))
                    c.execute('DELETE FROM receipt_profiles WHERE name=?',(target['name'],))
                    c.execute('DELETE FROM user_roles WHERE name=?',(target['name'],))
                    c.execute('DELETE FROM account_lockouts WHERE name=?',(target['name'],))
                    c.execute('DELETE FROM local_admin_sessions WHERE name=?',(target['name'],))
                    for token in list(SESSIONS):
                        if SESSIONS[token]['name'].casefold()==target['name'].casefold(): del SESSIONS[token]
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Removed employee: '+target['name'],''))
                elif self.path=='/api/vehicle':
                    if not route_allowed(u,self.path): raise Problem('Administrator access required.',403)
                    name=str(d.get('name','')).strip()
                    if not 1<=len(name)<=80: raise Problem('Enter a vehicle name.')
                    c.execute('INSERT INTO vehicles VALUES(?)',(name,))
                elif self.path=='/api/status':
                    jid=str(d.get('id',''))
                    old=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
                    if not old or d.get('revision')!=old['revision']: raise Problem('Someone changed this appointment. Close this popup, refresh, and try again.',409)
                    status=d.get('status')
                    j=json.loads(old['body'])
                    if not u['can_create']:
                        if status=='Canceled' and not has_permission(u,'cancel_appointments'): raise Problem('Cancellation permission required.',403)
                        if status not in ('Requested','Canceled'): raise Problem('Request-only users may only request or cancel appointments.',403)
                        if status=='Requested' and (not j.get('request') or j.get('requestedBy')!=u['name']): raise Problem('Only your pending requests can have Requested status.',403)
                    elif not has_permission(u,'cancel_appointments' if status=='Canceled' else 'update_status'): raise Problem('Status permission required.',403)
                    elif status not in ('Scheduled','In Route / In Progress','Completed','Canceled'): raise Problem('Choose a valid status.')
                    if status not in ('Completed','Canceled','Requested'):

                        for r in c.execute('SELECT * FROM jobs WHERE id!=?',(jid,)):
                            other=json.loads(r['body'])
                            if not other.get('request') and other['vehicle']==j['vehicle'] and other['status'] not in ('Completed','Canceled') and j['start']<other['end'] and j['end']>other['start']:
                                raise Problem('This vehicle is already booked during that time. Edit the appointment time or vehicle first.',409)
                    previous=j['status'];j['status']=status
                    j['statusUpdatedBy']=u['name'];j['statusUpdatedAt']=dt.datetime.now().astimezone().isoformat(timespec='seconds')
                    c.execute('UPDATE jobs SET revision=?,body=? WHERE id=?',(old['revision']+1,json.dumps(j),jid))
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],'Status: '+previous+' → '+status+' · '+j['customer'],jid))
                elif self.path in ('/api/save','/api/delete'):
                    if not d.get('id') and not has_permission(u,'create_appointments') and not has_permission(u,'submit_requests'): raise Problem('Request permission required.',403)
                    if d.get('id') and not has_permission(u,'delete_appointments' if self.path=='/api/delete' else 'edit_appointments'): raise Problem('Edit permission required.',403)
                    jid=str(d.get('id') or secrets.token_hex(12))
                    old=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
                    if d.get('id') and (not old or d.get('revision')!=old['revision']): raise Problem('Someone changed this job. Close this form, refresh, and try again.',409)
                    if old and json.loads(old['body']).get('request') and self.path=='/api/save' and not has_permission(u,'review_requests'): raise Problem('Request approval permission required.',403)
                    if self.path=='/api/delete':
                        if not old: raise Problem('Job not found.',404)
                        c.execute('DELETE FROM jobs WHERE id=?',(jid,)); action='Removed: '+json.loads(old['body'])['customer']
                    else:
                        fields=['type','customer','phone','address','items','vehicle','start','end','staff','notes','status']
                        j={k:str(d.get(k,'Scheduled' if k=='status' and not old else '')).strip() for k in fields}
                        if any(k in d for k in ('street','city','state','zip')):
                            for k in ('street','city','state','zip'): j[k]=str(d.get(k,'')).strip()
                            if u['can_create'] and any(not j[k] for k in ('street','city','state','zip')): raise Problem('Enter street address, city, state and ZIP code.')
                            j['address']='\n'.join(part for part in [j['street'],', '.join(part for part in [j['city'],' '.join(part for part in [j['state'],j['zip']] if part)] if part)] if part) if any(j[k] for k in ('street','city','zip')) else ''
                        if any(len(v)>5000 for v in j.values()): raise Problem('A field is too long.')
                        if any(not j[k] for k in (('customer','phone','address','items','vehicle','start','end') if u['can_create'] else ('customer',))): raise Problem('Complete the required fields.')
                        if 'staffNames' in d:
                            names=d['staffNames']
                            if not isinstance(names,list) or len(names)>100 or any(not isinstance(n,str) or len(n)>5000 for n in names): raise Problem('Choose valid employees.')
                            previous=json.loads(old['body']) if old else {}
                            allowed={r['name'] for r in c.execute('SELECT name FROM users')}
                            allowed.update(previous.get('staffNames', [previous['staff']] if previous.get('staff') else []))
                            if any(n not in allowed for n in names): raise Problem('An employee was removed. Reopen the appointment and select current employees.')
                            j['staffNames']=list(dict.fromkeys(names));j['staff']=', '.join(j['staffNames'])
                        if j['type'] not in ('Pickup','Delivery') or j['status'] not in ('Requested','Scheduled','Confirmed','In Route / In Progress','Completed','Canceled'): raise Problem('Invalid type or status.')
                        if u['can_create']:
                            try:
                                start=dt.datetime.strptime(j['start'],'%Y-%m-%dT%H:%M'); end=dt.datetime.strptime(j['end'],'%Y-%m-%dT%H:%M')
                            except ValueError: raise Problem('Choose a valid date and time.')
                            if end<=start: raise Problem('End time must be after start time.')
                            if not c.execute('SELECT 1 FROM vehicles WHERE name=?',(j['vehicle'],)).fetchone(): raise Problem('Choose an existing vehicle.')
                        else:
                            if j['start']:
                                try: dt.datetime.strptime(j['start'],'%Y-%m-%dT%H:%M')
                                except ValueError: raise Problem('Choose a valid requested date and time.')
                            j['end']='';j['vehicle']='';j['staff']='';j['staffNames']=[]
                        pending=not u['can_create'] and not old
                        if pending:
                            if j['status'] not in ('Requested','Canceled'): raise Problem('Request-only users may only request or cancel appointments.',403)
                            j['request']=True;j['requestedBy']=u['name']
                        if not pending and j['status'] not in ('Completed','Canceled'):
                            for r in c.execute('SELECT * FROM jobs WHERE id!=?',(jid,)):
                                other=json.loads(r['body'])
                                if not other.get('request') and other['vehicle']==j['vehicle'] and other['status'] not in ('Completed','Canceled') and j['start']<other['end'] and j['end']>other['start']:
                                    raise Problem('This vehicle is already booked during that time. Choose another time or vehicle.',409)
                        previous_job=json.loads(old['body']) if old else {}
                        if old and previous_job.get('status')!=j['status'] and not has_permission(u,'cancel_appointments' if j['status']=='Canceled' else 'update_status'): raise Problem('Status permission required.',403)
                        if not old or previous_job.get('status')!=j['status']:
                            j['statusUpdatedBy']=u['name'];j['statusUpdatedAt']=dt.datetime.now().astimezone().isoformat(timespec='seconds')
                        else:
                            for key in ('statusUpdatedBy','statusUpdatedAt'):
                                if key in previous_job: j[key]=previous_job[key]
                        if not old:
                            images=d.get('photos',[])
                            if not isinstance(images,list) or len(images)>3: raise Problem('Attach up to 3 photos.')
                            for i,encoded in enumerate(images):
                                try: raw=base64.b64decode(encoded,validate=True)
                                except Exception: raise Problem('Invalid photo.')
                                if len(raw)>1000000 or not raw.startswith(b'\xff\xd8\xff'): raise Problem('Photos must be JPEG and under 1 MB each.')
                                c.execute('INSERT INTO photos VALUES(?,?,?)',(jid,i,raw))
                            j['photoCount']=len(images)
                        else: j['photoCount']=previous_job.get('photoCount',0)
                        rev=old['revision']+1 if old else 1
                        c.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?)',(jid,rev,json.dumps(j)))
                        action=('Updated: ' if old else 'Created: ')+j['customer']
                    c.execute('INSERT INTO audit VALUES(?,?,?,?)',(dt.datetime.now().isoformat(timespec='seconds'),u['name'],action,jid))
                else: raise Problem('Not found',404)
            self.send({'ok':True})
        except Problem as e: self.send({'error':e.message,**e.details},e.status)
        except sqlite3.IntegrityError: self.send({'error':'That name already exists.'},409)
        except (ValueError,TypeError): self.send({'error':'Invalid request.'},400)
        except Exception as e:
            print('Request failed:',e); self.send({'error':'Unable to save. Check the server and try again.'},500)
    def add_user(self,c,name,p,admin):
        if not 1<=len(name)<=80 or not valid_credential(p): raise Problem('Enter a name and a password of 8–256 characters.')
        check_username_available(c,name)
        salt=secrets.token_hex(16)
        c.execute('INSERT INTO users VALUES(?,?,?,?)',(name,salt,password(p,salt),int(admin)))
        c.execute('INSERT INTO receipt_profiles VALUES(?,?)',(name,secrets.token_hex(16)))

if __name__=='__main__':
    if os.name=='nt':
        import ctypes
        kernel=ctypes.windll.kernel32
        kernel.CreateMutexW.restype=ctypes.c_void_p
        instance_mutex=kernel.CreateMutexW(None,False,'ThriftMartDispatchServer')
        if kernel.GetLastError()==183: raise SystemExit('MGC YFC Operations Server is already running.')
    data_lock=hold_data_lock()
    init(); threading.Thread(target=background,daemon=True).start()
    if WebPush is not None:
        threading.Thread(target=push_worker,daemon=True).start()
    threading.Thread(target=monitor_release_status,daemon=True).start()
    port=int(os.environ.get('DISPATCH_PORT','8080'))
    print('MGC YFC Operations Server '+updater.current())
    print(f'On this computer: http://localhost:{port}')
    for address in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
        if not address.startswith('127.'): print(f'On store Wi-Fi: http://{address}:{port}')
    print('Managed by the truck tray icon. Minimize to tray; use Exit server to stop.' if os.environ.get('DISPATCH_CONTROL_TOKEN') else 'Keep this window open. Press Ctrl+C to stop.')
    http=ThreadingHTTPServer(('0.0.0.0',port),Handler)
    http.serve_forever()
    http.server_close()
    if RESTART: raise SystemExit(76 if RESTART==76 else 75)
