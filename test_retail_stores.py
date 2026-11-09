import datetime as dt,json,uuid
from test_thrift_retail import ThriftTests
import server

class StoreTests(ThriftTests):
 def programs(self,**kwargs):
  p=self.f.call('pos/programs')[1]['programs'];p.update(kwargs)
  return self.ok('programs-save',**p)['programs']
 def binopoly(self):
  s=self.f.call('pos/stores')[1]['stores'][1]
  self.ok('store-save',**dict(s,tax_bps=1000,confirmed=True,receipt=dict(address='TEST Binopoly address',phone='',logo='',policy='TEST policy',footer='TEST Binopoly footer')))
 def test_weight_store_separation_receipt_and_refund(self):
  self.binopoly();p=self.product('Weighed goods',price=200,rules=dict(store_id='binopoly',sold_by_weight=True))
  self.assertEqual(self.f.call('pos/overview')[1]['products'],[])
  self.assertEqual(len(self.f.call('pos/overview?store_id=binopoly')[1]['products']),1)
  cart=self.cart(store_id='binopoly')
  for value in [0,True,1.25,'0','-1','NaN','1.0001','1e2','10000']:
   self.assertEqual(self.post('add',cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1,weight=value)[0],400)
  cart=self.add(cart,p,weight='3.25');self.assertEqual((cart['subtotal'],cart['tax']),(650,65))
  sale=self.sell(cart);self.assertEqual(sale['settings']['store'],'Binopoly');self.assertEqual(sale['lines'][0]['weight_milli'],3250)
  self.assertEqual(sale['receipt_design']['footer'],'TEST Binopoly footer')
  self.assertEqual(self.post('add',cart=self.cart()['id'],revision=1,product=p['id'],quantity=1,weight='1')[0],400)
  r=self.refund(sale);self.assertEqual(r['total'],715)
  today=dt.date.today();query='start='+today.isoformat()+'T00:00:00&end='+(today+dt.timedelta(days=1)).isoformat()+'T00:00:00'
  self.assertEqual(self.f.call('retail-reports?kind=dashboard&store_id=thrift-mart&'+query)[1]['transactions'],0)
  self.assertEqual(self.f.call('retail-reports?kind=dashboard&store_id=binopoly&'+query)[1]['transactions'],1)
 def test_program_defaults_and_gift_lifecycle(self):
  p=self.f.call('pos/programs')[1]['programs'];self.assertFalse(any(p[k] for k in ('drawers','gifts','membership','birthdays')))
  cart=self.cart();self.assertEqual(self.post('gift-add',cart=cart['id'],revision=cart['revision'],amount=2500)[0],400)
  self.programs(gifts=True);cart=self.ok('gift-add',cart=cart['id'],revision=cart['revision'],amount=2500)['cart']
  self.assertEqual(self.f.call('pos/gifts')[1]['gifts'],[])
  args=dict(cart=cart['id'],revision=cart['revision'],tender=2500,request=uuid.uuid4().hex)
  first=self.f.call('pos/cash',args);self.assertEqual(first[0],200,first);self.assertEqual(self.f.call('pos/cash',args),first)
  gifts=self.f.call('pos/gifts')[1]['gifts'];self.assertEqual(len(gifts),1);g=gifts[0]
  self.assertEqual(g['balance'],2500)
  self.assertEqual(self.post('account-adjust',account=g['account'],amount=1,direction='add',reason='No')[0],400)
  self.programs(gifts=False)
  account=self.f.call('pos/account?id='+str(g['account']))[1]['account'];cart=self.add(self.cart(),self.product(price=1000,taxable=False))
  sale=self.ok('credit',cart=cart['id'],revision=cart['revision'],account=account['id'],account_revision=account['revision'],amount=1000,tender=0)['sale']
  self.assertEqual(self.f.call('pos/gifts')[1]['gifts'][0]['balance'],1500)
  self.refund(sale);self.assertEqual(self.f.call('pos/gifts')[1]['gifts'][0]['balance'],2500)
 def test_loyalty_scope_and_birthday_race(self):
  self.binopoly();self.rules(loyalty=True,earn_cents=100,reward_points=10,reward_cents=500)
  customer=self.customer();self.sell(self.attach(self.add(self.cart(),self.product(price=1000,taxable=False)),customer))
  p=self.product(price=2000,taxable=False,rules=dict(store_id='binopoly'))
  self.sell(self.attach(self.add(self.cart(store_id='binopoly'),p),customer))
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test&store_id=binopoly')[1]['customers'][0]['points'],30)
  self.programs(loyalty_scope='store',membership=True,birthdays=True)
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test&store_id=binopoly')[1]['customers'][0]['points'],20)
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test')[1]['customers'][0]['points'],10)
  self.ok('member-save',customer=customer['id'],card='123456789012',birthday=dt.date.today().strftime('%m-%d'),previous=None)
  self.assertEqual(self.f.call('pos/membership-scan?code=123456789012')[1]['customer']['id'],customer['id'])
  carts=[]
  for _ in range(2):
   cart=self.attach(self.add(self.cart(store_id='binopoly'),p),customer)
   carts.append(self.ok('birthday-reward',cart=cart['id'],revision=cart['revision'])['cart'])
  self.sell(carts[0]);self.assertEqual(self.post('cash',cart=carts[1]['id'],revision=carts[1]['revision'],tender=carts[1]['total'])[0],409)
 def test_drawer_cash_refund_and_close(self):
  terminal=self.ok('terminal-save',name='Test register',device='1'*32,enabled=True)['id'];self.programs(drawers=True)
  p=self.product(price=1000,taxable=False);cart=self.add(self.cart(device='1'*32),p)
  self.assertEqual(self.post('cash',cart=cart['id'],revision=cart['revision'],tender=1000)[0],400)
  drawer=self.ok('drawer-open',terminal=terminal,opening=5000)['drawer'];sale=self.sell(cart)
  drawer=self.ok('drawer-move',id=drawer['id'],amount=500,direction='out',reason='TEST safe drop')['drawer'];self.assertEqual(drawer['expected'],5500)
  self.refund(sale);drawer=self.f.call('pos/drawers')[1]['drawers'][0];self.assertEqual(drawer['expected'],4500)
  closed=self.ok('drawer-close',id=drawer['id'],counted=4495,expected=4500,reason='TEST short count')['drawer'];self.assertEqual(closed['variance'],-5)
  self.assertEqual(self.post('drawer-close',id=drawer['id'],counted=4500,expected=4500,reason='Duplicate')[0],409)
 def test_shared_redemption_then_store_scope_cannot_reuse_points(self):
  self.binopoly();self.rules(loyalty=True,earn_cents=1000,reward_points=10,reward_cents=500)
  customer=self.customer()
  self.sell(self.attach(self.add(self.cart(),self.product(price=10000,taxable=False)),customer))
  p=self.product(price=1000,taxable=False,rules=dict(store_id='binopoly'))
  cart=self.attach(self.add(self.cart(store_id='binopoly'),p),customer)
  cart=self.ok('thrift-reward',cart=cart['id'],revision=cart['revision'],redeem=True)['cart'];sale=self.sell(cart)
  self.programs(loyalty_scope='store')
  for store in ('thrift-mart','binopoly'):
   self.assertEqual(self.f.call('pos/thrift-customers?search=Test&store_id='+store)[1]['customers'][0]['points'],0)
  self.refund(sale)
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test&store_id=thrift-mart')[1]['customers'][0]['points'],10)
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test&store_id=binopoly')[1]['customers'][0]['points'],0)
  self.programs(loyalty_scope='shared')
  self.assertEqual(self.f.call('pos/thrift-customers?search=Test')[1]['customers'][0]['points'],10)
 def test_additive_data_preservation_and_repeat_init(self):
  sale=self.sell(self.add(self.cart(),self.product()));self.customer()
  with server.connect() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
   before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
   server.stores_init(c);server.stores_init(c)
   for t,rows in before.items():self.assertEqual(rows,[tuple(r) for r in c.execute('SELECT * FROM '+t)],t)

if __name__=='__main__':__import__('unittest').main()
