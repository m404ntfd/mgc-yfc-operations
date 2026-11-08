import unittest,uuid,json,sqlite3,time,datetime as dt
from urllib.parse import urlencode
from test_update_coordination import CoordinatorFixture
import server
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.post('settings',store='Sample retail',tax_bps=1000,confirmed=True)
 def tearDown(self):self.f.close()
 def post(self,path,client=None,**data):return self.f.call('pos/'+path,dict(data,request=uuid.uuid4().hex),client)
 def ok(self,path,**data):
  code,result=self.post(path,**data);self.assertEqual(code,200,result);return result
 def product(self,name='Product',price=1000,taxable=True,rules=None):
  ident=self.ok('product-save',name=name,category='Retail',price=price,taxable=taxable,rules=rules or {})['ids'][0]
  return next(p for p in self.f.call('pos/catalog-config')[1]['products'] if p['id']==ident)
 def cart(self,**data):return self.ok('new',**data)['cart']
 def add(self,cart,p,**data):return self.ok('add',cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1,**data)['cart']
 def test_choices_promotion_availability_and_snapshot(self):
  p=self.product(rules={'modifiers':[{'id':'size','name':'Size','required':True,'options':[{'id':'large','name':'Large','price':200}]}]});cart=self.cart()
  self.assertEqual(self.post('add',cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1)[0],400)
  self.assertEqual(self.post('add',cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1,choices={'size':'bad'})[0],400)
  cart=self.add(cart,p,choices={'size':'large'});self.assertEqual(cart['total'],1320);self.assertEqual(cart['lines'][0]['modifiers'][0]['name'],'Large')
  p['price']=2000;self.ok('product-save',**p);self.assertEqual(self.f.call('pos/overview')[1]['carts'][0]['total'],1320)
  now=dt.datetime.now(dt.timezone.utc);promo=self.product(name='Promo',rules={'promo_price':800,'promo_from':(now-dt.timedelta(hours=1)).isoformat(),'promo_until':(now+dt.timedelta(hours=1)).isoformat()});self.assertEqual(self.add(cart,promo)['lines'][-1]['price'],800)
  future=self.product(name='Future',rules={'available_from':(now+dt.timedelta(days=1)).isoformat()});self.assertEqual(self.post('add',cart=cart['id'],revision=cart['revision']+1,product=future['id'],quantity=1)[0],409)
 def test_bundle_mixed_tax_allocation_and_adjustments(self):
  a=self.product('Taxable',1000);b=self.product('Exempt',500,False);bundle=self.product('Package',1001,rules={'components':[{'product':a['id'],'quantity':1},{'product':b['id'],'quantity':1}]});cart=self.add(self.cart(),bundle)
  line=cart['lines'][0];self.assertEqual([x['subtotal'] for x in line['components']],[667,334]);self.assertEqual(cart['tax'],67)
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=101,index=None,reason='Manager promotion')['cart'];self.assertEqual(cart['subtotal'],900);self.assertEqual(cart['tax'],60)
  sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=1000)['sale'];self.assertEqual(sale['change'],40)
  self.assertEqual(sale['adjustment']['approved_by'],'Admin');self.assertEqual(sum(c['subtotal'] for c in sale['lines'][0]['components']),900)
  a['rules']['components']=[{'product':bundle['id'],'quantity':1}];self.assertEqual(self.post('product-save',**a)[0],400)
  with server.connect() as c:
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM retail_sale_events')
   with self.assertRaises(sqlite3.IntegrityError):c.execute('UPDATE pos_sales SET body=\'{}\'')
 def test_manager_queue_stale_approval_transfer_and_permissions(self):
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));e=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),e)
  p=self.product();code,result=self.post('new',client=e);cart=result['cart'];cart=self.post('add',client=e,cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1)[1]['cart']
  args=dict(cart=cart['id'],revision=cart['revision'],mode='discount',amount=100,index=None,reason='Customer adjustment');r=self.post('adjustment-request',client=e,**args)[1]
  self.assertEqual(self.post('adjustment-decision',client=e,id=r['approval'],decision='approved',reason='Yes')[0],403)
  cart=self.post('hold',client=e,cart=cart['id'],revision=cart['revision'])[1]['cart'];self.assertEqual(self.post('adjustment-decision',id=r['approval'],decision='approved',reason='Reviewed')[0],409)
  self.ok('adjustment-decision',id=r['approval'],decision='denied',reason='Sale changed')
  with server.connect() as c:target=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Admin'").fetchone()[0]
  self.assertEqual(self.post('transfer-sale',client=e,cart=cart['id'],revision=cart['revision'],owner=target,reason='Handoff')[0],403)
  self.ok('transfer-sale',cart=cart['id'],revision=cart['revision'],owner=target,reason='Shift handoff');self.assertEqual(len(self.f.call('pos/held-sales',client=e)[1]['carts']),0)
  self.assertEqual(self.post('cash',cart=cart['id'],revision=cart['revision']+1,tender=2000)[0],409)
  cart=self.ok('resume',cart=cart['id'],revision=cart['revision']+1)['cart'];self.assertEqual(self.post('discard',cart=cart['id'],revision=cart['revision'])[0],400)
  self.ok('discard',cart=cart['id'],revision=cart['revision'],reason='Customer left')
 def test_bulk_atomicity_revision_and_idempotency(self):
  a=self.product('A');b=self.product('B');a['price']=900;b['price']=-1
  self.assertEqual(self.post('catalog-import',rows=[a,b],confirmed=True)[0],400)
  self.assertEqual(self.f.call('pos/catalog-config')[1]['products'][0]['price'],1000)
  b['price']=800;preview=self.ok('catalog-preview',rows=[a,b]);request=uuid.uuid4().hex;data={'rows':preview['rows'],'confirmed':True,'request':request};first=self.f.call('pos/catalog-import',data);self.assertEqual(first[0],200);self.assertEqual(first,self.f.call('pos/catalog-import',data))
  self.assertEqual(self.post('catalog-import',rows=[a,b],confirmed=True)[0],409)
 def test_print_categories_reports_and_completed_snapshot(self):
  p=self.product(rules={'print_category':'Preparation'});self.ok('print-routes',revision=0,routes=[{'category':'Preparation','printer':'Counter printer'}]);cart=self.add(self.cart(),p);sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=2000)['sale']
  ticket=self.f.call('pos/print-tickets?sale='+str(sale['id']))[1];self.assertEqual(ticket['tickets'][0]['printer'],'Counter printer')
  now=dt.datetime.now(dt.timezone.utc);q=urlencode({'start':(now-dt.timedelta(days=1)).isoformat(),'end':(now+dt.timedelta(days=1)).isoformat()});code,r=self.f.call('pos/sale-report?'+q);self.assertEqual(code,200,r);self.assertEqual(r['totals']['cash'],1100);self.assertEqual(r['totals']['tax'],100)
  p['name']='Renamed';p['price']=5000;self.ok('product-save',**p);self.assertEqual(self.f.call('pos/sales')[1]['sales'][0]['lines'][0]['name'],'Product')
if __name__=='__main__':unittest.main()
