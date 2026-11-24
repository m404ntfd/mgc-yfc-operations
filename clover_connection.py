"""Connection-only Clover pilot. No payment/order/refund API and no database access.

This is an unshipped adapter, not yet exposed by DESK or OFFICE. OAuth sessions
and credentials live only in memory. A future admin-only HTTPS callback must
supply its authenticated session identity; see CLOVER-CONNECTION-PILOT.md.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import ipaddress
import json
import math
import re
import secrets
import ssl
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import (HTTPRedirectHandler, HTTPSHandler, ProxyHandler,
                            Request, build_opener)

import certifi

USER_AGENT = 'CoastYouth-Retail-DESK/connection-pilot'
CA_URL = 'https://www.clover.com/v2/env_device_ca_certificate'
PING_PATH = '/connect/v1/device/ping'
ORIGINS = {
    'sandbox': ('https://sandbox.dev.clover.com', 'https://apisandbox.dev.clover.com'),
    'production': ('https://www.clover.com', 'https://api.clover.com'),
}
CIPHERS = (
    'ECDHE-ECDSA-AES128-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:'
    'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:'
    'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:'
    'AES128-GCM-SHA256:AES256-GCM-SHA384'
)
LAN_RANGES = tuple(ipaddress.ip_network(n) for n in
                   ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


class CloverError(ValueError):
    """Safe to display: never includes remote response bodies or credentials."""


def _identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise CloverError('Enter a valid ' + label + '.')
    return value


def device_address(value):
    """Only explicit RFC1918 IPv4 targets; no DNS rebinding, proxy, or redirects."""
    try:
        address = ipaddress.IPv4Address(value)
    except (ValueError, TypeError):
        raise CloverError('Enter the Clover local IPv4 address shown in REST Pay Display.') from None
    if not any(address in network for network in LAN_RANGES):
        raise CloverError('The Clover test requires a private local-network IPv4 address.')
    return str(address)


def _callback_uri(value):
    try:
        parts = urlsplit(value)
        if (parts.scheme != 'https' or not parts.hostname or parts.port not in (None, 443)
                or parts.username or parts.password or parts.query or parts.fragment
                or not parts.path.startswith('/') or parts.path.startswith('//')
                or any(ord(c) < 33 or ord(c) > 126 for c in value)
                or '\\' in value or '%' in value
                or any(p in ('.', '..') for p in parts.path.split('/'))
                or parts.hostname == 'localhost' or '.' not in parts.hostname):
            raise ValueError()
        try:
            ipaddress.ip_address(parts.hostname)
        except ValueError:
            pass
        else:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise CloverError('Use the registered public HTTPS callback address without query parameters.') from None
    return value


@dataclass(frozen=True)
class Binding:
    environment: str
    client_id: str
    merchant_id: str
    store_id: str
    terminal_id: str
    device_serial: str

    def __post_init__(self):
        if self.environment not in ORIGINS:
            raise CloverError('Choose sandbox or production explicitly.')
        for attr in ('client_id', 'merchant_id', 'store_id', 'terminal_id', 'device_serial'):
            _identifier(getattr(self, attr), attr.replace('_', ' '))


@dataclass(frozen=True)
class Grant:
    binding: Binding
    access_token: str = field(repr=False)
    access_expires: float
    refresh_token: str = field(repr=False)
    refresh_expires: float

    def access(self, binding, now):
        if binding != self.binding:
            raise CloverError('The store, terminal, merchant, device, or environment changed. Authorize again.')
        if now + 30 >= self.access_expires:
            raise CloverError('Clover authorization expired. Authorize again before testing.')
        return self.access_token


def _secret(value):
    if not isinstance(value, str) or not value or len(value) > 16384 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise CloverError('Clover returned invalid authorization details. Authorize again.')
    return value


def _grant(payload, binding, now):
    try:
        access_exp = payload['access_token_expiration']
        refresh_exp = payload['refresh_token_expiration']
        if any(isinstance(n, bool) or not isinstance(n, (int, float))
               or not math.isfinite(n) or n <= now + 30 for n in (access_exp, refresh_exp)):
            raise ValueError()
        return Grant(binding, _secret(payload['access_token']), access_exp,
                     _secret(payload['refresh_token']), refresh_exp)
    except (KeyError, TypeError, ValueError):
        raise CloverError('Clover returned invalid or expired authorization details. Authorize again.') from None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def public_context():
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def device_context(certificate):
    # Device trust is scoped to this client. Do not change Windows trust settings.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers(CIPHERS)
    try:
        pem = certificate.decode('ascii') if b'-----BEGIN CERTIFICATE-----' in certificate else ssl.DER_cert_to_PEM_cert(certificate)
        context.load_verify_locations(cadata=pem)
    except (ValueError, UnicodeError, ssl.SSLError):
        raise CloverError('The Clover certificate download was invalid. Try again later.') from None
    return context


def _read(request, context, limit=262144):
    """Bounded HTTPS transport. Never return remote error bodies to the caller."""
    opener = build_opener(ProxyHandler({}), _NoRedirect(), HTTPSHandler(context=context))
    try:
        try:
            response = opener.open(request, timeout=8)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            return status, b''
        with response:
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise CloverError('Clover returned an unexpectedly large response.')
            return response.status, raw
    except (URLError, OSError) as exc:
        reason = getattr(exc, 'reason', exc)
        if isinstance(reason, ssl.SSLError):
            raise CloverError('The Clover secure connection could not be verified. Check the device address, date, and certificates.') from None
        raise CloverError('Clover did not respond. Check REST Pay Display and the network connection.') from None


def _json(raw):
    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (ValueError, UnicodeError):
        raise CloverError('Clover returned an unexpected response. The connection is not confirmed.') from None


class CloverTransport:
    """Only OAuth and merchant/device read operations are permitted by this adapter."""

    def api(self, binding, operation, *, body=None, token=None):
        root = ORIGINS[binding.environment][1]
        merchant = '/v3/merchants/' + binding.merchant_id
        operations = {
            'token': ('POST', '/oauth/v2/token'),
            'merchant': ('GET', merchant),
            'devices': ('GET', merchant + '/devices?' + urlencode({'filter': 'serial=' + binding.device_serial})),
        }
        if operation not in operations:
            raise CloverError('This pilot allows authorization and connection checks only.')
        method, path = operations[operation]
        headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
        if operation == 'token':
            if (not isinstance(body, dict) or set(body) != {'client_id', 'code', 'code_verifier'}
                    or body['client_id'] != binding.client_id or token is not None):
                raise CloverError('Invalid Clover authorization request.')
            for value in body.values():
                _secret(value)
            headers['Content-Type'] = 'application/json'
            data = json.dumps(body).encode('utf-8')
        else:
            if body is not None:
                raise CloverError('Connection checks cannot change Clover merchant records.')
            headers['Authorization'] = 'Bearer ' + _secret(token)
            data = None
        status, raw = _read(Request(root + path, data=data, headers=headers, method=method), public_context())
        if status in (401, 403):
            raise CloverError('Clover authorization was refused. Check app approval, Merchant Read permission, and merchant authorization.')
        if status != 200:
            raise CloverError('Clover could not complete the authorization or merchant check (HTTP ' + str(status) + ').')
        return _json(raw)

    def ping(self, address, terminal_id, serial, *, token=None):
        address = device_address(address)
        headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json',
                   'X-POS-Id': _identifier(terminal_id, 'terminal identifier'),
                   'X-Clover-Device-Id': _identifier(serial, 'Clover serial number')}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + _secret(token)
        status, certificate = _read(Request(CA_URL, headers={'User-Agent': USER_AGENT}, method='GET'), public_context(), 65536)
        if status != 200:
            raise CloverError('The official Clover device certificate could not be downloaded.')
        status, raw = _read(Request('https://' + address + ':12346' + PING_PATH,
                                    headers=headers, method='GET'), device_context(certificate))
        return status, _json(raw) if status == 200 else {}


@dataclass(repr=False)
class AuthorizationAttempt:
    binding: Binding
    callback: str
    _session_digest: str
    _state: str
    _verifier: str
    _created: float
    _used: bool = False
    _lock: object = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def begin(cls, binding, callback, session_id, *, now=None):
        _secret(session_id)
        if len(session_id) < 32:
            raise CloverError('Start Clover authorization from a signed-in administrator session.')
        return cls(binding, _callback_uri(callback), hashlib.sha256(session_id.encode()).hexdigest(),
                   secrets.token_urlsafe(32), secrets.token_urlsafe(48), time.time() if now is None else now)

    def authorization_url(self):
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self._verifier.encode()).digest()).rstrip(b'=').decode()
        return ORIGINS[self.binding.environment][0] + '/oauth/v2/authorize?' + urlencode({
            'client_id': self.binding.client_id, 'redirect_uri': self.callback,
            'response_type': 'code', 'state': self._state,
            'code_challenge': challenge, 'code_challenge_method': 'S256',
        })

    def complete(self, callback_url, session_id, binding, transport=None, *, now=None):
        now = time.time() if now is None else now
        _secret(session_id)
        with self._lock:
            if self._used or not 0 <= now - self._created <= 600:
                raise CloverError('This Clover authorization attempt expired or was already used. Start again.')
            if binding != self.binding or not secrets.compare_digest(
                    self._session_digest, hashlib.sha256(session_id.encode()).hexdigest()):
                raise CloverError('Return to the administrator session that started Clover authorization.')
            try:
                parts = urlsplit(callback_url)
                received_base = parts._replace(query='', fragment='').geturl()
                query = parse_qs(parts.query, keep_blank_values=True, max_num_fields=12)
                if (received_base != self.callback or parts.fragment or len(callback_url) > 20000
                        or any(len(v) != 1 for v in query.values())
                        or not secrets.compare_digest(query.get('state', [''])[0], self._state)):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise CloverError('Clover authorization did not match this setup session. Start again.') from None
            self._used = True  # A returned code is single-use, including failed/ambiguous exchanges.
            verifier, self._verifier = self._verifier, ''
            if 'error' in query:
                raise CloverError('Clover authorization was canceled or refused. No connection was enabled.')
            if (query.get('client_id') != [binding.client_id]
                    or query.get('merchant_id') != [binding.merchant_id] or not query.get('code')):
                raise CloverError('Clover returned a different app or merchant. No connection was enabled.')
            code = _secret(query['code'][0])
            payload = (transport or CloverTransport()).api(binding, 'token', body={
                'client_id': binding.client_id, 'code': code, 'code_verifier': verifier})
            return _grant(payload, binding, now)


def check_network(address, terminal_id, serial, *, transport=None):
    """Unauthenticated preflight; reachable is never presented as authorized."""
    status, payload = (transport or CloverTransport()).ping(address, terminal_id, serial)
    if status == 401:
        return {'status': 'authorization_required', 'reachable': True, 'authorized': False,
                'message': 'Clover is reachable securely. Merchant authorization is still required.'}
    if status == 503:
        return {'status': 'busy', 'reachable': True, 'authorized': False,
                'message': 'Clover is busy. Finish its current task, then test again.'}
    if status == 200:
        return {'status': 'authorization_required', 'reachable': True, 'authorized': False,
                'message': 'Clover responded. Run the authorized merchant and device check before enabling the connection.'}
    raise CloverError('Clover did not confirm the network check (HTTP ' + str(status) + ').')


def check_authorized_device(grant, binding, address, *, transport=None, now=None):
    """Verify merchant ownership, then GET ping. Never starts a transaction."""
    now = time.time() if now is None else now
    device_address(address)
    if binding.environment != 'production':
        raise CloverError('Sandbox authorization cannot be used on the live Clover device.')
    token = grant.access(binding, now)
    transport = transport or CloverTransport()
    merchant = transport.api(binding, 'merchant', token=token)
    if merchant.get('id') != binding.merchant_id:
        raise CloverError('Clover merchant did not match the selected store. No device connection was authorized.')
    devices = transport.api(binding, 'devices', token=token)
    rows = devices.get('elements')
    if not isinstance(rows, list):
        raise CloverError('Clover could not confirm device ownership.')
    matches = [row for row in rows if isinstance(row, dict) and row.get('serial') == binding.device_serial]
    if len(matches) != 1:
        raise CloverError('This Clover serial number was not uniquely confirmed under the selected merchant.')
    owner = matches[0].get('merchant')
    if owner is not None and (not isinstance(owner, dict) or owner.get('id') != binding.merchant_id):
        raise CloverError('This Clover belongs to a different merchant. No device connection was authorized.')
    status, payload = transport.ping(address, binding.terminal_id, binding.device_serial, token=token)
    if status == 401:
        raise CloverError('The device refused Clover authorization. Authorize again and check REST Pay Display.')
    if status == 503:
        raise CloverError('The Clover is busy. No test transaction was created; try the connection check later.')
    if status != 200 or payload.get('connected') is not True:
        raise CloverError('Clover did not confirm the authorized connection. No test transaction was created.')
    return {'status': 'connected', 'reachable': True, 'authorized': True,
            'terminal_id': binding.terminal_id, 'store_id': binding.store_id,
            'merchant_id': binding.merchant_id, 'serial_last_four': binding.device_serial[-4:],
            'payments_attempted': 0, 'message': 'Merchant and device connection confirmed. No card was charged.'}


def main():
    """Manual, no-token preflight from the computer actually attached to Clover."""
    import argparse
    import platform
    parser = argparse.ArgumentParser(description='Clover network check only; never charges a card.')
    parser.add_argument('--address', required=True)
    parser.add_argument('--terminal', required=True)
    parser.add_argument('--serial', required=True)
    args = parser.parse_args()
    try:
        result = check_network(args.address, args.terminal, args.serial)
    except CloverError as exc:
        result = {'status': 'failed', 'authorized': False, 'message': str(exc)}
    result.update(source_computer=platform.node(), intended_terminal=args.terminal, payments_attempted=0)
    print(json.dumps(result, indent=2))
    return 1 if result['status'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
