"""Statement delivery preparation uses isolated SQLite data and never sends mail."""
import json
import sqlite3
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import server


class StatementDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:')
        self.c.row_factory = sqlite3.Row
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE audit(at TEXT,actor TEXT,action TEXT,detail TEXT)')
        server.giving_init(self.c)
        self.user = {'name':'Test administrator','admin':True}
        self.donor = self.post('donor', name='Synthetic Donor', email='donor@example.test',
                               address='Test address', delivery='email')['id']
        self.statement = self.post('statement_snapshot', donor=self.donor, period='2025')['id']

    def post(self, path, **body):
        with self.c:
            return server.giving_post(self.c, self.user, path, {'request':uuid.uuid4().hex, **body})

    def deliveries(self):
        return server.giving_get(self.c, self.user, 'statement_deliveries', {'statement':[self.statement]})

    def test_frozen_recipient_snapshot_and_idempotent_prepare(self):
        request = uuid.uuid4().hex
        with patch.object(server.smtplib, 'SMTP', side_effect=AssertionError('No email allowed')), \
             patch.object(server.smtplib, 'SMTP_SSL', side_effect=AssertionError('No email allowed')):
            first = self.post('queue_statement', statement=self.statement, request=request)
            self.assertEqual(first, self.post('queue_statement', statement=self.statement, request=request))
        self.post('donor', id=self.donor, revision=1, name='Renamed donor',
                  email='changed@example.test', address='New address', delivery='print')
        result = self.deliveries()
        self.assertFalse(result['sending_enabled'])
        self.assertEqual(len(result['deliveries']), 1)
        record = result['deliveries'][0]
        self.assertEqual(record['recipient'], 'donor@example.test')
        self.assertEqual(record['status'], 'prepared')
        self.assertEqual(record['actor'], self.user['name'])
        self.assertTrue(record['created_at'])
        snapshot = server.giving_get(self.c, self.user, 'statement_snapshot', {'id':[self.statement]})
        self.assertEqual(snapshot['donor']['name'], 'Synthetic Donor')
        self.assertEqual(snapshot['delivery'], 'not_sent')
        self.assertEqual(self.c.execute("SELECT count(*) FROM audit WHERE action='Giving queue_statement'").fetchone()[0], 1)

    def test_duplicate_and_cancellation_are_audited_and_terminal(self):
        delivery = self.post('queue_statement', statement=self.statement)['id']
        with self.assertRaises(server.Problem) as problem:
            self.post('queue_statement', statement=self.statement)
        self.assertEqual(problem.exception.status, 409)
        request = uuid.uuid4().hex
        result = self.post('cancel_statement_delivery', delivery=delivery, reason='Incorrect recipient', request=request)
        self.assertEqual(result, self.post('cancel_statement_delivery', delivery=delivery, reason='Incorrect recipient', request=request))
        record = self.deliveries()['deliveries'][0]
        self.assertEqual(record['status'], 'cancelled')
        self.assertEqual(record['cancellation']['reason'], 'Incorrect recipient')
        self.assertEqual(record['cancellation']['actor'], self.user['name'])
        self.assertTrue(record['cancellation']['at'])
        with self.assertRaises(server.Problem) as problem:
            self.post('cancel_statement_delivery', delivery=delivery, reason='Again')
        self.assertEqual(problem.exception.status, 409)
        with self.assertRaises(server.Problem):
            self.post('queue_statement', statement=self.statement)
        new_copy = self.post('statement_snapshot', donor=self.donor, period='2025')['id']
        self.assertTrue(self.post('queue_statement', statement=new_copy)['ok'])

    def test_permissions_and_request_ownership(self):
        request = uuid.uuid4().hex
        self.post('queue_statement', statement=self.statement, request=request)
        for grants in ({}, {'view_giving':True}, {'view_giving':True,'giving_statements':True},
                       {'view_giving':True,'giving_delivery':True}):
            self.user = {'name':'Restricted staff','admin':False,'grants':grants}
            for action in (lambda: self.deliveries(), lambda: self.post('queue_statement',statement=self.statement),
                           lambda: self.post('cancel_statement_delivery',delivery='missing',reason='Test')):
                with self.assertRaises(server.Problem) as problem:
                    action()
                self.assertEqual(problem.exception.status, 403)
        self.user['grants'] = dict(view_giving=True, giving_statements=True, giving_delivery=True)
        self.assertEqual(len(self.deliveries()['deliveries']), 1)
        with self.assertRaises(server.Problem) as problem:
            self.post('queue_statement', statement=self.statement, request=request)
        self.assertEqual(problem.exception.status, 409)

    def test_validation_and_saved_preference(self):
        with self.assertRaises(server.Problem) as problem:
            self.post('queue_statement', statement='missing')
        self.assertEqual(problem.exception.status, 404)
        with self.assertRaises(server.Problem):
            self.post('queue_statement', statement=self.statement, recipient='other@example.test')
        self.post('donor', id=self.donor, revision=1, name='Printed donor',
                  email='', address='Test address', delivery='print')
        printed = self.post('statement_snapshot', donor=self.donor, period='2025')['id']
        with self.assertRaises(server.Problem):
            self.post('queue_statement', statement=printed)
        # A later preference change cannot rewrite the saved copy's delivery choice.
        self.post('donor', id=self.donor, revision=2, name='Printed donor',
                  email='new@example.test', address='Test address', delivery='email')
        with self.assertRaises(server.Problem):
            self.post('queue_statement', statement=printed)
        delivery = self.post('queue_statement', statement=self.statement)['id']
        with self.assertRaises(server.Problem):
            self.post('cancel_statement_delivery', delivery=delivery, reason='   ')
        self.assertEqual(self.deliveries()['deliveries'][0]['status'], 'prepared')

    def test_failed_audit_rolls_back_queue_cancellation_and_retry_receipt(self):
        request = uuid.uuid4().hex
        self.c.execute("CREATE TRIGGER fail_delivery_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'Test failure'); END")
        self.c.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.post('queue_statement', statement=self.statement, request=request)
        self.assertEqual(self.deliveries()['deliveries'], [])
        self.assertIsNone(self.c.execute('SELECT 1 FROM giving_requests WHERE id=?',(request,)).fetchone())
        self.c.execute('DROP TRIGGER fail_delivery_audit')
        delivery = self.post('queue_statement', statement=self.statement, request=request)['id']
        self.c.execute("CREATE TRIGGER fail_delivery_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'Test failure'); END")
        self.c.commit()
        request = uuid.uuid4().hex
        with self.assertRaises(sqlite3.IntegrityError):
            self.post('cancel_statement_delivery', delivery=delivery, reason='Cancel', request=request)
        self.assertEqual(self.deliveries()['deliveries'][0]['status'], 'prepared')
        self.assertIsNone(self.c.execute('SELECT 1 FROM giving_requests WHERE id=?',(request,)).fetchone())

    def test_immutable_history_repeat_migration_and_backup(self):
        delivery = self.post('queue_statement', statement=self.statement)['id']
        self.post('cancel_statement_delivery', delivery=delivery, reason='Test cancellation')
        tables = [r[0] for r in self.c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = {t:list(map(tuple,self.c.execute('SELECT * FROM '+t))) for t in tables}
        server.giving_init(self.c); server.giving_init(self.c)
        self.assertEqual(before,{t:list(map(tuple,self.c.execute('SELECT * FROM '+t))) for t in tables})
        for table in ('giving_statement_deliveries','giving_statement_delivery_cancellations'):
            for operation in ('DELETE FROM '+table,'UPDATE '+table+' SET actor=actor'):
                with self.assertRaises(sqlite3.IntegrityError), self.c:
                    self.c.execute(operation)
        backup = sqlite3.connect(':memory:')
        self.addCleanup(backup.close)
        self.c.backup(backup)
        self.assertEqual(before,{t:list(map(tuple,backup.execute('SELECT * FROM '+t))) for t in tables})

    def test_concurrent_queue_requests_create_one_delivery(self):
        with tempfile.TemporaryDirectory(prefix='giving-delivery-', dir=Path(__file__).parent) as directory:
            database = str(Path(directory)/'synthetic.sqlite')
            with closing(sqlite3.connect(database)) as target:
                self.c.backup(target)
            def queue_one(_):
                c = sqlite3.connect(database, timeout=5)
                c.row_factory = sqlite3.Row
                try:
                    with c:
                        server.giving_post(c,self.user,'queue_statement',{'statement':self.statement,'request':uuid.uuid4().hex})
                    return 200
                except server.Problem as error:
                    return error.status
                finally:
                    c.close()
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(queue_one,range(2))), [200,409])
            with closing(sqlite3.connect(database)) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM giving_statement_deliveries').fetchone()[0],1)


if __name__=='__main__':
    unittest.main()
