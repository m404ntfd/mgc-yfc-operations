"""Registration targets only device/configuration records in an isolated shared server."""
import unittest
from test_computer_updates import ComputerTests
import server

class RegistrationTests(ComputerTests):
 def identity(self, app='office', device='b'*32, computer='1'*32):
  return dict(app=app,device=device,version='1.0.0',computer=dict(id=computer,hostname='FIXTURE-PC',macs=['AA:BB:CC:DD:EE:00'],os='Windows test'))
 def test_admin_registration_shared_identity_persists(self):
  staff=self.f.client('t');self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  data=self.identity()
  self.assertEqual(self.f.call('computers/self',data,staff)[0],200)
  self.assertFalse(self.f.call('computers/self',data,staff)[1]['computer']['registered'])
  register=dict(id='1'*32,revision=0,name='Thrift Mart office',role='office')
  self.assertEqual(self.f.call('computers/register',register,staff)[0],403)
  self.assertEqual(self.f.call('computers/register',register)[0],200)
  with server.connect() as c:c.execute("UPDATE retail_computer_apps SET ip='192.0.2.50',seen=0")
  data['computer'].update(hostname='RENAMED-PC',macs=[])
  for app,device in [('office','b'*32),('ops','c'*32),('pos','a'*32)]:
   result=self.f.call('computers/self',dict(data,app=app,device=device),staff)[1]
   self.assertEqual(result['computer']['name'],'Thrift Mart office');self.assertEqual(result['computer']['revision'],1)
  with server.connect() as c:
   server.init_computers(c)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_computers').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_computer_apps').fetchone()[0],3)
  self.assertEqual(self.f.call('computers/self',self.identity(computer='2'*32),staff)[0],409)
 def test_existing_checkout_assignment_is_preserved(self):
  self.f.call('computers/self',self.identity('pos','a'*32))
  with server.connect() as c:
   c.execute("INSERT INTO retail_terminals VALUES('existing','Original checkout',NULL,NULL,1,3,'previous')")
  register=dict(id='1'*32,revision=0,name='Thrift Mart front',role='pos',app='pos',device='a'*32,terminal='existing')
  code,result=self.f.call('computers/register',register);self.assertEqual(code,200,result)
  self.assertEqual(self.f.call('computers/self',self.identity('pos','a'*32))[1]['terminal']['name'],'Original checkout')
  with server.connect() as c:before=dict(c.execute("SELECT * FROM retail_terminals WHERE id='existing'").fetchone())
  self.assertEqual(self.f.call('computers/register',dict(register,revision=1,name='Renamed computer',terminal='different'))[0],200)
  with server.connect() as c:self.assertEqual(dict(c.execute("SELECT * FROM retail_terminals WHERE id='existing'").fetchone()),before)
  self.f.call('computers/self',self.identity('pos','d'*32,'2'*32))
  self.assertEqual(self.f.call('computers/register',dict(register,id='2'*32,revision=0,device='d'*32))[0],409)
  with server.connect() as c:
   self.assertEqual(c.execute("SELECT registered FROM retail_computers WHERE id=?",('2'*32,)).fetchone()[0],0)
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_registration_preserves_populated_business_records(self):
  with server.connect() as c:
   account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute("INSERT INTO work_periods VALUES(901,?,100,NULL,'Office',NULL)",(account,))
   c.execute('INSERT INTO work_breaks VALUES(902,901,200,NULL)')
   c.execute("INSERT INTO jobs VALUES('fixture-reservation',8,?)",('{"type":"Delivery","customer":"Fixture","notes":"Preserve"}',))
   c.execute("INSERT INTO photos VALUES('fixture-reservation',0,?)",(b'fixture-attachment',))
   c.execute("INSERT INTO pos_products VALUES('fixture-item',?)",('{"name":"Fixture","price":1200,"active":true}',))
   c.execute("INSERT INTO pos_carts VALUES('fixture-cart',?,3,'paid',?,1000)",(account,'{"total":1200,"lines":[]}'))
   c.execute("INSERT INTO pos_sales VALUES(903,'fixture-cart',?,?)",(account,'{"total":1200,"lines":[]}'))
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'retail_computer%' AND name NOT IN ('audit','sqlite_sequence')")]
   before={name:[tuple(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in tables}
  self.f.call('computers/self',self.identity());self.register()
  self.f.call('computers/self',self.identity());self.f.call('computers/state')
  with server.connect() as c:
   server.init_computers(c);server.init_computers(c)
   for name,rows in before.items():self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')],rows,name)
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_selected_computer_all_three_apps_and_ops_ticket(self):
  for app,device in [('office','b'*32),('ops','c'*32),('pos','a'*32)]:self.f.call('computers/self',self.identity(app,device))
  self.register();self.f.call('computers/self',self.identity('ops','d'*32,'2'*32));self.register('2'*32)
  code,result=self.f.call('computers/start',dict(computers=['1'*32],seconds=60));self.assertEqual(code,200,result)
  self.assertEqual(result['campaigns']['ops']['targets'],['c'*32])
  job=result['campaigns']['ops'];self.assertEqual(self.f.call('ops-update/ticket?id='+job['id'])[0],200)
  self.assertEqual(self.f.call('computers/self',self.identity('ops','c'*32))[1]['campaign']['id'],job['id'])
  self.assertNotIn('campaign',self.f.call('computers/self',self.identity('ops','d'*32,'2'*32))[1])
  self.f.call('computers/cancel',{});self.assertEqual(self.f.call('ops-update/ticket?id='+job['id'])[0],404)
if __name__=='__main__':unittest.main()
