import http.client,unittest
import test_server
class MobileMediaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_server.Tests.setUpClass()
 @classmethod
 def tearDownClass(cls):test_server.Tests.tearDownClass()
 def request(self,path,method='GET',headers=None):
  connection=http.client.HTTPConnection('127.0.0.1',test_server.Tests.port)
  connection.request(method,path,headers=headers or {});response=connection.getresponse();result=(response.status,dict(response.getheaders()),response.read());connection.close();return result
 def test_safari_byte_ranges_and_head(self):
  for extension in ('mp4','webm'):
   path='/media/mobile-intro.'+extension+'?v=title-2'
   status,headers,raw=self.request(path);self.assertEqual(status,200);self.assertEqual(headers['Accept-Ranges'],'bytes');self.assertGreater(len(raw),1000)
   status,partial,body=self.request(path,headers={'Range':'bytes=0-1'});self.assertEqual(status,206);self.assertEqual(body,raw[:2]);self.assertEqual(partial['Content-Range'],f'bytes 0-1/{len(raw)}');self.assertEqual(partial['Content-Length'],'2')
   self.assertEqual(self.request(path,headers={'Range':'bytes=-100'})[2],raw[-100:])
   self.assertEqual(self.request(path,headers={'Range':'bytes='+str(len(raw))+'-'})[0],416)
   self.assertEqual(self.request(path,headers={'Range':'bytes=9-2'})[0],416)
   status,head,body=self.request(path,'HEAD');self.assertEqual(status,200);self.assertEqual(body,b'');self.assertEqual(int(head['Content-Length']),len(raw))
   self.assertEqual(self.request(path,headers={'Range':'bytes=0-1','If-Range':'"changed"'})[0],200)
if __name__=='__main__':unittest.main()
