import unittest,http.cookiejar,urllib.request
import test_server
class PageColorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_server.Tests.setUpClass()
 @classmethod
 def tearDownClass(cls):test_server.Tests.tearDownClass()
 def test_authorization_validation_and_saved_colors(self):
  call=test_server.Tests.call;call('setup',{'name':'Admin','password':'testpassword'})
  guest=urllib.request.build_opener();pages=call('page-colors',client=guest)[1]['pages']
  self.assertEqual(pages['print']['header'],'#073ea6')
  call('user',{'name':'Employee','password':'testpassword'})
  employee=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));call('login',{'name':'Employee','password':'testpassword'},employee)
  self.assertEqual(call('page-colors',{'pages':pages},guest)[0],401)
  self.assertEqual(call('page-colors',{'pages':pages},employee)[0],403)
  pages['print']['header']='red;display:none';self.assertEqual(call('page-colors',{'pages':pages})[0],400)
  pages['print']['header']='#123ABC';self.assertEqual(call('page-colors',{'pages':pages})[0],200)
  self.assertEqual(call('page-colors',client=guest)[1]['pages']['print']['header'],'#123abc')
  self.assertEqual(call('page-colors',client=employee)[1]['pages']['print']['header'],'#123abc')
if __name__=='__main__':unittest.main()
