"""Check saved appearance, live system changes and ordinary employee access."""
from test_server import Tests as F
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  F.call('user',{'name':'Employee','password':'testpassword'})
  with sync_playwright() as p:
   browser=p.chromium.launch()
   for width in (390,1280):
    context=browser.new_context(viewport={'width':width,'height':900},color_scheme='dark',reduced_motion='reduce')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}')
    expect(page.locator('html')).to_have_attribute('data-theme','dark')
    page.locator('#login [name=name]').fill('Employee');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#app')).to_be_visible()
    if width==390:
     expect(page.locator('#sectionChooser')).to_be_visible()
     page.locator('[name=section][value=dispatch]').check();page.locator('#sectionChooserForm button').click()
    page.locator('#settingsTab').click();page.get_by_role('button',name='Application Settings',exact=True).click();page.get_by_role('button',name='Appearance',exact=True).click()
    expect(page.locator('#appearanceMode')).to_be_visible()
    expect(page.locator('#settingsSubcategories').get_by_role('button',name='Users',exact=True)).to_be_hidden()
    page.locator('#appearanceMode').select_option('light')
    expect(page.locator('html')).to_have_attribute('data-theme','light')
    page.reload();expect(page.locator('html')).to_have_attribute('data-theme','light')
    page.locator('#settingsTab').click();page.get_by_role('button',name='Application Settings',exact=True).click();page.get_by_role('button',name='Appearance',exact=True).click();page.locator('#appearanceMode').select_option('dark')
    page.emulate_media(color_scheme='light');expect(page.locator('html')).to_have_attribute('data-theme','dark')
    page.locator('#appearanceMode').select_option('system');expect(page.locator('html')).to_have_attribute('data-theme','light')
    page.emulate_media(color_scheme='dark');expect(page.locator('html')).to_have_attribute('data-theme','dark')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(Path(tempfile.gettempdir()) / f'appearance-{width}.png'))
    assert not errors,errors
    context.close()
   browser.close()
 finally:F.tearDownClass()
 print('PASS appearance persistence, explicit override, live system changes, employee permissions, mobile and desktop')
if __name__=='__main__':run()
