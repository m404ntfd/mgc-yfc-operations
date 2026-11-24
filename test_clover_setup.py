"""Isolated server settings and native bridge checks. No real device requests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import clover_desktop
import server
from pos_kiosk import KioskStore, KioskBridge
import test_cash_advances as fixtures


class CloverSetupTests(unittest.TestCase):
    setUp = fixtures.CashAdvanceTests.setUp
    tearDown = fixtures.CashAdvanceTests.tearDown
    post = fixtures.CashAdvanceTests.post
    ok = fixtures.CashAdvanceTests.ok

    def save(self, **changes):
        body = dict(terminal=self.terminal, revision=0, store_id='thrift-mart', address='192.168.2.50',
                    serial='TESTSERIAL0564', merchant_id='')
        body.update(changes)
        return self.post('clover-settings-save', **body)

    def approval(self):
        code, result = self.post('clover-test-approval', terminal=self.terminal, revision=1, device=self.device, nonce='b'*64)
        self.assertEqual(code, 200, result)
        return dict(token=result['token'], device=self.device, nonce='b'*64)

    def test_admin_only_access_and_validated_settings(self):
        staff = self.f.client('e')
        self.f.call('login', dict(name='Employee', password='testpassword'), staff)
        self.f.call('admin/permissions', dict(name='Employee', grants={'use_pos': True, 'manage_pos': True}, can_create=False, see_requests=False))
        self.assertEqual(self.f.call('pos/clover-settings', client=staff)[0], 403)
        self.assertEqual(self.post('clover-settings-save', client=staff, terminal=self.terminal, revision=0)[0], 403)
        self.assertEqual(self.post('clover-test-approval', client=staff, terminal=self.terminal, revision=0)[0], 403)
        for changes in (dict(address='127.0.0.1'), dict(address='8.8.8.8'), dict(address='169.254.169.254'),
                        dict(address='clover.local'), dict(serial='bad\nserial'), dict(merchant_id='not an id'),
                        dict(store_id='binopoly'), dict(revision=True)):
            self.assertIn(self.save(**changes)[0], (400, 409))
        code, result = self.save()
        self.assertEqual(code, 200, result)
        self.assertFalse(result['authorized'])
        self.assertFalse(result['payments_enabled'])
        self.assertEqual(self.save()[0], 409)
        self.assertEqual(self.f.call('pos/clover-settings?terminal='+self.terminal)[1]['settings']['revision'], 1)

    def test_one_use_bound_expiry_and_logout(self):
        self.assertEqual(self.save()[0], 200)
        request = self.approval()
        anonymous = self.f.client('n')
        for changes in (dict(device='2'*32), dict(nonce='c'*64)):
            self.assertEqual(self.f.call('pos/clover-test-redeem', dict(request, **changes), anonymous)[0], 403)
        code, result = self.f.call('pos/clover-test-redeem', request, anonymous)
        self.assertEqual(code, 200, result)
        self.assertEqual(result['purpose'], 'clover-network-check-only')
        self.assertEqual(result['address'], '192.168.2.50')
        self.assertEqual(self.f.call('pos/clover-test-redeem', request, anonymous)[0], 403)
        request = self.approval()
        server.CLOVER_PILOT_TICKETS[hashlib.sha256(request['token'].encode()).hexdigest()]['expires'] = 0
        self.assertEqual(self.f.call('pos/clover-test-redeem', request, anonymous)[0], 403)
        request = self.approval()
        server.SESSIONS.clear()
        self.assertEqual(self.f.call('pos/clover-test-redeem', request, anonymous)[0], 403)

    def test_edit_or_admin_revocation_invalidates_approval(self):
        self.assertEqual(self.save()[0], 200)
        request = self.approval()
        self.assertEqual(self.save(revision=1, address='192.168.2.51')[0], 200)
        self.assertEqual(self.f.call('pos/clover-test-redeem', request)[0], 409)
        self.assertEqual(self.save(revision=2)[0], 200)
        code, result = self.post('clover-test-approval', terminal=self.terminal, revision=3, device=self.device, nonce='b'*64)
        self.assertEqual(code, 200, result)
        with server.connect() as c:
            c.execute("UPDATE users SET admin=0 WHERE name='Admin'")
        self.assertEqual(self.f.call('pos/clover-test-redeem', dict(token=result['token'], device=self.device, nonce='b'*64))[0], 403)

    def test_store_move_removal_and_duplicate_device(self):
        self.assertEqual(self.save()[0], 200)
        other = self.ok('terminal-save', name='Other fixture', device='2'*32, enabled=True, store_id='binopoly')['id']
        self.assertEqual(self.save(terminal=other, store_id='binopoly')[0], 409)
        request = self.approval()
        with server.connect() as c:
            c.execute('INSERT INTO retail_terminal_stores VALUES(?,?) ON CONFLICT(terminal) DO UPDATE SET store=excluded.store', (self.terminal, 'binopoly'))
        self.assertTrue(self.f.call('pos/clover-settings?terminal='+self.terminal)[1]['store_changed'])
        self.assertEqual(self.f.call('pos/clover-test-redeem', request)[0], 409)
        self.assertEqual(self.post('clover-test-approval', terminal=self.terminal, revision=1, device=self.device, nonce='b'*64)[0], 409)
        with server.connect() as c:
            c.execute('UPDATE retail_terminals SET enabled=0 WHERE id=?', (self.terminal,))
        self.assertEqual(self.f.call('pos/clover-settings?terminal='+self.terminal)[0], 409)
        with server.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_clover_pilot WHERE terminal=?', (self.terminal,)).fetchone()[0], 1)

    def test_additive_setup_preserves_records_and_backup(self):
        product = self.ok('product-save', name='Retained sample book', category='Books', price=200, taxable=True)['ids'][0]
        for completed in (True, False):
            cart = self.ok('new', device=self.device)['cart']
            cart = self.ok('add', cart=cart['id'], revision=cart['revision'], product=product, quantity=1)['cart']
            if completed:
                self.ok('cash', cart=cart['id'], revision=cart['revision'], tender=500)
            else:
                self.ok('hold', cart=cart['id'], revision=cart['revision'])
        with server.connect() as c:
            account = self.people['Employee']
            c.execute('INSERT INTO work_periods VALUES(?,?,?,?,?,?)', (991, account, 100, None, 'Original site', None))
            c.execute('INSERT INTO work_breaks VALUES(?,?,?,?)', (992, 991, 120, None))
            c.execute('INSERT INTO work_periods VALUES(?,?,?,?,?,?)', (993, account, 10, 90, 'Original site', 'Original site'))
            c.execute('INSERT INTO work_breaks VALUES(?,?,?,?)', (994, 993, 30, 40))
            c.execute('INSERT INTO work_time_card_audit VALUES(?,?,?,?,?,?,?,?)', (995, 993, 'Employee', 'Admin', '2026-11-01T10:30:00-06:00', 'Keep original correction', '{"start":9}', '{"start":10}'))
            c.execute('INSERT INTO jobs VALUES(?,?,?)', ('clover-fixture-job', 7, json.dumps({'type': 'Pickup', 'notes': 'Preserve original appointment'})))
            c.execute('INSERT INTO photos VALUES(?,?,?)', ('clover-fixture-job', 0, b'preserved-test-attachment'))
            c.commit()
            tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('retail_clover_pilot','audit','sqlite_sequence')")]
            def snapshot(connection):
                return {name: [tuple(row) for row in connection.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in tables}
            before = snapshot(c)
        self.assertEqual(self.save()[0], 200)
        self.assertEqual(self.f.call('pos/clover-test-redeem', self.approval())[0], 200)
        with server.connect() as c:
            server.clover_pilot_init(c)
            server.clover_pilot_init(c)
            self.assertEqual(snapshot(c), before)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            import sqlite3
            with sqlite3.connect(':memory:') as backup:
                backup.row_factory = sqlite3.Row
                c.backup(backup)
                self.assertEqual(snapshot(backup), before)
                self.assertEqual(backup.execute('SELECT COUNT(*) FROM retail_clover_pilot').fetchone()[0], 1)


class CloverDesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        store = KioskStore(Path(self.temp.name)/'settings.json')
        store.set_passcode('123456', '123456')
        self.bridge = KioskBridge(store, 'https://operations.example.com')
        self.bridge._window = Mock()
        self.bridge._window.get_current_url.return_value = 'https://operations.example.com/pos'
        self.approval = dict(purpose='clover-network-check-only', device=store.data['device'], nonce=self.bridge._nonce,
                             terminal_id='test-terminal', terminal_name='Test POS', store_name='Test Store',
                             address='192.168.2.50', serial='TESTSERIAL0564')

    def test_only_server_approved_target_is_checked_and_data_stays_unchanged(self):
        before = self.bridge._store.path.read_bytes()
        with patch.object(clover_desktop, '_redeem', return_value=self.approval), \
                patch.object(clover_desktop, 'check_network', return_value={'authorized': False, 'status': 'authorization_required'}) as check:
            result = self.bridge.clover_connection_check('a'*64)
            self.assertEqual(result['payments_attempted'], 0)
            self.assertIn('source_computer', result)
            check.assert_called_once_with('192.168.2.50', 'test-terminal', 'TESTSERIAL0564')
        self.assertEqual(self.bridge._store.path.read_bytes(), before)

    def test_untrusted_page_office_or_malformed_approval_cannot_probe(self):
        with patch.object(clover_desktop, '_redeem', return_value=self.approval) as redeem, patch.object(clover_desktop, 'check_network') as check:
            for url in ('https://attacker.invalid/pos', 'https://operations.example.com/office', 'https://operations.example.com/'):
                self.bridge._window.get_current_url.return_value = url
                self.assertIn('error', self.bridge.clover_connection_check('a'*64))
            redeem.assert_not_called()
            self.bridge._window.get_current_url.return_value = 'https://operations.example.com/pos'
            for field, value in (('nonce', 'wrong'), ('device', 'wrong'), ('purpose', 'payment')):
                redeem.return_value = dict(self.approval, **{field: value})
                self.assertIn('error', self.bridge.clover_connection_check('a'*64))
            check.assert_not_called()


if __name__ == '__main__':
    unittest.main()
