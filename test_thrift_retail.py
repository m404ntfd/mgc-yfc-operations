import datetime as dt,json,uuid
from test_retail_workflows import WorkflowTests
import server

class ThriftTests(WorkflowTests):
 def test_intake_one_of_kind_scan_sale_return_and_restock(self):
  self.rules(tags=[dict(name='Blue',color='#2255aa',bps=5000,**{'from':'','to':''},days=list(range(7)),categories=[])])
  item=self.ok('thrift-intake-create',name='Test table',category='Furniture',price=4000,taxable=False,tag='Blue')['item']
  self.assertEqual(self.f.call('pos/thrift-scan?code='+item['code'])[1]['product'],item['product'])
  carts=[self.ok('add',cart=self.cart()['id'],revision=1,product=item['product'],quantity=1)['cart'] for _ in range(2)]
  self.assertEqual(carts[0]['total'],2000)
  self.assertEqual(self.post('add',cart=carts[0]['id'],revision=carts[0]['revision'],product=item['product'],quantity=1)[0],400)
  sale=self.sell(carts[0]);self.assertEqual(self.post('cash',cart=carts[1]['id'],revision=carts[1]['revision'],tender=2000)[0],409)
  self.refund(sale);self.assertEqual(self.f.call('pos/thrift-scan?code='+item['code'])[0],409)
  self.ok('thrift-intake-restock',id=item['id'],reason='Inspected test item');self.assertEqual(self.f.call('pos/thrift-scan?code='+item['code'])[0],200)
 def rules(self,**kw):
  s=self.f.call('pos/thrift-config')[1]['settings'];s.update(kw)
  return self.ok('thrift-settings',**s)['settings']
 def tagged(self,cart):return self.ok('thrift-tag',cart=cart['id'],revision=cart['revision'],index=0,tag='Blue')['cart']
 def customer(self):return self.ok('thrift-customer-save',name='Test Supporter',contact='TEST ONLY',marketing=False)['customer']
 def attach(self,cart,customer):return self.ok('thrift-customer',cart=cart['id'],revision=cart['revision'],customer=customer['id'])['cart']
 def sell(self,cart):return self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=cart['total'])['sale']
 def refund(self,sale,qty=1,revision=0):return self.ok('refund',sale=sale['id'],lines=[{'index':0,'quantity':qty}],reason='Test return',refund_revision=revision,policy_revision=self.f.call('pos/policies')[1]['policy']['revision'],confirmed=True)['refund']
 def test_tag_schedule_snapshot_stacking_and_refund(self):
  self.rules(tags=[dict(name='Blue',color='#2255aa',bps=5000,**{'from':'','to':''},days=list(range(7)),categories=['Retail'])])
  cart=self.tagged(self.add(self.cart(),self.product(price=999)));self.assertEqual((cart['subtotal'],cart['tax']),(499,50))
  self.assertEqual(self.post('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=10,index=0,reason='Stack')[0],400)
  self.rules(tags=[]);sale=self.sell(cart);self.assertEqual(sale['total'],549);self.assertEqual(self.refund(sale)['total'],549)
 def test_donation_roundup_separate_and_retries(self):
  self.rules(donations=True);cart=self.add(self.cart(),self.product(price=1234,taxable=False))
  args=dict(cart=cart['id'],revision=cart['revision'],amount=0,roundup=True,request=uuid.uuid4().hex)
  first=self.f.call('pos/thrift-donation',args);self.assertEqual(first[0],200,first);self.assertEqual(self.f.call('pos/thrift-donation',args),first);cart=first[1]['cart']
  self.assertEqual(cart['total'],1300);self.assertEqual(cart['lines'][1]['subtotal'],66)
  sale=self.sell(cart);self.assertEqual(self.refund(sale)['total'],1234)
  self.assertEqual(self.post('refund-preview',sale=sale['id'],lines=[{'index':1,'quantity':1}],reason='Not merchandise',refund_revision=1,policy_revision=0)[0],400)
  today=dt.date.today().isoformat();r=self.f.call('pos/thrift-reports?from='+today+'&to='+today)[1];self.assertEqual(r['donations'],66)
 def test_loyalty_earn_redeem_concurrent_cart_and_return(self):
  self.rules(loyalty=True,earn_cents=100,reward_points=10,reward_cents=500);customer=self.customer();product=self.product(price=1000,taxable=False)
  sale=self.sell(self.attach(self.add(self.cart(),product),customer))
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test')[1]['customers'][0]['points'],10)
  carts=[]
  for _ in range(2):
   cart=self.attach(self.add(self.cart(),product),customer);carts.append(self.ok('thrift-reward',cart=cart['id'],revision=cart['revision'],redeem=True)['cart'])
  second=self.sell(carts[0]);self.assertEqual(second['total'],500)
  self.assertEqual(self.post('cash',cart=carts[1]['id'],revision=carts[1]['revision'],tender=500)[0],409)
  self.refund(second);self.assertEqual(self.f.call('pos/thrift-customers?search=Test')[1]['customers'][0]['points'],10)
  self.refund(sale);self.assertEqual(self.f.call('pos/thrift-customers?search=Test')[1]['customers'][0]['points'],0)
 def test_voucher_restrictions_ledger_and_original_refund(self):
  a=self.ok('thrift-voucher-issue',name='Test assistance',reason='TEST funding',amount=5000,expires=(dt.date.today()+dt.timedelta(days=30)).isoformat(),categories=['Retail'])['account']
  cart=self.add(self.cart(),self.product(price=1000,taxable=False))
  sale=self.ok('credit',cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=1000,tender=0)['sale'];self.assertEqual(sale['voucher_paid'],1000)
  self.assertEqual(self.refund(sale)['store_credit'],1000);a=self.f.call('pos/account?id='+str(a['id']))[1]['account'];self.assertEqual(a['balance'],5000)
  cart=self.ok('add',cart=self.cart()['id'],revision=1,name='Excluded',category='Other',price=1000,quantity=1,taxable=False)['cart']
  self.assertEqual(self.post('credit',cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=1000,tender=0)[0],400)
  self.assertEqual(self.post('account-adjust',account=a['id'],account_revision=a['revision'],amount=100,direction='add',reason='No bypass')[0],400)
 def test_pickup_conflict_reports_and_record_preservation(self):
  sale=self.sell(self.add(self.cart(),self.product()));today=dt.date.today().isoformat()
  args=dict(sale=sale['id'],revision=0,customer='Test',contact='Sample',location='Bay A',due=today,status='awaiting_pickup',notes='TEST ONLY',dispatch_reference='Existing job reference')
  p=self.ok('thrift-pickup-save',**args)['pickup'];self.assertEqual(self.post('thrift-pickup-save',**args)[0],409)
  self.assertEqual(len(self.f.call('pos/thrift-pickups')[1]['pickups']),1)
  self.ok('thrift-pickup-save',**dict(args,revision=p['revision'],status='collected'));self.assertEqual(self.f.call('pos/thrift-pickups')[1]['pickups'],[])
  with server.connect() as c:
   before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('pos_sales','jobs','users','work_periods','work_breaks','audit')}
   server.thrift_init(c);server.thrift_init(c)
   for t,rows in before.items():self.assertEqual(rows,[tuple(r) for r in c.execute('SELECT * FROM '+t)])
 def test_permissions_and_settings_revision(self):
  s=self.rules(donations=True);self.assertEqual(self.post('thrift-settings',**dict(s,revision=0))[0],409)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));e=self.f.client('thrift-employee');self.f.call('login',dict(name='Employee',password='testpassword'),e)
  self.assertEqual(self.post('thrift-settings',client=e,**s)[0],403)
  self.assertEqual(self.f.call('pos/thrift-pickups',client=e)[0],403)
  self.assertEqual(self.post('thrift-voucher-issue',client=e)[0],403)

if __name__=='__main__':__import__('unittest').main()
