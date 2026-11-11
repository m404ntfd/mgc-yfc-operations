from test_ui_helpers import office_setting
import time,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_computer_updates import ComputerTests
import server
f=ComputerTests();f.setUp()
try:
 f.heartbeat();f.register()
 f.heartbeat('office','b'*32)
 f.heartbeat('office','c'*32,'2'*32)
 f.f.call('computers/register',dict(id='2'*32,revision=0,name='Back office',role='office'))
 f.heartbeat('pos','d'*32,'3'*32)
 with server.connect() as c:
  c.execute("UPDATE retail_computers SET hostname='CHECKOUT-01' WHERE id=?",('1'*32,))
  c.execute("UPDATE retail_computers SET hostname='OFFICE-01' WHERE id=?",('2'*32,))
  c.execute("UPDATE retail_computers SET hostname='CHECKOUT-02' WHERE id=?",('3'*32,))
  c.execute('UPDATE retail_computer_apps SET seen=? WHERE device=?',(time.time()-3600,'c'*32))
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));p=b.new_page(viewport={'width':1440,'height':1100});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  p.goto(f'http://127.0.0.1:{f.f.port}/office');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
  p.locator('[data-office-section=system]').click();office_setting(p,'computer-register').click();expect(p.locator('.computerCard')).to_have_count(3)
  Path('test-artifacts').mkdir(exist_ok=True);p.screenshot(path='test-artifacts/Computer-registration-preview.png')
  p.locator('[data-register-computer="'+('3'*32)+'"] [name=name]').fill('Second checkout')
  p.locator('[data-register-computer="'+('3'*32)+'"] button').click();expect(p.locator('#computerStatus')).to_contain_text('3 registered')
  p.locator('dialog[open] .flowClose').click()
  office_setting(p,'computer-updates').click();expect(p.locator('#computerVersions')).to_contain_text('9.0.0')
  expect(p.locator('#computerRollout button[type=submit]')).to_be_disabled()
  expect(p.locator('[data-select-computer]')).to_have_count(3)
  p.locator('[data-select-computer="'+('1'*32)+'"]').check()
  p.locator('#computerRefresh').click();expect(p.locator('[data-select-computer="'+('1'*32)+'"]')).to_be_checked()
  p.locator('#computerSelectNone').click();expect(p.locator('#computerRollout button[type=submit]')).to_be_disabled()
  p.locator('#computerSelectAll').click()
  p.locator('#computerRollout button[type=submit]').click();expect(p.locator('#computerStatus')).to_contain_text('4 application update(s) pending')
  p.screenshot(path='test-artifacts/Computer-updates-preview.png')
  p.on('dialog',lambda d:d.accept());p.locator('#computerCancel').click();expect(p.locator('#computerStatus')).to_contain_text('3 registered')
  assert not errors,errors;b.close()
 print('PASS computer registration, grouped application rollout, offline pending state and cancellation. Screens use synthetic data.')
finally:f.tearDown()
