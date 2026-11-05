"""Exercise registration, audience selection and the encrypted push request."""
import base64
from contextlib import contextmanager
import json
import sqlite3
import unittest
from unittest.mock import Mock, patch

import server


@unittest.skipIf(server.WebPush is None, 'Web Push runtime is not installed')
class WebPushTests(unittest.TestCase):
    def test_only_subscribed_unread_recipients_receive_generic_notification(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        c = sqlite3.connect(':memory:')
        self.addCleanup(c.close)
        c.row_factory = sqlite3.Row
        c.executescript("""
            CREATE TABLE users(name TEXT PRIMARY KEY);
            CREATE TABLE receipt_profiles(name TEXT,profile_id TEXT);
            INSERT INTO users VALUES ('Author'),('Reader'),('Other'),('Muted');
            INSERT INTO receipt_profiles VALUES
                ('Author','author'),('Reader','reader'),('Other','other'),('Muted','muted');
        """)
        server.init_comms(c)
        c.executemany('INSERT INTO comm_members(thread,account) VALUES (1,?)',
                      [('author',), ('reader',), ('muted',)])
        c.execute('INSERT INTO comm_prefs VALUES (?,?)', ('muted', '{"alerts":false}'))
        handler = Mock(headers={'Host':'operations.coastyfc.com'})
        handler.external_scheme.return_value = 'https'
        handler.send.side_effect = lambda body: body
        settings = server.push_settings(handler, c, 'reader', {})
        self.assertEqual(len(settings['publicKey']), 87)
        self.assertEqual(settings['publicKey'], server.push_settings(handler, c, 'reader', {})['publicKey'])
        client = ec.generate_private_key(ec.SECP256R1())
        auth = b'0' * 16
        public = client.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        def encode(data):
            return base64.urlsafe_b64encode(data).decode().rstrip('=')

        for i, account in enumerate(('author','reader','other','muted')):
            subscription = {
                'endpoint': f'https://fcm.googleapis.com/fcm/send/{account}',
                'keys': {'auth': encode(auth), 'p256dh': encode(public)}
            }
            device = f'{i:032x}'
            server.push_update(handler, c, account, dict(enabled=True, device=device, subscription=subscription))
        self.assertTrue(server.push_settings(handler, c, 'reader', {'device':[f'{1:032x}']})['enabled'])
        self.assertFalse(server.push_settings(handler, c, 'other', {'device':[f'{1:032x}']})['enabled'])
        with self.assertRaises(server.Problem):
            server.push_subscription({**subscription, 'endpoint':'https://fcm.googleapis.com@127.0.0.1/local'})
        with self.assertRaises(server.Problem):
            server.push_subscription({**subscription, 'endpoint':'https://[fcm.googleapis.com'})
        handler.external_scheme.return_value = 'http'
        self.assertEqual(server.push_settings(handler, c, 'reader', {})['reason'], 'https')

        @contextmanager
        def connect():
            with c:
                yield c

        session = Mock()
        session.post.return_value.status_code = 201
        with patch.object(server, 'connect', connect):
            server.push_deliver(session, 1, 10, 'author')
            session.post.assert_called_once()
            self.assertEqual(session.post.call_args.args[0], 'https://fcm.googleapis.com/fcm/send/reader')
            payload = session.post.call_args.kwargs['data']
            import http_ece
            clear = http_ece.decrypt(payload, private_key=client, auth_secret=auth, version='aes128gcm')
            self.assertEqual(json.loads(clear), {})

            c.execute("UPDATE comm_members SET seen=10 WHERE account='reader'")
            session.reset_mock()
            server.push_deliver(session, 1, 10, 'author')
            session.post.assert_not_called()

            session.post.return_value.status_code = 410
            server.push_deliver(session, 1, 11, 'author')
            self.assertFalse(c.execute("SELECT 1 FROM comm_push_devices WHERE account='reader'").fetchone())


if __name__ == '__main__':
    unittest.main()
