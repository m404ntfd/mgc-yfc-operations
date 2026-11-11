import json
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

import desktop_connection as connection
from remote.client import Client, normalize_address
from pos_kiosk import KioskBridge, KioskStore


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.mode = 'ok'
        case = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.reply()

            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length', 0)))
                self.reply()

            def reply(self):
                case.requests.append((self.command, self.path, dict(self.headers)))
                if self.headers.get('User-Agent') != connection.USER_AGENT:
                    self.send_response(403); self.end_headers(); return
                if case.mode == 'redirect':
                    self.send_response(302); self.send_header('Location', '/unexpected'); self.end_headers(); return
                body = {'application': 'thrift-mart-dispatch', 'version': '0.56.0'}
                if case.mode == 'wrong':body = {'application': 'another-server'}
                raw = json.dumps(body).encode()
                if self.path == '/pos.js':raw = b'kioskSetupDialog' if case.mode != 'old-pos' else b'old-client'
                if case.mode == 'html':raw = b'<html>Proxy sign-in</html>'
                if case.mode == 'large':raw = b' ' * 128001
                self.send_response(200); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.address = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def test_public_address_defaults_to_https_and_rejects_unsafe_addresses(self):
        self.assertEqual(connection.server_url('operations.coastyfc.com/'), connection.PUBLIC_SERVER)
        self.assertEqual(normalize_address('operations.coastyfc.com'), connection.PUBLIC_SERVER + ':443')
        self.assertEqual(connection.server_url('server-pc:8080'), 'http://server-pc:8080')
        for value in ['file:///data', 'https://user:password@site', 'https://site/path', 'http://site:0', 'http://site:65536', 'https://site?q=1', 'https://site/#a', 'http://my server']:
            with self.subTest(value=value), self.assertRaises(ValueError):connection.server_url(value)

    def test_identified_read_only_probes_for_all_desktop_apps(self):
        for app in ('office', 'pos', 'ops'):
            self.assertEqual(connection.probe_server(self.address, app), self.address)
        self.assertEqual([r[1] for r in self.requests], ['/api/session', '/api/session', '/pos.js', '/api/session'])
        for method, path, headers in self.requests:
            self.assertEqual(method, 'GET')
            self.assertNotIn('Cookie', headers)
            self.assertNotIn('Authorization', headers)

    def test_remote_admin_identifies_requests(self):
        self.assertEqual(Client(self.address).probe()['application'], 'thrift-mart-dispatch')
        self.assertEqual(self.requests[0][2]['User-Agent'], connection.USER_AGENT)

    def test_remote_helper_imports_without_the_project_on_python_path(self):
        folder = Path(__file__).resolve().parent / 'remote'
        command = "import sys;sys.path.insert(0," + repr(str(folder)) + ");from client import Client,USER_AGENT;assert USER_AGENT==" + repr(connection.USER_AGENT)
        result = subprocess.run([sys.executable, '-I', '-c', command], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_kiosk_approval_identifies_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KioskStore(Path(tmp) / 'settings.json')
            bridge = KioskBridge(store, self.address)
            self.assertEqual(bridge._redeem_remote('synthetic-test-token')['application'], 'thrift-mart-dispatch')
        self.assertEqual(self.requests[0][:2], ('POST', '/api/pos/kiosk-redeem'))
        self.assertEqual(self.requests[0][2]['User-Agent'], connection.USER_AGENT)

    def test_redirects_are_not_followed_or_replayed(self):
        self.mode = 'redirect'
        with self.assertRaisesRegex(ValueError, 'redirect'):connection.probe_server(self.address)
        with self.assertRaises(ValueError):Client(self.address).request('login', {'name': 'fixture', 'password': 'fixture-only'})
        self.assertEqual([r[1] for r in self.requests], ['/api/session', '/api/login'])

    def test_wrong_server_and_missing_desk_are_rejected(self):
        for mode, expected in [('wrong', 'not a compatible'), ('html', 'did not return'), ('large', 'unexpected'), ('old-pos', 'DESK-compatible')]:
            self.mode = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, expected):connection.probe_server(self.address, 'pos')

    def test_tls_verification_is_retained_and_errors_are_actionable(self):
        opener = Mock()
        opener.open.side_effect = URLError(ssl.SSLCertVerificationError('invalid certificate'))
        with patch.object(connection, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(ValueError, 'certificate'):connection.probe_server('https://fixture.invalid')
        self.assertNotIn('context', opener.open.call_args.kwargs)
        opener.open.side_effect = URLError('VPN disconnected')
        with patch.object(connection, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(ValueError, 'internet or VPN'):connection.probe_server('https://fixture.invalid')

    def test_ops_connection_change_preserves_other_settings_and_identity(self):
        from store_ops_desktop import save_connection
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            config = folder / 'connection.json'
            config.write_text(json.dumps({'server': self.address, 'custom': 'keep'}))
            device = folder / 'settings.json'; device.write_text('{"device":"keep-the-existing-device"}')
            before = device.read_bytes()
            save_connection(folder, connection.PUBLIC_SERVER)
            self.assertEqual(json.loads(config.read_text()), {'server': connection.PUBLIC_SERVER, 'custom': 'keep'})
            self.assertEqual(device.read_bytes(), before)
            config.write_text('damaged settings')
            with self.assertRaises(ValueError):save_connection(folder, self.address)
            self.assertEqual(config.read_text(), 'damaged settings')


if __name__ == '__main__':unittest.main()
