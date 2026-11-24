"""Connection probes are read-only; store timings retain old-client compatibility."""
import json
import unittest
import urllib.request
import uuid
from unittest.mock import patch
import server
from test_update_coordination import CoordinatorFixture


class DeskConnectionTests(unittest.TestCase):
 def setUp(self):self.f=CoordinatorFixture()
 def tearDown(self):self.f.close()
 def settings(self,store='thrift-mart'):
  code,data=self.f.call('pos/checkout-settings?store_id='+store)
  self.assertEqual(code,200,data);return data['settings']
 def save(self,settings,client=None):
  return self.f.call('pos/checkout-settings-save',dict(settings,request=uuid.uuid4().hex),client)
 def test_public_probe_verifies_nonce_without_database_or_session_access(self):
  nonce='a'*32
  with patch.object(server,'connect',side_effect=AssertionError('Probe must not open the database')):
   with urllib.request.urlopen(f'http://127.0.0.1:{self.f.port}/api/desk-connection?nonce={nonce}') as response:
    self.assertEqual(response.headers['Cache-Control'],'no-store')
    self.assertIsNone(response.headers.get('Set-Cookie'))
    self.assertEqual(json.load(response),dict(service='coastyouth-operations',online=True,nonce=nonce))
   self.assertEqual(self.f.call('desk-connection?nonce=bad')[0],400)
 def test_defaults_store_isolation_and_old_client_saves(self):
  current=self.settings()
  self.assertEqual(current['connection_monitor'],dict(interval_seconds=10,warning_seconds=20,offline_seconds=30))
  monitor=dict(interval_seconds=15,warning_seconds=30,offline_seconds=60)
  code,data=self.save(dict(current,connection_monitor=monitor));self.assertEqual(code,200,data)
  current=data['settings'];self.assertEqual(current['connection_monitor'],monitor)
  self.assertEqual(self.settings('binopoly')['connection_monitor']['interval_seconds'],10)
  old_client={k:v for k,v in current.items() if k!='connection_monitor'}
  code,data=self.save(old_client);self.assertEqual(code,200,data)
  self.assertEqual(data['settings']['connection_monitor'],monitor)
  self.assertEqual(data['settings']['presets'],current['presets'])
  self.assertEqual(data['settings']['reasons'],current['reasons'])
  self.assertEqual(data['settings']['receipt_reset_seconds'],current['receipt_reset_seconds'])
 def test_invalid_timings_and_stale_revisions_do_not_write(self):
  current=self.settings();original=current['connection_monitor']
  for value in (None,{},[],dict(original,interval_seconds=True),dict(original,interval_seconds='10'),dict(original,interval_seconds=4),dict(original,interval_seconds=61),dict(original,warning_seconds=19),dict(original,warning_seconds=301),dict(original,offline_seconds=29),dict(original,offline_seconds=601)):
   with self.subTest(value=value):
    self.assertEqual(self.save(dict(current,connection_monitor=value))[0],400)
    self.assertEqual(self.settings(),current)
  code,data=self.save(current);self.assertEqual(code,200,data)
  self.assertEqual(self.save(current)[0],409)
 def test_cashier_cannot_change_monitor_timings(self):
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  client=self.f.client('employee');self.f.call('login',dict(name='Employee',password='testpassword'),client)
  current=self.settings()
  self.assertEqual(self.save(current,client)[0],403)
  self.assertEqual(self.settings(),current)

if __name__=='__main__':unittest.main()
