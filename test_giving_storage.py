"""Giving persistence and authorization tests without network access."""
import json
import sqlite3
import unittest
import uuid
import server


class GivingStorageTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
        self.addCleanup(self.c.close)
        self.c.execute('CREATE TABLE audit(at TEXT,actor TEXT,action TEXT,detail TEXT)')
        server.giving_init(self.c)
        self.user={'name':'Test administrator','admin':True}
        self.donor=self.post('donor',name='Original donor',email='',address='Original address',delivery='print')['id']

    def post(self,path,**data):
        with self.c:
            return server.giving_post(self.c,self.user,path,{'request':uuid.uuid4().hex,**data})

    def get(self,path,**query):
        return server.giving_get(self.c,self.user,path,{key:[value] for key,value in query.items()})

    def test_frozen_snapshot_retry_and_history(self):
        gift=self.post('gift',donor=self.donor,day='2025-12-15',amount=10000,method='check',reference='Test 1',fund='Ministry',benefit='',benefit_value=0)
        request=uuid.uuid4().hex
        saved=self.post('statement_snapshot',donor=self.donor,period='2025',request=request)
        self.assertEqual(saved,self.post('statement_snapshot',donor=self.donor,period='2025',request=request))
        original=self.get('statement_snapshot',id=saved['id'])
        self.post('donor',id=self.donor,revision=1,name='Changed donor',email='',address='Changed address',delivery='print')
        self.post('settings',revision=0,organization='Changed organization',ein='',address='',monthly_message='Changed',annual_message='Changed')
        self.post('void',gift=gift['id'],reason='Correcting original entry')
        self.assertEqual(original,self.get('statement_snapshot',id=saved['id']))
        self.assertEqual(original['total'],10000)
        self.assertEqual(original['donor']['name'],'Original donor')
        self.assertEqual(original['delivery'],'not_sent')
        self.assertEqual(self.get('statement',donor=self.donor,period='2025')['total'],0)
        self.assertEqual(len(self.get('statement_history',donor=self.donor)['statements']),1)
        for sql in ('DELETE FROM giving_statements','UPDATE giving_statements SET period=period'):
            with self.assertRaises(sqlite3.IntegrityError),self.c:self.c.execute(sql)

    def test_correction_details_preserve_original_entry(self):
        gift=self.post('gift',donor=self.donor,day='2025-12-15',amount=10000,method='check',reference='Test 1',fund='Ministry',benefit='',benefit_value=0)
        original=self.get('overview')['gifts'][0]
        self.assertIsNone(original['correction'])
        self.post('void',gift=gift['id'],reason='Duplicate deposit entry')
        self.user={'name':'Viewer','admin':False,'grants':{'view_giving':True}}
        corrected=self.get('overview')['gifts'][0]
        self.assertTrue(corrected['voided'])
        self.assertEqual(corrected['correction']['reason'],'Duplicate deposit entry')
        self.assertEqual(corrected['correction']['actor'],'Test administrator')
        self.assertTrue(corrected['correction']['at'])
        for key in ('id','donor','amount','day','reference','actor','at'):
            self.assertEqual(corrected[key],original[key])
        self.user['grants']={}
        with self.assertRaises(server.Problem) as problem:self.get('overview')
        self.assertEqual(problem.exception.status,403)

    def test_permissions_validation_and_rollback(self):
        self.user={'name':'Viewer','admin':False,'grants':{'view_giving':True}}
        for path in ('statement_snapshot','statement_history'):
            with self.assertRaises(server.Problem) as problem:self.get(path,donor=self.donor,id='missing')
            self.assertEqual(problem.exception.status,403)
        with self.assertRaises(server.Problem) as problem:self.post('statement_snapshot',donor=self.donor,period='2025')
        self.assertEqual(problem.exception.status,403)
        self.user['grants']['giving_statements']=True
        for period in ('2025-13','0000','9999','2025-1','invalid'):
            with self.assertRaises(server.Problem):self.post('statement_snapshot',donor=self.donor,period=period)
        self.assertEqual(self.get('statement_history',donor=self.donor)['statements'],[])
        request=uuid.uuid4().hex
        self.post('statement_snapshot',donor=self.donor,period='2025-12',request=request)
        with self.assertRaises(server.Problem) as problem:self.post('statement_snapshot',donor=self.donor,period='2026',request=request)
        self.assertEqual(problem.exception.status,409)
        self.assertEqual(len(self.get('statement_history',donor=self.donor)['statements']),1)

    def test_additive_migration_preserves_populated_operational_tables(self):
        server.init_workforce(self.c)
        self.c.executescript('''
          CREATE TABLE jobs(id TEXT PRIMARY KEY,revision INTEGER,body TEXT);
          CREATE TABLE photos(job TEXT,position INTEGER,body BLOB);
          INSERT INTO work_periods VALUES(11,'existing',100,NULL,'Office',NULL);
          INSERT INTO work_breaks VALUES(21,11,200,NULL);
          INSERT INTO jobs VALUES('reservation',7,'{"status":"Scheduled"}');
          INSERT INTO photos VALUES('reservation',0,X'010203');
        ''')
        tables=[r[0] for r in self.c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before={t:list(map(tuple,self.c.execute('SELECT * FROM "'+t+'"'))) for t in tables}
        server.giving_init(self.c);server.giving_init(self.c)
        self.assertEqual(before,{t:list(map(tuple,self.c.execute('SELECT * FROM "'+t+'"'))) for t in tables})


if __name__=='__main__':unittest.main()
