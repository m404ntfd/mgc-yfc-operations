"""Explicit product taxes permit checkout without inventing a store default."""
import json, unittest, uuid
from test_update_coordination import CoordinatorFixture
import server

class ProductTaxCheckoutTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture()
  self.opts=dict(revision=0,categories=['Goods'],printing=['Counter'],taxes=[dict(id='sample-tax',name='SAMPLE 7%',bps=700,store_id='thrift-mart'),dict(id='zero',name='SAMPLE 0%',bps=0,store_id='thrift-mart')])
  self.ok('catalog-options-save',**self.opts)
 def tearDown(self):self.f.close()
 def post(self,path,**d):return self.f.call('pos/'+path,dict(d,request=uuid.uuid4().hex))
 def ok(self,path,**d):
  code,result=self.post(path,**d);self.assertEqual(code,200,(path,result));return result
 def product(self,name='SAMPLE item',price=1000,**rules):
  return self.ok('product-save',name=name,category='Goods',price=price,taxable=True,rules=dict(tax_ids=['sample-tax'],**rules))['ids'][0]
 def add(self,cart,product,**d):return self.ok('add',cart=cart['id'],revision=cart['revision'],product=product,quantity=1,**d)['cart']
 def rows(self,table):
  with server.connect() as c:return [tuple(r) for r in c.execute('SELECT * FROM '+table+' ORDER BY rowid')]
 def test_fixed_open_price_weight_zero_and_exempt_checkout(self):
  fixed=self.product();opened=self.product(name='SAMPLE open price',open_priced=True);weight=self.product(name='SAMPLE weighed',price=200,sold_by_weight=True)
  exempt=self.ok('product-save',name='SAMPLE exempt',category='Goods',price=100,taxable=False,rules={'tax_ids':[]})['ids'][0]
  zero=self.ok('product-save',name='SAMPLE zero rate',category='Goods',price=100,taxable=True,rules={'tax_ids':['zero']})['ids'][0]
  before={t:self.rows(t) for t in ('pos_settings','retail_stores','retail_catalog_options','pos_products','retail_product_rules')}
  cart=self.ok('new')['cart'];self.assertIsNone(cart['settings']['tax_bps'])
  args=dict(cart=cart['id'],revision=cart['revision'],product=fixed,quantity=1,request=uuid.uuid4().hex)
  first=self.f.call('pos/add',args);self.assertEqual(first[0],200,first);self.assertEqual(first,self.f.call('pos/add',args));cart=first[1]['cart']
  cart=self.add(cart,opened,open_price=1234);cart=self.add(cart,weight,weight='2.25');cart=self.add(cart,exempt);cart=self.add(cart,zero)
  self.assertEqual([l['tax'] for l in cart['lines']],[70,86,32,0,0]);self.assertEqual((cart['subtotal'],cart['tax'],cart['total']),(2884,188,3072))
  sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=4000)['sale'];self.assertEqual(sale['change'],928)
  self.assertEqual({t:self.rows(t) for t in before},before)
  self.assertIsNone(self.f.call('pos/overview')[1]['settings']['tax_bps'])
 def test_missing_default_and_invalid_inputs_leave_existing_sale_unchanged(self):
  fixed=self.product();opened=self.product(open_priced=True);weighed=self.product(sold_by_weight=True)
  legacy=self.ok('product-save',name='SAMPLE unconfigured',category='Goods',price=100,taxable=True,rules={})['ids'][0]
  cart=self.add(self.ok('new')['cart'],fixed);before=self.rows('pos_carts')
  for data,code in ((dict(product=legacy),409),(dict(name='Manual taxable',category='Goods',price=100,taxable=True),409),(dict(product=opened),400),(dict(product=weighed),400)):
   result=self.post('add',cart=cart['id'],revision=cart['revision'],quantity=1,**data);self.assertEqual(result[0],code,result);self.assertEqual(self.rows('pos_carts'),before)
  cart=self.ok('add',cart=cart['id'],revision=cart['revision'],quantity=1,name='Manual exempt',category='Goods',price=100,taxable=False)['cart'];self.assertEqual(cart['tax'],70)
 def test_later_default_only_applies_to_new_unassigned_lines(self):
  fixed=self.product();legacy=self.ok('product-save',name='SAMPLE default-tax item',category='Goods',price=1000,taxable=True,rules={})['ids'][0]
  cart=self.add(self.ok('new')['cart'],fixed);original=json.loads(json.dumps(cart['lines'][0]))
  self.ok('settings',store='Thrift Mart SAMPLE',tax_bps=900,confirmed=True)
  cart=self.add(cart,legacy);self.assertEqual(cart['lines'][0],original);self.assertEqual([l['tax'] for l in cart['lines']],[70,90])
  cart=self.ok('quantity',cart=cart['id'],revision=cart['revision'],index=0,quantity=2)['cart'];self.assertEqual([l['tax'] for l in cart['lines']],[140,90])
 def test_bundle_snapshot_quantity_discount_and_refund_without_default(self):
  taxed=self.product();exempt=self.ok('product-save',name='SAMPLE exempt',category='Goods',price=500,taxable=False,rules={'tax_ids':[]})['ids'][0]
  bundle=self.product(name='SAMPLE package',price=1001,components=[dict(product=taxed,quantity=1),dict(product=exempt,quantity=1)])
  cart=self.add(self.ok('new')['cart'],bundle);self.assertEqual(cart['tax'],47)
  self.opts['revision']=1;self.opts['taxes'][0]['bps']=900;self.ok('catalog-options-save',**self.opts)
  cart=self.ok('quantity',cart=cart['id'],revision=cart['revision'],index=0,quantity=2)['cart'];self.assertEqual(cart['tax'],93)
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=202,index=None,reason='SAMPLE promotion')['cart'];self.assertEqual((cart['subtotal'],cart['tax']),(1800,84))
  sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=2000)['sale'];before=self.rows('pos_sales');self.assertEqual(sale['total'],1884)
  refund=self.ok('refund',sale=sale['id'],lines=[{'index':0,'quantity':2}],reason='SAMPLE return',refund_revision=0,policy_revision=self.f.call('pos/policies')[1]['policy']['revision'],confirmed=True)['refund']
  self.assertEqual(refund['cash'],1884);self.assertEqual(self.rows('pos_sales'),before);self.assertEqual(sale['lines'][0]['components'][0]['tax_rates'][0]['bps'],700)

if __name__=='__main__':unittest.main()
