"""Server approval, account preferences and dedicated settings navigation."""
import http.cookiejar,urllib.request
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  F.call('user',{'name':'Employee','password':'testpassword'})
  F.call('admin/permissions',{'name':'Employee','grants':{'check_updates':True,'view_schedule':True}})
  client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  F.call('login',{'name':'Employee','password':'testpassword'},client)
  assert F.call('update-config',{'repository':'example/store'},client)[0]==403
  assert F.call('repository-unlock',{'name':'Employee','password':'testpassword'},client)[0]==403
  assert F.call('repository-unlock',{'name':'Admin','password':'wrong'},client)[0]==403
  assert F.call('repository-unlock',{'name':'Admin','password':'testpassword'},client)[0]==200
  assert F.call('session',client=client)[1]['user']['name']=='Employee'
  assert F.call('update-config',{'repository':'m404ntfd/mgc-yfc-operations'},client)[0]==200
  assert F.call('update-config',{'repository':'example/store'},client)[0]==403
  assert F.call('account/appearance',{'mode':'dark'},client)[0]==200
  F.call('logout',{},client);F.call('login',{'name':'Employee','password':'testpassword'},client)
  assert F.call('account/appearance',client=client)[1]['mode']=='dark'
  assert F.call('account/appearance')[1]['mode']=='system'
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (390,1280):
    page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}')
    if width==390:
     expect(page.locator('.shareYfc')).to_be_visible();page.locator('#shareYfcButton').click();expect(page.locator('#shareText')).to_be_visible();page.locator('#closeShare').click()
    page.locator('#login [name=name]').fill('Employee');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('html')).to_have_attribute('data-theme','dark')
    if page.locator('#sectionChooser').is_visible():page.locator('#sectionChooserForm button').click()
    expect(page.locator('#sectionChooser')).to_be_hidden()
    page.locator('#settingsTab').click();expect(page.locator('#overview')).to_be_hidden();expect(page.locator('.scheduleNav')).to_be_hidden();expect(page.locator('#currentSection')).to_have_text('Settings')
    page.get_by_role('button',name='Updates',exact=True).click();expect(page.locator('#updateRepo')).to_be_disabled()
    page.locator('#unlockRepository').click();page.locator('#repositoryUnlockForm [name=name]').fill('Admin');page.locator('#repositoryUnlockForm [name=password]').fill('testpassword');page.locator('#repositoryUnlockForm button[type=submit]').click();expect(page.locator('#updateRepo')).to_be_enabled()
    page.screenshot(path=f'/tmp/settings-revision-{width}.png')
    page.locator('#storeMenuButton').click();page.locator('#dispatchSection').click();expect(page.locator('#settings')).to_be_hidden();expect(page.locator('#overview')).to_be_visible()
    assert page.locator('#date').input_value()==page.evaluate("localDate(new Date())")
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors
    page.close()
   b.close()
 finally:F.tearDownClass()
 print('PASS admin-only one-use approval, account persistence/isolation, mobile share, settings isolation, Today navigation')
if __name__=='__main__':run()
