"""Touch-accessible closing, OFFICE settings, report paper and rollover recovery."""
import datetime as dt
import json
import os
import uuid
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright,expect
import server
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import office_setting,wait_for_pos_save

f=CoordinatorFixture();out=Path('output/preview/register-shifts');out.mkdir(parents=True,exist_ok=True)
clock={'now':dt.datetime(2026,11,24,12,tzinfo=ZoneInfo('America/Chicago')).timestamp()}
def post(path,**data):
 code,result=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert code==200,(path,code,result);return result
try:
 with patch.object(server,'shifts_clock',side_effect=lambda:clock['now']):
  post('settings',store='Thrift Mart · SAMPLE',tax_bps=700,confirmed=True)
  book=post('product-save',name='Hardback book',category='Books',price=200,taxable=True)['ids'][0]
  lamp=post('product-save',name='Table lamp',category='Household',price=899,taxable=True)['ids'][0]
  device='a'*32;terminal=post('terminal-save',name='Thrift Mart Register 1',device=device,enabled=True)['id']
  info=dict(app='pos',device=device,version='1.23.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-POS',macs=[],os='Windows fixture'))
  assert f.call('computers/self',info)[0]==200
  assert f.call('computers/register',dict(id='c'*32,revision=0,name='Sample Touch Register',role='pos',app='pos',device=device))[0]==200
  post('terminal-options-save',device=device,revision=0,printer='Sample Receipt Printer',replace_display=False)
  # A saved receipt supplies the closed shift's immutable sales summary.
  cart=post('new',device=device)['cart'];cart=post('add',device=device,cart=cart['id'],revision=cart['revision'],product=book,quantity=3)['cart'];post('cash',device=device,cart=cart['id'],revision=cart['revision'],tender=1000)
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None);ctx=b.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=True,reduced_motion='reduce')
   ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+''';window.shiftPrints=[];window.pywebview={api:{kiosk_info:async()=>fixtureInfo,terminal_info:async()=>fixtureInfo,receipt_printers:async()=>({printers:['Sample Receipt Printer']}),shift_print:async(printer,shift)=>{shiftPrints.push({printer,shift,paper:document.getElementById('registerShiftPaper').innerText});return {ok:true}}}};''')
   origin=f'http://127.0.0.1:{f.port}';ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
   p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/pos?kiosk=1');expect(p.locator('#deskSettings summary')).to_have_text('MORE ▾')
   p.locator('[data-pos-product="'+lamp+'"]').tap();wait_for_pos_save(p)
   p.evaluate('document.body.dataset.retailTheme="midnight";document.documentElement.dataset.theme="dark"')
   p.locator('#deskSettings summary').tap();p.locator('#deskEndShift').tap();expect(p.locator('#shiftEndConfirm')).to_be_disabled();expect(p.locator('.shiftBlocked')).to_contain_text('1 open transaction')
   p.screenshot(path=str(out/'end-shift-blocked.png'));p.locator('#shiftEndBack').tap()
   current=p.evaluate('posCurrent');post('discard',device=device,cart=current['id'],revision=current['revision'],reason='Customer changed mind')
   p.evaluate('()=>shiftWatch()');expect(p.locator('dialog[open]')).to_contain_text('Transaction closed');p.locator('dialog[open] .flowClose').tap()
   p.locator('#deskSettings summary').tap();p.locator('#deskEndShift').tap();expect(p.locator('#shiftEndConfirm')).to_be_enabled();p.screenshot(path=str(out/'end-shift-ready.png'))
   p.locator('#shiftEndConfirm').tap();expect(p.locator('.shiftReportPreview')).to_contain_text('CLOSED SHIFT');expect(p.locator('.shiftReportPreview')).to_contain_text('Unpaid void')
   p.screenshot(path=str(out/'shift-report.png'))
   p.locator('#shiftReportFormat').select_option('receipt');p.locator('#shiftPrintDetail').tap();p.wait_for_function('()=>shiftPrints.length===1');assert p.evaluate('shiftPrints[0].printer')=='Sample Receipt Printer'
   assert '$0.00 collected' in p.evaluate('shiftPrints[0].paper')
   report=f.call('pos/shift-status?device='+device)[1]['last']
   p.evaluate('r=>{const paper=document.createElement("section");paper.id="registerShiftPaper";paper.dataset.format="letter";paper.innerHTML=shiftReportHTML(r,true);document.body.append(paper);document.body.classList.add("registerShiftPrinting");}',report)
   p.pdf(path=str(out/'sample-shift-letter.pdf'),prefer_css_page_size=True,print_background=True)
   p.emulate_media(media='print');expect(p.locator('#registerShiftPaper .shiftReportHeader')).to_be_visible();p.screenshot(path=str(out/'letter-print.png'),full_page=True)
   p.evaluate('document.getElementById("registerShiftPaper").dataset.format="receipt"');p.screenshot(path=str(out/'receipt-print.png'),clip={'x':0,'y':0,'width':320,'height':1080})
   p.evaluate('document.getElementById("registerShiftPaper").remove();document.body.classList.remove("registerShiftPrinting")');p.emulate_media(media='screen');p.locator('dialog[open] .flowClose').tap()
   office=ctx.new_page();office.on('pageerror',lambda e:errors.append(str(e)));office.goto(origin+'/office');office_setting(office,'shift-settings').click();expect(office.locator('#registerShiftSettings [name=cutoff]')).to_have_value('23:59:59');office.screenshot(path=str(out/'office-shift-settings.png'))
   office.locator('#registerShiftSettings [name=print_format]').select_option('receipt');office.locator('#registerShiftSettings button').click();expect(office.locator('#registerShiftSettings')).to_have_count(0)
   p.locator('[data-pos-product="'+book+'"]').tap();wait_for_pos_save(p);p.evaluate('()=>shiftWatch()')
   clock['now']=dt.datetime(2026,11,25,0,0,1,tzinfo=ZoneInfo('America/Chicago')).timestamp()
   p.evaluate('()=>shiftWatch()');expect(p.locator('dialog[open]')).to_contain_text('$0.00 void');assert p.evaluate('posCurrent') is None
   p.screenshot(path=str(out/'automatic-close.png'));p.locator('dialog[open] .flowClose').tap()
   office_setting(office,'shift-history').click();office.locator('#shiftHistoryFilter [name=from]').fill('2026-11-24');office.locator('#shiftHistoryFilter [name=to]').fill('2026-11-24');office.locator('#shiftHistoryFilter button').click();expect(office.locator('[data-shift-report]')).to_have_count(2);office.screenshot(path=str(out/'office-shift-history.png'))
   assert not errors,errors;b.close()
finally:f.close()
print('Register shift UI, rollover recovery, report formats and print routing passed.')
