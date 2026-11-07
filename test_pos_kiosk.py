import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import server
from pos_kiosk import KioskStore,KioskBridge
from test_update_coordination import CoordinatorFixture

class StoreTests(unittest.TestCase):
 def test_storage_lockout_and_change(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'settings.json';path.write_text(json.dumps({'server':'http://localhost:8080'}))
   now=[100];s=KioskStore(path,lambda:now[0]);s.set_passcode('123456','123456')
   self.assertNotIn('123456',path.read_text());self.assertEqual(s.data['server'],'http://localhost:8080')
   for _ in range(5):self.assertFalse(s.verify('654321'))
   s=KioskStore(path,lambda:now[0])
   with self.assertRaises(ValueError):s.verify('123456')
   now[0]=161;self.assertTrue(s.verify('123456'))
   with self.assertRaises(ValueError):s.set_passcode('111111','222222')
   s.set_passcode('987654','987654');self.assertFalse(s.verify('123456'));self.assertTrue(s.verify('987654'))
   path.write_text('{broken')
   with self.assertRaises(ValueError):KioskStore(path)

 def test_native_boundary_and_work_guard(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=KioskStore(Path(tmp)/'settings.json');b=KioskBridge(s,'http://localhost:8080');w=Mock();b._window=w
   w.get_current_url.return_value='http://localhost:8080/pos?kiosk=1';w.evaluate_js.return_value=True
   self.assertFalse(b._closing());w.destroy.assert_not_called()
   b._redeem=lambda token:dict(admin=True,device=s.data['device'],nonce=b._nonce)
   self.assertTrue(b.configure_passcode('a'*64,'123456','123456')['ok'])
   self.assertIn('error',b.request_exit('000000'));w.destroy.assert_not_called()
   w.evaluate_js.return_value=False;self.assertIn('error',b.request_exit('123456'));w.destroy.assert_not_called()
   w.evaluate_js.return_value=True;self.assertTrue(b.open_operations('pos')['ok']);w.load_url.assert_called_with('http://localhost:8080/pos?kiosk=1')
   w.get_current_url.return_value='https://other.example/pos';self.assertIn('error',b.request_exit('123456'))
   self.assertIn('error',b.configure_passcode('a'*64,'111111','111111'))
   w.get_current_url.return_value='http://localhost:8080/';self.assertTrue(b.request_exit('123456')['ok']);w.destroy.assert_called_once();self.assertTrue(b._closing())

class OfficeDeviceTests(unittest.TestCase):
 def test_office_passcode_change_is_seen_by_running_desk(self):
  from office_desktop import OfficeBridge
  with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'APPDATA':tmp}):
   path=Path(tmp)/'MGCYFCPOS'/'settings.json'
   store=KioskStore(path);store.data['server']='http://localhost:8080';store.set_passcode('123456','123456')
   desk=KioskBridge(store,'http://localhost:8080');desk._window=Mock();desk._window.get_current_url.return_value='http://localhost:8080/pos';desk._window.evaluate_js.return_value=True
   office=OfficeBridge('http://localhost:8080');office._window=Mock();office._window.get_current_url.return_value='http://localhost:8080/office'
   info=office.office_kiosk_info();self.assertTrue(info['configured'])
   office._kiosk._redeem=lambda token:dict(admin=True,device=info['device'],nonce=info['nonce'])
   self.assertTrue(office.office_configure_passcode('a'*64,'987654','987654')['ok'])
   self.assertIn('error',desk.request_exit('123456'));desk._window.destroy.assert_not_called()
   self.assertTrue(desk.request_exit('987654')['ok'])
   other=OfficeBridge('http://other.example');self.assertTrue(other.office_kiosk_info()['unavailable'])

class ApprovalTests(unittest.TestCase):
 def setUp(self):self.f=CoordinatorFixture();server.POS_KIOSK_APPROVALS.clear()
 def tearDown(self):self.f.close();server.POS_KIOSK_APPROVALS.clear()
 def test_admin_only_bound_one_use_expiry_and_revocation(self):
  f=self.f;body=dict(device='a'*32,nonce='b'*64)
  employee=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),employee)
  f.call('admin/permissions',dict(name='Employee',grants={'manage_pos':True,'use_pos':True},can_create=False,see_requests=False))
  self.assertEqual(f.call('pos/kiosk-approval',body,employee)[0],403)
  anonymous=f.client('c');self.assertEqual(f.call('pos/kiosk-approval',body,anonymous)[0],401)
  token=f.call('pos/kiosk-approval',body)[1]['token'];request=dict(body,token=token)
  self.assertEqual(f.call('pos/kiosk-redeem',dict(request,nonce='c'*64),anonymous)[0],403)
  self.assertEqual(f.call('pos/kiosk-redeem',request,anonymous)[0],200)
  self.assertEqual(f.call('pos/kiosk-redeem',request,anonymous)[0],403)
  token=f.call('pos/kiosk-approval',body)[1]['token'];server.POS_KIOSK_APPROVALS[hashlib.sha256(token.encode()).hexdigest()]['expires']=0
  self.assertEqual(f.call('pos/kiosk-redeem',dict(body,token=token),anonymous)[0],403)
  token=f.call('pos/kiosk-approval',body)[1]['token']
  with server.connect() as c:c.execute("UPDATE users SET admin=0 WHERE name='Admin'")
  self.assertEqual(f.call('pos/kiosk-redeem',dict(body,token=token),anonymous)[0],403)

if __name__=='__main__':unittest.main()
