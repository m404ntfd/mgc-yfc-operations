import datetime as dt,json,unittest
from unittest.mock import patch
from test_update_coordination import CoordinatorFixture
import server
from desktop_updates import DesktopUpdateNotice,maintenance_banner_active
from pos_updater import PosUpdater

class UpdatePolicyTests(unittest.TestCase):
 def test_hourly_notices_never_download_or_install(self):
  notice=DesktopUpdateNotice('pos','1.18.0')
  with patch('desktop_updates.check_release',return_value={'version':'1.19.0'}) as check,patch('desktop_updates.time.monotonic',side_effect=[0,3599,3600]):
   self.assertTrue(notice.status()['available']);notice.status();self.assertEqual(check.call_count,1);notice.status();self.assertEqual(check.call_count,2)
  updater=PosUpdater(None);self.assertEqual(updater.observe('a'*64)['state'],'idle')
  with self.assertRaises(ValueError):updater.install()
 def test_central_banner_boundaries_and_dst(self):
  for stamp,visible in [('2026-11-15T09:49:59+00:00',False),('2026-11-15T09:50:00+00:00',True),('2026-11-15T10:01:59+00:00',True),('2026-11-15T10:02:00+00:00',False),('2026-07-01T08:50:00+00:00',True)]:
   self.assertEqual(server.maintenance_status(dt.datetime.fromisoformat(stamp))['banner'],visible,stamp)
   self.assertEqual(maintenance_banner_active(dt.datetime.fromisoformat(stamp)),visible,stamp)
  self.assertEqual(server.maintenance_now(dt.datetime.fromisoformat('2026-11-01T06:59:00+00:00')).utcoffset(),dt.timedelta(hours=-5))
  self.assertEqual(server.maintenance_now(dt.datetime.fromisoformat('2026-11-01T07:00:00+00:00')).utcoffset(),dt.timedelta(hours=-6))
 def test_scheduled_update_runs_once_and_freezes_new_writes(self):
  f=CoordinatorFixture()
  try:
   now=dt.datetime.fromisoformat('2026-11-15T10:00:00+00:00')
   with patch.object(server.updater,'check',return_value={'available':True,'latest':'0.59.0'}) as check:
    self.assertTrue(server.maintenance_check(f.http,now));f.stage.assert_called_once_with('0.59.0');self.assertTrue(f.done.is_set());self.assertEqual(f.call('pos/new',{'request':'a'*32})[0],503)
    self.assertFalse(server.maintenance_check(f.http,now));self.assertEqual(check.call_count,1)
  finally:server.MAINTENANCE_APPLYING=False;f.close()
 def test_failed_check_and_legacy_rollout_are_safe(self):
  f=CoordinatorFixture()
  try:
   with server.connect() as c:c.execute('INSERT INTO retail_computer_updates VALUES(?,?)',('pos',json.dumps({'id':'a'*64})));c.commit();self.assertIsNone(server.computer_campaign(c,'pos'))
   self.assertEqual(f.call('computers/start',{'computers':['a'*32]})[0],409)
   with patch.object(server.updater,'check',side_effect=ValueError('Test network outage')):
    self.assertFalse(server.maintenance_check(f.http,dt.datetime.fromisoformat('2026-11-15T10:00:00+00:00')));self.assertFalse(server.MAINTENANCE_APPLYING);self.assertFalse(f.done.is_set());f.stage.assert_not_called()
  finally:f.close()
if __name__=='__main__':unittest.main()
