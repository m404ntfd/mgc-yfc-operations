"""Two-level settings, automatic/manual device layout, favicon, and login counters."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect
from pathlib import Path
import tempfile

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  F.call('admin/login-security',{'max_attempts':3})
  with sync_playwright() as p:
   browser=p.chromium.launch()
   for width in (390,1280):
    page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce');errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}')
    favicon=page.request.get(f'http://127.0.0.1:{F.port}/favicon.svg');assert favicon.ok and 'image/svg+xml' in favicon.headers['content-type']
    assert '<svg' in favicon.text() and '#ea4520' in favicon.text()
    assert page.locator('link[rel=icon]').get_attribute('href')=='/favicon.svg'
    page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('wrongpassword');page.locator('#login button').click()
    expect(page.locator('#loginAttempts')).to_have_text('Attempts Remaining Until Account Lock: 2')
    page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#auth')).to_be_hidden()
    if width==390:
     expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#sectionChooser')).to_be_hidden()
    page.locator('#settingsTab').click()
    expect(page.locator('#settingsSubcategories')).to_be_visible()
    expect(page.locator('#settingsSubcategories').get_by_role('button',name='Appearance',exact=True)).to_be_visible()
    expect(page.locator('#appearanceSettings')).to_be_hidden()
    page.locator('#settingsCategories').get_by_role('button',name='Application Settings',exact=True).click()
    expect(page.locator('#settingsSubcategories')).to_contain_text('Appearance')
    page.locator('#settingsSubcategories').get_by_role('button',name='Mobile View',exact=True).click()
    page.screenshot(path=str(Path(tempfile.gettempdir())/f'settings28-{width}.png'))
    expect(page.locator('#mobileViewMode')).to_have_value('auto')
    assert page.evaluate('isMobileView()')==(width==390)
    page.locator('#mobileViewMode').select_option('mobile')
    assert page.evaluate('isMobileView()')
    assert page.locator('#loginBrand').evaluate('(e)=>getComputedStyle(e).display')=='none' or width==390
    page.reload();expect(page.locator('html')).to_have_attribute('data-mobile-view','mobile')
    page.locator('#settingsTab').click();page.locator('#settingsCategories').get_by_role('button',name='Application Settings',exact=True).click();page.get_by_role('button',name='Mobile View',exact=True).click()
    page.locator('#mobileViewMode').select_option('desktop');assert not page.evaluate('isMobileView()')
    assert page.locator('body').evaluate('(e)=>parseFloat(getComputedStyle(e).minWidth)')>=1000
    page.locator('#mobileViewMode').select_option('auto')
    page.locator('#settingsCategories').get_by_role('button',name='Thrift Mart Dispatch',exact=True).click()
    expect(page.locator('#settingsSubcategories')).to_contain_text('Vehicles');expect(page.locator('#mobileViewSettings')).to_be_hidden()
    page.locator('#settingsCategories').get_by_role('button',name='Receipts & Accounting',exact=True).click();page.get_by_role('button',name='Receipts',exact=True).click();expect(page.locator('#receiptSettings')).to_be_visible()
    assert not errors,errors;page.close()
   browser.close()
 finally:F.tearDownClass()

if __name__=='__main__':run()
