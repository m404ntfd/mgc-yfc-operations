import json,time,unittest
from unittest.mock import patch
from test_update_coordination import CoordinatorFixture
import server

class OnlineRequestTests(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.guest=self.f.client('g');self.employee=self.f.client('e')
  self.f.call('login',dict(name='Employee',password='testpassword'),self.employee)
 def tearDown(self):self.f.close()
 def test_durations_expiry_restart_and_manual_resume(self):
  self.assertFalse(self.f.call('online-requests',client=self.guest)[1]['paused'])
  for hours in (8,12,24):
   current=self.f.call('online-requests')[1];now=time.time()
   code,status=self.f.call('online-requests',dict(hours=hours,revision=current['revision']))
   self.assertEqual(code,200);self.assertTrue(status['paused']);self.assertAlmostEqual(status['paused_until']-now,hours*3600,delta=3)
   server.init();self.assertEqual(self.f.call('online-requests')[1]['paused_until'],status['paused_until'])
   with patch.object(server.time,'time',return_value=status['paused_until']):
    self.assertFalse(self.f.call('online-requests',client=self.guest)[1]['paused'])
  self.assertEqual(self.f.call('online-requests',dict(resume=True,revision=status['revision']))[0],200)
  self.assertFalse(self.f.call('state')[1]['onlineRequests']['paused'])
  with server.connect() as c:self.assertEqual(c.execute("SELECT count(*) FROM audit WHERE action IN ('Paused online requests','Resumed online requests')").fetchone()[0],4)
 def test_permissions_validation_stale_revision_and_public_privacy(self):
  self.assertEqual(self.f.call('online-requests',dict(hours=8,revision=0),self.guest)[0],401)
  with server.connect() as c:
   c.execute('INSERT OR REPLACE INTO user_grants VALUES(?,?)',('Employee',json.dumps({k:False for k in server.PERMISSIONS})))
  self.assertEqual(self.f.call('online-requests',dict(hours=8,revision=0),self.employee)[0],403)
  for data in [dict(hours=1),dict(hours=True),dict(hours=8.0),dict(hours='8'),dict(resume=False),dict(hours=8,resume=True)]:
   self.assertEqual(self.f.call('online-requests',dict(data,revision=0))[0],400)
  self.assertEqual(self.f.call('online-requests',dict(hours=8,revision=0))[0],200)
  self.assertEqual(self.f.call('online-requests',dict(hours=12,revision=0))[0],409)
  result=self.f.call('online-requests',client=self.guest)[1]
  self.assertEqual(set(result),{'service','supported','paused','status','paused_until','server_now','revision'})
 def test_blocks_online_writes_but_preserves_existing_data_and_staff_work(self):
  with server.connect() as c:
   c.execute('INSERT OR REPLACE INTO user_grants VALUES(?,?)',('Employee',json.dumps({k:k=='submit_requests' for k in server.PERMISSIONS})))
   c.execute('UPDATE permissions SET can_create=0 WHERE name=?',('Employee',))
  request=dict(customer='Synthetic donor',type='Pickup',status='Requested',notes='Existing request')
  self.assertEqual(self.f.call('save',request,self.employee)[0],200)
  with server.connect() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") if r[0] not in ('online_request_settings','audit')]
   before={t:[tuple(r) for r in c.execute('SELECT * FROM "'+t+'"')] for t in tables}
  paused=self.f.call('online-requests',dict(hours=8,revision=0))[1]
  for marker in ({},{'online_request':True}):
   code,result=self.f.call('save',dict(request,**marker),self.employee)
   self.assertEqual(code,423);self.assertEqual(result['code'],'online_requests_paused')
  server.init()
  with server.connect() as c:
   for t,rows in before.items():self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM "'+t+'"')],rows,t)
  # Staff-entered appointments continue while website submissions are paused.
  self.f.call('vehicle',dict(name='Test truck'))
  job=dict(request,phone='2285550100',address='Test address',items='Test chair',vehicle='Test truck',start='2030-01-01T09:00',end='2030-01-01T10:00',status='Scheduled')
  self.assertEqual(self.f.call('save',job)[0],200)
  self.f.call('online-requests',dict(resume=True,revision=paused['revision']))
  self.assertEqual(self.f.call('save',dict(request,online_request=True),self.employee)[0],200)

if __name__=='__main__':unittest.main()
