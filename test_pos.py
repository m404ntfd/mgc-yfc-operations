import json
import unittest
import server
from test_update_coordination import CoordinatorFixture

class PosTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.counter=0
 def tearDown(self):self.f.close()
 def post(self,path,**body):
  self.counter+=1;body.setdefault('request',f'{self.counter:032x}')
  return self.f.call('pos/'+path,body)
 def configured(self):
  self.assertEqual(self.post('settings',store='Test store',tax_bps=725,confirmed=True)[0],200)
  return self.post('new')[1]['cart']
 def add(self,cart,**extra):
  return self.post('add',cart=cart['id'],revision=cart['revision'],name='Test item',category='General',price=1001,quantity=2,taxable=True,**extra)
 def test_cash_totals_retry_and_immutable_receipt(self):
  self.assertEqual(self.post('new')[0],409)
  cart=self.configured();cart=self.add(cart)[1]['cart']
  self.assertEqual((cart['subtotal'],cart['tax'],cart['total']),(2002,145,2147))
  self.assertEqual(self.post('cash',cart=cart['id'],revision=cart['revision'],tender=2000)[0],400)
  request='f'*32;args=dict(cart=cart['id'],revision=cart['revision'],tender=3000,request=request)
  code,result=self.post('cash',**args);self.assertEqual(code,200);self.assertEqual(result['sale']['change'],853)
  self.assertEqual(self.post('cash',**args),(code,result))
  args['request']='e'*32;self.assertEqual(self.post('cash',**args)[0],409)
  self.post('settings',store='Changed store',tax_bps=1000,confirmed=True)
  sales=self.f.call('pos/sales')[1]['sales'];self.assertEqual(len(sales),1)
  self.assertEqual(sales[0]['settings']['store'],'Test store')
 def test_revision_product_snapshot_and_changed_request(self):
  cart=self.configured();product=self.post('product',name='Shirt',category='Clothing',price=399,taxable=False)[1]['product']
  args=dict(cart=cart['id'],revision=cart['revision'],product=product['id'],quantity=3,request='d'*32)
  saved=self.post('add',**args)[1]['cart'];self.assertEqual(saved['total'],1197)
  self.assertEqual(self.post('add',**args)[1]['cart'],saved)
  args['quantity']=4;self.assertEqual(self.post('add',**args)[0],409)
  self.assertEqual(self.add(cart)[0],409)
  self.assertEqual(self.post('card',cart=saved['id'],revision=saved['revision'])[0],400)
 def test_permission_and_ownership(self):
  cart=self.configured();employee=self.f.client('b');self.f.call('login',dict(name='Employee',password='testpassword'),employee)
  self.assertEqual(self.f.call('pos/overview',client=employee)[0],403)
  # Use the existing permissions API, not direct role overrides.
  code,_=self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  self.assertEqual(code,200)
  self.assertEqual(self.f.call('pos/overview',client=employee)[0],200)
  self.assertEqual(self.f.call('pos/settings',dict(request='a'*32,store='X',tax_bps=0,confirmed=True),employee)[0],403)
  self.assertEqual(self.f.call('pos/discard',dict(request='b'*32,cart=cart['id'],revision=1),employee)[0],404)
 def test_additive_migration_and_cash_leave_operational_data_intact(self):
  with server.connect() as c:
   c.execute("INSERT INTO jobs VALUES('reservation-1',9,?)",(json.dumps({'customer':'Test','notes':'Keep'}),))
   c.execute("INSERT INTO photos VALUES('reservation-1',0,?)",(b'test-photo',))
   account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute("INSERT INTO work_periods VALUES(11,?,100,NULL,'Office',NULL)",(account,))
   c.execute('INSERT INTO work_breaks VALUES(21,11,200,NULL)')
  def snapshot():
   with server.connect() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('jobs','photos','work_periods','work_breaks','work_time_card_audit','work_shifts')}
  before=snapshot();server.init();server.init();self.assertEqual(snapshot(),before)
  cart=self.add(self.configured())[1]['cart'];self.post('cash',cart=cart['id'],revision=cart['revision'],tender=3000)
  self.assertEqual(snapshot(),before)
  with server.connect() as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')

if __name__=='__main__':unittest.main()
