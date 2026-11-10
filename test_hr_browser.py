import base64,io,json,unittest,uuid,sqlite3,urllib.request
from pathlib import Path
from pypdf import PdfReader
from reportlab.pdfgen import canvas
import server
from test_hr_catalog import HrCatalogTests

def sample_pdf():
    out=io.BytesIO();p=canvas.Canvas(out,pagesize=(612,792))
    p.setFont('Helvetica-Bold',18);p.drawString(35,750,'SAMPLE ONLY - Browser onboarding form')
    p.setFont('Helvetica',11);p.drawString(35,715,'Employee name');p.drawString(35,650,'I confirm that the information I entered is accurate.')
    p.drawString(35,580,'Employee signature');p.drawString(350,580,'Date')
    p.drawString(35,480,'Employer review');p.drawString(35,420,'Employer signature');p.drawString(350,420,'Date')
    p.showPage();p.drawString(35,750,'SAMPLE ONLY - Instructions');p.drawString(35,720,'Read the full form before signing. This test is not an employment form.');p.save();return out.getvalue()

def sample_fields():
    def f(id,label,type,role,x,y,width=260,required=False):return dict(id=id,label=label,type=type,role=role,x=x,y=y,width=width,height=20,page=0,required=required)
    return [f('name','Employee name','text','employee',35,80,required=True),f('signature','Employee signature','signature','employee',35,215),f('date','Employee signing date','date','employee',350,215,160),f('review','Employer review','text','employer',35,320,required=True),f('employer_signature','Employer signature','signature','employer',35,375),f('employer_date','Employer signing date','date','employer',350,375,160)]

class BrowserFormsTests(HrCatalogTests):
    # Inherited checks intentionally verify backwards-compatible existing HR behavior too.
    def setup_form(self,kind='i9'):
        self.ok('template',dict(kind=kind,title='SAMPLE browser form',edition='TEST ONLY',file=base64.b64encode(sample_pdf()).decode(),reviewed=True))
        t=next(t['id'] for t in self.ok('dashboard')['templates'] if t['active'])
        form=self.ok('browser-publish',dict(template=t,fields=sample_fields(),attestations={'employee':'I confirm the information I entered is accurate.','employer':'I confirm my employer review is accurate.'},reviewed=True))['id']
        r=self.invite();e=self.login(r);self.ok('password',dict(password='employee-new-password'),e);self.ok('consent',dict(version=server.HR_CONSENT_VERSION,agree=True,access_test=True,name='Sample Employee'),e)
        return r,e,form
    def read_pages(self,form,e,extra=''):
        for page in range(2):
            with e[0].open(f'http://127.0.0.1:{self.f.port}/api/hr/browser-page?form={form}&page={page}'+extra) as response:self.assertEqual(response.headers['Content-Type'],'image/png')
    def test_signing_identity_versions_and_employer_boundary(self):
        r,e,form=self.setup_form();key=dict(form=form,role='employee')
        self.assertEqual(self.call('browser-save',dict(key,revision=0,values={'review':'forged'}),e)[0],403)
        result=self.ok('browser-save',dict(key,revision=0,values={'name':'Sample Employee'}),e);self.assertEqual(result['revision'],1)
        self.assertEqual(self.call('browser-save',dict(key,revision=0,values={'name':'stale'}),e)[0],409)
        sign=dict(key,revision=1,name='Sample Employee',password='employee-new-password',acknowledged=True,reviewed_pages=[0,1])
        self.assertEqual(self.call('browser-sign',sign,e)[0],400) # Pages not yet opened.
        self.read_pages(form,e)
        self.assertEqual(self.call('browser-sign',dict(sign,password='wrong-password'),e)[0],403)
        doc=self.ok('browser-sign',sign,e)['document'];self.assertEqual(self.ok('browser-sign',sign,e)['document'],doc)
        with server.connect() as c:
            row=c.execute('SELECT * FROM hr_documents WHERE id=?',(doc,)).fetchone();payload=server.hr_unpack(row['body'])
            self.assertNotIn(b'Sample Employee',row['body']);pdf=PdfReader(io.BytesIO(base64.b64decode(payload['file'])))
            self.assertIn('Sample Employee',pdf.pages[0].extract_text());self.assertFalse(pdf.get_fields())
            with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM hr_documents WHERE id=?',(doc,))
        self.assertEqual(self.call('review',dict(id=r['id'],document=doc,status='accepted',employer_verified=True))[0],400)
        employer=dict(form=form,role='employer',enrollment=r['id'],parent=doc)
        self.assertEqual(self.call('browser-save',dict(employer,revision=0,values={'review':'forged'}),e)[0],401)
        self.ok('browser-save',dict(employer,revision=0,values={'review':'Documents examined'}))
        self.read_pages(form,self.f.admin,'&role=employer&enrollment='+r['id']+'&parent='+doc)
        employer_sign=dict(employer,revision=1,name='Sample HR reviewer',password='testpassword',acknowledged=True,reviewed_pages=[0,1])
        self.assertEqual(self.call('browser-sign',employer_sign)[0],400)
        final=self.ok('browser-sign',dict(employer_sign,examined_documents=True))['document']
        self.ok('review',dict(id=r['id'],document=final,status='accepted',employer_verified=True))
        with server.connect() as c:
            body=server.hr_unpack(c.execute('SELECT body FROM hr_documents WHERE id=?',(final,)).fetchone()[0]);text=PdfReader(io.BytesIO(base64.b64decode(body['file']))).pages[0].extract_text()
            self.assertIn('Sample Employee',text);self.assertIn('Sample HR reviewer',text);self.assertEqual(body['signature']['parent'],doc)
        other=self.f.client('unauthenticated');self.assertEqual(self.call('browser-form?form='+form,client=other)[0],401)
        out=Path('output/preview');out.mkdir(parents=True,exist_ok=True);(out/'SAMPLE-Signed-Onboarding.pdf').write_bytes(base64.b64decode(body['file']))
    def test_correction_retains_previous_signed_record(self):
        r,e,form=self.setup_form('deposit');key=dict(form=form,role='employee');self.ok('browser-save',dict(key,revision=0,values={'name':'Original Sample'}),e);self.read_pages(form,e)
        sign=dict(key,revision=1,name='Sample Employee',password='employee-new-password',acknowledged=True,reviewed_pages=[0,1]);old=self.ok('browser-sign',sign,e)['document']
        self.ok('review',dict(id=r['id'],document=old,status='needs_correction',note='Correct the sample name.'))
        key['correction']=old;self.ok('browser-save',dict(key,revision=0,values={'name':'Corrected Sample'}),e);new=self.ok('browser-sign',dict(sign,correction=old),e)['document'];self.assertNotEqual(new,old)
        with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM hr_documents WHERE enrollment=?',(r['id'],)).fetchone()[0],2)

if __name__=='__main__':unittest.main()
