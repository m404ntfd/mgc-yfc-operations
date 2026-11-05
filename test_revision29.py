import base64,http.cookiejar,json,os,sqlite3,subprocess,sys,time,unittest,urllib.request
from pathlib import Path
from unittest.mock import patch
from test_server import Tests as F
from remote.client import Client

class Revision29Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.env=patch.dict(os.environ,{'DISPATCH_CONTROL_TOKEN':'local-test-control'});cls.env.start();F.setUpClass()
 @classmethod
 def tearDownClass(cls):F.tearDownClass();cls.env.stop()
 def test_receipts_sharing_and_local_session(self):
  call=F.call;call('setup',{'name':'Admin','password':'testpassword'})
  call('admin/receipt-categories',{'categories':['Office','Store']})
  clients={}
  for name in ('Alice','Bob','Accounting','Guest'):
   call('user',{'name':name,'password':'testpassword'})
   client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));clients[name]=client
   self.assertEqual(call('login',{'name':name,'password':'testpassword'},client)[0],200)
  call('admin/permissions',{'name':'Accounting','grants':{'view_all_receipts':True}})
  for i,name in enumerate(('Alice','Bob','Guest',None)):
   payload={'id':str(i)*32,'category':'Office','filename':('office' if name=='Alice' else 'other')+'.pdf','body':base64.b64encode(b'%PDF-1.4 test').decode()}
   if name is None:
    self.assertEqual(call('receipt-submit',payload,urllib.request.build_opener())[0],400)
    payload['assignee']=next(person['id'] for person in call('receipt-users')[1]['users'] if person['name']=='Admin')
   self.assertEqual(call('receipt-submit',payload,clients[name] if name else urllib.request.build_opener())[0],200)
  for name in ('Alice','Bob','Guest'):
   code,r=call('receipts',client=clients[name]);self.assertEqual(code,200);self.assertEqual(r['total'],1);self.assertEqual(r['receipts'][0]['actor'],name)
   self.assertEqual(call('receipts?scope=all',client=clients[name])[0],403)
  self.assertEqual(call('receipts?scope=all',client=clients['Accounting'])[1]['total'],4)
  self.assertEqual(call('receipt-file/'+'1'*32,client=clients['Alice'])[0],404)
  self.assertEqual(call('receipts?search=office',client=clients['Alice'])[1]['total'],1)
  self.assertEqual(call('receipts?search=absent',client=clients['Alice'])[1]['total'],0)
  self.assertEqual(call('receipts?from=bad',client=clients['Alice'])[0],400)
  settings={'mobile':{'text':False,'email':True,'native':False},'desktop':{'text':True,'email':False,'native':False}}
  self.assertEqual(call('sharing',settings,clients['Alice'])[0],403)
  self.assertEqual(call('sharing',settings)[1],settings)
  self.assertEqual(call('sharing',client=urllib.request.build_opener())[1],settings)
  self.assertEqual(call('admin/remove-user',{'name':'Alice'})[0],200)
  call('user',{'name':'Alice','password':'newpassword'})
  call('login',{'name':'Alice','password':'newpassword'},clients['Alice'])
  self.assertEqual(call('receipts',client=clients['Alice'])[1]['total'],0)
  self.assertEqual(call('login',{'name':'Admin','password':'testpassword','local_admin':True,'local_control_token':'wrong'})[0],403)
  with sqlite3.connect(Path(F.tmp.name)/'schedule.db') as connection:
   self.assertEqual(len(connection.execute('PRAGMA table_info(receipts)').fetchall()),8)
   connection.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?)',('f'*32,time.time(),'Bob','Office','legacy.pdf','application/pdf',b'%PDF-1.4 legacy','test'))
  connection.close()
  if os.name=='nt':
   session_path=Path(F.tmp.name)/'native.bin'
   local=Client(f'127.0.0.1:{F.port}',local_control='local-test-control',session_path=session_path)
   self.assertEqual(local.login('Admin','testpassword')['name'],'MGC YFC Operations Server')
   saved=session_path.read_bytes();self.assertNotIn(next(c.value for c in local.cookies if c.name=='session').encode(),saved)
   copied=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(local.cookies))
   self.assertIsNone(call('session',client=copied)[1]['user'])
   F.p.terminate();F.p.wait();F.p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py'))],env={**os.environ,'DISPATCH_DATA':F.tmp.name,'DISPATCH_PORT':str(F.port)},stdout=subprocess.DEVNULL)
   for _ in range(100):
    try:call('session');break
    except OSError:time.sleep(.05)
   restored=Client(f'127.0.0.1:{F.port}',local_control='local-test-control',session_path=session_path)
   self.assertIsNotNone(restored.restore_local_session())
   with sqlite3.connect(Path(F.tmp.name)/'schedule.db') as connection:connection.execute("UPDATE local_admin_sessions SET version='0.0.0'")
   connection.close()
   self.assertIsNone(restored.probe()['user'])

if __name__=='__main__':unittest.main()
