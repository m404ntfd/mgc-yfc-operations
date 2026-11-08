import unittest,uuid,datetime as dt,json,sqlite3
from urllib.parse import urlencode
from test_retail_workflows import WorkflowTests
import server
class FinanceTests(WorkflowTests):
 def policy(self,**changes):
  p=self.f.call('pos/policies')[1]['policy'];p.update(changes);return self.ok('policies-save',**p)['policy']
 def refund(self,sale,lines,revision=0,**extra):
  data={'sale':sale['id'],'lines':lines,'reason':'Customer return','refund_revision':revision,'policy_revision':self.f.call('pos/policies')[1]['policy']['revision']};data.update(extra);return data
 def test_cash_change_rounding_all_digits_and_snapshot(self):
  self.policy(cash_rounding='nearest5')
  for exact in range(10):
   cart=self.cart();cart=self.ok('add',cart=cart['id'],revision=cart['revision'],name='Sample',category='Retail',price=100-exact,quantity=1,taxable=False)['cart'];sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=100)['sale'];self.assertEqual(sale['change'],((exact+2)//5)*5);self.assertEqual(sale['cash_paid'],sale['total']+sale['cash_rounding']);self.assertEqual(sale['tax'],0)
  cart=self.cart();self.policy(cash_rounding='off');cart=self.ok('add',cart=cart['id'],revision=cart['revision'],name='Snapshot',category='Retail',price=98,quantity=1,taxable=False)['cart'];sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=100)['sale'];self.assertEqual(sale['change'],0)
 def test_partial_returns_cumulative_cents_and_duplicate_guard(self):
  self.policy(cash_rounding='nearest5');p=self.product(price=333,taxable=False);cart=self.cart();cart=self.ok('add',cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=3)['cart'];sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=1000)['sale'];self.assertEqual(sale['cash_paid'],1000)
  refunds=[]
  for i in range(3):
   data=self.refund(sale,[{'index':0,'quantity':1}],i);preview=self.ok('refund-preview',**data)['preview'];request=uuid.uuid4().hex;args=dict(data,confirmed=True,request=request);code,result=self.f.call('pos/refund',args);self.assertEqual(code,200,result);self.assertEqual(self.f.call('pos/refund',args),(code,result));refunds.append(result['refund']);self.assertEqual(result['refund']['cash'],preview['cash'])
  self.assertEqual(sum(r['cash'] for r in refunds),1000);self.assertEqual(sum(r['total'] for r in refunds),999)
  self.assertEqual(self.post('refund',**dict(self.refund(sale,[{'index':0,'quantity':1}],3),confirmed=True))[0],400)
  with server.connect() as c:
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM retail_refunds')
   original=json.loads(c.execute('SELECT body FROM pos_sales WHERE id=?',(sale['id'],)).fetchone()[0]);self.assertEqual(original['total'],999)
 def test_mixed_tender_refund_restores_original_account_and_tax(self):
  self.policy(cash_rounding='nearest5');a=self.ok('account-create',kind='customer',name='Sample',contact='')['account'];a=self.ok('account-adjust',account=a['id'],account_revision=a['revision'],amount=500,direction='add',reason='Test credit')['account'];p=self.product(price=999,taxable=False);cart=self.add(self.cart(),p);sale=self.ok('credit',cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=500,tender=500)['sale'];self.assertEqual(sale['change'],0)
  result=self.ok('refund',**dict(self.refund(sale,[{'index':0,'quantity':1}]),confirmed=True))['refund'];self.assertEqual((result['cash'],result['store_credit']),(500,500));self.assertEqual(self.f.call('pos/account?id='+str(a['id']))[1]['account']['balance'],500)
 def test_return_window_permissions_and_policy_conflicts(self):
  p=self.product();cart=self.add(self.cart(),p);sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=2000)['sale'];data=self.refund(sale,[{'index':0,'quantity':1}]);self.policy(return_days=30);self.assertEqual(self.post('refund-preview',**data)[0],409)
  from unittest.mock import patch
  current_data=self.refund(sale,[{'index':0,'quantity':1}])
  with patch.object(server.time,'time',return_value=server.time.time()+31*86400):
   with server.connect() as c:
    with self.assertRaises(server.Problem):server.retail_refund_preview(c,{'admin':True,'name':'Admin'},current_data)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));e=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),e);self.assertEqual(self.post('refund-preview',client=e,**self.refund(sale,[{'index':0,'quantity':1}]))[0],403)
 def test_discount_rules_percent_restore_and_promo_exclusion(self):
  p=self.product();cart=self.add(self.cart(),p)
  self.assertEqual(self.post('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=201,index=None,reason='Too large')[0],400)
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=0,percent_bps=1000,index=None,reason='Ten percent')['cart'];self.assertEqual(cart['subtotal'],900)
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=0,index=None,reason='Restore')['cart'];self.assertEqual(cart['subtotal'],1000);self.assertNotIn('adjustment',cart)
  self.policy(discount_categories=['Other']);self.assertEqual(self.post('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=100,index=None,reason='Ineligible')[0],400)
 def test_percentage_limit_rounds_fractional_cents_consistently(self):
  p=self.product(price=999,taxable=False);cart=self.add(self.cart(),p)
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],mode='discount',amount=0,percent_bps=2000,index=None,reason='Maximum allowed discount')['cart']
  self.assertEqual(cart['subtotal'],799)
if __name__=='__main__':unittest.main()
