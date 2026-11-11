from test_ui_helpers import office_setting
import os
from test_update_coordination import CoordinatorFixture
from playwright.sync_api import sync_playwright,expect
f=CoordinatorFixture()
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));p=b.new_page(viewport={'width':1440,'height':1000});p.goto(f'http://127.0.0.1:{f.port}/office');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();p.locator('#officeNav [data-office-section=staff]').click();office_setting(p,'timekeeping-manage').click();frame=p.frame_locator('iframe');expect(frame.locator('#workforce')).to_be_visible(timeout=15000);expect(frame.locator('#workTimeCards')).to_be_visible();p.screenshot(path='test-artifacts/STORE-OPS-OFFICE-Timekeeping.png');b.close()
 print('PASS OFFICE embedded timekeeping')
finally:f.close()
