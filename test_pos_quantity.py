"""Receipt quantity changes preserve captured prices, taxes, and protected records."""
import json, unittest, uuid
import server
import test_retail_workflows as workflow

class QuantityTests(unittest.TestCase):
 setUp=workflow.WorkflowTests.setUp
 tearDown=workflow.WorkflowTests.tearDown
 post=workflow.WorkflowTests.post
 ok=workflow.WorkflowTests.ok
 product=workflow.WorkflowTests.product
 cart=workflow.WorkflowTests.cart
 add=workflow.WorkflowTests.add
 def resize(self,cart,qty,index=0):return self.ok('quantity',cart=cart['id'],revision=cart['revision'],index=index,quantity=qty)['cart']
 def test_snapshot_retry_conflict_and_payment(self):
  p=self.product(price=1234,rules={'open_priced':True,'modifiers':[{'id':'size','name':'Size','required':True,'options':[{'id':'large','name':'Large','price':200}]}]})
  c=self.add(self.cart(),p,open_price=555,choices={'size':'large'})
  p['price']=9999;p['taxable']=False;p['rules']['modifiers'][0]['options'][0]['price']=999;self.ok('product-save',**p)
  self.ok('settings',store='Changed catalog',tax_bps=700,confirmed=True)
  args=dict(cart=c['id'],revision=c['revision'],index=0,quantity=3,request=uuid.uuid4().hex)
  first=self.f.call('pos/quantity',args);self.assertEqual(first[0],200,first);self.assertEqual(first,self.f.call('pos/quantity',args))
  new=first[1]['cart'];line=new['lines'][0]
  self.assertEqual((line['price'],line['entered_price'],line['quantity'],line['subtotal'],line['tax']),(755,555,3,2265,227))
  self.assertEqual(line['modifiers'],c['lines'][0]['modifiers']);self.assertEqual(line.get('tax_rates'),c['lines'][0].get('tax_rates'))
  self.assertEqual(self.post('quantity',cart=c['id'],revision=c['revision'],index=0,quantity=2)[0],409)
  new=self.resize(new,1);sale=self.ok('cash',cart=new['id'],revision=new['revision'],tender=1000)['sale']
  self.assertEqual(sale['total'],831)
  self.assertEqual(self.post('quantity',cart=new['id'],revision=new['revision']+1,index=0,quantity=2)[0],409)
  self.assertEqual(self.f.call('pos/sales')[1]['sales'][0],sale)
  with server.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM retail_sale_events WHERE action='quantity-changed'").fetchone()[0],2)
 def test_bundle_roundtrip_and_partial_refund(self):
  a=self.product('A',1000);b=self.product('B',500,False);p=self.product('Bundle',1001,rules={'components':[{'product':a['id'],'quantity':2},{'product':b['id'],'quantity':1}]})
  c=self.add(self.cart(),p);initial=c['lines'][0]
  for qty in (3,2,7,1):
   c=self.resize(c,qty);line=c['lines'][0]
   self.assertEqual(line['subtotal'],1001*qty);self.assertEqual(sum(p['subtotal'] for p in line['components']),line['subtotal'])
   self.assertEqual([p['quantity'] for p in line['components']],[2*qty,qty])
  result=dict(c['lines'][0]);result.pop('quantity_basis');self.assertEqual(result,initial)
  c=self.resize(c,3);sale=self.ok('cash',cart=c['id'],revision=c['revision'],tender=5000)['sale']
  refund=self.ok('refund',sale=sale['id'],lines=[{'index':0,'quantity':3}],reason='Test complete return',refund_revision=0,policy_revision=self.f.call('pos/policies')[1]['policy']['revision'],confirmed=True)['refund']
  self.assertEqual(refund['cash'],sale['total'])
 def test_tag_manual_and_captured_multi_tax(self):
  line=dict(name='Sample',price=101,quantity=1,subtotal=101,taxable=True,tax_rates=[dict(id='one',name='Tax A',bps=700),dict(id='two',name='Tax B',bps=250)])
  server.catalog_tax(line,0);original=json.loads(json.dumps(line));line.update(tag_original=original,tag=dict(name='Blue',bps=2500,color='#0000ff',discount=25),subtotal=76);server.catalog_tax(line,0)
  three=server.pos_resize_line(line,3,9999)
  self.assertEqual((three['subtotal'],three['tag']['discount'],three['tax']),(227,76,22))
  back=server.pos_resize_line(three,1,9999);self.assertEqual(back,line)
  c=self.cart();c=self.ok('add',cart=c['id'],revision=c['revision'],name='Manual',category='Retail',price=75,quantity=1,taxable=True)['cart'];c=self.resize(c,3);self.assertEqual(c['total'],248)
 def test_guards_and_unchanged_data(self):
  with server.connect() as db:
   owner=db.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   db.execute("INSERT INTO work_periods VALUES(901,?,1200,NULL,'Office',NULL)",(owner,));db.execute('INSERT INTO work_breaks VALUES(902,901,1300,NULL)')
   db.execute('INSERT INTO jobs VALUES(?,?,?)',('Delivery',903,json.dumps({'type':'Delivery','customer':'Protected'})));db.execute('INSERT INTO photos VALUES(?,?,?)',('Delivery',0,b'protected'))
  def snapshot():
   with server.connect() as db:return {table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in ('users','work_periods','work_breaks','jobs','photos','pos_sales','pos_products','pos_settings')}
  p=self.product();c=self.add(self.cart(),p);before=snapshot()
  for qty in (0,-1,1000,1.2,True,'2',None):self.assertEqual(self.post('quantity',cart=c['id'],revision=c['revision'],index=0,quantity=qty)[0],400)
  self.assertEqual(self.post('quantity',cart=c['id'],revision=c['revision'],index=99,quantity=2)[0],400)
  c=self.ok('hold',cart=c['id'],revision=c['revision'])['cart'];self.assertEqual(self.post('quantity',cart=c['id'],revision=c['revision'],index=0,quantity=2)[0],409)
  c=self.ok('resume',cart=c['id'],revision=c['revision'])['cart'];c=self.resize(c,2)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));other=self.f.client('qty-other');self.f.call('login',dict(name='Employee',password='testpassword'),other)
  self.assertEqual(self.post('quantity',client=other,cart=c['id'],revision=c['revision'],index=0,quantity=3)[0],404)
  c=self.ok('adjustment-request',cart=c['id'],revision=c['revision'],mode='discount',amount=100,index=None,reason='Test discount')['cart']
  self.assertEqual(self.post('quantity',cart=c['id'],revision=c['revision'],index=0,quantity=3)[0],409)
  self.assertEqual(snapshot(),before)
  for special in ('weight_milli','intake','gift_certificate','donation'):
   with self.assertRaises(server.Problem):server.pos_resize_line(dict(c['lines'][0],**{special:1}),2,1000)

if __name__=='__main__':unittest.main()
