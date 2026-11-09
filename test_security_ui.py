"""Browser test for administrator and delegated account-unlock settings."""
import test_server,os
from test_ui_helpers import password_login_page
from playwright.sync_api import sync_playwright,expect

def run():
 Fixture=test_server.Tests
 Fixture.setUpClass()
 try:
  Fixture.call('setup',{'name':'Admin','password':'testpassword'})
  Fixture.call('user',{'name':'Helper','password':'1234'})
  Fixture.call('user',{'name':'Brad','password':'1234'})
  Fixture.call('admin/permissions',{'name':'Helper','grants':{'unlock_users':True}})
  with sync_playwright() as p:
   browser=p.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   base=f'http://127.0.0.1:{Fixture.port}'
   def login(name,password):
    page.emulate_media(reduced_motion='reduce');page.goto(base+'/office');password_login_page(page).locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill(password);page.locator('#login button').click();page.locator('[data-office-action=login-security]').click()
   login('Admin','testpassword');expect(page.locator('#officeLoginLimit [name=max_attempts]')).to_have_value('5');page.locator('#officeLoginLimit [name=max_attempts]').fill('2');page.locator('#officeLoginLimit button').click();expect(page.locator('#officeSecurityStatus')).to_have_text('Login limit saved.')
   for _ in range(2):Fixture.call('login',{'name':'Brad','password':'bad'})
   page.evaluate("officeAction('login-security')");expect(page.locator('#officeLockedUsers')).to_contain_text('Brad')
   page.context.clear_cookies();login('Helper','1234');expect(page.locator('#officeLoginLimit')).to_be_hidden();expect(page.locator('#officeLockedUsers')).to_contain_text('Brad');page.locator('[data-office-unlock="Brad"]').click();expect(page.locator('#officeLockedUsers')).to_contain_text('No locked accounts.')
   assert not errors,errors;browser.close()
 finally:Fixture.tearDownClass()
 print('PASS mobile administrator settings and delegated unlock without administrator privileges')
if __name__=='__main__':run()
