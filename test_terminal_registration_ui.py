"""First-time desktop enrollment, persistent status, selection and update work guards."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_computer_updates import ComputerTests
from test_ui_helpers import password_login_page
f=ComputerTests();f.setUp()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));errors=[]
  for number,(app,path,name) in enumerate([('office','/office','Thrift Mart Office'),('pos','/pos?kiosk=1','Thrift Mart Checkout'),('ops','/','Binopoly OPS')],1):
   print('Checking',app,flush=True)
   context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   info=dict(app=app,device=str(number)*32,version='1.0.0',configured=True,nonce='f'*64,computer=dict(id=str(number)*32,hostname='TEST-PC-'+str(number),macs=[],os='Windows fixture'))
   page.add_init_script("window.fixtureInfo="+json.dumps(info)+";window.pywebview={api:{terminal_info:async()=>window.fixtureInfo}};"+("window.pywebview.api.kiosk_info=async()=>window.fixtureInfo;" if app=='pos' else ''))
   if app=='ops':page.add_init_script("window.testSeconds=30;window.installAttempts=0;window.pywebview.api.ops_update_status=async id=>id?{state:'ready',seconds:window.testSeconds}:{state:'idle'};window.pywebview.api.ops_install_update=async()=>{window.installAttempts++;return window.posUpdateFreeze()?{ok:true}:{error:'Save your work'};}")
   page.goto(f'http://127.0.0.1:{f.f.port}'+path)
   def login(user):
    password_login_page(page);page.locator('#login [name=name]').fill(user);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button[type=submit],#login button:not([type])').first.click()
   # Non-admins cannot dismiss enrollment or register the computer.
   login('Employee');expect(page.locator('#nativeTerminalSetup')).to_be_visible();expect(page.locator('#nativeTerminalSetup')).to_contain_text('An administrator must sign in')
   page.keyboard.press('Escape');expect(page.locator('#nativeTerminalSetup')).to_be_visible();expect(page.locator('#nativeTerminalForm')).to_have_count(0)
   with page.expect_navigation():page.locator('#nativeTerminalSignOut').click()
   login('Admin')
   expect(page.locator('#nativeTerminalForm')).to_be_visible();page.locator('#nativeTerminalForm [name=name]').fill(name)
   Path('test-artifacts').mkdir(exist_ok=True)
   if app=='office':page.screenshot(path='test-artifacts/Terminal-first-time-setup.png')
   page.locator('#nativeTerminalForm button').click();expect(page.locator('#nativeTerminalSetup')).not_to_be_visible();expect(page.locator('#nativeTerminalStatus')).to_have_text('Terminal: '+name+' · Registered')
   if app=='ops':
    expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChoices [name=section]').first.check();page.locator('#sectionChooserForm button').click();expect(page.locator('#sectionChooser')).not_to_be_visible()
   page.reload();expect(page.locator('#nativeTerminalStatus')).to_have_text('Terminal: '+name+' · Registered');expect(page.locator('#nativeTerminalSetup')).not_to_be_visible()
   # Readable saved status is available inside Terminal setup on every application.
   page.locator('#nativeTerminalStatus').click();expect(page.locator('#nativeTerminalSetup')).to_contain_text('Registered: '+name)
   if app=='pos':expect(page.locator('#nativeTerminalSetup')).to_contain_text('Checkout terminal: '+name)
   page.locator('#nativeTerminalClose').click()
   if app=='ops':
    page.evaluate("const form=document.createElement('form');form.id='testDraft';document.body.append(form);changedForms.set(form,'unsaved');")
    code,result=f.f.call('computers/start',dict(computers=['3'*32],seconds=30));assert code==200,result
    expect(page.locator('#opsComputerUpdateBanner')).to_be_visible(timeout=10000);assert page.evaluate('window.installAttempts')==0
    page.evaluate('window.testSeconds=0');expect(page.locator('#opsComputerUpdateBanner')).to_contain_text('Waiting for unfinished work',timeout=10000);assert page.evaluate('window.installAttempts')==0
    page.evaluate("changedForms.clear();document.getElementById('testDraft').remove()")
    expect(page.locator('body')).to_have_attribute('inert','',timeout=10000);assert page.evaluate('window.installAttempts')==1
   context.close()
  assert not errors,errors;browser.close()
 print('PASS first-time admin registration and persistent named status on OFFICE, DESK and STORE OPS; non-admin setup cannot be dismissed.')
finally:f.tearDown()
