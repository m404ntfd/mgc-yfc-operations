"""Store-scoped terminal setup and checkout; no production data is used."""
import json, unittest, uuid
from test_update_coordination import CoordinatorFixture
import server

class StoreCheckoutTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture()
  self.ok('settings',store='Thrift Mart SAMPLE',tax_bps=700,confirmed=True)
  self.profile('binopoly',tax_bps=1000,name='Binopoly SAMPLE')
 def tearDown(self):self.f.close()
 def post(self,path,**d):return self.f.call('pos/'+path,dict(d,request=uuid.uuid4().hex))
 def ok(self,path,**d):
  code,result=self.post(path,**d);self.assertEqual(code,200,(path,result));return result
 def profile(self,store,**changes):
  p=next(s for s in self.f.call('pos/stores')[1]['stores'] if s['id']==store)
  return self.ok('store-save',**dict(p,confirmed=True,**changes))['store']
 def terminal(self,device,store='binopoly'):
  return self.ok('terminal-save',name='SAMPLE register '+device[0],device=device,store_id=store,enabled=True)['id']
 def product(self,store='binopoly'):
  return self.ok('product-save',name='SAMPLE merchandise',category='Goods',price=500,taxable=True,rules={'store_id':store})['ids'][0]
 def sale(self,device,product):
  cart=self.ok('new',device=device)['cart']
  cart=self.ok('add',device=device,cart=cart['id'],revision=cart['revision'],product=product,quantity=1)['cart']
  return self.ok('cash',device=device,cart=cart['id'],revision=cart['revision'],tender=1000)['sale']
 def test_two_terminals_share_store_taxes_receipts_and_keep_history(self):
  a='a'*32;b='b'*32;self.terminal(a);self.terminal(b);item=self.product()
  receipt=dict(address='SAMPLE Binopoly address',phone='',logo='',policy='SAMPLE policy',footer='Shared Binopoly receipt')
  self.profile('binopoly',receipt=receipt)
  first=self.sale(a,item);second=self.sale(b,item)
  self.assertEqual((first['tax'],second['tax']),(50,50))
  self.assertEqual(first['receipt_design'],second['receipt_design']);self.assertEqual(first['receipt_design'],receipt)
  with server.connect() as c:before=[tuple(r) for r in c.execute('SELECT * FROM pos_sales ORDER BY id')]
  self.profile('binopoly',tax_bps=800,receipt=dict(receipt,footer='New shared footer'))
  for device in (a,b):
   overview=self.f.call('pos/overview?device='+device)[1]
   self.assertEqual(overview['settings']['tax_bps'],800)
  third=self.sale(b,item);self.assertEqual(third['tax'],40);self.assertEqual(third['receipt_design']['footer'],'New shared footer')
  with server.connect() as c:self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM pos_sales ORDER BY id')][:2])
  self.assertEqual(self.f.call('pos/overview?store_id=thrift-mart')[1]['settings']['tax_bps'],700)
 def test_receipt_only_legacy_profile_uses_confirmed_store_rate_without_rewrite(self):
  with server.connect() as c:
   profile=server.stores_profile(c,'thrift-mart');body={k:v for k,v in profile.items() if k not in ('id','revision')};body['tax_bps']=None
   body['receipt']['footer']='Preserved legacy footer'
   c.execute('INSERT INTO retail_stores VALUES(?,?,?)',('thrift-mart',2,json.dumps(body)))
   before=tuple(c.execute("SELECT * FROM retail_stores WHERE id='thrift-mart'").fetchone())
  self.terminal('c'*32,'thrift-mart');sale=self.sale('c'*32,self.product('thrift-mart'))
  self.assertEqual(sale['tax'],35);self.assertEqual(sale['receipt_design']['footer'],'Preserved legacy footer')
  with server.connect() as c:self.assertEqual(before,tuple(c.execute("SELECT * FROM retail_stores WHERE id='thrift-mart'").fetchone()))
 def test_legacy_settings_update_shared_profile_without_erasing_receipt(self):
  p=self.profile('thrift-mart');receipt=dict(p['receipt'],footer='Keep branding');self.profile('thrift-mart',receipt=receipt)
  self.ok('settings',store='Thrift Mart SAMPLE',tax_bps=725,confirmed=True)
  with server.connect() as c:
   profile=server.stores_profile(c,'thrift-mart');self.assertEqual(profile['tax_bps'],725);self.assertEqual(profile['receipt'],receipt)
  self.ok('settings',store_id='binopoly',store='Binopoly SAMPLE',tax_bps=600,confirmed=True)
  with server.connect() as c:self.assertEqual(server.stores_profile(c,'thrift-mart')['tax_bps'],725)
 def test_assignment_change_requires_clear_drawer_and_saved_sales_and_detects_conflicts(self):
  device='d'*32;ident=self.terminal(device);cart=self.ok('new',device=device)['cart']
  current=self.f.call('pos/terminal?device='+device)[1]['terminal']
  args=dict(current,store_id='thrift-mart',previous_store='binopoly',enabled=True)
  self.assertEqual(self.post('terminal-save',**args)[0],400)
  self.ok('discard',device=device,cart=cart['id'],revision=cart['revision'],reason='Sample cancel')
  self.ok('store-terminal',terminal=ident,store_id='thrift-mart',previous='binopoly')
  self.assertEqual(self.post('terminal-save',**args)[0],409)
  self.ok('store-terminal',terminal=ident,store_id='binopoly',previous='thrift-mart')
  self.ok('programs-save',**dict(self.f.call('pos/programs')[1]['programs'],drawers=True))
  self.ok('drawer-open',terminal=ident,opening=1000)
  self.assertEqual(self.post('store-terminal',terminal=ident,store_id='thrift-mart',previous='binopoly')[0],400)
 def test_native_enrollment_selects_store_and_existing_binding_stays_registered(self):
  info=dict(app='pos',device='e'*32,version='1.18.0',computer=dict(id='f'*32,hostname='SAMPLE-PC',macs=[],os='Windows test'))
  self.assertEqual(self.f.call('computers/self',info)[0],200)
  data=dict(id='f'*32,revision=0,name='SAMPLE new checkout',role='pos',app='pos',device='e'*32,store_id='binopoly')
  self.assertEqual(self.f.call('computers/register',data)[0],200)
  result=self.f.call('computers/self',info)[1];self.assertEqual(result['terminal']['store_id'],'binopoly')
  self.assertEqual(result['terminal']['store_name'],'Binopoly SAMPLE')
  self.assertEqual(self.f.call('computers/register',dict(data,revision=1,name='Renamed computer',store_id='thrift-mart'))[0],200)
  self.assertEqual(self.f.call('computers/self',info)[1]['terminal']['store_id'],'binopoly')
 def test_invalid_registration_store_rolls_back_and_unconfigured_store_stays_blocked(self):
  info=dict(app='pos',device='f'*32,version='1.18.0',computer=dict(id='e'*32,hostname='SAMPLE-PC2',macs=[],os='Windows test'))
  self.f.call('computers/self',info)
  self.assertEqual(self.f.call('computers/register',dict(id='e'*32,revision=0,name='SAMPLE failed registration',role='pos',app='pos',device='f'*32,store_id='missing'))[0],404)
  self.assertIsNone(self.f.call('computers/self',info)[1]['terminal'])
  with server.connect() as c:
   c.execute("DELETE FROM pos_settings")
   before=[tuple(r) for r in c.execute('SELECT * FROM pos_carts')]
  cart=self.ok('new')['cart']
  with server.connect() as c:before=[tuple(r) for r in c.execute('SELECT * FROM pos_carts')]
  self.assertEqual(self.post('add',cart=cart['id'],revision=cart['revision'],name='Unconfigured taxable amount',category='Goods',price=100,quantity=1,taxable=True)[0],409)
  with server.connect() as c:self.assertEqual(before,[tuple(r) for r in c.execute('SELECT * FROM pos_carts')])

if __name__=='__main__':unittest.main()
