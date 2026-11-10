import unittest,uuid,base64,json,urllib.request,zipfile
from unittest.mock import patch
from pathlib import Path
import server
from test_update_coordination import CoordinatorFixture

class HrCatalogTests(unittest.TestCase):
 def setUp(self):self.f=CoordinatorFixture()
 def tearDown(self):self.f.close()
 def call(self,path,body=None,client=None):return self.f.call('hr/'+path,body,client)
 def ok(self,path,body=None,client=None):
  code,r=self.call(path,body,client);self.assertEqual(code,200,r);return r
 def invite(self):return self.ok('invite',dict(request=uuid.uuid4().hex,first='Sample',middle='',last='Employee',phone='228-555-0100',email='sample@example.test',username='New employee',employer=server.HR_EMPLOYERS[1]))
 def login(self,r):
  e=self.f.client('h');self.ok('login',dict(token=r['link'].split('#')[1],username=r['username'],password=r['temporary_password']),e);return e
 def test_private_invitation_consent_encryption_and_idempotent_upload(self):
  employee=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),employee)
  self.assertEqual(self.call('dashboard',client=employee)[0],403)
  self.assertEqual(self.call('state',client=self.f.client('x'))[0],401)
  r=self.invite();self.assertEqual(self.f.call('login',dict(name=r['username'],password=r['temporary_password']),self.f.client('n'))[0],403)
  e=self.login(r);self.ok('activity',client=e)
  with server.connect() as c:self.assertTrue(any(x['kind']=='Employee onboarding' for x in server.flow_collect(c).values()))
  self.assertEqual(self.call('consent',dict(agree=True),e)[0],403)
  self.ok('password',dict(password='new-long-password'),e)
  self.ok('consent',dict(version=server.HR_CONSENT_VERSION,agree=True,access_test=True,name='Sample Employee'),e)
  doc=base64.b64encode(b'%PDF-1.4 TEST completed document SSN-TEST-123').decode()
  self.ok('template',dict(kind='w4',title='TEST W4',edition='TEST',file=doc,reviewed=True))
  template=next(t['id'] for t in self.ok('dashboard')['templates'] if t['active']);args=dict(kind='w4',template=template,file=doc,name='Sample Employee',completed_signed=True)
  self.ok('upload',args,e);self.ok('upload',args,e);s=self.ok('state',client=e);self.assertEqual(len(s['documents']),1)
  with server.connect() as c:
   raw=c.execute('SELECT body FROM hr_documents').fetchone()[0];self.assertNotIn(b'SSN-TEST-123',raw);self.assertIn('file',server.hr_unpack(raw))
  self.ok('help',dict(message='Please help with this section'),e);self.assertEqual(self.ok('dashboard')['employees'][0]['help_open'],1)
  self.ok('reply',dict(id=r['id'],message='We can help tomorrow'))
  self.assertEqual(self.ok('state',client=e)['messages'][-1]['body'],'We can help tomorrow')
  self.ok('resolve',dict(id=r['id']));self.assertEqual(self.ok('dashboard')['employees'][0]['help_open'],0)
  self.ok('revoke',dict(id=r['id']));self.assertEqual(self.call('state',client=e)[0],401)
 def test_expiry_and_duplicate_invitation(self):
  args=dict(request=uuid.uuid4().hex,first='Sample',middle='',last='Person',phone='228-555-0100',email='example@example.test',username='Sample person',employer=server.HR_EMPLOYERS[0])
  a=self.ok('invite',args);b=self.ok('invite',args);self.assertTrue(b['already_created'])
  with server.connect() as c:
   self.assertEqual(c.execute("SELECT COUNT(*) FROM users WHERE name='Sample person'").fetchone()[0],1)
   c.execute('UPDATE hr_enrollments SET expires=0 WHERE id=?',(a['id'],))
  self.assertEqual(self.call('login',dict(token=a['link'].split('#')[1],username=a['username'],password=a['temporary_password']),self.f.client('k'))[0],401)
 def test_catalog_multitax_snapshot_discount_and_sale(self):
  def post(path,**kw):
   code,r=self.f.call('pos/'+path,dict(request=uuid.uuid4().hex,**kw));self.assertEqual(code,200,r);return r
  post('settings',store='TEST',tax_bps=700,confirmed=True)
  opts=dict(revision=0,categories=['Clothing'],printing=['Counter'],taxes=[dict(id='state',name='State',bps=700,store_id='thrift-mart'),dict(id='local',name='Local',bps=100,store_id='thrift-mart')])
  post('catalog-options-save',**opts)
  p=post('product-save',name='Sample',category='Clothing',price=1000,taxable=True,rules=dict(tax_ids=['state','local'],print_category='Counter'))['ids'][0]
  cart=post('new')['cart'];cart=post('add',cart=cart['id'],revision=cart['revision'],product=p,quantity=1)['cart'];self.assertEqual(cart['tax'],80)
  opts['revision']=1;opts['taxes'][0]['bps']=900;post('catalog-options-save',**opts)
  with server.connect() as c:
   server.retail_adjust(c,cart,dict(mode='discount',amount=100,reason='TEST'), 'Admin');self.assertEqual(cart['tax'],72)
  sale=post('cash',cart=cart['id'],revision=cart['revision'],tender=1000)['sale'];self.assertEqual(sale['tax'],72)
  self.assertEqual(sale['lines'][0]['tax_rates'][0]['bps'],700)
 def test_backup_includes_hr_key_and_restores(self):
  self.invite()
  with server.connect() as c:r=c.execute('SELECT body FROM hr_enrollments').fetchone()[0]
  before=server.hr_unpack(r);key=(server.DATA/'hr-encryption.key').read_bytes()
  from remote.restore import restore_backup
  import sqlite3
  dest=server.DATA/'backup.zip'
  with zipfile.ZipFile(dest,'w') as z:
   z.write(server.DB,'schedule.db');z.write(server.DATA/'hr-encryption.key','hr-encryption.key');z.writestr('manifest.json',json.dumps(dict(application='thrift-mart-dispatch',format=1)))
  restored=server.DATA/'restored';restore_backup(dest,restored)
  self.assertEqual((restored/'hr-encryption.key').read_bytes(),key)
  from cryptography.fernet import Fernet
  with sqlite3.connect(restored/'schedule.db') as c:payload=c.execute('SELECT body FROM hr_enrollments').fetchone()[0]
  c.close()
  self.assertEqual(json.loads(Fernet(key).decrypt(payload)),before)

if __name__=='__main__':unittest.main()
