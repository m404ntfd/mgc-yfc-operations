import json,unittest,uuid
from test_retail_workflows import WorkflowTests
import server

class TrainingTests(unittest.TestCase):
 setUp=WorkflowTests.setUp
 tearDown=WorkflowTests.tearDown
 post=WorkflowTests.post
 ok=WorkflowTests.ok
 product=WorkflowTests.product
 cart=WorkflowTests.cart
 add=WorkflowTests.add
 def toggle(self,enabled,revision=0):return self.ok('training-mode',enabled=enabled,revision=revision)
 def financial(self):
  with server.connect() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in ('pos_sales','pos_credit_accounts','pos_credit_ledger','pos_refunds','retail_cash_advances','thrift_customers','thrift_intake','retail_gifts','work_periods','work_breaks','jobs','retail_drawers','retail_drawer_events')]
   return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}
 def test_practice_cash_and_retry_leave_financial_records_unchanged(self):
  p=self.product();before=self.financial();self.toggle(True);cart=self.add(self.cart(),p)
  self.assertTrue(cart['training']);payload=dict(request=uuid.uuid4().hex,cart=cart['id'],revision=cart['revision'],tender=2000)
  code,result=self.f.call('pos/cash',payload);self.assertEqual(code,200,result);self.assertTrue(result['sale']['training'])
  self.assertEqual(self.f.call('pos/cash',payload),(code,result));self.assertEqual(before,self.financial())
  report=self.f.call('pos/training-report')[1];self.assertEqual(report['count'],1);self.assertEqual(report['transactions'][0]['id'],result['sale']['id'])
  self.toggle(False,1);self.assertFalse(self.cart()['training'])
 def test_mode_conflicts_and_held_cart_are_isolated(self):
  p=self.product();cart=self.add(self.cart(),p)
  self.assertEqual(self.post('training-mode',enabled=True,revision=0)[0],409)
  self.ok('hold',cart=cart['id'],revision=cart['revision']);self.toggle(True)
  self.assertEqual(self.post('resume',cart=cart['id'],revision=cart['revision']+1)[0],409)
  self.assertEqual(self.post('product-save',name='Should not exist',category='Retail',price=1,taxable=True,rules={})[0],409)
  self.assertEqual(self.post('training-mode',enabled=False,revision=0)[0],409)
 def test_practice_credit_does_not_debit_customer_balance(self):
  p=self.product();account=self.ok('account-create',kind='customer',name='Sample customer',contact='')['account']
  account=self.ok('account-adjust',account=account['id'],account_revision=account['revision'],amount=5000,direction='add',reason='Sample balance')['account']
  before=self.financial();self.toggle(True);cart=self.add(self.cart(),p)
  sale=self.ok('credit',cart=cart['id'],revision=cart['revision'],account=account['id'],account_revision=account['revision'],amount=cart['total'],tender=0)['sale']
  self.assertTrue(sale['training']);self.assertEqual(before,self.financial())
  self.assertEqual(self.post('account-adjust',account=account['id'],account_revision=account['revision'],amount=100,direction='add',reason='Not allowed')[0],409)
 def test_practice_advance_is_replay_safe_without_changing_a_drawer(self):
  device='d'*32
  self.ok('terminal-save',name='SAMPLE Training checkout',device=device,enabled=True)
  programs=self.f.call('pos/programs')[1]['programs'];self.ok('programs-save',**dict(programs,drawers=True))
  context=self.f.call('pos/cash-advance-setup?device='+device)[1]
  before=self.financial();self.ok('training-mode',device=device,enabled=True,revision=0)
  payload=dict(request=uuid.uuid4().hex,device=device,terminal=context['context']['terminal'],store_id=context['context']['store_id'],drawer_id=None,employee=context['employees'][0]['id'],amount=2500,reason='Practice advance',confirmed=True)
  code,result=self.f.call('pos/cash-advance',payload);self.assertEqual(code,200,result);self.assertTrue(result['advance']['training'])
  self.assertEqual(self.f.call('pos/cash-advance',payload),(code,result));self.assertEqual(before,self.financial())
  self.assertEqual(self.f.call('pos/cash-advance-status?request='+payload['request'])[1]['advance'],result['advance'])
  self.assertEqual(self.f.call('pos/training-report')[1]['transactions'][0]['kind'],'cash-advance')
  staff=self.f.client('b');self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  self.assertEqual(self.f.call('pos/cash-advance',dict(payload,request=uuid.uuid4().hex),staff)[0],403)
 def test_cashier_can_reprint_own_training_receipts_without_report_access(self):
  p=self.product();staff=self.f.client('staff')
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  def send(path,**data):
   code,r=self.f.call('pos/'+path,dict(request=uuid.uuid4().hex,**data),staff);self.assertEqual(code,200,r);return r
  send('training-mode',enabled=True,revision=0)
  cart=send('new')['cart'];cart=send('add',cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1)['cart']
  sale=send('cash',cart=cart['id'],revision=cart['revision'],tender=2000)['sale']
  code,r=self.f.call('pos/training-receipts',client=staff);self.assertEqual(code,200,r);self.assertEqual([s['id'] for s in r['transactions']],[sale['id']])
  self.assertEqual(self.f.call('pos/training-report',client=staff)[0],403)
 def test_canceled_practice_is_logged_and_not_added_to_totals(self):
  p=self.product();before=self.financial();self.toggle(True);cart=self.add(self.cart(),p)
  self.ok('discard',cart=cart['id'],revision=cart['revision'],reason='Practice cancellation')
  report=self.f.call('pos/training-report')[1];self.assertEqual((report['count'],report['total']),(1,0))
  self.assertEqual(report['transactions'][0]['kind'],'canceled');self.assertEqual(report['transactions'][0]['reason'],'Practice cancellation');self.assertEqual(before,self.financial())

if __name__=='__main__':unittest.main()
