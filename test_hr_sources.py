import base64,io,json,time,unittest
from pathlib import Path
import server
from test_hr_catalog import HrCatalogTests

class SourceFormsTests(HrCatalogTests):
 def test_source_forms_and_phone(self):
  dashboard=self.ok('dashboard');sources=[x for x in dashboard['templates'] if x['id'].startswith('source-')]
  self.assertEqual({x['kind'] for x in sources},{'background','i9','w4','ms'})
  for t in sources:self.ok('browser-source-activate',dict(template=t['id'],reviewed=True))
  invite=self.invite();employee=self.login(invite)
  self.ok('password',dict(password='new-employee-password'),employee)
  self.ok('consent',dict(version=server.HR_CONSENT_VERSION,agree=True,access_test=True,name='Sample Employee'),employee)
  profile=dict(first='Sample',middle='',last='Employee',phone='555-0100',email='sample@example.test',address='100 Test Street',city='Gulfport',state='MS',zip='39501')
  self.assertEqual(self.call('profile',profile,employee)[0],400)
  self.ok('profile',dict(profile,phone='+1 (228) 555-0100'),employee)
  self.assertEqual(self.ok('state',client=employee)['profile']['phone'],'(228) 555-0100')
  self.assertEqual(self.call('completed-file',client=employee)[0],400)
  out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
  for t in sources:
   form=self.ok('browser-form?form='+t['id'],client=employee)
   self.assertTrue(any(f['type']=='signature' for f in form['config']['fields']))
   with server.connect() as c:
    row=c.execute('SELECT f.*,t.body AS pdf FROM hr_browser_forms f JOIN hr_templates t ON t.id=f.template WHERE f.id=?',(t['id'],)).fetchone()
    raw=server.hr_browser_render(c,row,form['config'],form['values'],'employee',name='SAMPLE Employee',signed_at=time.time())
   (out/('SAMPLE-Original-'+t['kind']+'.pdf')).write_bytes(raw)
   pdf=server.hr_pdf_libraries()[2].PdfDocument(raw)
   for i in range(2 if t['kind']=='background' else 1):
    page=pdf[i];bitmap=page.render(scale=1.3);bitmap.to_pil().save(out/('Original-'+t['kind']+'-'+str(i)+'.png'));bitmap.close();page.close()
   pdf.close()

if __name__=='__main__':unittest.main()
