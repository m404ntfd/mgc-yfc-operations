"""Desktop browser links preserve authentication and reach the requested screen."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  with sync_playwright() as p:
   b=p.chromium.launch();page=b.new_page(reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   base=f'http://127.0.0.1:{F.port}/'
   page.goto(base+'#settings');expect(page.locator('#auth')).to_be_visible();expect(page.locator('#settings')).to_be_hidden()
   page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
   expect(page.locator('#updatePanel')).to_be_visible();expect(page.locator('#sectionChooser')).to_be_hidden();expect(page.locator('#overview')).to_be_hidden()
   page.goto(base+'#login');expect(page.locator('#auth')).to_be_visible();expect(page.locator('#app')).to_be_hidden()
   assert page.request.get(base+'api/session').json()['user'] is None
   page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
   expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click();expect(page.locator('#sectionChooser')).to_be_hidden()
   page.goto(base+'#settings');expect(page.locator('#updatePanel')).to_be_visible()
   assert not errors,errors;b.close()
 finally:F.tearDownClass()
 print('PASS desktop login forces sign-in; manage opens updates only after authentication; hash navigation works')
if __name__=='__main__':run()
