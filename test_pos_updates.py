import hashlib,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import server,pos_updater
from pos_kiosk import KioskStore,KioskBridge
from test_update_coordination import CoordinatorFixture
class Coordination(unittest.TestCase):
 def setUp(self):
  self.f=CoordinatorFixture();self.p=patch.object(server,'POS_UPDATE_RELEASE',{'checking':False,'version':'9.0.0','checked':time.time()});self.p.start();server.POS_UPDATE_DEVICES.clear()
 def tearDown(self):self.p.stop();server.POS_UPDATE_DEVICES.clear();self.f.close()
 def test_admin_warning_cancel_and_data(self):
  f=self.f;e=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),e)
  for action in ['check','start','cancel','settings']:
   self.assertEqual(f.call('pos-update/'+action,{},e)[0],403)
   self.assertEqual(f.call('pos-update/'+action,{})[0],409)
  server.pos_update_save({'seconds':30,'campaign':{'id':'a'*64,'version':'9.0.0'}})
  self.assertIsNone(server.pos_update_read()['campaign'])
  self.assertEqual(f.call('pos-update/ticket?id='+'a'*64)[0],404)
class Native(unittest.TestCase):
 def test_checksum_and_origin(self):
  asset={'name':'MGC-YFC-POS-Setup-v9.0.0.exe','digest':'sha256:'+hashlib.sha256(b'correct').hexdigest(),'browser_download_url':'https://github.com/'+pos_updater.REPO+'/releases/download/v9/installer.exe'}
  with patch.object(pos_updater,'fetch',side_effect=[json.dumps({'assets':[asset]}).encode(),b'wrong']):
   with self.assertRaisesRegex(ValueError,'checksum'):pos_updater.verified_installer('9.0.0')
  asset['browser_download_url']='https://other.example/installer.exe'
  with patch.object(pos_updater,'fetch',return_value=json.dumps({'assets':[asset]}).encode()):
   with self.assertRaises(ValueError):pos_updater.verified_installer('9.0.0')
 def test_full_warning_work_freeze_and_launch_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=KioskBridge(KioskStore(Path(tmp)/'settings.json'),'http://localhost');b._window=Mock();b._window.get_current_url.return_value='http://localhost/pos'
   with patch.object(pos_updater.subprocess,'Popen') as process:
    self.assertEqual(b._updates.observe('a'*64)['state'],'idle')
    self.assertEqual(b.retry_update('a'*64)['state'],'idle')
    with self.assertRaisesRegex(ValueError,'Restart this application'):b._updates.install()
    process.assert_not_called();b._window.destroy.assert_not_called()
 def test_failed_download_retries_without_restarting_warning(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=KioskBridge(KioskStore(Path(tmp)/'settings.json'),'http://localhost');b._window=Mock();b._window.get_current_url.return_value='http://localhost/pos'
   with patch.object(pos_updater.subprocess,'Popen') as process:
    self.assertEqual(b._updates.observe('a'*64)['state'],'idle')
    self.assertEqual(b.retry_update('a'*64)['state'],'idle')
    with self.assertRaisesRegex(ValueError,'Restart this application'):b._updates.install()
    process.assert_not_called();b._window.destroy.assert_not_called()

if __name__=='__main__':unittest.main()
