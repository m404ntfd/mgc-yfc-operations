import json,sqlite3
from test_pos import PosTests
import server

class CreditTests(PosTests):
 def account(self):return self.post('account-create',kind='customer',name='Sample Customer',contact='Reference A')[1]['account']
 def adjust(self,a,amount=5000,**extra):
  data=dict(account=a['id'],account_revision=a['revision'],amount=amount,direction='add',reason='Opening promotional credit');data.update(extra)
  return self.post('account-adjust',**data)
 def test_credit_checkout_retry_and_cash_remainder(self):
  a=self.account();a=self.adjust(a,1000)[1]['account'];cart=self.add(self.configured())[1]['cart']
  args=dict(cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=1000,tender=2000,request='f'*32)
  code,result=self.post('credit',**args);self.assertEqual(code,200,result);self.assertEqual(result['sale']['change'],853)
  self.assertEqual(self.post('credit',**args),(code,result))
  detail=self.f.call('pos/account?id='+str(a['id']))[1];self.assertEqual(detail['account']['balance'],0);self.assertEqual(len(detail['history']),2)
  self.assertEqual(detail['history'][0]['sale'],result['sale']['id'])
  with server.connect() as c:
   for statement in ['UPDATE pos_credit_ledger SET amount=1','DELETE FROM pos_credit_ledger']:
    with self.assertRaises(sqlite3.IntegrityError):c.execute(statement)
 def test_invalid_adjustment_stale_balance_and_permissions(self):
  a=self.account();self.assertEqual(self.adjust(a,100,reason='')[0],400)
  self.assertEqual(self.adjust(a,100,direction='subtract')[0],400)
  self.assertEqual(self.adjust(a,100.1)[0],400)
  new=self.adjust(a)[1]['account'];self.assertEqual(self.adjust(a)[0],409)
  cart=self.add(self.configured())[1]['cart']
  args=dict(cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=1000,tender=2000)
  self.assertEqual(self.post('credit',**args)[0],409)
  args.update(account_revision=new['revision'],amount=5001);self.assertEqual(self.post('credit',**args)[0],400)
  args.update(amount=2147,tender=1);self.assertEqual(self.post('credit',**args)[0],400)
  args['tender']=0;self.assertEqual(self.post('credit',**args)[0],200)
  employee=self.f.client('b');self.f.call('login',dict(name='Employee',password='testpassword'),employee)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('pos/accounts',client=employee)[0],403)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True,'use_store_credit':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('pos/accounts',client=employee)[0],200)
  self.assertEqual(self.f.call('pos/account-adjust',dict(request='e'*32,account=a['id'],amount=100),employee)[0],403)
 def test_failed_ledger_write_rolls_back_sale_and_cart(self):
  a=self.adjust(self.account())[1]['account'];cart=self.add(self.configured())[1]['cart']
  with server.connect() as c:
   owner=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Admin'").fetchone()[0]
   c.execute("CREATE TRIGGER test_credit_fail BEFORE INSERT ON pos_credit_ledger BEGIN SELECT RAISE(ABORT,'Simulated disk failure'); END")
  with self.assertRaises(sqlite3.IntegrityError):
   with server.connect() as c:
    server.pos_post(None,c,{'admin':True,'name':'Admin','receipt_owner':owner},'credit',dict(request='e'*32,cart=cart['id'],revision=cart['revision'],account=a['id'],account_revision=a['revision'],amount=2147,tender=0))
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM pos_sales').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT status FROM pos_carts WHERE id=?',(cart['id'],)).fetchone()[0],'open')
   self.assertEqual(server.pos_credit_account(c,a['id'])['balance'],5000)

 def test_employee_link_and_data_preservation(self):
  with server.connect() as c:
   employee=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute("INSERT INTO jobs VALUES('reservation-1',9,?)",(json.dumps({'notes':'Keep'}),))
   c.execute("INSERT INTO photos VALUES('reservation-1',0,?)",(b'attachment',))
   c.execute("INSERT INTO work_periods VALUES(11,?,100,NULL,'Office',NULL)",(employee,));c.execute('INSERT INTO work_breaks VALUES(21,11,200,NULL)')
  def snapshot():
   with server.connect() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('jobs','photos','work_periods','work_breaks','work_time_card_audit','receipt_profiles')}
  before=snapshot();a=self.post('account-create',kind='employee',name='Employee',employee=employee)[1]['account']
  self.assertEqual(self.post('account-create',kind='employee',name='Employee',employee=employee)[0],409)
  self.adjust(a);server.init();server.init();self.assertEqual(snapshot(),before)
  with server.connect() as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')

if __name__=='__main__':
 import unittest
 unittest.main()
