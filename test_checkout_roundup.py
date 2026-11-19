"""Round-up consent display, accounting and preservation against isolated fixture data."""
import json,time,unittest,uuid,urllib.request
import server
from test_update_coordination import CoordinatorFixture
from test_retail_workflows import WorkflowTests

class RoundupTests(unittest.TestCase):
 setUp=WorkflowTests.setUp
 tearDown=WorkflowTests.tearDown
 post=WorkflowTests.post
 ok=WorkflowTests.ok
 product=WorkflowTests.product
 cart=WorkflowTests.cart
 add=WorkflowTests.add
 def rules(self,enabled=True):
  s=self.f.call('pos/thrift-config')[1]['settings'];self.ok('thrift-settings',**dict(s,donations=enabled))
 def public(self,token):
  with urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.f.port}/api/customer-display',headers={'X-Display-Token':token})) as r:return json.load(r)
 def pair(self):
  s=self.f.call('pos/customer-settings')[1]['display'];self.ok('customer-settings-save',kind='display',**dict(s,enabled=True))
  return self.ok('display-pair')['token']
 def prompt(self,token,cart,**extra):
  code,result=self.f.call('pos/display-state',dict(token=token,cart=cart['id'],roundup=dict(revision=cart['revision'],theme={'accent':'#176d61','text':'#243e3a','bad':'url(https://invalid.test)'},**extra)))
  self.assertEqual(code,200,result)
 def test_prompt_has_exact_amount_theme_and_expires_without_changing_cart(self):
  self.rules();cart=self.add(self.cart(),self.product(price=1237,taxable=False));token=self.pair()
  with server.connect() as c:before=tuple(c.execute('SELECT * FROM pos_carts WHERE id=?',(cart['id'],)).fetchone())
  self.prompt(token,cart);data=self.public(token);self.assertEqual(data['roundup']['amount'],63);self.assertEqual(data['roundup']['total'],1300);self.assertEqual(data['roundup']['theme'],{'accent':'#176d61','text':'#243e3a'})
  with server.connect() as c:
   self.assertEqual(before,tuple(c.execute('SELECT * FROM pos_carts WHERE id=?',(cart['id'],)).fetchone()))
   c.execute('UPDATE customer_checkout_prompts SET expires=?',(time.time()-1,))
  self.assertIsNone(self.public(token)['roundup'])
  self.prompt(token,cart);self.f.call('pos/display-state',dict(token=token,cart=cart['id'],roundup=None));self.assertIsNone(self.public(token)['roundup'])
 def test_roundup_after_discount_keeps_tax_and_replay_and_restore_preserves_donation(self):
  self.rules();cart=self.add(self.cart(),self.product(price=1234,taxable=True))
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=100,index=None,reason='Sample discount')['cart']
  expected=(-cart['total'])%100;tax=cart['tax'];old_lines=json.loads(json.dumps(cart['lines']))
  payload=dict(request=uuid.uuid4().hex,cart=cart['id'],revision=cart['revision'],amount=0,roundup=True)
  first=self.f.call('pos/thrift-donation',payload);self.assertEqual(first[0],200,first);self.assertEqual(self.f.call('pos/thrift-donation',payload),first)
  new=first[1]['cart'];self.assertEqual(new['lines'][:-1],old_lines);self.assertEqual(new['lines'][-1]['subtotal'],expected);self.assertEqual(new['tax'],tax);self.assertEqual(new['total']%100,0)
  restored=self.ok('adjustment-request',cart=new['id'],revision=new['revision'],mode='discount',amount=0,index=None,reason='Restore prices')['cart'];self.assertEqual(restored['lines'][-1]['subtotal'],expected)
  self.assertEqual(restored['lines'][0]['subtotal'],1234)
 def test_whole_dollars_existing_donations_disabled_and_changed_cart(self):
  self.rules();cart=self.add(self.cart(),self.product(price=1200,taxable=False));token=self.pair();self.prompt(token,cart);self.assertIsNone(self.public(token)['roundup'])
  cart=self.add(cart,self.product(price=37,taxable=False));self.prompt(token,cart);self.assertEqual(self.public(token)['roundup']['amount'],63)
  cart=self.ok('thrift-donation',cart=cart['id'],revision=cart['revision'],amount=25)['cart'];self.assertIsNone(self.public(token)['roundup'])
  self.prompt(token,cart);self.assertIsNone(self.public(token)['roundup'])
  cart=self.ok('thrift-donation',cart=cart['id'],revision=cart['revision'],amount=0)['cart'];self.rules(False);self.prompt(token,cart);self.assertIsNone(self.public(token)['roundup'])
  self.assertEqual(self.post('thrift-donation',cart=cart['id'],revision=cart['revision'],amount=0,roundup=True)[0],400)
 def test_reward_and_its_removal_preserve_the_agreed_donation(self):
  settings=self.f.call('pos/thrift-config')[1]['settings'];self.ok('thrift-settings',**dict(settings,donations=True,loyalty=True,earn_cents=100,reward_points=10,reward_cents=500))
  customer=self.ok('thrift-customer-save',name='Sample Supporter',contact='TEST ONLY',marketing=False)['customer']
  product=self.product(price=1237,taxable=False)
  cart=self.add(self.cart(),product);cart=self.ok('thrift-customer',cart=cart['id'],revision=cart['revision'],customer=customer['id'])['cart'];self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=1237)
  cart=self.add(self.cart(),product);cart=self.ok('thrift-customer',cart=cart['id'],revision=cart['revision'],customer=customer['id'])['cart']
  cart=self.ok('thrift-reward',cart=cart['id'],revision=cart['revision'],redeem=True)['cart'];reward=cart['reward']
  cart=self.ok('thrift-donation',cart=cart['id'],revision=cart['revision'],amount=0,roundup=True)['cart']
  self.assertEqual(cart['reward'],reward);self.assertEqual(cart['total'],800);self.assertEqual(cart['lines'][-1]['subtotal'],63)
  cart=self.ok('thrift-reward',cart=cart['id'],revision=cart['revision'],redeem=False)['cart'];self.assertEqual(cart['total'],1300);self.assertEqual(cart['lines'][-1]['subtotal'],63)
 def test_persistent_terminal_display_isolated_and_clears_for_payment(self):
  self.rules();device='1'*32;terminal=self.ok('terminal-save',name='Sample register',device=device,enabled=True)['id'];self.ok('terminal-options-save',terminal=terminal,revision=0,printer='')
  self.ok('store-display-save',store_id='thrift-mart',revision=0,enabled=True,welcome='Hello',thanks='Thanks')
  options=self.f.call('pos/terminal-options?device='+device)[1];token=options['display_path'].split('#')[1]
  cart=self.add(self.cart(device=device),self.product(price=1237,taxable=False))
  data=dict(device=device,token=token,cart=cart['id'],roundup={'revision':cart['revision'],'theme':{}})
  self.assertEqual(self.f.call('pos/display-state',data)[0],200);self.assertEqual(self.public(token)['roundup']['amount'],63)
  other=self.ok('terminal-save',name='Other register',device='2'*32,enabled=True)['id']
  self.assertEqual(self.f.call('pos/display-state',dict(data,device='2'*32))[0],403)
  cart=self.ok('thrift-donation',cart=cart['id'],revision=cart['revision'],amount=0,roundup=True,device=device)['cart'];self.assertIsNone(self.public(token)['roundup'])
  sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=1300,device=device)['sale'];self.assertEqual(sale['total'],1300);self.assertEqual(sale['lines'][-1]['subtotal'],63)
  self.f.call('pos/display-state',dict(device=device,token=token,cart=None,sale=sale['id'],roundup=None));self.assertEqual(self.public(token)['state'],'paid');self.assertNotIn('roundup',self.public(token))
 def test_additive_initialization_preserves_existing_records(self):
  self.rules();cart=self.add(self.cart(),self.product(price=1237,taxable=False));self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=1300)
  with server.connect() as c:
   c.execute('INSERT INTO jobs VALUES(?,?,?)',('sample-appointment',7,json.dumps({'customer':'Sample','start':'2026-11-20T10:00','status':'Scheduled'})))
   c.execute('INSERT INTO photos VALUES(?,?,?)',('sample-appointment',0,b'sample attachment'))
   c.execute("INSERT INTO work_periods VALUES(811,'sample-worker',100,1000,'Store','Store')")
   c.execute("INSERT INTO work_periods VALUES(812,'sample-worker',1200,NULL,'Store',NULL)")
   c.execute('INSERT INTO work_breaks VALUES(821,811,200,300)')
   c.execute('INSERT INTO work_breaks VALUES(822,812,1300,NULL)')
   tables=['jobs','photos','users','work_periods','work_breaks','audit','pos_sales','pos_carts','pos_products','pos_settings']
   before={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
   server.customer_init(c);server.customer_init(c)
   for t in tables:self.assertEqual(before[t],[tuple(r) for r in c.execute('SELECT * FROM '+t)],t)

if __name__=='__main__':unittest.main()
