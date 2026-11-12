import unittest,json,uuid,os
from unittest.mock import patch
from test_retail_workflows import WorkflowTests
import server
class CheckoutTests(WorkflowTests):
 def choices(self,**changes):
  current=self.f.call('pos/checkout-settings')[1]['settings'];current.update(changes)
  return self.ok('checkout-settings-save',**current)['settings']
 def test_configured_presets_reasons_revision_and_permissions(self):
  config=self.choices(presets=[dict(id='ten',name='Member discount',mode='discount',scope='transaction',kind='percent',value=1000)])
  p=self.product();cart=self.add(self.cart(),p)
  cart=self.ok('adjustment-request',cart=cart['id'],revision=cart['revision'],preset='ten',settings_revision=config['revision'],index=None,amount=99999,mode='surcharge')['cart']
  self.assertEqual(cart['subtotal'],900);self.assertEqual(cart['adjustment']['reason'],'Member discount')
  self.assertEqual(self.post('adjustment-request',cart=cart['id'],revision=cart['revision'],preset='ten',settings_revision=0,index=None)[0],409)
  self.assertEqual(self.post('discard',cart=cart['id'],revision=cart['revision'],reason_id='bogus',settings_revision=config['revision'])[0],400)
  self.ok('discard',cart=cart['id'],revision=cart['revision'],reason_id='entry-error',settings_revision=config['revision'])
  with server.connect() as c:self.assertEqual(c.execute('SELECT status FROM pos_carts WHERE id=?',(cart['id'],)).fetchone()[0],'discarded')
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));client=self.f.client('employee');self.f.call('login',dict(name='Employee',password='testpassword'),client)
  self.assertEqual(self.post('checkout-settings-save',client=client,**config)[0],403)
 def test_round_due_low_tender_and_replay(self):
  policy=self.f.call('pos/policies')[1]['policy'];self.ok('policies-save',**dict(policy,cash_rounding='nearest5'))
  p=self.product(price=1002,taxable=False);cart=self.add(self.cart(),p)
  args=dict(cart=cart['id'],revision=cart['revision'],tender=1000,request=uuid.uuid4().hex)
  first=self.f.call('pos/cash',args);self.assertEqual(first[0],200,first);self.assertEqual(self.f.call('pos/cash',args),first)
  self.assertEqual(self.f.call('pos/checkout-payment-status?request='+args['request'])[1]['result'],first[1])
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));e=self.f.client('status-other');self.f.call('login',dict(name='Employee',password='testpassword'),e)
  self.assertFalse(self.f.call('pos/checkout-payment-status?request='+args['request'],client=e)[1]['confirmed'])
  s=first[1]['sale'];self.assertEqual((s['total'],s['cash_rounding'],s['cash_paid'],s['change']),(1002,-2,1000,0))
  self.assertEqual(server.retail_cash_change({'cash_rounding':'nearest5'},1003,1002)['cash_paid'],1003)
 def test_partial_credit_and_cash_and_email_snapshot(self):
  policy=self.f.call('pos/policies')[1]['policy'];self.ok('policies-save',**dict(policy,cash_rounding='nearest5'))
  a=self.ok('account-create',kind='customer',name='Sample customer',contact='')['account'];a=self.ok('account-adjust',account=a['id'],account_revision=a['revision'],amount=500,direction='add',reason='Sample credit')['account']
  cart=self.add(self.cart(),self.product(price=1002,taxable=False));s=self.ok('credit',cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=500,tender=500)['sale']
  self.assertEqual((s['store_credit'],s['cash_paid'],s['cash_rounding']),(500,500,-2))
  self.assertEqual(self.post('email-receipt',sale=s['id'],email='test@example.invalid')[0],409)
  with server.connect() as c:
   settings=dict(server.customer_settings(c,'email'),enabled=True,sender='fixture@example.invalid');c.execute("INSERT OR REPLACE INTO customer_settings VALUES('email',1,?)",(json.dumps(settings),));c.commit()
  with patch.dict(os.environ,{'COASTYOUTH_GMAIL_APP_PASSWORD':'fixture-only'}):
   args=dict(sale=s['id'],email='customer@example.invalid',request=uuid.uuid4().hex)
   first=self.f.call('pos/email-receipt',args);self.assertEqual(first[0],200,first);self.assertEqual(self.f.call('pos/email-receipt',args),first)
  with server.connect() as c:
   rows=c.execute("SELECT * FROM customer_delivery WHERE kind='receipt'").fetchall();self.assertEqual(len(rows),1);self.assertIn('Cash rounding: $-0.02',json.loads(rows[0]['body'])['text'])
  self.assertEqual(self.f.call('pos/today-receipts')[1]['sales'][0]['id'],s['id'])
if __name__=='__main__':unittest.main()
