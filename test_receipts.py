"""Receipt storage, guest isolation, validation, retries and backup coverage."""
import base64, json, sqlite3, unittest, urllib.request, zipfile
from contextlib import closing
from pathlib import Path
import test_server

class Receipts(unittest.TestCase):
 @classmethod
 def setUpClass(cls): test_server.Tests.setUpClass()
 @classmethod
 def tearDownClass(cls): test_server.Tests.tearDownClass()
 def test_receipts(self):
  call=test_server.Tests.call;guest=urllib.request.build_opener()
  self.assertEqual(call('setup',{'name':'Admin','password':'testpassword'})[0],200)
  self.assertEqual(call('admin/receipt-categories',{'categories':['Ministry','Store supplies']})[0],200)
  self.assertEqual(call('receipt-categories',client=guest)[1]['categories'],['Ministry','Store supplies'])
  self.assertEqual(call('admin/receipt-categories',{'categories':['Intruder']},guest)[0],401)
  body=base64.b64encode(b'%PDF-1.4\nreceipt test').decode()
  data=dict(id='a'*32,category='Ministry',filename='receipt.pdf',body=body)
  self.assertEqual(call('receipt-submit',dict(data,category='missing'),guest)[0],400)
  self.assertEqual(call('receipt-submit',dict(data,body=base64.b64encode(b'<script>bad</script>').decode()),guest)[0],400)
  code,result=call('receipt-submit',data,guest);self.assertEqual(code,200);self.assertTrue(result['email_pending'])
  self.assertEqual(call('receipt-submit',data,guest)[0],200)
  self.assertEqual(len(call('admin/receipts')[1]['receipts']),1)
  for route in ('state','account/landing','admin/receipts','admin/receipt-file/'+'a'*32): self.assertEqual(call(route,client=guest)[0],401)
  self.assertEqual(call('session',client=guest)[1]['user'],None)
  self.assertEqual(call('user',{'name':'Employee','password':'testpassword'})[0],200)
  employee=urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
  self.assertEqual(call('login',{'name':'Employee','password':'testpassword'},employee)[0],200)
  self.assertEqual(call('admin/receipts',client=employee)[0],403)
  self.assertEqual(call('admin/receipt-file/'+'a'*32,client=employee)[0],403)
  folder=str(Path(test_server.Tests.tmp.name)/'complete')
  self.assertEqual(call('admin/backup-settings',{'folder':folder,'enabled':False})[0],200)
  self.assertEqual(call('admin/backup-now',{})[0],200)
  archive=next(Path(folder).glob('*.zip'))
  with zipfile.ZipFile(archive) as z: snapshot=Path(test_server.Tests.tmp.name)/'saved.db';snapshot.write_bytes(z.read('schedule.db'))
  with closing(sqlite3.connect(snapshot)) as c:
   self.assertEqual(c.execute('SELECT body FROM receipts').fetchone()[0],b'%PDF-1.4\nreceipt test')
   self.assertEqual(c.execute('SELECT COUNT(*) FROM receipt_categories').fetchone()[0],2)

if __name__=='__main__': unittest.main()
