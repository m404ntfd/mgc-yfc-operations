"""Employee advances use isolated databases and exact cents; never live cash/data."""
import datetime as dt,json,sqlite3,unittest,uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from test_update_coordination import CoordinatorFixture
import server

class CashAdvanceTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.device='1'*32
  self.ok('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
  self.terminal=self.ok('terminal-save',name='SAMPLE Front checkout',device=self.device,enabled=True)['id']
  with server.connect() as c:self.people=dict(c.execute('SELECT name,profile_id FROM receipt_profiles'))
 def tearDown(self):self.f.close()
 def post(self,path,client=None,**data):return self.f.call('pos/'+path,dict(request=uuid.uuid4().hex,**data),client)
 def ok(self,path,**data):
  code,r=self.post(path,**data);self.assertEqual(code,200,r);return r
 def setup(self,device=None):
  code,r=self.f.call('pos/cash-advance-setup?device='+(device or self.device));self.assertEqual(code,200,r);return r
 def payload(self,**change):
  ctx=self.setup()['context'];return dict(request=uuid.uuid4().hex,device=self.device,terminal=ctx['terminal'],store_id=ctx['store_id'],drawer_id=ctx['drawer_id'],employee=self.people['Employee'],amount=2500,reason='SAMPLE approved advance',confirmed=True,**change)
 def query(self,kind='cash-advances',**filters):
  today=dt.date.today();return 'retail-reports?'+urlencode(dict(kind=kind,start=str(today)+'T00:00:00',end=str(today+dt.timedelta(days=1))+'T00:00:00',**filters))
 def drawers(self):
  p=self.f.call('pos/programs')[1]['programs'];self.ok('programs-save',**dict(p,drawers=True))
  return self.ok('drawer-open',terminal=self.terminal,opening=10000)['drawer']
 def test_permissions_amounts_employee_and_context(self):
  staff=self.f.client('b');self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  args=self.payload()
  self.assertEqual(self.f.call('pos/cash-advance',args,staff)[0],403)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True,'issue_cash_advances':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('pos/cash-advance',args,staff)[0],403) # Self payment prohibited.
  other=dict(args,employee=self.people['Second']);self.assertEqual(self.f.call('pos/cash-advance',other,staff)[0],200)
  self.assertEqual(self.f.call(self.query(),client=staff)[0],403)
  self.f.call('admin/permissions',dict(name='Employee',grants={'view_cash_advances':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call(self.query(),client=staff)[0],200)
  self.assertEqual(self.f.call(self.query('sales'),client=staff)[0],403)
  for value in [0,-1,True,12.5,'2500',10000001,None]:
   self.assertEqual(self.f.call('pos/cash-advance',dict(args,request=uuid.uuid4().hex,amount=value))[0],400)
  for change in [dict(employee='missing'),dict(reason=''),dict(reason='x'*301),dict(confirmed=False),dict(device={}),dict(device='')]:
   self.assertIn(self.f.call('pos/cash-advance',dict(args,request=uuid.uuid4().hex,**change))[0],[400,409])
  for change in [dict(terminal='wrong'),dict(store_id='binopoly'),dict(drawer_id=99)]:
   self.assertEqual(self.f.call('pos/cash-advance',dict(args,request=uuid.uuid4().hex,**change))[0],409)
  self.assertNotIn(self.people['Admin'],[e['id'] for e in self.setup()['employees']])
 def test_no_drawer_idempotency_reports_and_historical_names(self):
  args=self.payload();first=self.f.call('pos/cash-advance',args);self.assertEqual(first[0],200,first)
  self.assertEqual(self.f.call('pos/cash-advance',args),first)
  self.assertEqual(self.f.call('pos/cash-advance',dict(args,amount=2000))[0],409)
  self.assertEqual(self.f.call('pos/cash-advance-status?request='+args['request'])[1]['advance'],first[1]['advance'])
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_cash_advances').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_drawer_events').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM pos_sales').fetchone()[0],0)
   for sql in ['UPDATE retail_cash_advances SET amount=1','DELETE FROM retail_cash_advances']:
    with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)
  for kind in ['cash','drawer','shift']:
   report=self.f.call(self.query(kind,store_id='thrift-mart'))[1];self.assertEqual(report['rows'][0][2:],['0.00','25.00','-25.00','0.00'])
  report=self.f.call(self.query(store_id='thrift-mart'))[1];self.assertEqual(report['summary'],[['Advances','1'],['Total cash paid out','$25.00']]);self.assertEqual(report['rows'][0][2],'Employee')
  self.assertEqual(self.f.call(self.query(store_id='binopoly'))[1]['rows'],[])
  self.assertEqual(self.f.call(self.query(employee='second'))[1]['rows'],[])
  self.assertEqual(len(self.f.call(self.query(employee='EMPLO'))[1]['rows']),1)
  self.assertEqual(self.f.call(self.query('dashboard'))[1]['net'],0)
  # Rename a user through the supported API: the saved payment retains their name and identity.
  r=self.f.call('admin/user-identity',dict(name='Employee',username='Renamed',first='Sample',middle='',last='Employee'));self.assertEqual(r[0],200,r)
  saved=self.f.call(self.query())[1]['rows'][0];self.assertEqual(saved[2],'Employee')
  with server.connect() as c:self.assertEqual(c.execute('SELECT employee FROM retail_cash_advances').fetchone()[0],self.people['Employee'])
 def test_tracked_drawer_cash_math_close_and_concurrency(self):
  drawer=self.drawers();args=self.payload();self.assertEqual(self.f.call('pos/cash-advance',args)[0],200)
  d=self.f.call('pos/drawers')[1]['drawers'][0];self.assertEqual((d['advances'],d['movements'],d['expected']),(2500,-2500,7500))
  # Only one competing $50 advance fits the remaining $75.
  requests=[dict(args,request=uuid.uuid4().hex,amount=5000) for _ in range(2)]
  with ThreadPoolExecutor(2) as pool:codes=sorted(pool.map(lambda x:self.f.call('pos/cash-advance',x)[0],requests))
  self.assertEqual(codes,[200,409])
  d=self.f.call('pos/drawers')[1]['drawers'][0];self.assertEqual((d['advances'],d['expected']),(7500,2500))
  report=self.f.call(self.query('cash-reconciliation'))[1];self.assertEqual(report['rows'][0][6:8],['75.00','25.00'])
  closed=self.ok('drawer-close',id=d['id'],expected=2500,counted=2500,reason='SAMPLE count')['drawer'];self.assertEqual(closed['variance'],0)
  self.assertEqual(self.f.call('pos/cash-advance',dict(args,request=uuid.uuid4().hex))[0],409)
  self.assertEqual(self.f.call('pos/drawers')[1]['drawers'][0]['advances'],7500)
  self.ok('drawer-open',terminal=self.terminal,opening=1000)
  self.assertEqual(self.f.call('pos/cash-advance',dict(args,request=uuid.uuid4().hex))[0],409) # Stale session cannot post to a new drawer.
 def test_store_assignment_and_optional_program_changes(self):
  args=self.payload();self.ok('store-terminal',terminal=self.terminal,store_id='binopoly',previous='thrift-mart')
  self.assertEqual(self.f.call('pos/cash-advance',args)[0],409)
  args=self.payload();self.assertEqual(args['store_id'],'binopoly');self.assertEqual(self.f.call('pos/cash-advance',args)[0],200)
  self.assertEqual(len(self.f.call(self.query(store_id='binopoly'))[1]['rows']),1)
  self.assertEqual(self.f.call(self.query(store_id='thrift-mart'))[1]['rows'],[])
  p=self.f.call('pos/programs')[1]['programs'];self.ok('programs-save',**dict(p,drawers=True))
  self.assertEqual(self.f.call('pos/cash-advance',dict(self.payload(),request=uuid.uuid4().hex))[0],409)
 def test_repeat_migration_preserves_all_records(self):
  with server.connect() as c:
   person=self.people['Employee'];c.execute('INSERT INTO work_periods VALUES(11,?,100,NULL,?,NULL)',(person,'Office'));c.execute('INSERT INTO work_breaks VALUES(21,11,200,NULL)')
   c.execute('INSERT INTO jobs VALUES(?,?,?)',('sample',7,json.dumps({'customer':'SAMPLE reservation','notes':'Keep'})));c.execute('INSERT INTO photos VALUES(?,?,?)',('sample',0,b'sample attachment'))
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('audit','pos_operations','retail_cash_advances','retail_drawer_events')")]
   before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
  self.assertEqual(self.f.call('pos/cash-advance',self.payload())[0],200)
  with server.connect() as c:
   server.stores_init(c);server.stores_init(c)
   self.assertEqual(before,{t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables})
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')

if __name__=='__main__':unittest.main()
