from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect
def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'});F.call('user',{'name':'Employee','password':'testpassword'})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (390,1280):
    page=b.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}');page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    if width==390:
     expect(page.locator('#sectionChooser')).to_be_visible();page.locator('[name=section][value=print]').check();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#printPurpose')).to_be_visible();assert page.locator('body>header').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(7, 62, 166)'
    page.locator('#settingsTab').click();page.get_by_role('button',name='Application Settings',exact=True).click();page.get_by_role('button',name='Page Colors',exact=True).click()
    expect(page.locator('#pageColorForm [name=print_header]')).to_have_value('#073ea6')
    page.locator('#pageColorForm [name=print_light]').fill('#e1e2e3');page.locator('#pageColorForm [name=print_dark]').fill('#141516');page.locator('#pageColorForm button[type=submit]').click();expect(page.locator('#pageColorStatus')).to_have_text('Page colors saved for everyone.')
    page.locator('#storeMenuButton').click();page.locator('#printSection').click();page.evaluate("window.appAppearance.set('light')");expect(page.locator('body')).to_have_css('background-color','rgb(225, 226, 227)')
    page.evaluate("window.appAppearance.set('dark')");expect(page.locator('body')).to_have_css('background-color','rgb(20, 21, 22)');expect(page.locator('#currentSection')).to_have_css('color','rgb(255, 255, 255)')
    page.reload();expect(page.locator('#printPurpose')).to_be_visible();expect(page.locator('body>header')).to_have_css('background-color','rgb(7, 62, 166)')
    assert not errors,errors;page.close()
   page=b.new_page();page.goto(f'http://127.0.0.1:{F.port}');page.locator('#login [name=name]').fill('Employee');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click();page.locator('#settingsTab').click();page.get_by_role('button',name='Application Settings',exact=True).click();expect(page.get_by_role('button',name='Page Colors',exact=True)).to_be_hidden();b.close()
 finally:F.tearDownClass()
if __name__=='__main__':run()
