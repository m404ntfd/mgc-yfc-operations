import hashlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from pos_updater import PosUpdater
from computer_identity import computer_info
class NativeComputerTests(unittest.TestCase):
 def test_identity_stable_across_host_and_mac_changes(self):
  registry=SimpleNamespace(HKEY_LOCAL_MACHINE=1,KEY_READ=2,KEY_WOW64_64KEY=4,OpenKey=Mock(),QueryValueEx=Mock(return_value=('stable-machine-guid',1)))
  registry.OpenKey.return_value.__enter__=Mock(return_value=object());registry.OpenKey.return_value.__exit__=Mock(return_value=False)
  with patch.dict('sys.modules',{'winreg':registry}),patch('computer_identity.platform.system',return_value='Windows'),patch('computer_identity.platform.node',return_value='OLD-PC'),patch('computer_identity.uuid.getnode',return_value=0xAABBCCDDEE00):a=computer_info()
  with patch.dict('sys.modules',{'winreg':registry}),patch('computer_identity.platform.system',return_value='Windows'),patch('computer_identity.platform.node',return_value='NEW-PC'),patch('computer_identity.uuid.getnode',return_value=0xAABBCCDDEE02):b=computer_info()
  self.assertEqual(a['id'],b['id']);self.assertNotEqual(a['macs'],b['macs']);self.assertEqual(len(a['id']),32)
 def test_office_connection_change_preserves_device_configuration(self):
  from office_desktop import save_connection
  from pos_kiosk import KioskStore
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'settings.json';store=KioskStore(path);store.data.update(server='http://old-server:8080',custom_setting='keep');store.save();before=dict(store.data)
   self.assertEqual(save_connection(path,'http://new-server:8080'),'http://new-server:8080')
   self.assertEqual(KioskStore(path).data,{**before,'server':'http://new-server:8080'})
   path.write_text('invalid settings',encoding='utf-8')
   with self.assertRaises(ValueError):save_connection(path,'http://new-server:8080')
   self.assertEqual(path.read_text(),'invalid settings')
 def test_ops_installer_requires_verified_official_asset(self):
  from pos_updater import verified_installer
  import json
  raw=b'isolated-ops-installer';digest=hashlib.sha256(raw).hexdigest()
  release={'assets':[{'name':'CoastYouth-Retail-STORE-OPS-Setup-v9.0.0.exe','digest':'sha256:'+digest,'browser_download_url':'https://github.com/m404ntfd/mgc-yfc-operations/releases/download/v9.0.0/CoastYouth-Retail-STORE-OPS-Setup-v9.0.0.exe'}]}
  with patch('pos_updater.fetch',side_effect=[json.dumps(release).encode(),raw]):self.assertEqual(verified_installer('9.0.0','ops'),(raw,digest))
  with patch('pos_updater.fetch',side_effect=[json.dumps(release).encode(),b'changed']):
   with self.assertRaisesRegex(ValueError,'checksum mismatch'):verified_installer('9.0.0','ops')
 def test_native_target_scope_and_uncanceled_work_guard(self):
  bridge=SimpleNamespace(_trusted=lambda:True,_store=SimpleNamespace(data={'device':'a'*32}),_window=Mock())
  update=PosUpdater(bridge,current='1.0.0');job={'id':'f'*64,'target':'registered','targets':['b'*32],'version':'9.0.0','seconds':30,'mode':'notify','automatic':True}
  with patch.object(update,'ticket',return_value=job),patch('pos_updater.threading.Thread') as thread:
   self.assertEqual(update.observe(job['id'])['state'],'idle');thread.assert_not_called()
   job['targets']=['a'*32];self.assertEqual(update.observe(job['id'])['state'],'downloading');thread.assert_called_once()
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'installer.exe';path.write_bytes(b'fixture-only');update.path=path;update.digest=hashlib.sha256(path.read_bytes()).hexdigest();update.state='ready';update.deadline=0
   bridge._window.evaluate_js.return_value=False
   with patch.object(update,'ticket',return_value=job),patch('pos_updater.sys.frozen',True,create=True),patch('pos_updater.subprocess.Popen') as process:
    with self.assertRaisesRegex(ValueError,'unfinished entries'):update.install()
    process.assert_not_called();bridge._window.destroy.assert_not_called()
    self.assertIn('false',bridge._window.evaluate_js.call_args.args[0])
   with patch.object(update,'ticket',side_effect=ValueError('Canceled')),patch('pos_updater.subprocess.Popen') as process:
    with self.assertRaisesRegex(ValueError,'Canceled'):update.install()
    process.assert_not_called()
if __name__=='__main__':unittest.main()
