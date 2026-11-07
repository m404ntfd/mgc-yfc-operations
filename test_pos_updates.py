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
  for action in ['check','start','cancel','settings']:self.assertEqual(f.call('pos-update/'+action,{},e)[0],403)
  self.assertEqual(f.call('pos-update/settings',{'seconds':1})[0],400)
  self.assertEqual(f.call('pos-update/settings',{'seconds':60})[0],200)
  with server.connect() as c:
   c.execute("INSERT INTO jobs VALUES('keep',3,?)",(json.dumps({'notes':'Reservation unchanged'}),));c.execute("INSERT INTO photos VALUES('keep',0,?)",(b'keep-image',))
   account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute("INSERT INTO work_periods VALUES(19,?,100,NULL,'Office',NULL)",(account,));c.execute('INSERT INTO work_breaks VALUES(20,19,120,NULL)')
  def snapshot():
   with server.connect() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ['jobs','photos','work_periods','work_breaks','work_time_card_audit']}
  before=snapshot();status,result=f.call('pos-update/start',{'target':'all'});self.assertEqual(status,200);job=result['campaign'];self.assertEqual(job['seconds'],60)
  self.assertEqual(server.pos_update_read()['campaign'],job)
  self.assertEqual(f.call('pos-update/start',{'target':'all'})[0],409)
  anon=f.client('c');self.assertEqual(f.call('pos-update/ticket?id='+job['id'],client=anon)[0],200)
  f.call('pos-update/cancel',{});self.assertEqual(f.call('pos-update/ticket?id='+job['id'],client=anon)[0],404)
  self.assertEqual(snapshot(),before)
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
   b=KioskBridge(KioskStore(Path(tmp)/'settings.json'),'http://localhost');b._window=Mock();b._window.get_current_url.return_value='http://localhost/pos';u=b._updates
   job={'id':'a'*64,'version':'9.0.0','target':'all','seconds':120};u.ticket=Mock(return_value=job)
   with patch.object(u,'download'):
    result=u.observe(job['id']);self.assertGreaterEqual(result['seconds'],119)
   u.state='ready';u.path=Path(tmp)/'installer.exe';u.path.write_bytes(b'test');u.digest=hashlib.sha256(b'test').hexdigest()
   with self.assertRaisesRegex(ValueError,'countdown'):u.install()
   u.deadline=0;b._window.evaluate_js.return_value=False
   with patch.object(pos_updater.sys,'frozen',True,create=True):
    with self.assertRaisesRegex(ValueError,'current sale'):u.install()
    b._window.destroy.assert_not_called();b._window.evaluate_js.return_value=True
    with patch.object(pos_updater.shutil,'copy2'),patch.object(pos_updater.subprocess,'Popen',side_effect=OSError('Launch failed')):
     with self.assertRaises(OSError):u.install()
    b._window.run_js.assert_called_with('window.posUpdateUnfreeze && window.posUpdateUnfreeze()');b._window.destroy.assert_not_called()
    u.ticket.side_effect=ValueError('Canceled')
    with self.assertRaisesRegex(ValueError,'Canceled'):u.install()
if __name__=='__main__':unittest.main()
