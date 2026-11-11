"""Giving endpoints against an isolated database; never calls a payment provider."""
import unittest, uuid, sqlite3
import server
from test_update_coordination import CoordinatorFixture

class GivingTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture()
  self.d=self.post('donor',name='Sample Donor',email='',address='Test address',delivery='print',revision=0)[1]['id']
 def tearDown(self):self.f.close()
 def post(self,path,**data):return self.f.call('giving/'+path,{'request':uuid.uuid4().hex,**data})
 def gift(self,**extra):
  data=dict(donor=self.d,day='2025-12-15',amount=5000,method='check',reference='Sample check',fund='Ministry',benefit='',benefit_value=0);data.update(extra)
  return self.post('gift',**data)
 def test_ledger_idempotency_void_and_statement_boundaries(self):
  request=uuid.uuid4().hex
  code,g=self.gift(request=request);self.assertEqual(code,200)
  self.assertEqual(self.gift(request=request)[1],g)
  self.assertEqual(self.gift(request=request,amount=6000)[0],409)
  self.gift(day='2026-01-01',amount=2000)
  statement=lambda period:self.f.call('giving/statement?donor='+self.d+'&period='+period)[1]
  self.assertEqual(statement('2025')['total'],5000)
  self.assertEqual(statement('2026-01')['total'],2000)
  self.assertEqual(statement('2026-02')['ytd'],2000)
  self.assertEqual(self.post('void',gift=g['id'],reason='Wrong entry')[0],200)
  self.assertEqual(statement('2025')['total'],0)
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM giving_gifts').fetchone()[0],2)
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM giving_gifts')
 def test_replace_gift_is_atomic_and_preserves_saved_statements(self):
  original=self.gift()[1]['id']
  saved=self.post('statement_snapshot',donor=self.d,period='2025')[1]['id']
  request=uuid.uuid4().hex
  data=dict(gift=original,reason='Wrong amount',donor=self.d,day='2025-12-15',amount=6000,
            method='check',reference='Sample check',fund='Ministry',benefit='',benefit_value=0)
  ledger=lambda:{g['id']:g for g in self.f.call('giving/overview')[1]['gifts']}
  self.assertEqual(self.post('replace_gift',**dict(data,amount=0))[0],400)
  self.assertEqual(self.post('replace_gift',**dict(data,reason=''))[0],400)
  self.assertFalse(ledger()[original]['voided'])
  employee=self.f.client('e')
  self.f.call('login',dict(name='Employee',password='testpassword'),employee)
  for grant in ('adjust_gifts','record_gifts'):
   self.f.call('admin/permissions',dict(name='Employee',grants={'view_giving':True,grant:True},can_create=False,see_requests=False))
   self.assertEqual(self.f.call('giving/replace_gift',dict(data,request=request),employee)[0],403)
  code,replacement=self.post('replace_gift',request=request,**data)
  self.assertEqual(code,200)
  self.assertEqual(self.post('replace_gift',request=request,**data)[1],replacement)
  self.assertEqual(self.post('replace_gift',**data)[0],409)
  self.assertEqual(self.post('void',gift=original,reason='Already corrected')[0],409)
  gifts=ledger()
  self.assertEqual(len(gifts),2)
  self.assertEqual(gifts[original]['amount'],5000)
  self.assertEqual(gifts[original]['replacement'],replacement['id'])
  self.assertEqual(gifts[original]['correction']['reason'],'Wrong amount')
  self.assertEqual(gifts[replacement['id']]['replaces'],original)
  self.assertEqual(self.f.call('giving/statement?donor='+self.d+'&period=2025-12')[1]['total'],6000)
  self.assertEqual(self.f.call('giving/statement_snapshot?id='+saved)[1]['total'],5000)
  with server.connect() as c:
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM giving_gift_replacements')

 def test_permissions_and_validation(self):
  e=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),e)
  self.assertEqual(self.f.call('giving/overview',client=e)[0],403)
  self.f.call('admin/permissions',dict(name='Employee',grants={'view_giving':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('giving/overview',client=e)[0],200)
  self.assertIsNone(self.f.call('giving/overview',client=e)[1]['settings'])
  self.assertEqual(self.f.call('giving/donor',dict(request=uuid.uuid4().hex,name='Denied'),e)[0],403)
  self.assertEqual(self.f.call('giving/statement?donor='+self.d+'&period=2025',client=e)[0],403)
  for value in [True,0,-1,1.2,'100']:
   self.assertEqual(self.gift(amount=value)[0],400)
  self.assertEqual(self.gift(day='2025-02-30')[0],400)
  self.assertEqual(self.gift(card_number='not allowed')[0],400)
 def test_drafts_concurrency_and_repeat_migration(self):
  plan=dict(donor=self.d,amount=2500,start='2026-12-01',billing_day=1,fund='Ministry',status='active')
  self.assertEqual(self.post('plan',**plan)[0],400)
  plan['status']='draft';self.assertEqual(self.post('plan',**plan)[0],200)
  donor=dict(id=self.d,revision=1,name='Updated',email='',address='',delivery='print')
  self.assertEqual(self.post('donor',**donor)[0],200)
  self.assertEqual(self.post('donor',**donor)[0],409)
  with server.connect() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if not r[0].startswith('giving_')]
   before={t:list(map(tuple,c.execute('SELECT * FROM "'+t+'"'))) for t in tables}
   server.giving_init(c);server.giving_init(c)
   self.assertEqual(before,{t:list(map(tuple,c.execute('SELECT * FROM "'+t+'"'))) for t in tables})

 def test_monthly_commitment_history(self):
  draft = dict(donor=self.d, amount=2500, start='2026-12-01',
               billing_day=1, fund='Ministry', status='draft')
  code, result = self.post('plan', **draft)
  self.assertEqual(code, 200)
  plan = result['id']
  history_path = 'giving/plan_history?id=' + plan
  edit = dict(draft, id=plan, revision=1, amount=4000, status='cancelled')
  request = uuid.uuid4().hex
  self.assertEqual(self.post('plan', request=request, **edit), (200, result))
  self.assertEqual(self.post('plan', request=request, **edit), (200, result))
  self.assertEqual(self.post('plan', **edit)[0], 409)
  self.assertEqual(self.post('plan', **dict(edit, revision=True))[0], 400)
  self.assertEqual(self.post('plan', **dict(edit, id=uuid.uuid4().hex, revision=0))[0], 404)
  self.assertEqual(self.post('plan', **dict(edit, revision=2, status='active'))[0], 400)
  history = self.f.call(history_path)[1]['history']
  self.assertEqual([row['revision'] for row in history], [2, 1])
  self.assertEqual(history[0]['before'], history[1]['after'])
  self.assertEqual(history[0]['after']['status'], 'cancelled')
  self.assertEqual(history[0]['after']['amount'], 4000)
  self.assertEqual(history[0]['actor'], 'Admin')
  self.assertTrue(history[0]['at'])
  self.assertIsNone(history[1]['before'])
  employee = self.f.client('e')
  self.f.call('login', dict(name='Employee', password='testpassword'), employee)
  self.f.call('admin/permissions', dict(name='Employee', grants={'view_giving': True},
                                      can_create=False, see_requests=False))
  self.assertEqual(self.f.call(history_path, client=employee)[0], 403)
  with server.connect() as c:
   for sql in ('DELETE FROM giving_plan_history', 'UPDATE giving_plan_history SET actor=actor'):
    with self.assertRaises(sqlite3.IntegrityError), c:
     c.execute(sql)

 def test_saved_statement_is_frozen_and_retry_is_idempotent(self):
  gift=self.gift()[1]['id'];request=uuid.uuid4().hex
  code,saved=self.post('statement_snapshot',donor=self.d,period='2025',request=request)
  self.assertEqual(code,200)
  self.assertEqual(self.post('statement_snapshot',donor=self.d,period='2025',request=request)[1],saved)
  self.assertEqual(self.post('statement_snapshot',donor=self.d,period='2026',request=request)[0],409)
  read=lambda:self.f.call('giving/statement_snapshot?id='+saved['id'])[1]
  original=read();self.assertEqual(original['total'],5000);self.assertEqual(original['delivery'],'not_sent')
  self.post('donor',id=self.d,revision=1,name='Changed name',email='',address='Changed address',delivery='print')
  self.post('settings',revision=0,organization='Changed organization',ein='',address='',monthly_message='Changed monthly',annual_message='Changed annual')
  self.post('void',gift=gift,reason='Correction after saving')
  self.assertEqual(read(),original)
  self.assertEqual(self.f.call('giving/statement?donor='+self.d+'&period=2025')[1]['total'],0)
  history=self.f.call('giving/statement_history?donor='+self.d)[1]['statements']
  self.assertEqual(len(history),1);self.assertEqual(history[0]['id'],saved['id'])
  self.assertEqual(self.post('statement_snapshot',donor=self.d,period='2025-13')[0],400)
  self.assertEqual(self.f.call('giving/statement_snapshot?id=missing')[0],404)
  with server.connect() as c:
   server.giving_init(c)
   for sql in ('DELETE FROM giving_statements','UPDATE giving_statements SET period=period'):
    with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)

 def test_saved_statement_permissions(self):
  e=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),e)
  self.f.call('admin/permissions',dict(name='Employee',grants={'view_giving':True},can_create=False,see_requests=False))
  for path in ('giving/statement_history?donor='+self.d,'giving/statement_snapshot?id=missing'):
   self.assertEqual(self.f.call(path,client=e)[0],403)
  payload=dict(request=uuid.uuid4().hex,donor=self.d,period='2025')
  self.assertEqual(self.f.call('giving/statement_snapshot',payload,e)[0],403)
  self.f.call('admin/permissions',dict(name='Employee',grants={'view_giving':True,'giving_statements':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('giving/statement_snapshot',payload,e)[0],200)

if __name__=='__main__':unittest.main()
