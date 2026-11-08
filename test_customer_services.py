import unittest,json,datetime as dt,time,uuid,urllib.request,urllib.error
from unittest.mock import patch
from test_update_coordination import CoordinatorFixture
import server

class CustomerTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.post('settings',store='Sample store',tax_bps=700,confirmed=True)
  self.job={'customer':'Sample customer','type':'Delivery','start':(dt.datetime.now()+dt.timedelta(hours=12)).isoformat(timespec='minutes'),'end':(dt.datetime.now()+dt.timedelta(hours=13)).isoformat(timespec='minutes'),'address':'123 Sample Street','status':'Scheduled','notes':'PRIVATE NOTES','phone':'PRIVATE PHONE'}
  with server.connect() as c:c.execute('INSERT INTO jobs VALUES(?,?,?)',('reservation-fixture',8,json.dumps(self.job)));c.execute('INSERT INTO photos VALUES(?,?,?)',('reservation-fixture',0,b'original-attachment'))
 def tearDown(self):self.f.close()
 def post(self,path,**data):
  code,result=self.f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));self.assertEqual(code,200,result);return result
 def save(self,kind,**data):
  current=self.f.call('pos/customer-settings')[1][kind];return self.post('customer-settings-save',kind=kind,**dict(current,**data))['settings']
 def contact(self,**data):return self.post('reservation-contact',**dict(job='reservation-fixture',revision=0,email='customer@example.test',confirmations=True,reminders=True,**data))
 def display(self,token):
  req=urllib.request.Request(f'http://127.0.0.1:{self.f.port}/api/customer-display',headers={'X-Display-Token':token})
  try:
   with urllib.request.urlopen(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_receipt_snapshot_and_reservations_untouched(self):
  with server.connect() as c:before=[tuple(r) for r in c.execute('SELECT * FROM jobs')];photos=[tuple(r) for r in c.execute('SELECT * FROM photos')]
  self.save('receipt',address='Sample address',footer='Original footer',policy='30-day returns')
  cart=self.post('new')['cart'];cart=self.post('add',cart=cart['id'],revision=cart['revision'],name='Sample',category='Retail',price=100,quantity=1,taxable=True)['cart'];sale=self.post('cash',cart=cart['id'],revision=cart['revision'],tender=200)['sale'];self.assertEqual(sale['receipt_design']['footer'],'Original footer')
  self.save('receipt',footer='New footer');self.assertEqual(self.f.call('pos/sales')[1]['sales'][0]['receipt_design']['footer'],'Original footer')
  self.contact();self.post('reservation-preview',job='reservation-fixture',kind='confirmation')
  with server.connect() as c:self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM jobs')],before);self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM photos')],photos)
 def test_preview_paused_queue_and_no_duplicate_enrollment(self):
  self.contact();self.contact_again=self.post('reservation-contact',job='reservation-fixture',revision=1,email='customer@example.test',confirmations=True,reminders=True)
  with patch.object(server,'customer_smtp') as send:
   server.customer_delivery_tick();server.customer_delivery_tick();send.assert_not_called()
  data=self.f.call('pos/reservation-messages')[1];self.assertEqual(len(data['deliveries']),2)
  preview=self.post('reservation-preview',job='reservation-fixture',kind='confirmation');self.assertIn('Sample customer',preview['text']);self.assertNotIn('PRIVATE',preview['text'])
 def test_send_once_and_canceled_reservation_suppresses_reminder(self):
  with patch.dict(server.os.environ,{'COASTYOUTH_GMAIL_APP_PASSWORD':'fixture-only-secret'}):
   self.save('email',sender='sender@example.test',enabled=True);self.contact()
   with patch.object(server,'customer_smtp') as send:
    server.customer_delivery_tick();self.assertEqual(send.call_count,1)
    with server.connect() as c:
     j=dict(self.job,status='Canceled');c.execute('UPDATE jobs SET body=? WHERE id=?',(json.dumps(j),'reservation-fixture'))
    server.customer_delivery_tick();server.customer_delivery_tick();self.assertEqual(send.call_count,1)
   statuses=[x['status'] for x in self.f.call('pos/reservation-messages')[1]['deliveries']];self.assertIn('sent',statuses);self.assertIn('canceled',statuses)
 def test_uncertain_delivery_requires_explicit_review(self):
  with patch.dict(server.os.environ,{'COASTYOUTH_GMAIL_APP_PASSWORD':'fixture-only-secret'}):
   self.save('email',sender='sender@example.test',enabled=True);self.post('reservation-contact',job='reservation-fixture',revision=0,email='customer@example.test',confirmations=True,reminders=False)
   with patch.object(server,'customer_smtp',side_effect=TimeoutError) as send:
    server.customer_delivery_tick();server.customer_delivery_tick();self.assertEqual(send.call_count,1)
   message=self.f.call('pos/reservation-messages')[1]['deliveries'][0];self.assertEqual(message['status'],'uncertain')
   self.assertEqual(self.f.call('pos/delivery-retry',dict(id=message['id'],checked_sent=False,request=uuid.uuid4().hex))[0],400)
   self.post('delivery-retry',id=message['id'],checked_sent=True)
   with patch.object(server,'customer_smtp') as send:server.customer_delivery_tick();send.assert_called_once()
 def test_stale_reservation_new_message_and_past_exclusion(self):
  self.contact()
  with server.connect() as c:
   changed=dict(self.job,start=(dt.datetime.now()+dt.timedelta(days=2)).isoformat());c.execute('UPDATE jobs SET body=? WHERE id=?',(json.dumps(changed),'reservation-fixture'));server.customer_schedule(c)
   statuses=[r[0] for r in c.execute('SELECT status FROM customer_delivery')];self.assertEqual(statuses.count('canceled'),2);self.assertEqual(statuses.count('pending'),2)
   changed['start']='2000-01-01T12:00';c.execute('UPDATE jobs SET body=? WHERE id=?',(json.dumps(changed),'reservation-fixture'));server.customer_schedule(c);self.assertEqual(c.execute("SELECT COUNT(*) FROM customer_delivery WHERE status='pending'").fetchone()[0],0)
 def test_returning_to_original_date_creates_fresh_messages(self):
  self.contact()
  with server.connect() as c:
   for job in (dict(self.job,start=(dt.datetime.now()+dt.timedelta(days=2)).isoformat()), self.job):
    c.execute('UPDATE jobs SET body=? WHERE id=?',(json.dumps(job),'reservation-fixture'));server.customer_schedule(c)
   self.assertEqual(c.execute("SELECT COUNT(*) FROM customer_delivery WHERE status='pending'").fetchone()[0],2)
   self.assertEqual(c.execute("SELECT COUNT(*) FROM customer_delivery WHERE status='canceled'").fetchone()[0],4)
   server.customer_schedule(c)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM customer_delivery').fetchone()[0],6)
 def test_display_privacy_isolation_timeout_and_revocation(self):
  self.save('display',enabled=True);paired=self.post('display-pair');token=paired['token'];self.assertEqual(self.display(token)[1]['state'],'idle')
  cart=self.post('new')['cart'];cart=self.post('add',cart=cart['id'],revision=cart['revision'],name='Sample product',category='Retail',price=1234,quantity=2,taxable=True)['cart']
  self.f.call('pos/display-state',dict(token=token,cart=cart['id'],sale=None));code,data=self.display(token);self.assertEqual(code,200);self.assertEqual(data['total'],2641);self.assertNotIn('owner',data);self.assertNotIn('settings',data)
  e=self.f.client('other');self.f.call('login',dict(name='Employee',password='testpassword'),e);self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('pos/display-state',dict(token=token,cart=cart['id'],sale=None),e)[0],404)
  self.assertEqual(self.display('wrong-token')[0],404)
  with server.connect() as c:c.execute('UPDATE customer_displays SET heartbeat=?',(time.time()-31,))
  self.assertEqual(self.display(token)[1]['state'],'idle')
  self.save('display',enabled=False);self.assertEqual(self.display(token)[0],404)
 def test_permissions_and_secret_not_exposed(self):
  e=self.f.client('restricted');self.f.call('login',dict(name='Employee',password='testpassword'),e);self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  self.assertEqual(self.f.call('pos/customer-settings',client=e)[0],403)
  self.assertEqual(self.f.call('pos/customer-settings-save',dict(kind='receipt',revision=0,request=uuid.uuid4().hex),e)[0],403)
  with patch.dict(server.os.environ,{'COASTYOUTH_GMAIL_APP_PASSWORD':'never-return-this'}):self.assertNotIn('never-return-this',json.dumps(self.f.call('pos/customer-settings')[1]))
  bad=self.f.call('pos/customer-settings-save',dict(kind='receipt',revision=0,logo='data:image/svg+xml;base64,PHN2Zz4=',request=uuid.uuid4().hex));self.assertEqual(bad[0],400)

if __name__=='__main__':unittest.main()
