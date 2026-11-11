"""Focused OFFICE menus: real navigation, role filtering and unsaved-work guards."""
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
  assert f.call('pos/product',dict(request=uuid.uuid4().hex,name='Preserved sample shirt',price=599,category='Clothing',taxable=True))[0]==200
  original=f.call('pos/catalog-config')[1]
  assert f.call('admin/permissions',dict(name='Employee',grants={'manage_users':True},can_create=False,see_requests=False))[0]==200
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
   p=b.new_page(viewport={'width':1440,'height':1000});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   def login(page,name):
    page.goto(f'http://127.0.0.1:{f.port}/office');page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#officeTiles')).to_be_visible()
   login(p,'Admin')
   expect(p.locator('#officeTiles [data-office-category]')).to_have_count(6)
   expect(p.locator('#officeTiles [data-office-action]')).to_have_count(0)
   expected=['Products','Sales','Customers','Staff','Reports','System']
   assert p.locator('#officeTiles strong').all_text_contents()==expected
   # Every available tool has exactly one destination, including search aliases.
   coverage=p.evaluate('''()=>{const actions=officeMenuCards().map(c=>c.action);return actions.map(a=>[a,officeNavigationGroups.filter(g=>g.actions.includes(a)).length]);}''')
   assert all(n==1 for a,n in coverage),coverage
   for section in ['products','sales','accounts','staff','reports','system']:
    p.locator('#officeNav [data-office-section='+section+']').click()
    groups=p.locator('#officeGroups [data-office-group]').evaluate_all('(xs)=>xs.map(x=>x.dataset.officeGroup)')
    for group in groups:
     p.locator('#officeGroups [data-office-group='+group+']').click()
     assert 1<=p.locator('#officeTiles [data-office-action]').count()<=5
     assert p.locator('#officeGroupHeading h2').inner_text()
   # Home and the item hierarchy match the reference's short task tiles.
   p.locator('#officeNav [data-office-section=home]').click()
   p.evaluate("document.body.dataset.retailTheme='glass-teal';document.documentElement.dataset.theme='light'")
   p.screenshot(path=str(out/'OFFICE-Organized-Home.png'))
   p.locator('#officeTiles [data-office-category=products]').click()
   p.locator('#officeGroups [data-office-group=organization]').click()
   p.screenshot(path=str(out/'OFFICE-Organized-Products.png'))
   p.locator('#officeTiles [data-office-action=departments]').click();expect(p.locator('dialog.catalogSetup h2')).to_have_text('Departments');p.locator('dialog[open] .flowClose').click()
   expect(p.locator('#officeGroups [data-office-group=organization]')).to_have_attribute('aria-pressed','true')
   # Search establishes the right location and Back returns to that subgroup.
   p.locator('#officeSearchInput').fill('rounding')
   expect(p.locator('#officeSearchResults [data-office-action=cash-rules] .officeSearchPath')).to_have_text('Sales › Taxes & payment rules')
   p.locator('#officeSearchResults [data-office-action=cash-rules]').click();expect(p.locator('#financeRules')).to_be_visible()
   p.locator('#officeBack').click();expect(p.locator('#officeGroups [data-office-group=policies]')).to_have_attribute('aria-pressed','true')
   p.evaluate("document.body.dataset.retailTheme='midnight'");p.screenshot(path=str(out/'OFFICE-Organized-Sales-Dark.png'))
   # New group controls and breadcrumbs cannot discard an unsaved product.
   p.locator('#officeNav [data-office-section=products]').click();p.locator('#officeTiles [data-office-action=catalog]').click()
   form=p.locator('#flowProductForm');form.locator('[name=name]').fill('KEEP THIS UNSAVED ITEM')
   p.locator('#officeBreadcrumb [data-office-category=home]').click();expect(p.locator('#itemKeepEditing')).to_be_visible();p.locator('#itemKeepEditing').click();expect(form.locator('[name=name]')).to_have_value('KEEP THIS UNSAVED ITEM')
   p.locator('#officeNav [data-office-section=system]').click();p.locator('#itemDiscardLeave').click();expect(p.locator('#officeHeading')).to_have_text('System')
   assert f.call('pos/catalog-config')[1]==original, 'Navigation must not modify products, prices or taxes'
   # All palettes, including glass over a dark account preference, keep menus readable.
   themes=['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+x for x in ['blue','teal','violet','rose','graphite']]
   for theme in themes:
    for mode in ['light','dark']:
     p.evaluate('([t,m])=>{document.body.dataset.retailTheme=t;document.documentElement.dataset.theme=m}',[theme,mode]);p.wait_for_timeout(60)
     issues=p.evaluate(AUDIT);assert not issues,(theme,mode,issues)
   for width in [1920,1440,1366,1280,1200,1024,760]:
    p.set_viewport_size({'width':width,'height':900});p.wait_for_timeout(80)
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
    for section in ['products','sales','accounts','staff','reports','system']:
     p.locator('#officeNav [data-office-section='+section+']').click()
     expect(p.locator('#officeNav [data-office-section='+section+']')).to_have_attribute('aria-current','page')
   # Restricted roles see only permitted groups, with no administrative routes.
   limited=b.new_page();login(limited,'Employee')
   assert limited.locator('#officeTiles strong').all_text_contents()==['Staff','System']
   limited.locator('#officeTiles [data-office-category=staff]').click();expect(limited.locator('#officeGroups button')).to_have_count(1)
   expect(limited.locator('#officeTiles [data-office-action=roles]')).to_have_count(0)
   limited.locator('#officeTiles [data-office-action=users]').click();expect(limited.locator('#officeUserRows')).to_be_visible()
   limited.locator('#signOut').click();login(limited,'Employee');expect(limited.locator('#officeHeading')).to_have_text('OFFICE settings')
   desk=b.new_page();desk.goto(f'http://127.0.0.1:{f.port}/pos');expect(desk.locator('#officeNavigation')).to_have_count(0)
   assert not errors,errors;b.close()
  print('PASS focused groups, full tool coverage, search paths, navigation guards, permissions, catalog preservation, themes and widths.')
 finally:f.close()

if __name__=='__main__':run()
