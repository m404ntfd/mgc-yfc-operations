import json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent/'remote'))
from client import Client,normalize_address
from restore import restore_backup,data_lock
import test_server
class RemoteTests(test_server.Tests):
 def test_remote_management_and_restore(self):
  # Each class owns its own temporary server. This method sorts before test_workflow.
  self.assertEqual(self.call('setup',{'name':'RemoteAdmin','password':'testpassword'})[0],200)
  client=Client(f'127.0.0.1:{self.port}')
  self.assertEqual(client.probe()['application'],'thrift-mart-dispatch')
  self.assertEqual(client.login('RemoteAdmin','testpassword')['name'],'MGC YFC Operations Server')
  self.assertEqual(self.call('admin/restart',{})[0],400)  # direct server: no supervisor
  self.assertEqual(self.call('admin/backup-now',{})[0],400)
  with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as dest:
   self.assertEqual(self.call('admin/backup-settings',{'enabled':True,'folder':folder})[0],200)
   r=client.request('admin/backup-now',{});archive=Path(r['backup']);self.assertTrue(archive.exists())
   with zipfile.ZipFile(archive) as z:self.assertTrue({'schedule.db','manifest.json','backup-settings.json'}<=set(z.namelist()))
   restore_backup(archive,dest)
   self.assertFalse(json.loads((Path(dest)/'backup-settings.json').read_text())['enabled'])
   with data_lock(dest):
    with self.assertRaises(ValueError):restore_backup(archive,dest)
   # Verify the restored account and schema directly.
   import sqlite3
   from contextlib import closing
   with closing(sqlite3.connect(Path(dest)/'schedule.db')) as c:self.assertEqual(c.execute('SELECT name FROM users').fetchone()[0],'RemoteAdmin')
   bad=Path(folder)/'bad.zip'
   with zipfile.ZipFile(bad,'w') as z:z.writestr('../outside','bad')
   with self.assertRaises(ValueError):restore_backup(bad,dest)
  self.assertEqual(self.call('admin/backup-settings',{'enabled':False,'folder':''})[0],200)
  self.assertEqual(self.call('user',{'name':'Employee','password':'testpassword'})[0],200)
  employee=Client(f'127.0.0.1:{self.port}')
  with self.assertRaisesRegex(ValueError,'administrator'):employee.login('Employee','testpassword')
  # Verify access independently of the remote UI.
  employee.request('login',{'name':'Employee','password':'testpassword'})
  for path in ('admin/backup','admin/backup-now','admin/backup-settings','admin/restart'):
   with self.assertRaisesRegex(ValueError,'Administrator'):employee.request(path,{})
 def test_workflow(self):pass # base workflow is tested by its own class
class AddressTests(unittest.TestCase):
 def test_addresses(self):
  self.assertEqual(normalize_address('192.168.1.50'),'http://192.168.1.50:8080')
  self.assertEqual(normalize_address('http://store-pc:8081/'),'http://store-pc:8081')
  for value in ('file:///foo','http://user:pass@server','server/path','http://server:99999','http://server?q=a'):
   with self.assertRaises(ValueError):normalize_address(value)
if __name__=='__main__':unittest.main()

class PasswordTests(test_server.Tests):
 def test_admin_password_changes(self):
  self.assertEqual(self.call('setup',{'name':'Boss','password':'OriginalBossPass'})[0],200)
  self.assertEqual(self.call('user',{'name':'Worker','password':'OriginalWorkerPass'})[0],200)
  base=f'127.0.0.1:{self.port}'
  employee=Client(base);employee.request('login',{'name':'Worker','password':'OriginalWorkerPass'})
  employee2=Client(base);employee2.request('login',{'name':'Worker','password':'OriginalWorkerPass'})
  admin2=Client(base);admin2.login('Boss','OriginalBossPass')
  payload={'name':'Worker','password':'ReplacementWorkerPass','confirm':'ReplacementWorkerPass'}
  with self.assertRaisesRegex(ValueError,'Administrator'):employee.request('admin/password',payload)
  with self.assertRaisesRegex(ValueError,'Administrator'):employee.request('admin/users')
  self.assertEqual(self.call('admin/password',{**payload,'confirm':'wrong'})[0],400)
  self.assertEqual(self.call('admin/password',{**payload,'password':'short','confirm':'short'})[0],400)
  self.assertEqual(self.call('admin/password',{**payload,'name':'Missing'})[0],404)
  self.assertEqual(self.call('admin/password',payload)[1],{'ok':True,'signed_out':False})
  for c in (employee,employee2):
   with self.assertRaisesRegex(ValueError,'sign in'):c.request('state')
  with self.assertRaisesRegex(ValueError,'Incorrect'):employee.request('login',{'name':'Worker','password':'OriginalWorkerPass'})
  employee.request('login',{'name':'Worker','password':'ReplacementWorkerPass'})
  self.assertEqual(employee.request('session')['user']['name'],'Worker')
  audit=str(self.call('audit')[1]);self.assertIn('Password changed for: Worker',audit);self.assertNotIn('ReplacementWorkerPass',audit)
  r=self.call('admin/password',{'name':'boss','password':'ReplacementBossPass','confirm':'ReplacementBossPass'})
  self.assertTrue(r[1]['signed_out'])
  self.assertEqual(self.call('state')[0],401)
  with self.assertRaisesRegex(ValueError,'sign in'):admin2.request('admin/users')
  self.assertEqual(self.call('login',{'name':'Boss','password':'ReplacementBossPass'})[0],200)
  self.assertEqual(len(self.call('admin/users')[1]['users']),2)
 def test_workflow(self):pass
