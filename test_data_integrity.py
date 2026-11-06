"""Existing timecards and reservations must survive additive scheduling upgrades."""
import json
import sqlite3
import unittest

import server


class DataIntegrityTests(unittest.TestCase):
    def test_job_catalogue_migration_preserves_operational_records(self):
        connection=sqlite3.connect(':memory:')
        self.addCleanup(connection.close)
        connection.row_factory=sqlite3.Row
        server.init_workforce(connection)
        # v0.38.5 has the same workforce tables, without the new job catalogue.
        connection.execute('DROP TABLE work_job_definitions')
        connection.execute('DROP TABLE work_shift_save_receipts')
        connection.executescript('''
            CREATE TABLE jobs(id TEXT PRIMARY KEY, revision INTEGER, body TEXT);
            CREATE TABLE photos(job TEXT, position INTEGER, body BLOB, PRIMARY KEY(job,position));
            CREATE TABLE users(name TEXT PRIMARY KEY, admin INTEGER);
            CREATE TABLE receipt_profiles(name TEXT PRIMARY KEY,profile_id TEXT UNIQUE);
            INSERT INTO users VALUES('Existing employee',0);
            INSERT INTO receipt_profiles VALUES('Existing employee','employee-unchanged');
            INSERT INTO work_periods VALUES(11,'employee-unchanged',100,1000,'Site A','Site A');
            INSERT INTO work_periods VALUES(12,'employee-unchanged',1200,NULL,'Site A',NULL);
            INSERT INTO work_breaks VALUES(21,11,200,300);
            INSERT INTO work_breaks VALUES(22,12,1300,NULL);
            INSERT INTO work_shifts(id,account,start,end,location,notes,revision,job)
                VALUES(31,'employee-unchanged',100,1000,'Site A','Keep these notes',7,'Driver');
            INSERT INTO work_time_card_audit VALUES(41,11,'Existing employee','Manager',
                '2026-11-01T10:30:00-06:00','Original correction','{"start":90}','{"start":100}');
            INSERT INTO work_requests VALUES(51,'employee-unchanged','time-off',
                '{"start":"2026-12-01","end":"2026-12-01"}','Original request',
                'approved','2026-12-01','2026-12-01','Manager','2026-11-01T10:00:00');
        ''')
        assignment=dict(jobs=['Driver','Host'],sites=[],primary_job='Driver',primary_site=None,require_location=False)
        connection.execute('INSERT INTO work_assignments VALUES(?,?)',('employee-unchanged',json.dumps(assignment)))
        for kind in ('Pickup','Delivery'):
            reservation=dict(type=kind,customer='Test reservation',start='2026-11-15T09:00',
                             end='2026-11-15T10:00',status='Scheduled',notes='Preserve exact data')
            connection.execute('INSERT INTO jobs VALUES(?,?,?)',(kind,8,json.dumps(reservation)))
            connection.execute('INSERT INTO photos VALUES(?,?,?)',(kind,0,b'fixture-photo-bytes'))
        connection.commit()
        tables=[row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        def snapshot():
            return {name:[tuple(row) for row in connection.execute('SELECT * FROM "'+name+'" ORDER BY rowid')]
                    for name in tables}
        before=snapshot()
        hours=server.work_hours(connection,'employee-unchanged',(0,2000),1500)
        for _ in range(2):
            server.init_workforce(connection)
            self.assertEqual(snapshot(),before)
            self.assertEqual(server.work_hours(connection,'employee-unchanged',(0,2000),1500),hours)
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual({row[0] for row in connection.execute('SELECT name FROM work_job_definitions')},{'Driver','Host'})
        for sql in ('UPDATE work_time_card_audit SET reason="changed" WHERE id=41',
                    'DELETE FROM work_time_card_audit WHERE id=41'):
            with self.assertRaises(sqlite3.IntegrityError): connection.execute(sql)


if __name__=='__main__': unittest.main()
