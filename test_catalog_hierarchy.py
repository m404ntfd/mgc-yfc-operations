"""Hierarchy changes preserve existing business records and snapshot future reporting."""
import datetime as dt,json,unittest,uuid
from test_update_coordination import CoordinatorFixture
import server
from unittest.mock import patch
class HierarchyTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.post('settings',store='Fixture store',tax_bps=0,confirmed=True)
 def tearDown(self):self.f.close()
 def post(self,path,**data):
  code,result=self.f.call('pos/'+path,dict(request=uuid.uuid4().hex,**data));self.assertEqual(code,200,result);return result
 def options(self):return self.f.call('pos/catalog-options')[1]
 def save(self,section,rows):return self.post('catalog-options-save',revision=self.options()['revision'],section=section,**{section:rows})
 def seed(self):
  self.product=self.post('product',name='Fixture chair',category='Furniture',price=1000,taxable=False)['product']['id']
  self.save('revenue_centers',[dict(id='retail',name='Thrift retail'),dict(id='bins',name='Binopoly')])
  self.save('departments',[dict(id='home',name='Home goods',revenue_center_id='retail')])
  subs=self.options()['sub_departments'];subs[0]['department_id']='home';self.save('sub_departments',subs)
 def sale(self):
  cart=self.post('new')['cart'];cart=self.post('add',cart=cart['id'],revision=cart['revision'],product=self.product,quantity=1)['cart']
  return self.post('cash',cart=cart['id'],revision=cart['revision'],tender=1000)['sale']
 def report(self,kind):
  today=dt.date.today();code,result=self.f.call('retail-reports?kind='+kind+'&start='+str(today)+'T00:00:00&end='+str(today+dt.timedelta(days=1))+'T00:00:00');self.assertEqual(code,200,result);return result
 def test_independent_sections_permissions_and_concurrency(self):
  self.seed();before=self.options()
  self.save('taxes',[dict(id='sample',name='Sample tax',bps=700,store_id='thrift-mart')])
  self.save('printing',['Warehouse'])
  after=self.options()
  for key in ['sub_departments','departments','revenue_centers']:self.assertEqual(before[key],after[key])
  self.assertEqual(after['taxes'][0]['bps'],700)
  code,_=self.f.call('pos/catalog-options-save',dict(request=uuid.uuid4().hex,revision=before['revision'],section='printing',printing=['Wrong']))
  self.assertEqual(code,409);self.assertEqual(self.options()['printing'],['Warehouse'])
  staff=self.f.client('restricted');self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  self.assertEqual(self.f.call('pos/catalog-options',client=staff)[0],403)
  self.assertEqual(self.f.call('pos/catalog-options-save',dict(request=uuid.uuid4().hex,revision=after['revision'],section='departments',departments=[]),staff)[0],403)
 def test_parent_validation_and_no_orphans(self):
  self.seed();before=self.options()
  for section,rows in [('departments',[dict(id='home',name='Home',revenue_center_id='missing')]),('sub_departments',before['sub_departments']+[dict(id='new',name='New',department_id='')]),('revenue_centers',[]),('departments',[dict(id='home',name='Home',revenue_center_id='retail'),dict(id='duplicate',name='HOME',revenue_center_id='retail')])]:
   code,_=self.f.call('pos/catalog-options-save',dict(request=uuid.uuid4().hex,revision=before['revision'],section=section,**{section:rows}));self.assertEqual(code,400);self.assertEqual(self.options(),before)
 def test_sale_and_refund_keep_original_hierarchy(self):
  self.seed();sale=self.sale()
  self.assertEqual(sale['lines'][0]['reporting']['revenue_center'],'Thrift retail')
  self.save('departments',[dict(id='home',name='Home goods',revenue_center_id='bins')])
  subs=self.options()['sub_departments'];subs[0]['name']='Home furniture';self.save('sub_departments',subs)
  newer=self.sale();self.assertEqual(newer['lines'][0]['reporting']['revenue_center'],'Binopoly')
  self.assertEqual(newer['lines'][0]['category'],'Furniture');self.assertEqual(newer['lines'][0]['reporting']['sub_department'],'Home furniture')
  policy=self.f.call('pos/policies')[1]['policy']
  refund=self.post('refund',sale=sale['id'],policy_revision=policy['revision'],refund_revision=0,reason='Fixture return',lines=[dict(index=0,quantity=1)],confirmed=True)
  self.assertEqual(refund['refund']['lines'][0]['reporting']['revenue_center'],'Thrift retail')
  rows=self.report('revenue-centers')['rows'];self.assertIn(['Thrift retail',0,'0.00'],rows);self.assertIn(['Binopoly',1,'10.00'],rows)
  self.assertEqual(self.report('hierarchy')['rows'][0][-3:],['Home furniture','Home goods','Binopoly'])
 def test_renamed_display_names_preserve_product_and_eligibility_links(self):
  self.seed();subs=self.options()['sub_departments'];subs[0]['name']='Home furniture';self.save('sub_departments',subs)
  new=self.post('product',name='New chair',category='Home furniture',price=1000,taxable=False)['product']
  self.assertEqual(new['category'],'Furniture')
  with server.connect() as c:self.assertEqual(server.retail_product(c,c.execute('SELECT * FROM pos_products WHERE id=?',(new['id'],)).fetchone())['reporting']['department'],'Home goods')
  cart=self.post('new')['cart'];cart=self.post('add',cart=cart['id'],revision=cart['revision'],name='Manual chair',category='Home furniture',price=1000,quantity=1,taxable=False)['cart']
  self.assertEqual(cart['lines'][0]['category'],'Furniture');self.assertEqual(cart['lines'][0]['reporting']['sub_department'],'Home furniture')
  settings=self.f.call('pos/thrift-config')[1]['settings'];settings['tags']=[dict(name='Blue',color='#2255aa',bps=5000,**{'from':'','to':''},days=list(range(7)),categories=['Home furniture'])]
  self.post('thrift-settings',**settings)
  self.assertEqual(self.f.call('pos/thrift-config')[1]['settings']['tags'][0]['categories'],['Furniture'])
  intake=self.post('thrift-intake-create',name='Tagged chair',category='Home furniture',price=2000,taxable=False,tag='Blue')['item']
  tagged=self.post('new')['cart'];tagged=self.post('add',cart=tagged['id'],revision=tagged['revision'],product=intake['product'],quantity=1)['cart']
  self.assertEqual(tagged['total'],1000);self.assertEqual(tagged['lines'][0]['category'],'Furniture')
  current=self.f.call('pos/thrift-config')[1]['settings'];code,result=self.f.call('pos/thrift-settings',dict(current,tags=[],request=uuid.uuid4().hex));self.assertEqual(code,400);self.assertIn('attached to priced inventory',result['error']);self.assertEqual(self.f.call('pos/thrift-config')[1]['settings'],current)
  account=self.post('thrift-voucher-issue',name='Fixture voucher',reason='Test only',amount=1000,expires=(dt.date.today()+dt.timedelta(days=30)).isoformat(),categories=['Home furniture'])['account']
  sale=self.post('credit',cart=cart['id'],revision=cart['revision'],account=account['id'],account_revision=account['revision'],amount=1000,tender=0)['sale']
  self.assertEqual(sale['voucher_paid'],1000)
  self.assertEqual(self.report('dashboard')['categories'],{'Home furniture':1000})
  self.assertEqual(self.report('products')['rows'][0][1],'Home furniture')
  before=self.options();code,_=self.f.call('pos/catalog-options-save',dict(request=uuid.uuid4().hex,revision=before['revision'],section='sub_departments',sub_departments=before['sub_departments']+[dict(id='collision',name='Furniture',department_id='home')]))
  self.assertEqual(code,400);self.assertEqual(before,self.options())
 def test_unused_entries_delete_but_assigned_entries_are_protected(self):
  self.seed();self.save('revenue_centers',self.options()['revenue_centers']+[dict(id='unused',name='Unused center')]);self.save('departments',self.options()['departments']+[dict(id='unused-dept',name='Unused department',revenue_center_id='unused')]);self.save('sub_departments',self.options()['sub_departments']+[dict(id='unused-sub',name='Unused sub',department_id='unused-dept')])
  def denied(section,rows,text):
   before=self.options();code,result=self.f.call('pos/catalog-options-save',dict(request=uuid.uuid4().hex,revision=before['revision'],section=section,**{section:rows}));self.assertEqual(code,400,result);self.assertIn(text,result['error']);self.assertEqual(self.options(),before)
  denied('revenue_centers',[x for x in self.options()['revenue_centers'] if x['id']!='unused'],'assigned to a Department')
  denied('departments',[x for x in self.options()['departments'] if x['id']!='unused-dept'],'assigned to a Sub Department')
  denied('sub_departments',[x for x in self.options()['sub_departments'] if x['key']!='Furniture'],'assigned to a product')
  self.save('sub_departments',[x for x in self.options()['sub_departments'] if x['id']!='unused-sub'])
  self.save('departments',[x for x in self.options()['departments'] if x['id']!='unused-dept'])
  self.save('revenue_centers',[x for x in self.options()['revenue_centers'] if x['id']!='unused'])
  self.save('taxes',[dict(id='sample-tax',name='Sample tax',bps=700,store_id='thrift-mart')]);self.save('printing',['Warehouse'])
  product=self.f.call('pos/catalog-config')[1]['products'][0];product['rules'].update(tax_ids=['sample-tax'],print_category='Warehouse');self.post('product-save',**product)
  denied('taxes',[],'assigned to a product');denied('printing',[],'assigned to a product')
  cart=self.post('new')['cart'];cart=self.post('add',cart=cart['id'],revision=cart['revision'],product=self.product,quantity=1)['cart'];sale=self.post('cash',cart=cart['id'],revision=cart['revision'],tender=cart['total'])['sale'];self.assertEqual(sale['total'],1070)
  with server.connect() as c:before_sale=c.execute('SELECT body FROM pos_sales WHERE id=?',(sale['id'],)).fetchone()[0]
  product=self.f.call('pos/catalog-config')[1]['products'][0];product['rules'].update(tax_ids=[],print_category='');self.post('product-save',**product)
  self.save('taxes',[]);self.save('printing',[])
  with server.connect() as c:self.assertEqual(c.execute('SELECT body FROM pos_sales WHERE id=?',(sale['id'],)).fetchone()[0],before_sale)
  policy=self.f.call('pos/policies')[1]['policy'];refund=self.post('refund',sale=sale['id'],policy_revision=policy['revision'],refund_revision=0,reason='Fixture return',lines=[dict(index=0,quantity=1)],confirmed=True)['refund'];self.assertEqual(refund['total'],1070)
 def test_historical_records_and_keys_stay_intact(self):
  self.product=self.post('product',name='Old item',category='Furniture',price=1000,taxable=False)['product']['id']
  with patch.object(server,'catalog_stamp',side_effect=lambda c,line,legacy:line):sale=self.sale()
  with server.connect() as c:
   self.assertNotIn('reporting',json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(sale['id'],)).fetchone()[0])['lines'][0])
   account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute("INSERT INTO work_periods VALUES(901,?,100,NULL,'Office',NULL)",(account,));c.execute('INSERT INTO work_breaks VALUES(902,901,200,NULL)')
   c.execute("INSERT INTO jobs VALUES('existing',8,?)",('{"type":"Delivery","notes":"Preserve"}',));c.execute("INSERT INTO photos VALUES('existing',0,?)",(b'fixture-attachment',))
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('retail_catalog_options','audit','pos_operations','sqlite_sequence')")]
   before={name:[tuple(row) for row in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in tables}
  self.save('revenue_centers',[dict(id='retail',name='Thrift retail')]);self.save('departments',[dict(id='home',name='Home',revenue_center_id='retail')])
  subs=self.options()['sub_departments'];subs[0]['department_id']='home';subs[0]['name']='Renamed furniture';self.save('sub_departments',subs)
  self.assertEqual(self.report('revenue-centers')['rows'],[['Not recorded (historical sales)',1,'10.00']])
  self.assertEqual(self.report('sub-departments')['rows'][0][-3:],['Furniture',1,'10.00'])
  with server.connect() as c:
   server.catalog_init(c);server.catalog_init(c)
   for name,rows in before.items():self.assertEqual([tuple(row) for row in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')],rows,name)
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
if __name__=='__main__':unittest.main()
