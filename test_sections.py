"""Browser smoke checks for Operations section routing and branding."""
import test_server
from playwright.sync_api import sync_playwright,expect

def run():
 Fixture=test_server.Tests
 Fixture.setUpClass()
 try:
  Fixture.call('setup',{'name':'Admin','password':'testpassword'})
  with sync_playwright() as p:
   browser=p.chromium.launch();errors=[]
   for width,path in [(390,'/mobile'),(1280,'/')]:
    guest=browser.new_page(viewport={'width':width,'height':844},reduced_motion='reduce')
    guest.on('pageerror',lambda e:errors.append(str(e)))
    guest.goto(f'http://127.0.0.1:{Fixture.port}{path}')
    for section in ('dispatchSection','pagingSection','receiptsSection','printSection','commsSection','workforceSection','appearanceMenu','chooseStartSection'):
     guest.locator('#receiptShortcut').click()
     expect(guest.locator('#receiptUpload')).to_be_visible()
     guest.locator('#storeMenuButton').click()
     guest.locator('#'+section).click()
     prompt=guest.get_by_role('button',name='Log in first',exact=True)
     expect(prompt).to_be_visible()
     expect(guest.locator('#receiptUpload')).to_be_visible()
     prompt.click()
     expect(guest.locator('#receiptUpload')).to_be_hidden()
     expect(guest.locator('#currentSection')).to_have_text('Sign in')
     expect(guest.locator('#login [name=name]')).to_be_focused()
    guest.close()
   page=browser.new_page(viewport={'width':390,'height':844});page.on('pageerror',lambda e:errors.append(str(e)))
   page.emulate_media(reduced_motion='reduce');page.goto(f'http://127.0.0.1:{Fixture.port}')
   page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
   page.locator('[name=section][value=receipts]').check();page.locator('#sectionChooserForm button').click()
   expect(page.locator('#receipts')).to_be_visible();expect(page.locator('.operationsTitle')).to_contain_text('MGC YFC Operations');expect(page.locator('#currentSection')).to_have_text('Receipts & Accounting')
   assert page.locator('body>header').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(6, 122, 6)'
   page.reload();expect(page.locator('#receipts')).to_be_visible()
   page.locator('#storeMenuButton').click();page.locator('#pagingSection').click();expect(page.locator('#currentSection')).to_have_text('Store Associate Paging');expect(page.locator('#receipts')).to_be_hidden()
   assert page.locator('body>header').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(122, 21, 32)'
   page.locator('#storeMenuButton').click();page.locator('#dispatchSection').click();expect(page.locator('#app')).to_be_visible();expect(page.locator('#paging')).to_be_hidden()
   page.locator('#storeMenuButton').click();page.locator('#receiptsSection').click();expect(page.locator('#app')).to_be_hidden()
   page.context.clear_cookies();page.reload();expect(page.locator('#receipts')).to_be_hidden();expect(page.locator('#auth')).to_be_visible()
   assert not errors,errors;browser.close()
 finally:Fixture.tearDownClass()
 print('PASS branding, section colors, receipts navigation, saved start section and logout')
if __name__=='__main__':run()
