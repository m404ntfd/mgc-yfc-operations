import unittest,uuid,base64,io,json,urllib.request
from pypdf import PdfReader
from test_hr_catalog import HrCatalogTests
from test_hr_browser import sample_pdf
import server

class CompletionTests(HrCatalogTests):
 def test_completion_notices_individual_dismissal_and_print_permissions(self):
  r=self.invite();employee=self.login(r);self.ok('password',dict(password='employee-new-password'),employee);self.ok('consent',dict(version=server.HR_CONSENT_VERSION,agree=True,access_test=True,name='Sample Employee'),employee)
  self.ok('profile',dict(first='Sample',middle='',last='Employee',phone='228-555-0100',email='sample@example.test',address='Test street',city='Test',zip='39501'),employee)
  raw=sample_pdf()
  for kind in server.HR_STEPS:
   self.ok('template',dict(kind=kind,title='SAMPLE '+kind,edition='TEST',file=base64.b64encode(raw).decode(),reviewed=True))
   template=next(x['id'] for x in self.ok('dashboard')['templates'] if x['kind']==kind and x['active'])
   self.ok('upload',dict(kind=kind,template=template,file=base64.b64encode(raw).decode(),completed_signed=True,name='Sample Employee'),employee)
  with employee[0].open(f'http://127.0.0.1:{self.f.port}/api/hr/completed-file') as response:self.assertEqual(len(PdfReader(io.BytesIO(response.read())).pages),11)
  notices=self.ok('notifications');self.assertEqual(len(notices),1);self.assertEqual(notices[0]['enrollment'],r['id'])
  self.assertEqual(self.call('notifications',client=employee)[0],401)
  self.assertEqual(self.call('employee-file?id='+r['id'],client=employee)[0],401)
  reviewer=self.f.client('r');self.f.call('login',dict(name='Employee',password='testpassword'),reviewer)
  self.assertEqual(self.call('notifications',client=reviewer)[0],403)
  with server.connect() as c:c.execute('INSERT INTO user_grants VALUES(?,?) ON CONFLICT(name) DO UPDATE SET body=excluded.body',('Employee',json.dumps({'manage_hr':True})))
  # Reauthenticate to refresh this account's permissions.
  self.f.call('login',dict(name='Employee',password='testpassword'),reviewer)
  self.assertEqual(len(self.ok('notifications',client=reviewer)),1)
  self.ok('notification-read',dict(notification=notices[0]['id']));self.assertEqual(self.ok('notifications'),[]);self.assertEqual(len(self.ok('notifications',client=reviewer)),1)
  with self.f.admin[0].open(f'http://127.0.0.1:{self.f.port}/api/hr/employee-file?id='+r['id']) as response:pdf=PdfReader(io.BytesIO(response.read()))
  self.assertEqual(len(pdf.pages),11);self.assertIn('Sample',pdf.pages[0].extract_text());self.assertIn('submitted',pdf.pages[0].extract_text())
  doc=self.ok('employee?id='+r['id'])['documents'][0]['id'];self.ok('review',dict(id=r['id'],document=doc,status='needs_correction',note='Please correct the sample.'));self.assertEqual(self.ok('notifications',client=reviewer),[])

if __name__=='__main__':unittest.main()
