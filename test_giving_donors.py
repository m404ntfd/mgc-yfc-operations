"""Donor backend regression checks using synthetic records and isolated storage."""
import json
import sqlite3
import unittest
import uuid
import server
import test_giving_storage as storage


class DonorBackendTests(unittest.TestCase):
    setUp = storage.GivingStorageTests.setUp
    post = storage.GivingStorageTests.post
    get = storage.GivingStorageTests.get

    def edit(self, **changes):
        data = dict(id=self.donor, revision=1, name='Updated donor', email='', address='New address', delivery='print')
        data.update(changes)
        return self.post('donor', **data)

    def test_history_is_immutable_and_retries_do_not_duplicate(self):
        original = self.get('donor', id=self.donor)['donor']
        request = uuid.uuid4().hex
        result = self.edit(request=request)
        self.assertEqual(result, self.edit(request=request))
        history = self.get('donor_history', donor=self.donor)['history']
        self.assertEqual([r['revision'] for r in history], [2, 1])
        self.assertEqual(history[0]['before'], original)
        self.assertEqual(history[0]['after'], self.get('donor', id=self.donor)['donor'])
        self.assertEqual(history[0]['actor'], self.user['name'])
        self.assertTrue(history[0]['at'])
        self.assertIsNone(history[1]['before'])
        for sql in ('DELETE FROM giving_donor_history', 'UPDATE giving_donor_history SET actor=actor'):
            with self.assertRaises(sqlite3.IntegrityError), self.c:
                self.c.execute(sql)

    def test_old_records_preserved_without_inventing_past_history(self):
        legacy = uuid.uuid4().hex
        body = dict(name='Legacy donor', email='', address='Original', delivery='print')
        self.c.execute('INSERT INTO giving_donors VALUES(?,?,?)', (legacy, 7, json.dumps(body)))
        self.c.commit()
        server.giving_init(self.c)
        server.giving_init(self.c)
        self.assertEqual(self.get('donor_history', donor=legacy)['history'], [])
        self.edit(id=legacy, revision=7)
        history = self.get('donor_history', donor=legacy)['history']
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['before'], dict(body, id=legacy, revision=7))

    def test_invalid_or_stale_edits_leave_history_unchanged(self):
        self.edit()
        for revision, status in ((1, 409), (True, 400), (2.0, 400), ('2', 400), (-1, 400)):
            with self.assertRaises(server.Problem) as error:
                self.edit(revision=revision)
            self.assertEqual(error.exception.status, status)
        with self.assertRaises(server.Problem) as error:
            self.edit(id=uuid.uuid4().hex, revision=0)
        self.assertEqual(error.exception.status, 404)
        self.assertEqual(len(self.get('donor_history', donor=self.donor)['history']), 2)

    def test_history_and_profile_roll_back_together(self):
        self.c.execute("CREATE TRIGGER fail_history BEFORE INSERT ON giving_donor_history BEGIN SELECT RAISE(ABORT,'Test failure'); END")
        self.c.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.edit()
        self.assertEqual(self.get('donor', id=self.donor)['donor']['revision'], 1)
        self.assertEqual(len(self.get('donor_history', donor=self.donor)['history']), 1)

    def test_directory_search_paging_and_validation(self):
        self.post('donor', name='Alpha', email='household@example.test', address='Gulfport', delivery='email')
        self.post('donor', name='Beta', email='household@example.test', address='Biloxi', delivery='print')
        results = self.get('donors', search='HOUSEHOLD@EXAMPLE.TEST', limit='1', offset='1')
        self.assertEqual(results['total'], 2)
        self.assertEqual(results['donors'][0]['name'], 'Beta')
        self.assertEqual(self.get('donors', search='gulfport')['donors'][0]['name'], 'Alpha')
        self.assertEqual(self.get('donors', search='%')['total'], 0)
        self.assertEqual(self.get('donors', offset='99')['donors'], [])
        for query in ({'limit':'101'}, {'limit':'0'}, {'offset':'-1'}, {'limit':'1.5'}, {'search':'x'*255}):
            with self.assertRaises(server.Problem):self.get('donors', **query)

    def test_read_and_history_permissions(self):
        self.user = {'name':'Viewer','admin':False,'grants':{'view_giving':True}}
        self.assertEqual(self.get('donors')['total'], 1)
        self.assertEqual(self.get('donor', id=self.donor)['donor']['revision'], 1)
        with self.assertRaises(server.Problem) as error:self.get('donor_history', donor=self.donor)
        self.assertEqual(error.exception.status, 403)
        self.user['grants']['manage_donors'] = True
        self.assertEqual(len(self.get('donor_history', donor=self.donor)['history']), 1)
        self.user['grants']['view_giving'] = False
        for path, query in (('donors',{}), ('donor',{'id':self.donor}), ('donor_history',{'donor':self.donor})):
            with self.assertRaises(server.Problem) as error:self.get(path, **query)
            self.assertEqual(error.exception.status, 403)


if __name__ == '__main__':
    unittest.main()
