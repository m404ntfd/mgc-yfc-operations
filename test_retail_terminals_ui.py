from test_ui_helpers import password_login_page
import os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
f=CoordinatorFixture()
def post(path,**data):
 code,result=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert code==200,result;return result
try:
 post('settings',store='CoastYouth Retail',tax_bps=700,confirmed=True)
 products=[]
 for name,category,price in [('Adult shirt','Clothing',599),('Jeans','Clothing',899),('Jacket','Clothing',1499),('Kids shirt','Clothing',399),('Table lamp','Home',1299),('Picture frame','Home',499),('Paperback','Books',199),('Side table','Furniture',2499)]:products.append(post('product',name=name,category=category,price=price,taxable=True)['product'])
 with sync_playwright() as pw:
  b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));ctx=b.new_context(viewport={'width':1440,'height':1000});p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));origin=f'http://127.0.0.1:{f.port}';out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True);
  p.goto(origin+'/office');password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(p.locator('#officeTiles .officeTile')).to_have_count(32)
  p.screenshot(path=str(out/'Retail-OFFICE-Home-Preview.png'))
  p.locator('[data-office-action=layouts]').click();p.locator('#layoutForm [name=name]').fill('Front counter');p.locator('#groupName').fill('Clothing');p.locator('#groupColor').fill('#9b477e')
  for product in products[:4]:p.locator('[data-product-add="'+product['id']+'"]').click()
  p.locator('#groupAdd').click();p.locator('#groupName').fill('Home & gifts');p.locator('#groupColor').fill('#287a87')
  for product in products[4:]:p.locator('[data-product-add="'+product['id']+'"]').click()
  p.locator('#layoutForm button').filter(has_text='Save layout').click();expect(p.locator('#layoutStatus')).to_contain_text('saved')
  p.screenshot(path=str(out/'Retail-OFFICE-Layout-Preview.png'))
  p.locator('#officeBack').click();p.locator('[data-office-action=terminals]').click();p.locator('#terminalForm [name=name]').fill('Front counter 1');p.locator('#terminalForm [name=layout]').select_option(label='Front counter');p.locator('#terminalForm button').first.click();expect(p.locator('#terminalStatus')).to_have_text('Terminal saved.')
  d=ctx.new_page();d.on('pageerror',lambda e:errors.append(str(e)));d.goto(origin+'/pos');expect(d.locator('#retailEnroll')).to_be_visible();d.locator('#retailEnroll').click();d.locator('dialog[open] [name=terminal]').select_option(label='Front counter 1');d.locator('dialog[open] button').filter(has_text='Register').click();expect(d.locator('#retailScreenBar')).to_contain_text('Front counter 1');expect(d.locator('#posCatalog button')).to_have_count(4)
  d.locator('#posNew').click();expect(d.locator('#posCart')).to_contain_text('Saved on server');d.locator('#posCatalog button').filter(has_text='Adult shirt').click();expect(d.locator('#posCart')).to_contain_text('Adult shirt');d.locator('#retailNext').click();expect(d.locator('#posCatalog')).to_contain_text('Table lamp');d.locator('#posCatalog button').filter(has_text='Table lamp').click();expect(d.locator('#posCart')).to_contain_text('$20.31');assert d.locator('#posCatalog button').first.evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(40, 122, 135)';d.screenshot(path=str(out/'Retail-DESK-Configured-Preview.png'))
  p.locator('#officeBack').click();p.locator('[data-office-action=terminals]').click();expect(p.locator('#retailEditor')).to_contain_text('Registered');p.screenshot(path=str(out/'Retail-OFFICE-Terminals-Preview.png'))
  d.locator('#posPayNow').click();d.locator('#posCash [name=tender]').fill('25');d.locator('#posCash button.primary').click();expect(d.locator('#posReceipt')).to_contain_text('Change: $4.69')
  p.locator('#officeBack').click();p.locator('[data-office-action=layouts]').click();p.locator('#groupName').fill('Unsaved');p.locator('#officeBack').click();expect(p.locator('#layoutForm')).to_be_visible();p.locator('#layoutRevert').click();expect(p.locator('#groupName')).to_have_value('Clothing')
  for width in [1024,1366]:
   p.set_viewport_size({'width':width,'height':900});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   d.set_viewport_size({'width':width,'height':900});assert d.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors;b.close()
finally:f.close()
print('PASS OFFICE layout editing, terminal enrollment, DESK groups, cash checkout, unsaved-work guard and previews')

