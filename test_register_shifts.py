"""Isolated shift closure, payment boundary, legacy recovery and audit preservation."""
import datetime as dt
import json
import sqlite3
import unittest
import uuid
from unittest.mock import patch
from zoneinfo import ZoneInfo
import server
from test_update_coordination import CoordinatorFixture

def central(value):return dt.datetime.fromisoformat(value).replace(tzinfo=ZoneInfo('America/Chicago')).timestamp()

class RegisterShiftTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.now=central('2026-11-24T12:00:00');self.clock=patch.object(server,'shifts_clock',side_effect=lambda:self.now);self.clock.start()
  self.devices=['1'*32,'2'*32];self.terminals=[]
  self.post('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
  for i,device in enumerate(self.devices):self.terminals.append(self.post('terminal-save',name='Checkout '+str(i+1),device=device,hostname='POS'+str(i+1),enabled=True,store_id='thrift-mart')['id'])
  self.product=self.post('product-save',name='Sample book',category='Books',price=200,taxable=True)['ids'][0]
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  self.employee=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),self.employee)
 def tearDown(self):self.clock.stop();self.f.close()
 def call(self,path,data=None,client=None):return self.f.call('pos/'+path,data,client)
 def post(self,path,client=None,**data):
  code,result=self.call(path,dict(request=uuid.uuid4().hex,**data),client);self.assertEqual(code,200,result);return result
 def get(self,path,device=None):
  code,result=self.call(path+('?' if '?' not in path else '&')+'device='+(device or self.devices[0]));self.assertEqual(code,200,result);return result
 def cart(self,device=None,client=None,held=False,training=False):
  device=device or self.devices[0]
  if training:self.post('training-mode',client=client,device=device,enabled=True,revision=0)
  cart=self.post('new',client=client,device=device)['cart']
  cart=self.post('add',client=client,device=device,cart=cart['id'],revision=cart['revision'],product=self.product,quantity=1)['cart']
  if held:cart=self.post('hold',client=client,device=device,cart=cart['id'],revision=cart['revision'])['cart']
  return cart
 def pay(self,cart,device=None):return self.post('cash',device=device or self.devices[0],cart=cart['id'],revision=cart['revision'],tender=500)['sale']
 def test_manual_blocks_all_users_then_closes_idempotently(self):
  cart=self.cart(client=self.employee,held=True);other=self.cart(self.devices[1]);status=self.get('shift-status')
  self.assertEqual(status['open'][0]['cashier'],'Employee');ident=status['current']['id']
  data=dict(device=self.devices[0],shift=ident,confirmed=True,request=uuid.uuid4().hex)
  self.assertEqual(self.call('shift-end',data)[0],409)
  self.post('discard',client=self.employee,device=self.devices[0],cart=cart['id'],revision=cart['revision'],reason='Customer left')
  code,result=self.call('shift-end',data);self.assertEqual(code,200,result)
  self.assertEqual(self.call('shift-end',data)[1],result)
  self.assertEqual(result['report']['voided'],1);self.assertEqual(result['report']['cash'],0)
  with server.connect() as c:self.assertEqual(c.execute('SELECT status FROM pos_carts WHERE id=?',(other['id'],)).fetchone()[0],'open')
  nextcart=self.cart();self.assertNotEqual(self.get('shift-status')['current']['id'],ident)
 def test_automatic_closes_only_unpaid_with_previous_day_and_preserves_money(self):
  paid=self.pay(self.cart());open_cart=self.cart(held=True);training=self.cart(self.devices[1],training=True)
  before=self.get('shift-status');ident=before['current']['id']
  with server.connect() as c:paid_bytes=c.execute('SELECT body FROM pos_sales WHERE id=?',(paid['id'],)).fetchone()[0]
  self.now=central('2026-11-25T00:00:01');status=self.get('shift-status');report=status['last']
  self.assertIsNone(status['current']);self.assertEqual(status['open'],[])
  self.assertEqual(report['business_date'],'2026-11-24');self.assertEqual(report['reason'],'end-of-business-day')
  self.assertEqual(report['sales_total'],paid['total']);self.assertEqual(report['completed'],1);self.assertEqual(report['voided'],1)
  void=next(e for e in report['events'] if e['kind']=='void');self.assertEqual(void['original']['lines'],open_cart['lines']);self.assertEqual(void['collected'],0);self.assertEqual(void['total'],0)
  self.assertEqual(self.get('shift-status')['last'],report)
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT body FROM pos_sales WHERE id=?',(paid['id'],)).fetchone()[0],paid_bytes)
   self.assertEqual(c.execute('SELECT count(*) FROM pos_sales').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT status FROM pos_carts WHERE id=?',(training['id'],)).fetchone()[0],'open')
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM retail_shift_events WHERE shift=?',(ident,))
   with self.assertRaises(sqlite3.IntegrityError):c.execute('UPDATE retail_register_shifts SET closed=NULL WHERE id=?',(ident,))
  self.assertEqual(self.call('cash',dict(device=self.devices[0],cart=open_cart['id'],revision=open_cart['revision'],tender=500,request=uuid.uuid4().hex))[0],409)
 def test_exact_cutoff_payment_and_retry(self):
  cart=self.cart();self.now=central('2026-11-24T23:59:58');payment=dict(device=self.devices[0],cart=cart['id'],revision=cart['revision'],tender=500,request=uuid.uuid4().hex)
  code,paid=self.call('cash',payment);self.assertEqual(code,200,paid)
  unpaid=self.cart();self.now=central('2026-11-24T23:59:59')
  self.assertEqual(self.call('cash',payment)[1],paid)
  self.assertEqual(self.call('cash',dict(payment,cart=unpaid['id'],revision=unpaid['revision'],request=uuid.uuid4().hex))[0],409)
  new=self.cart();self.assertEqual(self.get('shift-status')['current']['business_date'],'2026-11-25')
 def test_settings_store_scope_validation_and_open_deadline_snapshot(self):
  cart=self.cart();current=self.get('shift-status')['current'];settings=self.get('shift-settings')
  self.assertEqual(settings['cutoff'],'23:59:59')
  for bad in ('24:00:00','23:60:00','12:00','foo',None):self.assertEqual(self.call('shift-settings-save',dict(settings,cutoff=bad,request=uuid.uuid4().hex))[0],400)
  self.assertEqual(self.call('shift-settings-save',dict(settings,request=uuid.uuid4().hex),self.employee)[0],403)
  updated=self.post('shift-settings-save',**dict(settings,cutoff='22:00:00',print_format='receipt'))
  self.assertEqual(self.call('shift-settings-save',dict(settings,request=uuid.uuid4().hex))[0],409)
  self.cart();self.assertEqual(self.get('shift-status')['current']['deadline'],current['deadline'])
  self.assertEqual(self.get('shift-settings?store_id=binopoly')['cutoff'],'23:59:59')
 def test_restart_catchup_and_legacy_adoption_without_rewriting_original(self):
  cart=self.cart();ident=self.get('shift-status')['current']['id']
  with server.connect() as c:
   original=c.execute('SELECT body FROM pos_carts WHERE id=?',(cart['id'],)).fetchone()[0]
   # Simulate a pre-feature cart without erasing any operational data.
   legacy=uuid.uuid4().hex;owner=c.execute('SELECT owner FROM pos_carts WHERE id=?',(cart['id'],)).fetchone()[0]
   c.execute('INSERT INTO pos_carts VALUES(?,?,1,?,?,?)',(legacy,owner,'open',original,central('2026-11-22T11:00:00')));c.commit()
  self.now=central('2026-11-27T09:00:00');server.init();server.shifts_tick();server.shifts_tick()
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT body FROM pos_carts WHERE id=?',(cart['id'],)).fetchone()[0],original)
   self.assertEqual(c.execute('SELECT count(*) FROM retail_shift_events WHERE kind="void"').fetchone()[0],2)
   row=c.execute('SELECT s.business_date FROM retail_register_shifts s JOIN retail_shift_carts c ON s.id=c.shift WHERE c.cart=?',(legacy,)).fetchone();self.assertEqual(row[0],'2026-11-22')
 def test_terminal_transfer_and_report_access(self):
  cart=self.cart(held=True)
  cart=self.post('resume',device=self.devices[1],cart=cart['id'],revision=cart['revision'])['cart'];paid=self.pay(cart,self.devices[1])
  first=self.get('shift-status');second=self.get('shift-status',self.devices[1]);self.assertEqual(first['current']['completed'],0);self.assertEqual(second['current']['completed'],1)
  self.assertEqual(self.call('shift-report?id='+str(second['current']['id'])+'&device='+self.devices[0],client=self.employee)[0],403)
  self.assertEqual(self.call('shift-history',client=self.employee)[0],403)
 def test_cash_advance_mixed_credit_and_refund_totals(self):
  device=self.devices[0]
  account=self.post('account-create',kind='customer',name='Sample customer',contact='')['account']
  account=self.post('account-adjust',account=account['id'],account_revision=account['revision'],amount=100,direction='add',reason='Sample starting credit')['account']
  cart=self.cart();sale=self.post('credit',device=device,cart=cart['id'],revision=cart['revision'],account=account['id'],account_revision=account['revision'],amount=100,tender=200)['sale']
  with server.connect() as c:employee=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
  context=self.get('cash-advance-setup')['context']
  self.post('cash-advance',device=device,terminal=context['terminal'],store_id=context['store_id'],drawer_id=context['drawer_id'],employee=employee,amount=50,reason='Sample approved advance',confirmed=True)
  policy=self.get('policies')['policy']
  refund=self.post('refund',device=device,sale=sale['id'],lines=[dict(index=0,quantity=1)],reason='Sample return',refund_revision=0,policy_revision=policy['revision'],confirmed=True)['refund']
  report=self.get('shift-status')['current']
  self.assertEqual(report['cash'],sale['tender']-sale['change']);self.assertEqual(report['store_credit'],100)
  self.assertEqual(report['cash_refunds'],refund['cash']);self.assertEqual(report['credit_refunds'],refund['store_credit'])
  self.assertEqual(report['advances'],50);self.assertEqual(report['net_cash'],-50)
  self.assertEqual([e['kind'] for e in report['events']].count('refund'),1)
 def test_dst_and_custom_cutoff(self):
  before=central('2026-11-24T21:59:59');day,end=server.shifts_period(before,'22:00:00');self.assertEqual(day,'2026-11-24');self.assertEqual(end,central('2026-11-24T22:00:00'))
  self.assertEqual(server.shifts_period(end,'22:00:00')[0],'2026-11-25')
  # Repeated 01:30 closes once, on its later occurrence.
  day,end=server.shifts_period(central('2026-11-01T00:00:00'),'01:30:00')
  self.assertEqual(dt.datetime.fromtimestamp(end,ZoneInfo('America/Chicago')).fold,1)
  day,end=server.shifts_period(central('2026-03-08T00:00:00'),'02:30:00')
  self.assertEqual(dt.datetime.fromtimestamp(end,ZoneInfo('America/Chicago')).hour,3)

if __name__=='__main__':unittest.main()
