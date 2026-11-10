import time,unittest,json
from unittest.mock import patch
from test_update_coordination import CoordinatorFixture
import server
class ComputerTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture()
  self.old=(server.POS_UPDATE_RELEASE,server.OFFICE_UPDATE_RELEASE,server.OPS_UPDATE_RELEASE)
  server.POS_UPDATE_RELEASE={'version':'9.0.0','checked':time.time(),'checking':False}
  server.OPS_UPDATE_RELEASE={'version':'9.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
  server.OFFICE_UPDATE_RELEASE={'version':'9.0.0','checked':time.time(),'checking':False}
 def tearDown(self):
  server.POS_UPDATE_RELEASE,server.OFFICE_UPDATE_RELEASE,server.OPS_UPDATE_RELEASE=self.old;self.f.close()
 def heartbeat(self,app='pos',device='a'*32,computer='1'*32,version='1.0.0'):
  return self.f.call(app+'-update/heartbeat',dict(device=device,version=version,updater=True,status='Connected',computer=dict(id=computer,hostname='TEST-POS',macs=['AA:BB:CC:DD:EE:00'],os='Windows test')))
 def register(self,ident='1'*32,revision=0):
  return self.f.call('computers/register',dict(id=ident,revision=revision,name='Front checkout',role='pos'))
 def test_grouping_registration_restart_and_update_all(self):
  self.assertEqual(self.heartbeat()[0],200);self.assertEqual(self.heartbeat('office','b'*32)[0],200)
  state=self.f.call('computers/state')[1];self.assertEqual(len(state['computers']),1);self.assertEqual(len(state['computers'][0]['apps']),2)
  self.assertEqual(self.f.call('computers/start',dict(computers=['1'*32],seconds=30))[0],400)
  self.assertEqual(self.register()[0],200);self.assertEqual(self.register()[0],409)
  code,result=self.f.call('computers/start',dict(computers=['1'*32],seconds=60));self.assertEqual(code,200,result)
  jobs=result['campaigns'];self.assertEqual(jobs['pos']['targets'],['a'*32]);self.assertEqual(jobs['office']['targets'],['b'*32]);self.assertTrue(jobs['office']['automatic'])
  self.assertEqual(self.heartbeat()[1]['campaign']['id'],jobs['pos']['id'])
  self.assertEqual(self.f.call('pos-update/ticket?id='+jobs['pos']['id'])[0],200)
  server.POS_UPDATE_DEVICES.clear();server.OFFICE_UPDATE_DEVICES.clear()
  with server.connect() as c:c.execute('UPDATE retail_computer_apps SET seen=0,ip=?',('192.0.2.1',))
  result=self.f.call('computers/state')[1];self.assertEqual(result['computers'][0]['apps'][0]['progress'],'Waiting for application to reconnect')
  self.heartbeat(version='9.0.0');self.heartbeat('office','b'*32,version='9.0.0')
  result=self.f.call('computers/state')[1];self.assertEqual(len(result['computers']),1);self.assertTrue(all(a['complete'] for a in result['computers'][0]['apps']))
  self.assertEqual(self.f.call('computers/cancel',{})[0],200);self.assertEqual(self.f.call('pos-update/ticket?id='+jobs['pos']['id'])[0],404)
 def test_permissions_target_snapshot_and_no_duplicate_reassignment(self):
  other=self.f.client('fleet-employee');self.f.call('login',dict(name='Employee',password='testpassword'),other)
  for path,data in [('computers/state',None),('computers/register',{}),('computers/start',{}),('computers/check',{}),('computers/cancel',{})]:self.assertEqual(self.f.call(path,data,other)[0],403)
  self.heartbeat();self.register();self.f.call('computers/start',dict(computers=['1'*32],seconds=30))
  self.assertEqual(self.heartbeat(computer='2'*32)[0],409)
  result=self.heartbeat(device='c'*32,computer='2'*32)[1];self.assertFalse(result.get('campaign'))
  self.assertEqual(self.f.call('computers/start',dict(computers=['1'*32],seconds=30))[0],409)
 def test_start_atomicity_and_operational_rows_untouched(self):
  self.heartbeat();self.heartbeat('office','b'*32);self.register()
  with server.connect() as c:
   before={r[0]:c.execute('SELECT * FROM "'+r[0]+'" ORDER BY rowid').fetchall() for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'retail_computer%' AND name NOT IN ('audit','sqlite_sequence')")}
  server.OFFICE_UPDATE_RELEASE={'error':'Unavailable','checked':time.time()}
  self.assertEqual(self.f.call('computers/start',dict(computers=['1'*32],seconds=60))[0],409)
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_computer_updates').fetchone()[0],0)
   for name,rows in before.items():self.assertEqual(c.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall(),rows,name)
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
if __name__=='__main__':unittest.main()
