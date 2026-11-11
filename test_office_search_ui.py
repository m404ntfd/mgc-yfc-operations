"""OFFICE settings search: permissions, navigation guards, keyboard and readable layouts."""
import os, time, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_update_coordination import CoordinatorFixture
from test_theme_contrast import AUDIT
import server

def run():
 f=CoordinatorFixture();out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
 server.POS_UPDATE_RELEASE=server.OFFICE_UPDATE_RELEASE={'version':'0.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
 try:
  code,result=f.call('pos/settings',dict(request=uuid.uuid4().hex,store='Thrift Mart',tax_bps=700,confirmed=True));assert code==200,result
  code,result=f.call('pos/product',dict(request=uuid.uuid4().hex,name='SAMPLE Shirt',price=599,category='Clothing',taxable=True));assert code==200,result
  code,result=f.call('admin/permissions',dict(name='Employee',grants={'manage_users':True},can_create=False,see_requests=False));assert code==200,result
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
   p=b.new_page(viewport={'width':1440,'height':1000});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   origin=f'http://127.0.0.1:{f.port}'
   def login(page,name):
    page.goto(origin+'/office');expect(page.locator('#officeSettingsSearch')).to_be_hidden()
    page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#officeTiles')).to_be_visible();expect(page.locator('#officeSettingsSearch')).to_be_visible()
   login(p,'Admin');search=p.locator('#officeSearchInput');results=p.locator('#officeSearchResults')
   search.fill('taxes');expect(results.locator('[data-office-action=taxes]')).to_be_visible()
   assert not p.evaluate('unfinished()'), 'Search must never mark business forms dirty'
   search.press('Enter');expect(p.locator('dialog.catalogSetup')).to_be_visible();expect(p.locator('dialog.catalogSetup h2')).to_have_text('Taxes');p.locator('dialog[open] .flowClose').click()
   search.fill('  rEvEnUe  CENTer ');search.press('Enter');expect(p.locator('dialog.catalogSetup h2')).to_have_text('Revenue Centers');p.locator('dialog[open] .flowClose').click()
   search.fill('categories');expect(results.locator('[data-office-action=sub-departments]')).to_be_visible()
   results.locator('[data-office-action=sub-departments]').click();expect(p.locator('dialog.catalogSetup h2')).to_have_text('Sub Departments');p.locator('dialog[open] .flowClose').click()
   for query,action in [('rounding','cash-rules'),('password','user-setup'),('gmail','reservation-messages'),('register computer','computer-register'),('open price','catalog'),('theme','office-appearance')]:
    search.fill(query);expect(results.locator('[data-office-action='+action+']')).to_be_visible()
   results.locator('[data-office-action=office-appearance]').click();expect(p.locator('#retailThemeForm')).to_be_visible();p.locator('dialog[open] .flowClose').click()
   search.fill('unlikelysearchxyz');expect(p.locator('#officeSearchSummary')).to_contain_text('No matching');expect(results.locator('button')).to_have_count(0)
   search.fill('<script>alert(1)</script>');expect(results.locator('script')).to_have_count(0);expect(results.locator('button')).to_have_count(0)
   p.locator('#officeSearchClear').click();expect(search).to_have_value('');expect(p.locator('#officeSearchSummary')).to_contain_text('Find a setting')
   search.fill('print');search.press('ArrowDown');expect(search).to_have_attribute('aria-activedescendant','officeSearchResult1');search.press('ArrowUp');expect(search).to_have_attribute('aria-activedescendant','officeSearchResult0')
   search.press('Escape');expect(p.locator('#officeSearchPopup')).to_be_hidden();p.locator('#officeHeading').click();p.keyboard.press('Control+k');expect(search).to_be_focused();expect(p.locator('#officeSearchPopup')).to_be_visible()
   # Search navigation uses the same Save / Discard / Keep editing flow as the tabs.
   search.fill('open price');results.locator('[data-office-action=catalog]').click();form=p.locator('#flowProductForm');form.locator('[name=name]').fill('UNSAVED SAMPLE')
   search.fill('Taxes');results.locator('[data-office-action=taxes]').click();expect(p.locator('#itemKeepEditing')).to_be_visible();p.locator('#itemKeepEditing').click();expect(form.locator('[name=name]')).to_have_value('UNSAVED SAMPLE')
   search.click();results.locator('[data-office-action=taxes]').click();p.locator('#itemDiscardLeave').click();expect(p.locator('dialog.catalogSetup h2')).to_have_text('Taxes');assert not p.evaluate('changedForms.has(document.querySelector("#flowProductForm"))');p.locator('dialog[open] .flowClose').click()
   p.locator('[data-office-section=home]').click()
   search.fill('open price');results.locator('[data-office-action=catalog]').click()
   form.locator('[name=name]').fill('SAVED SEARCH SAMPLE');form.locator('[name=category]').select_option('Clothing')
   search.fill('Taxes');results.locator('[data-office-action=taxes]').click();p.locator('#itemSaveLeave').click()
   expect(p.locator('dialog.catalogSetup h2')).to_have_text('Taxes')
   assert any(x['name']=='SAVED SEARCH SAMPLE' for x in f.call('pos/catalog-config')[1]['products'])
   p.locator('dialog[open] .flowClose').click();p.locator('[data-office-section=home]').click()
   # Settings with a different unsaved form cannot be switched behind the guard.
   search.fill('rounding');results.locator('[data-office-action=cash-rules]').click();p.locator('#financeRules [name=cash_rounding]').select_option('nearest5')
   search.fill('Taxes');results.locator('[data-office-action=taxes]').click();expect(p.locator('#financeRules')).to_be_visible();expect(p.locator('#financeRules [name=cash_rounding]')).to_have_value('nearest5');expect(p.locator('dialog.catalogSetup')).to_have_count(0)
   p.locator('#financeRulesDiscard').click();p.locator('[data-office-section=home]').click()
   themes=['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+x for x in ['blue','teal','violet','rose','graphite']]
   search.fill('tax')
   for theme in themes:
    for mode in ['light','dark']:
     p.evaluate('([t,m])=>{document.body.dataset.retailTheme=t;document.documentElement.dataset.theme=m}',[theme,mode]);p.wait_for_timeout(60)
     issues=p.evaluate(AUDIT);assert not issues,(theme,mode,issues)
   p.evaluate("posMessage('');document.body.dataset.retailTheme='classic-gray';document.documentElement.dataset.theme='light'")
   p.screenshot(path=str(out/'OFFICE-Settings-Search.png'))
   p.evaluate("document.body.dataset.retailTheme='midnight'");p.screenshot(path=str(out/'OFFICE-Settings-Search-Dark.png'))
   for width in [1920,1440,1366,1200,1100,1024,1000]:
    p.set_viewport_size({'width':width,'height':800});p.wait_for_timeout(80)
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('Overflow',width)
    assert p.locator('#officeSearchPopup').evaluate('(e)=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight}'), ('Clipped results',width)
    assert p.locator('#officeSearchInput').evaluate('(e)=>{const r=e.getBoundingClientRect();const nav=document.querySelector("#officeNav").getBoundingClientRect();return r.left>=nav.right||r.top>=nav.bottom}'), ('Overlapping tabs',width)
   p.screenshot(path=str(out/'OFFICE-Settings-Search-Compact.png'))
   # Role-limited users can find allowed screens but never see administrative settings.
   limited=b.new_page();login(limited,'Employee');limited.locator('#officeSearchInput').fill('users');expect(limited.locator('#officeSearchResults [data-office-action=users]')).to_be_visible()
   for query in ['taxes','computer updates']:
    limited.locator('#officeSearchInput').fill(query);expect(limited.locator('#officeSearchResults button')).to_have_count(0)
   limited.locator('#officeSearchInput').fill('roles permissions');expect(limited.locator('#officeSearchResults [data-office-action=roles]')).to_have_count(0)
   limited.locator('#officeSearchInput').fill('user');limited.locator('#officeSearchResults [data-office-action=users]').click();expect(limited.locator('#officeUserRows')).to_be_visible()
   limited.locator('#signOut').click();expect(limited.locator('#officeSettingsSearch')).to_be_hidden();expect(limited.locator('#officeSearchResults button')).to_have_count(0)
   desk=b.new_page();desk.goto(origin+'/pos');expect(desk.locator('#officeSettingsSearch')).to_have_count(0)
   assert not errors,errors;b.close()
  print('PASS settings search, aliases, keyboard, permissions, unsaved-item protection, 20 theme checks and 7 desktop widths.')
 finally:f.close()

if __name__=='__main__':run()
