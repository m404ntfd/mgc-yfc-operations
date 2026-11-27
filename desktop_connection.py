"""Read-only startup connection checks; never opens a business database."""
import json
import queue
import ssl
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

USER_AGENT = 'CoastYouth-Retail-Desktop/0.57.0'
PUBLIC_SERVER = 'https://operations.coastyfc.com'


def server_url(value):
    if not isinstance(value, str):
        raise ValueError('Enter a server address.')
    value = value.strip()
    if '://' not in value:
        host = value.split('/')[0].split(':')[0].lower()
        value = ('https://' if host == 'operations.coastyfc.com' else 'http://') + value
    parts = urlsplit(value)
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username or parts.password or parts.path not in ('', '/')
            or parts.query or parts.fragment or any(c.isspace() for c in value)):
        raise ValueError('Enter only the server address, such as https://operations.coastyfc.com or http://192.168.1.20:8080.')
    try:
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError()
    except ValueError:
        raise ValueError('Enter a valid server port.') from None
    return value.rstrip('/')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe_server(address, app='office', *, timeout_seconds=10):
    """No cookies, credentials or writes. Never follows a redirect to another server."""
    address = server_url(address)
    deadline = time.monotonic() + max(1,min(120,float(timeout_seconds)))
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise TimeoutError('Connection deadline reached')
        return value
    opener = build_opener(ProxyHandler({}), NoRedirect())

    def read(path, limit):
        request = Request(address + path, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
        with opener.open(request, timeout=remaining()) as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('The address returned an unexpected response. Check the server address.')
        return raw

    try:
        try:
            session = json.loads(read('/api/session', 128000))
        except (json.JSONDecodeError, UnicodeError):
            raise ValueError('This address did not return the CoastYouth server. Check the address or contact your administrator.') from None
        if not isinstance(session, dict) or session.get('application') != 'thrift-mart-dispatch':
            raise ValueError('This is not a compatible CoastYouth server. Check the server address.')
        if app == 'pos' and b'kioskSetupDialog' not in read('/pos.js', 2000000):
            raise ValueError('The server needs a DESK-compatible update. Ask an administrator to update the server, then retry.')
        remaining()
        return address
    except HTTPError as exc:
        exc.close()
        if 300 <= exc.code < 400:
            raise ValueError('The server redirected the connection. Enter its final HTTPS address; automatic redirects are not allowed.') from None
        if exc.code in (401, 403):
            raise ValueError('The server refused this connection. Ask an administrator to check remote access permissions, then retry.') from None
        raise ValueError('The server is unavailable (HTTP ' + str(exc.code) + '). Check the address and try again.') from None
    except (ssl.SSLError, URLError, OSError) as exc:
        reason = getattr(exc, 'reason', exc)
        if isinstance(reason, ssl.SSLError):
            raise ValueError('The secure connection could not be verified. Check this computer’s date and the server certificate with your administrator.') from None
        raise ValueError('The server did not respond. Check that the server is running and your internet or VPN connection is connected.') from None


def reconnect_desktop(bridge, app, address, exit_code=''):
    """Verify a new endpoint before changing only this app's saved server address."""
    import os
    import secrets
    from pathlib import Path
    from pos_kiosk import KioskStore
    try:
        if app not in ('pos','office','ops') or not bridge._trusted():
            raise ValueError('Open the configured application before changing its server.')
        if bridge._window.evaluate_js('window.desktopConnectionCanChange ? window.desktopConnectionCanChange() : false') is not True:
            raise ValueError('Finish or save current work before changing the server connection.')
        candidate=server_url(address)
        path=bridge._store.path if app=='pos' else Path(os.environ.get('APPDATA',str(Path.home())))/('CoastYouthRetailOffice' if app=='office' else 'CoastYouthRetailStoreOps')/'settings.json'
        store=bridge._store if app=='pos' else KioskStore(path)
        if app=='pos' and candidate!=bridge._address and store.configured and not store.verify(exit_code):
            raise ValueError('Enter the current admin exit passcode to change this DESK server.')
        from connection_preferences import load
        duration=load(app)['timeout_seconds'];deadline=time.monotonic()+duration
        # DNS and some platform TLS calls do not always honor socket timeouts.
        # The worker is read-only; only this bounded caller may save/navigate.
        result=queue.Queue(maxsize=1)
        def check():
            try:probe_server(candidate,app,timeout_seconds=duration);result.put(None)
            except Exception as error:result.put(error)
        threading.Thread(target=check,daemon=True).start()
        try:error=result.get(timeout=duration)
        except queue.Empty:raise ValueError('The connection check timed out. Retry the connection.') from None
        if error:raise error
        # Recheck after the network operation so intervening edits cannot be lost.
        if not bridge._trusted():
            raise ValueError('The application page changed. Reopen connection settings and try again.')
        if bridge._window.evaluate_js('window.desktopConnectionCanChange ? window.desktopConnectionCanChange() : false') is not True:
            raise ValueError('New work is in progress. Save it before reconnecting.')
        if time.monotonic()>=deadline:
            raise ValueError('The connection check timed out. Retry the connection.')
        previous_data=dict(store.data)
        if app!='ops':store.data['server']=candidate
        try:
            if app=='ops':
                from store_ops_desktop import save_connection
                save_connection(path.parent,candidate)
            else:store.save()
        except Exception:
            store.data=previous_data
            raise
        bridge._store=store;bridge._address=candidate
        if app=='pos':bridge._nonce=secrets.token_hex(32)
        elif app=='office':bridge._signed_in=False;bridge._kiosk=None
        if hasattr(bridge,'_updates'):
            from pos_updater import PosUpdater
            previous=bridge._updates
            bridge._updates=PosUpdater(bridge,app=app,current=previous.version)
        try:bridge._window.load_url(candidate+('/pos?kiosk=1&setup=1' if app=='pos' else '/office?setup=1' if app=='office' else '/?setup=1'))
        except Exception:
            return {'error':'The server address was saved. Close and reopen the application to sign in and register this PC.','saved':True}
        return {'ok':True}
    except Exception as exc:
        return {'error':str(exc)}


def connect_before_open(app, address, save, *, configure=False, authorize=None, on_register=None):
    from connection_dialog import connect
    return connect(app,address,save,probe_server,server_url,configure=configure,
                   authorize=authorize,on_register=on_register)
