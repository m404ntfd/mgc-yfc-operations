"""Native recovery controls with isolated records and mocked native navigation."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_computer_updates import ComputerTests
from test_ui_helpers import password_login_page

def run():
 fixture=ComputerTests();fixture.setUp();f=fixture.f
 out=Path('output/preview/terminal-recovery');out.mkdir(parents=True,exist_ok=True)
 def post(action,**data):
  code,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert code==200,(action,result);return result
 try:
  post('settings',store='Thrift Mart · SAMPLE',tax_bps=0,confirmed=True)
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None);errors=[]
   for number,app in enumerate(('office','pos'),4):
    print('Checking recovery',app,flush=True)
    context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
    info=dict(app=app,device=str(number)*32,version='1.0.0',configured=True,nonce='f'*64,computer=dict(id=str(number)*32,hostname='SAMPLE-'+app.upper()+'-PC',macs=[],os='Windows fixture'))
    page.add_init_script('window.fixtureInfo='+json.dumps(info)+''';window.reconnectCalls=[];window.pywebview={api:{terminal_info:async()=>window.fixtureInfo,kiosk_info:async()=>window.fixtureInfo,desktop_reconnect:async(address,code)=>{window.reconnectCalls.push([address,code]);return {error:'The server did not respond. Check your internet or VPN connection, then retry.'}}}};''')
    origin=f'http://127.0.0.1:{f.port}';page.goto(origin+('/office?setup=1' if app=='office' else '/pos?kiosk=1&setup=1'))
    # Available before login, including when server registration cannot be checked.
    page.locator('#desktopConnectionSetup').click();expect(page.locator('#nativeServerForm')).to_be_visible()
    page.locator('#nativeServerForm [name=server]').fill('https://operations.coastyfc.com')
    if app=='pos':page.locator('#nativeServerForm [name=code]').fill('123456')
    assert page.evaluate('window.desktopConnectionCanChange()')
    page.locator('#nativeServerForm button').click();expect(page.locator('#nativeTerminalError')).to_contain_text('did not respond')
    contrast=page.locator('#nativeServerForm button').evaluate('''button=>{const css=getComputedStyle(button),light=color=>{const channels=color.match(/[\\d.]+/g).slice(0,3).map(n=>Number(n)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;};const a=light(css.color),b=light(css.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);}''')
    assert contrast>=4.5,(app,contrast)
    assert page.evaluate('window.reconnectCalls')==[['https://operations.coastyfc.com','123456' if app=='pos' else '']]
    if app=='pos':expect(page.locator('#nativeServerForm [name=code]')).to_have_value('')
    page.screenshot(path=str(out/(app.upper()+'-Server-Connection.png')))
    page.locator('#nativeServerCancel').click()
    password_login_page(page);page.locator('#login [name=name]').fill('Employee');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button[type=submit],#login button:not([type])').first.click()
    expect(page.locator('#nativeTerminalLogin')).to_be_visible();expect(page.locator('#nativeTerminalForm')).to_have_count(0)
    page.keyboard.press('Escape');expect(page.locator('#nativeTerminalSetup')).to_be_visible()
    form=page.locator('#nativeTerminalLogin');form.locator('[name=name]').fill('Admin');form.locator('[name=password]').fill('wrong-password');form.locator('button').click()
    expect(page.locator('#nativeTerminalError')).to_contain_text('Incorrect');expect(form.locator('[name=password]')).to_have_value('')
    form.locator('[name=name]').fill('Employee');form.locator('[name=password]').fill('testpassword');form.locator('button').click()
    expect(page.locator('#nativeTerminalError')).to_contain_text('not an administrator')
    form.locator('[name=name]').fill('Admin');page.evaluate("document.getElementById('nativeTerminalError').textContent=''");page.screenshot(path=str(out/(app.upper()+'-Admin-Registration.png')))
    form.locator('[name=password]').fill('testpassword');form.locator('button').click()
    expect(page.locator('#nativeTerminalForm')).to_be_visible();name='Thrift Mart '+('Office' if app=='office' else 'Checkout')+' · SAMPLE'
    page.locator('#nativeTerminalForm [name=name]').fill(name);page.locator('#nativeTerminalForm button').click()
    expect(page.locator('#nativeTerminalSetup')).not_to_be_visible();expect(page.locator('#nativeTerminalStatus')).to_have_text('Terminal: '+name+' · Registered')
    # A verified registration stays on the same identity after reconnect/reload.
    page.reload();expect(page.locator('#nativeTerminalSetup')).to_be_visible() # Explicit setup=1 reopens details.
    expect(page.locator('#nativeTerminalSetup')).to_contain_text('Registered: '+name);page.locator('#nativeTerminalClose').click()
    # An unreachable server exposes both retry and address editing from status.
    page.route('**/api/computers/self',lambda route:route.abort())
    page.locator('#nativeTerminalStatus').click();expect(page.locator('#nativeTerminalRetry')).to_be_visible()
    page.locator('#nativeTerminalSetup [data-terminal-connection]').click();expect(page.locator('#nativeServerForm')).to_be_visible()
    page.evaluate("const draft=document.createElement('form');draft.id='fixtureDraft';document.body.append(draft);changedForms.set(draft,'unsaved');")
    assert not page.evaluate('window.desktopConnectionCanChange()')
    page.evaluate("changedForms.delete(document.getElementById('fixtureDraft'));document.getElementById('fixtureDraft').remove()")
    page.unroute('**/api/computers/self');page.locator('#nativeServerCancel').click()
    if app=='pos':
     state=f.call('computers/self',info)[1];terminal=state['terminal']['id'];config=f.call('pos/retail-config')[1];row=next(t for t in config['terminals'] if t['id']==terminal)
     post('terminal-remove',id=terminal,revision=row['revision'],confirmed=True)
     expect(page.locator('#nativeTerminalSetup')).to_be_visible(timeout=15000);expect(page.locator('#nativeTerminalSetup')).to_contain_text('This checkout was removed')
     expect(page.locator('#nativeTerminalForm [name=terminal]')).to_have_count(0);expect(page.locator('#nativeTerminalForm [name=store_id]')).to_have_count(0)
     page.screenshot(path=str(out/'DESK-Re-register-Original-Terminal.png'))
     page.locator('#nativeTerminalForm button').click();expect(page.locator('#nativeTerminalSetup')).to_be_visible() # Required confirmation.
     page.locator('#nativeTerminalForm [name=confirm_restore]').check();page.locator('#nativeTerminalForm button').click()
     expect(page.locator('#nativeTerminalSetup')).not_to_be_visible();expect(page.locator('#nativeTerminalStatus')).to_contain_text('Registered')
     restored=f.call('computers/self',info)[1];assert restored['terminal']['id']==terminal and restored['terminal']['store_id']=='thrift-mart' and restored['removed_terminal'] is None
    assert not page.evaluate('window.reconnectCalls.length>1'),'No automatic changes to server address'
    context.close()
   assert not errors,errors;browser.close()
  print('PASS OFFICE/DESK connection recovery, admin login and denial, failed-server retry, unsaved-work protection, original-terminal re-registration and retained identity')
 finally:fixture.tearDown()

if __name__=='__main__':run()
