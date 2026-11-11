from test_ui_helpers import office_setting
"""Setup list retries, copy isolation, deletion confirmation, routes and color tags."""
import os,time,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_theme_contrast import AUDIT
import server
f=CoordinatorFixture();out=Path('output/preview');out.mkdir(exist_ok=True,parents=True)
server.POS_UPDATE_RELEASE=server.OFFICE_UPDATE_RELEASE={'version':'0.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
def post(path,**body):
 code,result=f.call('pos/'+path,dict(request=uuid.uuid4().hex,**body));assert code==200,result;return result
try:
 post('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
 post('catalog-options-save',revision=0,section='printing',printing=['Counter','Warehouse'])
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));p=b.new_page(viewport={'width':1440,'height':1050});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));accept=[True];dialogs=[]
  def dialog(d):
   dialogs.append(d.message)
   if accept[0]:d.accept()
   else:d.dismiss()
  p.on('dialog',dialog);p.goto(f'http://127.0.0.1:{f.port}/office');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(p.locator('#officeTiles')).to_be_visible()
  office_setting(p,'revenue-centers').click();form=p.locator('#catalogOptionsForm');form.locator('[name=entry_name]').fill('RETRY SAMPLE')
  captured=[]
  def lost_response(route):
   captured.append(route.request.post_data_json);response=route.fetch();assert response.status==200;route.abort()
  p.route('**/api/pos/catalog-options-save',lost_response,times=1);form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_class('setupStatus setupError');expect(form.locator('[name=entry_name]')).to_have_value('RETRY SAMPLE')
  assert len(f.call('pos/catalog-options')[1]['revenue_centers'])==1
  form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('Revenue Center added.');assert len(f.call('pos/catalog-options')[1]['revenue_centers'])==1
  p.locator('[data-setup-action=copy]:visible').click();expect(form.locator('[name=entry_name]')).to_have_value('RETRY SAMPLE (copy)');accept[0]=False;p.locator('[data-catalog-section=taxes]').click();expect(form.locator('[name=entry_name]')).to_have_value('RETRY SAMPLE (copy)');assert 'Discard' in dialogs[-1]
  accept[0]=True;form.locator('.setupCancel').click();accept[0]=False;p.locator('[data-setup-action=delete]:visible').click();expect(p.locator('[data-setup-row]:visible')).to_have_count(1);accept[0]=True;p.locator('[data-setup-action=delete]:visible').click();expect(p.locator('[data-setup-row]:visible')).to_have_count(0);p.locator('dialog[open] .flowClose').click()
  office_setting(p,'printing').click();routeForm=p.locator('#flowRoutes');routeForm.locator('[name=route_category]').select_option('Counter');routeForm.locator('[name=route_printer]').fill('Receipt printer');routeForm.locator('[type=submit]').click();expect(p.locator('#flowRouteStatus')).to_have_text('printer route added.')
  p.locator('[data-setup-action=copy]:visible').click();expect(routeForm.locator('[name=route_printer]')).to_have_value('Receipt printer');routeForm.locator('[name=route_category]').select_option('Warehouse');routeForm.locator('[type=submit]').click();expect(p.locator('[data-setup-row]:visible')).to_have_count(2)
  p.locator('[data-setup-action=edit]:visible').click();routeForm.locator('[name=route_printer]').fill('Warehouse printer');routeForm.locator('[type=submit]').click();expect(p.locator('#flowRouteStatus')).to_have_text('printer route updated.');p.screenshot(path=str(out/'OFFICE-Printer-Route-List.png'))
  p.locator('[data-setup-action=delete]:visible').click();expect(p.locator('[data-setup-row]:visible')).to_have_count(1);p.locator('#officeBack').click();office_setting(p,'thrift-settings').click()
  tagForm=p.locator('#thriftTagSetupForm');tagForm.locator('[name=tag_name]').fill('SAMPLE Blue');tagForm.locator('[name=percent]').fill('25');tagForm.locator('[type=submit]').click();expect(p.locator('#thriftTagStatus')).to_have_text('color tag added.')
  p.locator('[data-setup-action=copy]:visible').click();expect(tagForm.locator('[name=percent]')).to_have_value('25');tagForm.locator('[name=tag_name]').fill('SAMPLE Green');tagForm.locator('[name=color]').fill('#227744');tagForm.locator('[type=submit]').click();expect(p.locator('[data-setup-row]:visible')).to_have_count(2)
  p.locator('[data-setup-action=edit]:visible').click();tagForm.locator('[name=percent]').fill('50');tagForm.locator('[type=submit]').click();expect(p.locator('[aria-selected=true]:visible')).to_contain_text('50%');p.screenshot(path=str(out/'OFFICE-Color-Tag-List.png'))
  for theme in ['classic-gray','midnight','glass-teal']:
   p.evaluate('(t)=>document.body.dataset.retailTheme=t',theme);p.wait_for_timeout(80);issues=p.evaluate(AUDIT);assert not issues,(theme,issues)
  p.locator('[data-setup-action=delete]:visible').click();expect(p.locator('[data-setup-row]:visible')).to_have_count(1)
  p.locator('[data-thrift-tab=donations]').click();p.locator('#thriftSettings [name=donations]').check();p.locator('#thriftSaveRules').click();expect(p.locator('#thriftRulesStatus')).to_have_text('Thrift rules saved.');config=f.call('pos/thrift-config')[1]['settings'];assert config['donations'] and len(config['tags'])==1 and config['tags'][0]['bps']==2500
  p.locator('.flowClose').click();assert not errors,errors;b.close()
 print('PASS interrupted-save retry without duplicates, copy isolation, cancel/discard protection, printer routes and color-tag list actions.')
finally:f.close()
