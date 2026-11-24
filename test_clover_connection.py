"""Connection pilot regression tests with synthetic merchants/tokens only."""
import base64
import datetime as dt
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

import clover_connection as clover


NOW = 1800000000
BINDING = clover.Binding('production', 'TESTAPP', 'TESTMERCHANT', 'test-store', 'test-pos', 'TESTSERIAL0564')
SESSION = 'isolated-admin-session-' + 'x' * 32
CALLBACK = 'https://example.com/clover/callback'


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.payload = {'access_token': 'test-access-secret', 'access_token_expiration': NOW + 300,
                        'refresh_token': 'test-refresh-secret', 'refresh_token_expiration': NOW + 900}
        self.merchant = {'id': BINDING.merchant_id}
        self.devices = {'elements': [{'serial': BINDING.device_serial, 'merchant': {'id': BINDING.merchant_id}}]}
        self.ping_status = 200
        self.ping_body = {'connected': True}

    def api(self, binding, operation, **kwargs):
        self.calls.append((operation, binding, kwargs))
        return {'token': self.payload, 'merchant': self.merchant, 'devices': self.devices}[operation]

    def ping(self, *args, **kwargs):
        self.calls.append(('ping', args, kwargs))
        return self.ping_status, self.ping_body


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.attempt = clover.AuthorizationAttempt.begin(BINDING, CALLBACK, SESSION, now=NOW)
        self.transport = FakeTransport()

    def callback(self, **overrides):
        query = {'state': parse_qs(urlsplit(self.attempt.authorization_url()).query)['state'][0],
                 'client_id': BINDING.client_id, 'merchant_id': BINDING.merchant_id, 'code': 'test-code'}
        query.update(overrides)
        return CALLBACK + '?' + urlencode(query)

    def complete(self, **kwargs):
        args = {'callback_url': self.callback(), 'session_id': SESSION, 'binding': BINDING,
                'transport': self.transport, 'now': NOW + 1}
        args.update(kwargs)
        return self.attempt.complete(**args)

    def test_pkce_code_exchange_and_secret_free_representations(self):
        url = self.attempt.authorization_url()
        query = parse_qs(urlsplit(url).query)
        grant = self.complete()
        sent = self.transport.calls[0][2]['body']
        challenge = base64.urlsafe_b64encode(hashlib.sha256(sent['code_verifier'].encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(query['code_challenge'], [challenge])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertEqual(set(sent), {'client_id', 'code', 'code_verifier'})
        self.assertNotIn(sent['code_verifier'], url)
        self.assertEqual(grant.access(BINDING, NOW), 'test-access-secret')
        for secret in ('test-access-secret', 'test-refresh-secret', sent['code_verifier']):
            self.assertNotIn(secret, repr(grant) + repr(self.attempt))

    def test_wrong_state_session_store_device_or_callback_sends_nothing(self):
        for arguments in ({'callback_url': self.callback(state='wrong')},
                          {'session_id': 'other-admin-' + 'y'*32},
                          {'binding': replace(BINDING, store_id='other-store')},
                          {'binding': replace(BINDING, device_serial='OTHERDEVICE')},
                          {'callback_url': self.callback().replace('example.com', 'attacker.invalid')},
                          {'callback_url': self.callback() + '&state=duplicate'},
                          {'callback_url': self.callback() + '#fragment'}):
            with self.subTest(arguments=tuple(arguments)):
                with self.assertRaises(clover.CloverError):
                    self.complete(**arguments)
        self.assertEqual(self.transport.calls, [])

    def test_wrong_merchant_or_app_never_exchanges_code(self):
        for field in ('merchant_id', 'client_id'):
            with self.subTest(field=field):
                self.setUp()
                with self.assertRaises(clover.CloverError):
                    self.complete(callback_url=self.callback(**{field: 'WRONG'}))
                self.assertEqual(self.transport.calls, [])

    def test_expired_and_future_sessions_cannot_exchange(self):
        for now in (NOW + 601, NOW - 1):
            with self.assertRaises(clover.CloverError):
                self.complete(now=now)
        self.assertEqual(self.transport.calls, [])

    def test_replay_including_parallel_callbacks_only_exchanges_once(self):
        callback = self.callback()
        results = []
        def finish():
            try:
                results.append(self.complete(callback_url=callback))
            except clover.CloverError:
                results.append(None)
        threads = [threading.Thread(target=finish) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len([r for r in results if r is not None]), 1)
        self.assertEqual(len(self.transport.calls), 1)

    def test_ambiguous_exchange_is_not_retried(self):
        callback = self.callback()
        with patch.object(self.transport, 'api', side_effect=clover.CloverError('Network interrupted.')) as api:
            for _ in range(2):
                with self.assertRaises(clover.CloverError):
                    self.complete(callback_url=callback)
            self.assertEqual(api.call_count, 1)

    def test_denial_does_not_expose_provider_error_text(self):
        with self.assertRaises(clover.CloverError) as result:
            self.complete(callback_url=self.callback(error='secret-from-provider'))
        self.assertNotIn('secret-from-provider', str(result.exception))
        self.assertEqual(self.transport.calls, [])

    def test_invalid_or_expired_token_payload_rejected(self):
        for field, value in (('access_token', 'bad\r\nheader'), ('refresh_token', ''),
                             ('access_token_expiration', NOW - 1), ('access_token_expiration', float('inf')),
                             ('refresh_token_expiration', True)):
            with self.subTest(field=field):
                self.setUp()
                self.transport.payload[field] = value
                with self.assertRaises(clover.CloverError):
                    self.complete()

    def test_callback_must_be_explicit_https_without_ambiguous_components(self):
        for uri in ('http://example.com/clover', 'https://example.com/callback?code=bad',
                    'https://example.com/a/../clover', 'https://example.com/%2e%2e/clover',
                    'https://user:pass@example.com/clover', 'https://127.0.0.1/clover',
                    'https://localhost/clover', 'https://example.com:8080/clover'):
            with self.subTest(uri=uri), self.assertRaises(clover.CloverError):
                clover.AuthorizationAttempt.begin(BINDING, uri, SESSION)


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.grant = clover.Grant(BINDING, 'test-access', NOW+300, 'test-refresh', NOW+900)

    def run_check(self, **kwargs):
        arguments = {'grant': self.grant, 'binding': BINDING, 'address': '192.168.2.50',
                     'transport': self.transport, 'now': NOW}
        arguments.update(kwargs)
        return clover.check_authorized_device(**arguments)

    def test_only_merchant_read_device_read_and_get_ping_on_success(self):
        result = self.run_check()
        self.assertTrue(result['authorized'])
        self.assertEqual(result['payments_attempted'], 0)
        self.assertEqual([call[0] for call in self.transport.calls], ['merchant', 'devices', 'ping'])
        self.assertEqual(result['serial_last_four'], '0564')

    def test_different_store_terminal_merchant_serial_or_environment_blocks_all_calls(self):
        for field in ('store_id', 'terminal_id', 'merchant_id', 'device_serial', 'client_id', 'environment'):
            value = 'sandbox' if field == 'environment' else 'other'
            with self.subTest(field=field), self.assertRaises(clover.CloverError):
                self.run_check(binding=replace(BINDING, **{field: value}))
        self.assertEqual(self.transport.calls, [])

    def test_expired_access_requires_reauthorization_without_automatic_refresh(self):
        with self.assertRaises(clover.CloverError):
            self.run_check(now=NOW+280)
        self.assertEqual(self.transport.calls, [])

    def test_no_device_token_if_merchant_or_ownership_does_not_match(self):
        cases = [({'id': 'OTHER'}, self.transport.devices),
                 (self.transport.merchant, {'elements': []}),
                 (self.transport.merchant, {'elements': [{'serial': 'OTHER'}]}),
                 (self.transport.merchant, {'elements': [{'serial': BINDING.device_serial, 'merchant': {'id': 'OTHER'}}]}),
                 (self.transport.merchant, {'elements': [{'serial': BINDING.device_serial}]*2})]
        for merchant, devices in cases:
            with self.subTest(devices=devices):
                self.transport = FakeTransport()
                self.transport.merchant, self.transport.devices = merchant, devices
                with self.assertRaises(clover.CloverError):
                    self.run_check()
                self.assertNotIn('ping', [call[0] for call in self.transport.calls])

    def test_busy_expired_or_false_ping_is_not_success_and_never_retried(self):
        for status, payload in ((503, {}), (401, {}), (500, {}), (200, {'connected': False}),
                                (200, {'connected': 'true'}), (200, {})):
            with self.subTest(status=status):
                self.transport = FakeTransport()
                self.transport.ping_status, self.transport.ping_body = status, payload
                with self.assertRaises(clover.CloverError):
                    self.run_check()
                self.assertEqual([call[0] for call in self.transport.calls].count('ping'), 1)

    def test_network_preflight_is_not_a_successful_authorization(self):
        for status in (200, 401, 503):
            self.transport.ping_status = status
            result = clover.check_network('192.168.2.50', 'test-pos', BINDING.device_serial, transport=self.transport)
            self.assertTrue(result['reachable'])
            self.assertFalse(result['authorized'])

    def test_device_address_rejects_public_loopback_linklocal_dns_and_injection(self):
        for value in ('127.0.0.1', '169.254.169.254', '8.8.8.8', '::1', 'clover.local',
                      'https://192.168.2.50', '192.168.2.50:8080', '192.168.2.50/charge'):
            with self.subTest(value=value), self.assertRaises(clover.CloverError):
                clover.device_address(value)
        self.assertEqual(clover.device_address('192.168.2.50'), '192.168.2.50')


class TransportTests(unittest.TestCase):
    def test_api_cannot_send_payment_refund_or_arbitrary_methods(self):
        transport = clover.CloverTransport()
        with patch.object(clover, '_read') as read:
            for operation in ('payment', 'refund', 'order', 'cancel', '/connect/v1/payments'):
                with self.assertRaises(clover.CloverError):
                    transport.api(BINDING, operation, token='test-token')
            with self.assertRaises(clover.CloverError):
                transport.api(BINDING, 'merchant', token='test-token', body={'amount': 1})
            read.assert_not_called()

    def test_environment_hosts_and_payloads_are_fixed(self):
        for environment, domain in (('production', 'api.clover.com'), ('sandbox', 'apisandbox.dev.clover.com')):
            binding = replace(BINDING, environment=environment)
            with patch.object(clover, '_read', return_value=(200, b'{}')) as read:
                clover.CloverTransport().api(binding, 'devices', token='test-token')
                request = read.call_args.args[0]
                self.assertEqual(urlsplit(request.full_url).hostname, domain)
                self.assertEqual(request.get_method(), 'GET')
                self.assertIsNone(request.data)
                self.assertEqual(request.get_header('Authorization'), 'Bearer test-token')

    def test_no_redirect_or_device_auth_headers_on_certificate_download(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with patch.object(clover, '_read', side_effect=[(200, b'fixture-cert'), (401, b'')]) as read, \
                patch.object(clover, 'device_context', return_value=context):
            clover.CloverTransport().ping('192.168.2.50', 'test-pos', BINDING.device_serial, token='test-token')
            certificate_request = read.call_args_list[0].args[0]
            ping_request = read.call_args_list[1].args[0]
            self.assertEqual(certificate_request.full_url, clover.CA_URL)
            self.assertIsNone(certificate_request.get_header('Authorization'))
            self.assertEqual(ping_request.full_url, 'https://192.168.2.50:12346/connect/v1/device/ping')
            self.assertEqual(ping_request.get_method(), 'GET')
            self.assertEqual(ping_request.get_header('X-pos-id'), 'test-pos')
        self.assertIsNone(clover._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://attacker.invalid'))

    def test_http_errors_do_not_echo_tokens_or_remote_body(self):
        with patch.object(clover, '_read', return_value=(401, b'test-secret-in-error')):
            with self.assertRaises(clover.CloverError) as result:
                clover.CloverTransport().api(BINDING, 'merchant', token='test-token')
            self.assertNotIn('test-secret', str(result.exception))


class RealTlsTests(unittest.TestCase):
    """Disposable loopback HTTPS endpoints; no actual Clover or store data."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.now = dt.datetime.now(dt.timezone.utc)
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Isolated Clover test CA')])
        cls.ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                  .public_key(cls.key.public_key()).serial_number(x509.random_serial_number())
                  .not_valid_before(cls.now-dt.timedelta(days=3)).not_valid_after(cls.now+dt.timedelta(days=3))
                  .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                  .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, None, None), critical=True)
                  .add_extension(x509.SubjectKeyIdentifier.from_public_key(cls.key.public_key()), critical=False)
                  .sign(cls.key, hashes.SHA256()))
        cls.pem = cls.ca.public_bytes(serialization.Encoding.PEM)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def endpoint(self, *, expired=False, wrong_name=False, response=200):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Isolated device fixture')])
        names = [x509.DNSName('wrong.invalid')] if wrong_name else [x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(self.ca.subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(self.now-dt.timedelta(days=2))
                .not_valid_after(self.now+dt.timedelta(days=-1 if expired else 1))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.SubjectAlternativeName(names), critical=False)
                .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, None, None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.key.public_key()), critical=False)
                .sign(self.key, hashes.SHA256()))
        cert_file, key_file = self.root/'device.pem', self.root/'device.key'
        cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(response)
                if response == 302:
                    self.send_header('Location', '/unexpected-redirect')
                self.end_headers()
                self.wfile.write(b'{"connected":true}')
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('AES256-GCM-SHA384')
        context.load_cert_chain(cert_file, key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.addCleanup(cleanup)
        return Request('https://127.0.0.1:' + str(server.server_port) + '/connect/v1/device/ping'), requests

    def test_documented_tls_cipher_works_with_pem_and_der_ca(self):
        request, seen = self.endpoint()
        for certificate in (self.pem, self.ca.public_bytes(serialization.Encoding.DER)):
            context = clover.device_context(certificate)
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            status, raw = clover._read(request, context)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw), {'connected': True})
        self.assertEqual(len(seen), 2)

    def test_wrong_hostname_expired_and_untrusted_certificates_rejected(self):
        for expired, wrong_name, trusted in ((True, False, True), (False, True, True), (False, False, False)):
            with self.subTest(expired=expired, wrong_name=wrong_name, trusted=trusted):
                request, seen = self.endpoint(expired=expired, wrong_name=wrong_name)
                context = clover.device_context(self.pem) if trusted else ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.maximum_version = ssl.TLSVersion.TLSv1_2
                context.set_ciphers(clover.CIPHERS)
                with self.assertRaisesRegex(clover.CloverError, 'secure connection could not be verified'):
                    clover._read(request, context)
                self.assertEqual(seen, [])

    def test_http_redirect_never_forwards_request(self):
        request, seen = self.endpoint(response=302)
        status, raw = clover._read(request, clover.device_context(self.pem))
        self.assertEqual((status, raw), (302, b''))
        self.assertEqual(seen, ['/connect/v1/device/ping'])

    def test_response_size_is_limited(self):
        request, _ = self.endpoint()
        with self.assertRaisesRegex(clover.CloverError, 'large response'):
            clover._read(request, clover.device_context(self.pem), limit=4)


if __name__ == '__main__':
    unittest.main()
