import unittest,time,os
from unittest.mock import patch
from test_update_coordination import CoordinatorFixture
from remote.client import Client
import server

class ActivityControllerTests(unittest.TestCase):
 def setUp(self):
  self.control=patch.dict(os.environ,{'DISPATCH_CONTROL_TOKEN':'isolated-controller-secret'});self.control.start()
  self.f=CoordinatorFixture();self.native=Client(f'http://127.0.0.1:{self.f.port}',local_control='isolated-controller-secret');self.native.login('Admin','testpassword')
 def tearDown(self):self.f.close();self.control.stop()
 def idle_employee(self,seconds=301):
  with server.LOCK:
   for session in server.SESSIONS.values():
    if session['name']=='Employee':
     session['last_active']=time.time()-seconds
     for conn in session['connections'].values():conn['last_active']=time.time()-seconds
 def test_local_controller_excluded_and_activity_settings(self):
  f=self.f;e=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),e)
  rows=self.native.request('admin/update-connections',activity=False)
  self.assertEqual(len(rows['connections']),2) # Browser admin + employee; no native controller.
  self.assertEqual(rows['inactive_minutes'],5)
  self.idle_employee();f.call('account/connection',{},e)
  rows=f.call('admin/update-connections')[1];self.assertEqual(rows['other_connections'],0)
  self.assertEqual(next(r for r in rows['connections'] if r['name']=='Employee')['status'],'inactive')
  f.call('account/activity',{},e);self.assertEqual(f.call('admin/update-connections')[1]['other_connections'],1)
  self.assertEqual(f.call('activity-settings',{'inactive_minutes':1},e)[0],403)
  for value in [0,121,True,'5']:self.assertEqual(f.call('activity-settings',{'inactive_minutes':value})[0],400)
  self.assertEqual(f.call('activity-settings',{'inactive_minutes':1})[0],200)
  self.idle_employee(61);self.assertEqual(f.call('admin/update-connections')[1]['other_connections'],0)
 def test_local_override_bypasses_wait_and_is_audited(self):
  f=self.f;e=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),e)
  self.assertEqual(f.call('update-flow/force',dict(version='99.0.0',ready=True))[0],403)
  request=self.native.request('update-flow/start',dict(version='99.0.0',ready=True))
  f.wait(lambda:server.UPDATE_FLOW['phase']=='waiting');self.assertFalse(f.done.is_set())
  result=self.native.request('update-flow/force',dict(version='99.0.0',ready=True));self.assertTrue(result['force'])
  self.assertTrue(f.done.wait(3))
  with server.connect() as c:self.assertTrue(any('overrode' in str(tuple(r)) for r in c.execute('SELECT * FROM audit')))
 def test_native_notification_reaches_browser_and_inactivity_unblocks(self):
  f=self.f;e=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),e);f.call('logout',{})
  request=self.native.request('update-flow/start',dict(version='99.0.0',ready=True))
  f.wait(lambda:server.UPDATE_FLOW['phase']=='waiting')
  received=f.call('update-flow',client=e)[1];self.assertEqual(received['id'],request['id']);self.assertFalse(received['requester'])
  self.assertEqual(received['waiting'],1);self.idle_employee()
  self.assertTrue(f.done.wait(3))
if __name__=='__main__':unittest.main()
