"""DESK native connection-only bridge. A web page never supplies a network target."""
import json
import platform
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPSHandler, ProxyHandler, build_opener

from clover_connection import CloverError, check_network, _NoRedirect, public_context


def _redeem(bridge, token):
    request = Request(bridge._address + '/api/pos/clover-test-redeem',
        data=json.dumps({'token': token, 'device': bridge._store.data['device'], 'nonce': bridge._nonce}).encode(),
        headers={'Content-Type': 'application/json', 'X-Dispatch': '1', 'User-Agent': 'CoastYouth-DESK/Clover-pilot'})
    try:
        with build_opener(ProxyHandler({}), _NoRedirect(), HTTPSHandler(context=public_context())).open(request, timeout=8) as response:
            raw = response.read(16385)
            if len(raw) > 16384:
                raise CloverError('The server returned an unexpected test approval.')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise CloverError('The server returned an unexpected test approval.')
            return result
    except HTTPError as exc:
        exc.close()
        raise CloverError('The server refused this test approval. Sign in as an administrator and start a new test.') from None
    except (URLError, OSError, ValueError):
        raise CloverError('The server could not verify this test approval. Check its connection and try again.') from None


def check_from_desk(bridge, token):
    try:
        with bridge._lock:
            if (not bridge._trusted() or urlsplit(bridge._window.get_current_url()).path not in ('/pos', '/pos/')
                    or not bridge._store.configured):
                raise CloverError('Open the registered DESK application before testing Clover.')
            if not isinstance(token, str) or not re.fullmatch('[0-9a-f]{64}', token):
                raise CloverError('An administrator must approve this connection check.')
            approval = _redeem(bridge, token)
            if (approval.get('purpose') != 'clover-network-check-only'
                    or approval.get('device') != bridge._store.data['device'] or approval.get('nonce') != bridge._nonce):
                raise CloverError('This Clover approval does not match this registered computer.')
            if not bridge._trusted() or urlsplit(bridge._window.get_current_url()).path not in ('/pos', '/pos/'):
                raise CloverError('The application page changed. Reopen Clover setup.')
            result = check_network(approval['address'], approval['terminal_id'], approval['serial'])
            return dict(result, source_computer=platform.node(), terminal_name=approval['terminal_name'],
                        store_name=approval['store_name'], payments_attempted=0)
    except CloverError as exc:
        return {'error': str(exc), 'payments_attempted': 0}
    except Exception:
        return {'error': 'The Clover connection check could not be completed. Reopen setup and try again.', 'payments_attempted': 0}
