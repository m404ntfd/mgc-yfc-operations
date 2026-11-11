"""Interactive giving preview using synthetic donors only."""
import os,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server

f=CoordinatorFixture()
try:
 server.POS_UPDATE_RELEASE=server.OFFICE_UPDATE_RELEASE={'version':'0.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
 with sync_playwright() as pw:
  b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
  p=b.new_page(viewport={'width':1440,'height':1000});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  p.goto(f'http://127.0.0.1:{f.port}/office');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
  expect(p.locator('#officeTiles [data-office-category]')).to_have_count(7)
  p.locator('#officeNav [data-office-section=giving]').click();p.locator('[data-office-action=giving-workspace]').click()
  d=p.locator('#givingDialog');expect(d).to_be_visible()
  d.locator('[data-new=donor]').click();d.locator('[name=name]').fill('Preview Donor');d.locator('[type=submit]').click();expect(d.locator('table')).to_contain_text('Preview Donor')
  d.locator('[data-tab=gifts]').click();d.locator('[data-new=gift]').click();d.locator('[name=day]').fill('2025-12-15');d.locator('[name=amount]').fill('100');d.locator('[name=reference]').fill('Preview check 123');d.locator('[type=submit]').click();expect(d.locator('table')).to_contain_text('$100.00')
  d.locator('[data-tab=plans]').click();d.locator('[data-new=plan]').click();d.locator('[name=amount]').fill('25');d.locator('[type=submit]').click();expect(d.locator('table')).to_contain_text('draft')
  out=Path('output/preview');out.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(out/'OFFICE-Giving-Monthly.png'))
  d.locator('[data-tab=statements]').click();d.locator('[name=period]').fill('2025');d.locator('[type=submit]').click();expect(d.locator('#givingStatementPreview')).to_contain_text('$100.00')
  p.evaluate("window.givingPrintCapture=[];thriftPrint=(title,body)=>givingPrintCapture.push(body)")
  d.locator('#givingPrint').click()
  assert 'Statement preview - not saved or sent' in p.evaluate('givingPrintCapture.at(-1)')
  p.screenshot(path=str(out/'OFFICE-Giving-Statement.png'))
  d.locator('#givingSaveStatement').click();expect(d.locator('#givingStatementPreview')).to_contain_text('Saved statement')
  expect(d.locator('#givingStatementHistory [data-snapshot]')).to_have_count(1)
  d.locator('[data-tab=donors]').click();d.locator('[data-edit-donor]').click();d.locator('[name=name]').fill('Renamed Preview Donor');d.locator('[type=submit]').click()
  expect(d.locator('#givingEdit')).to_have_count(0)
  expect(d.locator('table')).to_contain_text('Renamed Preview Donor')
  d.locator('[data-tab=statements]').click();d.locator('[data-snapshot]').click()
  expect(d.locator('#givingStatementPreview')).to_contain_text('Preview Donor')
  expect(d.locator('#givingStatementPreview')).not_to_contain_text('Renamed Preview Donor')
  p.screenshot(path=str(out/'OFFICE-Giving-Saved-Statement.png'))
  d.locator('#givingPrint').click()
  assert 'Saved statement - not sent' in p.evaluate('givingPrintCapture.at(-1)')
  assert 'Reference:' in p.evaluate('givingPrintCapture.at(-1)')
  d.locator('[data-tab=gifts]').click()
  expect(d.locator('table')).to_contain_text('Preview check 123')
  p.once('dialog',lambda dialog:dialog.accept('Duplicate entry <script>invalid()</script>'))
  d.locator('[data-void]').click()
  expect(d.locator('table')).to_contain_text('Duplicate entry <script>invalid()</script>')
  expect(d.locator('table')).to_contain_text('By Admin')
  expect(d.locator('[data-void]')).to_have_count(0)
  assert d.locator('table script').count()==0
  p.screenshot(path=str(out/'OFFICE-Giving-Correction-History.png'))
  # Prepare a new emailed copy through the actual server, then cancel it.
  d.locator('[data-tab=donors]').click();d.locator('[data-edit-donor]').click()
  d.locator('[name=email]').fill('synthetic@example.test');d.locator('[name=delivery]').select_option('email')
  d.locator('[type=submit]').click();expect(d.locator('table')).to_contain_text('synthetic@example.test')
  d.locator('[data-tab=statements]').click();d.locator('[name=period]').fill('2025')
  d.locator('[type=submit]').click();expect(d.locator('#givingStatementPreview')).to_contain_text('Statement preview')
  d.locator('#givingSaveStatement').click();expect(d.locator('#givingStatementPreview')).to_contain_text('Saved statement')
  d.locator('#givingDelivery').click()
  d.get_by_role('button',name='Prepare email delivery',exact=True).click()
  expect(d.locator('.givingDeliveryRecord')).to_contain_text('Prepared - not sent')
  expect(d.locator('.givingDeliveryRecord')).to_contain_text('synthetic@example.test')
  p.screenshot(path=str(out/'OFFICE-Giving-Delivery-Prepared.png'))
  d.locator('[name=reason]').fill('Synthetic review cancellation')
  d.get_by_role('button',name='Cancel preparation',exact=True).click()
  expect(d.locator('.givingDeliveryRecord')).to_contain_text('Cancelled - not sent')
  expect(d.locator('.givingDeliveryRecord')).to_contain_text('Synthetic review cancellation')
  p.screenshot(path=str(out/'OFFICE-Giving-Delivery-Cancelled.png'))
  assert not errors,errors
  b.close()
finally:f.close()

