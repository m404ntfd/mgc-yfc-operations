"""Native reconnection changes only a verified endpoint, preserving local identity."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from pos_kiosk import KioskStore,KioskBridge
from office_desktop import OfficeBridge
import desktop_connection as connection

class ReconnectTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.env=patch.dict(os.environ,{'APPDATA':str(self.root)});self.env.start()
  self.old='http://original-server:8080';self.new='https://operations.coastyfc.com'
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def bridge(self,app):
  path=self.root/('MGCYFCPOS' if app=='pos' else 'CoastYouthRetailOffice')/'settings.json'
  store=KioskStore(path);store.data.update(server=self.old,custom={'printer':'retained'});store.save()
  if app=='pos':store.set_passcode('123456','123456')
  bridge=KioskBridge(store,self.old) if app=='pos' else OfficeBridge(self.old)
  bridge._window=Mock();bridge._window.get_current_url.return_value=self.old+('/pos' if app=='pos' else '/office');bridge._window.evaluate_js.return_value=True
  return bridge,store
 def test_verified_connection_retains_identity_passcode_and_custom_settings(self):
  for app in ('pos','office'):
   with self.subTest(app=app):
    bridge,store=self.bridge(app);before=json.loads(store.path.read_text());nonce=getattr(bridge,'_nonce',None);version=bridge._updates.version if app=='pos' else None
    with patch.object(connection,'probe_server',return_value=self.new) as probe:
     self.assertEqual(bridge.desktop_reconnect(self.new,'123456'),{'ok':True})
    probe.assert_called_once_with(self.new,app)
    self.assertEqual(json.loads(store.path.read_text()),dict(before,server=self.new))
    bridge._window.load_url.assert_called_once_with(self.new+('/pos?kiosk=1&setup=1' if app=='pos' else '/office?setup=1'))
    self.assertEqual(bridge._address,self.new)
    if app=='pos':self.assertNotEqual(bridge._nonce,nonce);self.assertEqual(bridge._updates.version,version)
 def test_wrong_server_or_failed_probe_never_changes_saved_address(self):
  for app in ('pos','office'):
   bridge,store=self.bridge(app);before=store.path.read_bytes()
   with patch.object(connection,'probe_server',side_effect=ValueError('Server did not respond')):
    self.assertIn('did not respond',bridge.desktop_reconnect(self.new,'123456')['error'])
   self.assertEqual(store.path.read_bytes(),before);self.assertEqual(bridge._address,self.old);bridge._window.load_url.assert_not_called()
   with patch.object(connection,'probe_server') as probe:
    self.assertIn('server address',bridge.desktop_reconnect('https://name:password@example.com','123456')['error']);probe.assert_not_called()
 def test_untrusted_pages_and_unsaved_work_block_before_and_after_probe(self):
  for app in ('pos','office'):
   bridge,store=self.bridge(app);before=store.path.read_bytes()
   with patch.object(connection,'probe_server') as probe:
    bridge._window.get_current_url.return_value='https://other.invalid/office'
    self.assertIn('configured application',bridge.desktop_reconnect(self.new,'123456')['error']);probe.assert_not_called()
    bridge._window.get_current_url.return_value=self.old+('/pos' if app=='pos' else '/office')
    bridge._window.evaluate_js.return_value=False
    self.assertIn('Finish or save',bridge.desktop_reconnect(self.new,'123456')['error']);probe.assert_not_called()
    bridge._window.evaluate_js.side_effect=[True,False]
    self.assertIn('New work',bridge.desktop_reconnect(self.new,'123456')['error']);self.assertEqual(probe.call_count,1)
   self.assertEqual(store.path.read_bytes(),before);bridge._window.load_url.assert_not_called()
 def test_desk_passcode_required_only_for_address_changes_and_lockout_persists(self):
  bridge,store=self.bridge('pos')
  with patch.object(connection,'probe_server') as probe:
   self.assertIn('exit passcode',bridge.desktop_reconnect(self.new,'000000')['error']);probe.assert_not_called()
   self.assertEqual(json.loads(store.path.read_text())['server'],self.old)
   for _ in range(4):bridge.desktop_reconnect(self.new,'000000')
   self.assertIn('Too many',bridge.desktop_reconnect(self.new,'123456')['error']);probe.assert_not_called()
   self.assertEqual(bridge.desktop_reconnect(self.old),{'ok':True});probe.assert_called_once_with(self.old,'pos')
 def test_failed_save_and_page_navigation_cannot_replace_address(self):
  bridge,store=self.bridge('office');before=store.path.read_bytes()
  with patch.object(connection,'probe_server'),patch.object(KioskStore,'save',side_effect=OSError('Read-only settings')):
   self.assertIn('Read-only',bridge.desktop_reconnect(self.new)['error'])
  self.assertEqual(store.path.read_bytes(),before);self.assertEqual(bridge._address,self.old)
  bridge._window.get_current_url.side_effect=[self.old+'/office','https://untrusted.invalid/office']
  with patch.object(connection,'probe_server'):
   self.assertIn('page changed',bridge.desktop_reconnect(self.new)['error'])
  self.assertEqual(store.path.read_bytes(),before);bridge._window.load_url.assert_not_called()
 def test_navigation_failure_reports_saved_connection_without_losing_identity(self):
  bridge,store=self.bridge('office');device=store.data['device'];bridge._window.load_url.side_effect=RuntimeError('Window is closing')
  with patch.object(connection,'probe_server'):
   result=bridge.desktop_reconnect(self.new)
  self.assertTrue(result['saved']);self.assertIn('reopen',result['error'])
  self.assertEqual(json.loads(store.path.read_text())['device'],device)

if __name__=='__main__':unittest.main()
