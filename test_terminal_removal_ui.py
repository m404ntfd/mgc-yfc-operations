"""OFFICE removal/restore preview and DESK registration against sample data only."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import office_setting

def run():
 f=CoordinatorFixture();out=Path('output/preview/terminal-removal');out.mkdir(parents=True,exist_ok=True)
 def post(action,**data):
  code,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert code==200,(action,result);return result
 try:
  post('settings',store='Thrift Mart · SAMPLE',tax_bps=0,confirmed=True)
  device='a'*32;terminal=post('terminal-save',name='Thrift Mart Register 1',device=device,enabled=True)['id']
  post('terminal-save',name='Binopoly Register 1',device='b'*32,enabled=True,store_id='binopoly')
  info=dict(app='pos',device=device,version='1.20.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-TOUCH-PC',macs=[],os='Windows fixture'))
  assert f.call('computers/self',info)[0]==200
  assert f.call('computers/register',dict(id='c'*32,revision=0,name='Thrift Mart Register 1',role='pos',app='pos',device=device))[0]==200
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
   ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
   origin=f'http://127.0.0.1:{f.port}';assert ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'}).status==200
   p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/office')
   office_setting(p,'terminals').click();expect(p.locator('[data-terminal-remove]')).to_have_count(2)
   p.screenshot(path=str(out/'OFFICE-Terminal-Removal.png'))
   button=p.locator('[data-terminal-remove="'+terminal+'"]');button.click()
   expect(p.locator('dialog[open]')).to_contain_text('records will stay intact')
   p.screenshot(path=str(out/'OFFICE-Remove-Terminal-Confirmation.png'))
   p.locator('#terminalRemovalCancel').click();expect(button).to_be_visible()
   # Unsaved edits cannot be discarded as a side effect of removal.
   p.locator('#terminalForm [name=name]').fill('Unsaved terminal');button.click()
   expect(p.locator('#terminalRemovalConfirm')).to_have_count(0)
   expect(p.locator('#terminalForm [name=name]')).to_have_value('Unsaved terminal')
   p.locator('#terminalClear').click()
   desktop=ctx.new_page();desktop.on('pageerror',lambda e:errors.append(str(e)))
   desktop.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo}};')
   desktop.goto(origin+'/pos?kiosk=1');expect(desktop.locator('#nativeTerminalStatus')).to_contain_text('Registered')
   button.click();p.locator('#terminalRemovalConfirm').click()
   expect(p.locator('#terminalStatus')).to_contain_text('Historical records are retained')
   expect(p.locator('[data-terminal-remove]')).to_have_count(1)
   expect(desktop.locator('#nativeTerminalStatus')).to_contain_text('Registration required',timeout=15000)
   expect(desktop.locator('#nativeTerminalSetup')).to_be_visible()
   p.locator('#removedTerminals summary').click();expect(p.locator('#removedTerminals')).to_contain_text('Thrift Mart Register 1');p.locator('#removedTerminals').scroll_into_view_if_needed()
   p.screenshot(path=str(out/'OFFICE-Removed-Terminal-History.png'))
   p.locator('[data-terminal-restore="'+terminal+'"]').click();p.locator('#terminalRemovalConfirm').click()
   expect(p.locator('#terminalStatus')).to_contain_text('restored')
   expect(p.locator('[data-terminal-remove]')).to_have_count(2)
   expect(desktop.locator('#nativeTerminalStatus')).to_contain_text('Registered',timeout=15000)
   expect(desktop.locator('#nativeTerminalSetup')).not_to_be_visible(timeout=10000)
   # New settings offer round-up without any administrator enabling it first.
   p.locator('#officeBack').click();office_setting(p,'thrift-settings').click();p.locator('[data-thrift-tab=donations]').click()
   expect(p.locator('#thriftSettings [name=donations]')).to_be_checked();expect(p.locator('dialog[open]')).to_contain_text('On by default')
   p.screenshot(path=str(out/'OFFICE-Round-Up-Default.png'))
   assert not errors,errors;browser.close()
 finally:f.close()
 print('PASS terminal removal confirmation, cancellation, unsaved-work guard, restore, native registration status, and round-up default')

if __name__=='__main__':run()
