import http.client
import http.cookiejar,json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  cls.p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py'))],env={**os.environ,'DISPATCH_DATA':cls.tmp.name,'DISPATCH_PORT':str(cls.port)},stdout=subprocess.DEVNULL)
  cls.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  for i in range(100):
   try: cls.call('session');break
   except OSError: time.sleep(.05)
 @classmethod
 def tearDownClass(cls):cls.p.terminate();cls.p.wait();cls.tmp.cleanup()
 @classmethod
 def call(cls,path,data=None,client=None):
  req=urllib.request.Request(f'http://127.0.0.1:{cls.port}/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-Dispatch':'1','Content-Type':'application/json'})
  try:
   with (client or cls.client).open(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_mobile_routes(self):
  for path in ('/mobile','/mobile/'):
   with urllib.request.urlopen(f'http://127.0.0.1:{self.port}'+path) as r:
    self.assertEqual(r.status,200)
    self.assertIn(b'id="addPickup"',r.read())
 def test_workflow(self):
  self.assertTrue(self.call('session')[1]['setup'])
  self.assertEqual(self.call('local/stop',{'token':'invalid'})[0],403)
  anon=urllib.request.build_opener()
  self.assertEqual(self.call('state',client=anon)[0],401)
  self.assertEqual(self.call('setup',{'name':'Manager','password':'testpassword'})[0],200)
  self.assertEqual(self.call('setup',{'name':'Other','password':'testpassword'})[0],409)
  # Simulate cloudflared on loopback forwarding the original HTTPS Host and Origin.
  def tunnel_post(path,data,origin='https://operations.coastyfc.com',proto='https',cookie=None):
   conn=http.client.HTTPConnection('127.0.0.1',self.port)
   headers={'Host':'operations.coastyfc.com','Origin':origin,'X-Forwarded-Proto':proto,'X-Dispatch':'1','Content-Type':'application/json'}
   if cookie: headers['Cookie']=cookie
   conn.request('POST','/api/'+path,json.dumps(data),headers)
   response=conn.getresponse(); result=(response.status,json.loads(response.read()),response.getheader('Set-Cookie'));conn.close();return result
  login={'name':'Manager','password':'testpassword'}
  for origin in ('https://evil.example','https://operations.coastyfc.com.evil.example','https://operations.coastyfc.com:8443','null','http://operations.coastyfc.com'):
   self.assertEqual(tunnel_post('login',login,origin=origin)[0],403)
  self.assertEqual(tunnel_post('login',login,proto='')[0],403)
  self.assertEqual(tunnel_post('setup',login)[0],403)
  code,body,cookie=tunnel_post('login',login)
  self.assertEqual(code,200)
  self.assertIn('; Secure',cookie)
  session_cookie=cookie.split(';')[0]
  self.assertEqual(tunnel_post('account/landing',{'section':'dispatch'},cookie=session_cookie)[0],200)
  code,body,cookie=tunnel_post('logout',{},cookie=session_cookie)
  self.assertEqual(code,200)
  self.assertIn('; Secure',cookie)
  self.assertEqual(self.call('updates')[1]['current'],Path(__file__).with_name('VERSION').read_text().strip())
  self.assertEqual(self.call('update-config',{'repository':'example/store'})[0],200)
  self.assertEqual(self.call('updates')[1]['repository'],'example/store')
  self.assertEqual(self.call('update-install',{'version':'0.2.1'})[0],400)
  self.assertEqual(self.call('vehicle',{'name':'Truck 1'})[0],200)
  self.assertEqual(self.call('user',{'name':'Alex','password':'testpassword'})[0],200)
  job=dict(type='Pickup',status='Scheduled',customer='Test customer',phone='555-0100',address='Test address',items='Sofa',vehicle='Truck 1',start='2026-10-28T09:00',end='2026-10-28T10:00',staff='',notes='')
  self.assertEqual(self.call('save',job)[0],200)
  self.assertEqual(self.call('save',job)[0],409)
  saved=self.call('state')[1]['jobs'][0]
  self.assertEqual(self.call('save',{**saved,'notes':'Changed'})[0],200)
  self.assertEqual(self.call('save',saved)[0],409)
  self.assertEqual(self.call('delete',saved)[0],409)
  self.assertEqual(self.call('save',{**job,'start':'2026-10-28T10:00','end':'2026-10-28T11:00'})[0],200)
  employee=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  self.assertEqual(self.call('login',{'name':'Alex','password':'testpassword'},employee)[0],200)
  self.assertEqual(self.call('vehicle',{'name':'Truck 2'},employee)[0],403)
  self.assertEqual(self.call('update-config',{'repository':'other/repo'},employee)[0],403)
  self.assertEqual(self.call('update-install',{'version':'0.2.1'},employee)[0],403)
  fresh=self.call('state',client=employee)[1]['jobs'][0]
  self.assertEqual(self.call('save',{**fresh,'status':'Canceled'},employee)[0],200)
  self.assertEqual(self.call('save',job,employee)[0],200)
  fresh=self.call('state')[1]['jobs'][0]
  self.assertEqual(self.call('delete',fresh,employee)[0],200)
  self.assertTrue(len(self.call('audit')[1])>=5)
  self.assertEqual(self.call('save',{**job,'end':'2026-10-27T09:00'})[0],400)
  structured={**job,'start':'2026-11-01T09:00','end':'2026-11-01T10:00','street':'12 Main St','city':'Springfield','state':'IL','zip':'62701','staffNames':['Alex','Manager']}
  self.assertEqual(self.call('save',{**structured,'phone':''})[0],400)
  self.assertEqual(self.call('save',{**structured,'city':''})[0],400)
  self.assertEqual(self.call('save',{**structured,'staffNames':['Unknown']})[0],400)
  self.assertEqual(self.call('save',structured)[0],200)
  appointment=next(j for j in self.call('state')[1]['jobs'] if j.get('street')=='12 Main St')
  self.assertEqual(appointment['address'],'12 Main St\nSpringfield, IL 62701')
  self.assertEqual(appointment['staffNames'],['Alex','Manager'])
  self.assertEqual(self.call('admin/remove-user',{'name':'Alex'},employee)[0],403)
  self.assertEqual(self.call('admin/remove-user',{'name':'Manager'})[0],403)
  self.assertEqual(self.call('admin/remove-user',{'name':'Alex'})[0],200)
  self.assertEqual(self.call('state',client=employee)[0],401)
  self.assertEqual(self.call('login',{'name':'Alex','password':'testpassword'},employee)[0],401)
  self.assertEqual(self.call('save',{**appointment,'notes':'Kept previous assignments'})[0],200)
  appointment=next(j for j in self.call('state')[1]['jobs'] if j.get('street')=='12 Main St')
  self.assertEqual(self.call('status',{'id':appointment['id'],'revision':appointment['revision'],'status':'Unknown'})[0],400)
  self.assertEqual(self.call('status',{'id':appointment['id'],'revision':appointment['revision'],'status':'In Route / In Progress'})[0],200)
  self.assertEqual(self.call('status',{'id':appointment['id'],'revision':appointment['revision'],'status':'Completed'})[0],409)
  updated=next(j for j in self.call('state')[1]['jobs'] if j['id']==appointment['id'])
  self.assertEqual(updated['staffNames'],appointment['staffNames'])
  self.assertEqual(updated['address'],appointment['address'])
  self.assertEqual(updated['status'],'In Route / In Progress')
  self.assertEqual(updated['statusUpdatedBy'],'Manager')
  self.assertTrue(updated['statusUpdatedAt'])
  self.assertEqual(self.call('save',{**updated,'notes':'Only details changed'})[0],200)
  unchanged=next(j for j in self.call('state')[1]['jobs'] if j['id']==updated['id'])
  self.assertEqual(unchanged['statusUpdatedAt'],updated['statusUpdatedAt'])

  self.assertEqual(self.call('user',{'name':'Requester','password':'testpassword'})[0],200)
  self.assertEqual(self.call('admin/permissions',{'name':'Requester','can_create':False,'see_requests':True})[0],200)
  requester=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  self.assertEqual(self.call('login',{'name':'Requester','password':'testpassword'},requester)[0],200)
  self.assertEqual(self.call('save',{**job,'status':'Requested','start':'2026-12-01T09:00','end':'2026-12-01T10:00'},requester)[0],200)
  requested=self.call('state',client=requester)[1]
  self.assertFalse(requested['permissions']['can_create'])
  self.assertFalse(requested['permissions']['see_requests'])
  self.assertEqual(len(requested['requests']),1)
  pending=requested['requests'][0]
  self.assertEqual(self.call('save',pending,requester)[0],403)
  self.assertEqual(self.call('status',{**pending,'status':'Scheduled','vehicle':'Truck 1','end':'2026-12-01T10:00'},requester)[0],403)
  self.assertEqual(self.call('save',{**pending,'status':'Scheduled','vehicle':'Truck 1','end':'2026-12-01T10:00'})[0],200)
  self.assertEqual(len(self.call('state')[1]['requests']),0)
  approved=next(j for j in self.call('state')[1]['jobs'] if j['id']==pending['id'])
  self.assertEqual(self.call('status',{**approved,'status':'Canceled'},requester)[0],200)
  self.assertEqual(self.call('save',{'customer':'Name only','type':'Pickup','status':'Requested'},requester)[0],200)
  minimal=next(j for j in self.call('state',client=requester)[1]['requests'] if j['customer']=='Name only')
  self.assertEqual(minimal['start'],'')
  self.assertEqual(minimal['photoCount'],0)
  self.assertEqual(self.call('save',{'customer':'Bad photo','type':'Pickup','status':'Requested','photos':['bad']},requester)[0],400)
  self.assertEqual(self.call('paging/send',{'area':'Front register'},requester)[0],403)
  self.assertEqual(self.call('paging/send',{'area':'Front register'})[0],200)
  self.assertEqual(self.call('paging')[1]['pages'][-1]['area'],'Front register')
  self.assertEqual(self.call('paging/send',{'area':'Office'})[0],429)
  self.assertEqual(self.call('logout',{})[0],200)
  self.assertEqual(self.call('state')[0],401)
if __name__=='__main__':unittest.main()
