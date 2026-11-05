from contextlib import closing
"""Account lockout and delegated-unlock integration tests."""
import http.cookiejar, urllib.request, sqlite3, subprocess, sys, os, time
from pathlib import Path
from test_server import Tests as ServerFixture
class LockoutTests(ServerFixture):
 def test_mobile_routes(self):pass
 def test_workflow(self):
  def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  self.assertEqual(self.call('setup',{'name':'Admin','password':'testpassword'})[0],200)
  for name in ['Brad','Helper','Other']:
   self.assertEqual(self.call('user',{'name':name,'password':'1234'})[0],200)
  stranger=client();helper=client()
  self.assertEqual(self.call('admin/lockouts',client=stranger)[0],401)
  self.assertEqual(self.call('login',{'name':'Helper','password':'1234'},helper)[0],200)
  self.assertEqual(self.call('admin/unlock-user',{'name':'Brad'},helper)[0],403)
  self.assertEqual(self.call('admin/login-security',{'max_attempts':3})[0],200)
  for value in [0,101,True,2.5,'5',None]:self.assertEqual(self.call('admin/login-security',{'max_attempts':value})[0],400)
  self.assertEqual(self.call('admin/login-security')[1]['max_attempts'],3)
  for expected in [401,401,423]:self.assertEqual(self.call('login',{'name':'bRaD','password':'bad'},stranger)[0],expected)
  self.assertEqual(self.call('login',{'name':'Brad','password':'1234'},stranger)[0],423)
  locked=self.call('admin/lockouts')[1]['users'];self.assertEqual(locked[0]['name'],'Brad');self.assertEqual(locked[0]['failures'],3)
  # Stored in SQLite, so failures and locks survive process restarts and backups.
  with closing(sqlite3.connect(self.tmp.name+'/schedule.db')) as db:self.assertIsNotNone(db.execute('SELECT locked_at FROM account_lockouts WHERE name="Brad"').fetchone()[0])
  self.p.terminate();self.p.wait()
  self.__class__.p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py'))],env={**os.environ,'DISPATCH_DATA':self.tmp.name,'DISPATCH_PORT':str(self.port)},stdout=subprocess.DEVNULL)
  for _ in range(100):
   try:self.call('session');break
   except OSError:time.sleep(.05)
  self.assertEqual(self.call('login',{'name':'Brad','password':'1234'},stranger)[0],423)
  self.assertEqual(self.call('login',{'name':'Admin','password':'testpassword'})[0],200)
  self.assertEqual(self.call('login',{'name':'Helper','password':'1234'},helper)[0],200)
  self.assertEqual(self.call('login',{'name':'Other','password':'1234'},stranger)[0],200)
  self.assertEqual(self.call('admin/permissions',{'name':'Helper','grants':{'unlock_users':True}})[0],200)
  self.assertEqual(self.call('admin/login-security',{'max_attempts':20},helper)[0],403)
  self.assertEqual(self.call('admin/password',{'name':'Brad','password':'9999','confirm':'9999'},helper)[0],403)
  self.assertEqual(self.call('admin/lockouts',client=helper)[0],200)
  self.assertEqual(self.call('admin/unlock-user',{'name':'BRAD'},helper)[0],200)
  self.assertEqual(self.call('admin/lockouts',client=helper)[1]['users'],[])
  self.assertEqual(self.call('login',{'name':'Brad','password':'1234'},stranger)[0],200)
  for _ in range(2):self.assertEqual(self.call('login',{'name':'Brad','password':'bad'},stranger)[0],401)
  self.assertEqual(self.call('login',{'name':'Brad','password':'1234'},stranger)[0],200)
  self.assertEqual(self.call('login',{'name':'Brad','password':'bad'},stranger)[0],401)
  from unlock_local import unlock
  self.assertEqual(unlock(self.tmp.name,'Brad'),'Brad')
  self.assertTrue(any('Account unlocked: Brad' in a['action'] for a in self.call('audit')[1]))
# Avoid running the imported fixture's workflow twice under unittest discovery.
del ServerFixture
if __name__=='__main__':
 import unittest;unittest.main()
