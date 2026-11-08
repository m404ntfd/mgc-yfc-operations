import unittest,json,datetime as dt,time,uuid
from unittest.mock import patch
from test_update_coordination import CoordinatorFixture
import server

class ExpansionTests(unittest.TestCase):
 def setUp(self):self.f=CoordinatorFixture()
 def tearDown(self):self.f.close()
 def post(self,path,**data):
  code,r=self.f.call(path,dict(request=uuid.uuid4().hex,**data));self.assertEqual(code,200,r);return r
 def query(self,kind):
  today=dt.date.today();return 'retail-reports?kind='+kind+'&start='+str(today)+'T00:00:00&end='+str(today+dt.timedelta(days=1))+'T00:00:00'
 def test_reports_totals_readonly_and_permissions(self):
  self.post('pos/settings',store='CoastYouth Retail',tax_bps=700,confirmed=True)
  self.post('pos/product',name='Shirt',category='Apparel',price=1200,taxable=True)
  cart=self.post('pos/new')['cart'];cart=self.post('pos/add',cart=cart['id'],revision=cart['revision'],name='Shirt',category='Apparel',price=1200,quantity=2,taxable=True)['cart']
  sale=self.post('pos/cash',cart=cart['id'],revision=cart['revision'],tender=3000)['sale']
  with server.connect() as c:
   tables=['jobs','work_periods','work_breaks','pos_sales','pos_products','users'];before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
  for kind in ('dashboard','sales','transactions','cash','drawer','employee-time','products','modifiers','products-hour','seven-day','pricing','hierarchy','tax-assignment','tax-audit','accounts','adjustments','journal','tabs','reservations','labor','time-entries','schedule'):
   code,data=self.f.call(self.query(kind));self.assertEqual(code,200,(kind,data))
   if kind=='dashboard':self.assertEqual(data['net'],2400);self.assertEqual(data['gross'],2400);self.assertEqual(data['items']['Shirt'],2400)
  with server.connect() as c:self.assertEqual(before,{t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables})
  other=self.f.client('report-restricted');self.f.call('login',dict(name='Employee',password='testpassword'),other)
  self.assertEqual(self.f.call(self.query('dashboard'),client=other)[0],403)
  self.assertEqual(self.f.call(self.query('labor'),client=other)[0],403)
 def test_pin_logout_and_lockout(self):
  self.post('admin/clock-pin',name='Employee',pin='654321');other=self.f.client('pin')
  self.assertEqual(self.f.call('pos-pin-login',{'pin':'654321'},other)[0],200)
  self.assertEqual(self.f.call('session',client=other)[1]['user']['name'],'Employee')
  self.f.call('logout',{},other);self.assertIsNone(self.f.call('session',client=other)[1]['user'])
  for _ in range(8):self.assertEqual(self.f.call('pos-pin-login',{'pin':'111111'},other)[0],403)
  self.assertEqual(self.f.call('pos-pin-login',{'pin':'654321'},other)[0],429)
 def test_idle_list_and_shared_profile(self):
  other=self.f.client('idle');self.f.call('login',dict(name='Employee',password='testpassword'),other)
  for s in server.SESSIONS.values():
   if s['name']=='Employee':
    for c in s['connections'].values():c['last_active']=time.time()-901
  data=self.f.call('admin/update-connections')[1];self.assertFalse(any(r['name']=='Employee' for r in data['connections']))
  r=self.post('admin/office-user-details',name='Employee',revision=0,email='sample@example.test',city='Mobile')
  self.assertEqual(r['city'],'Mobile');self.assertEqual(self.f.call('admin/office-user-details?name=Employee')[1]['city'],'Mobile')
  self.assertEqual(self.f.call('admin/office-user-details',dict(name='Employee',revision=0))[0],409)
 def test_office_update_separate_and_force_restricted(self):
  server.OFFICE_UPDATE_RELEASE={'checking':False,'version':'1.4.0','checked':time.time()}
  self.post('office-update/start',target='all',mode='notify')
  self.assertIsNotNone(self.f.call('office-update/state')[1]['campaign'])
  self.assertIsNone(self.f.call('pos-update/state')[1]['campaign'])
  self.post('office-update/cancel')
  self.assertEqual(self.f.call('office-update/start',dict(target='all',mode='force'))[0],403)

if __name__=='__main__':unittest.main()
