"""Local timeout/theme preferences cannot modify registration or store records."""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import connection_preferences as preferences
import desktop_connection
from store_ops_desktop import CloseGuard, save_connection
from pos_kiosk import KioskStore


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        env=patch.dict(os.environ,{'APPDATA':self.tmp.name});env.start();self.addCleanup(env.stop)

    def test_timeout_validation_contrast_and_separate_local_files(self):
        for app in ('pos','office','ops'):
            path=preferences.path(app);path.parent.mkdir(parents=True,exist_ok=True)
            identity=path.parent/'settings.json';identity.write_text('{"device":"keep-this-identity"}')
            self.assertEqual(preferences.load(app)['timeout_seconds'],10)
            result=preferences.save(app,dict(timeout_seconds=7,panel='#202020',text='#202020',muted='#202020',password='never save'))
            self.assertEqual(preferences.load(app)['timeout_seconds'],7)
            self.assertGreaterEqual(preferences.contrast(result['text'],result['panel']),4.5)
            self.assertNotIn('password',path.read_text())
            self.assertEqual(identity.read_text(),'{"device":"keep-this-identity"}')
        for value in (0,121,True,'10',2.5,None):self.assertEqual(preferences.clean({'timeout_seconds':value})['timeout_seconds'],10)

    def test_preferences_require_configured_app_origin(self):
        bridge=Mock();bridge._trusted.return_value=False
        self.assertIn('error',preferences.bridge_preferences(bridge,'pos',{'timeout_seconds':3}))
        self.assertFalse(preferences.path('pos').exists())

    def test_store_ops_reconnect_keeps_identity_and_existing_settings(self):
        folder=Path(self.tmp.name)/'CoastYouthRetailStoreOps';store=KioskStore(folder/'settings.json');store.save()
        save_connection(folder,'http://old:8080');before=store.path.read_bytes()
        window=Mock();window.get_current_url.return_value='http://old:8080/';window.evaluate_js.return_value=True
        bridge=CloseGuard(window,'http://old:8080')
        preferences.save('ops',{'timeout_seconds':4})
        with patch.object(desktop_connection,'probe_server') as probe:
            self.assertEqual(bridge.desktop_reconnect('https://operations.coastyfc.com'),{'ok':True})
        probe.assert_called_once_with('https://operations.coastyfc.com','ops',timeout_seconds=4)
        self.assertEqual(store.path.read_bytes(),before)
        self.assertEqual(json.loads((folder/'connection.json').read_text())['server'],'https://operations.coastyfc.com')
        window.load_url.assert_called_once_with('https://operations.coastyfc.com/?setup=1')

    def test_late_reconnect_does_not_save_or_navigate(self):
        folder=Path(self.tmp.name)/'CoastYouthRetailStoreOps';save_connection(folder,'http://old:8080')
        window=Mock();window.get_current_url.return_value='http://old:8080/';window.evaluate_js.return_value=True
        bridge=CloseGuard(window,'http://old:8080');before=(folder/'connection.json').read_bytes()
        with patch.object(desktop_connection,'probe_server'),patch.object(desktop_connection.time,'monotonic',side_effect=[0,11]):
            self.assertIn('timed out',bridge.desktop_reconnect('http://new:8080')['error'])
        self.assertEqual((folder/'connection.json').read_bytes(),before);window.load_url.assert_not_called()

    def test_stalled_native_probe_is_bounded_and_cannot_later_save(self):
        folder=Path(self.tmp.name)/'CoastYouthRetailStoreOps';save_connection(folder,'http://old:8080')
        window=Mock();window.get_current_url.return_value='http://old:8080/';window.evaluate_js.return_value=True
        bridge=CloseGuard(window,'http://old:8080');before=(folder/'connection.json').read_bytes()
        preferences.save('ops',{'timeout_seconds':1});release=threading.Event();finished=threading.Event()
        def slow(*args,**kwargs):release.wait(5);finished.set()
        with patch.object(desktop_connection,'probe_server',side_effect=slow):
            started=time.monotonic()
            self.assertIn('timed out',bridge.desktop_reconnect('http://new:8080')['error'])
            self.assertLess(time.monotonic()-started,2)
            release.set();self.assertTrue(finished.wait(1))
        self.assertEqual((folder/'connection.json').read_bytes(),before);window.load_url.assert_not_called()


if __name__=='__main__':unittest.main()
