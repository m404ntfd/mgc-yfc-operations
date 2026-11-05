import http.cookiejar,urllib.request,unittest
from test_server import Tests as Fixture

class LoginCountTests(unittest.TestCase):
 setUpClass=Fixture.__dict__['setUpClass']
 tearDownClass=Fixture.__dict__['tearDownClass']
 call=Fixture.__dict__['call']
 def test_remaining_count_and_reset(self):
  self.call('setup',{'name':'Admin','password':'testpassword'})
  self.call('admin/login-security',{'max_attempts':3})
  stranger=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  for remaining in (2,1):
   code,result=self.call('login',{'name':'Admin','password':'wrong'},stranger)
   self.assertEqual(code,401);self.assertEqual(result['attempts_remaining'],remaining)
  self.assertEqual(self.call('login',{'name':'Admin','password':'testpassword'},stranger)[0],200)
  self.assertEqual(self.call('login',{'name':'Admin','password':'wrong'},stranger)[1]['attempts_remaining'],2)
  for _ in range(2):code,result=self.call('login',{'name':'Admin','password':'wrong'},stranger)
  self.assertEqual(code,423);self.assertEqual(result['attempts_remaining'],0)
  self.assertEqual(self.call('login',{'name':'No such user','password':'wrong'},stranger)[0],401)

del Fixture
