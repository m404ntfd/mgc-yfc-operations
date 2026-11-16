"""Exercise real keyboard events and menu hit targets, using only sample records."""
import json, os, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_update_coordination import CoordinatorFixture

f = CoordinatorFixture()
out = Path('output/preview/desk-focus-menu'); out.mkdir(parents=True, exist_ok=True)
def post(action, **data):
    code, result = f.call('pos/'+action, dict(data, request=uuid.uuid4().hex))
    assert code == 200, result
    return result

try:
    post('settings', store='Thrift Mart · SAMPLE', tax_bps=700, confirmed=True)
    product = post('product-save', name='Sports & Outdoors SALE', category='Sports & Outdoors', price=3000, taxable=True)['ids'][0]
    info = dict(app='pos', device='a'*32, version='1.19.0', configured=True, nonce='b'*64,
                computer=dict(id='c'*32, hostname='SAMPLE-TOUCH-PC', macs=[], os='Windows fixture'))
    post('terminal-save', name='Sample Touch Register', device='a'*32, enabled=True)
    assert f.call('computers/self', info)[0] == 200
    assert f.call('computers/register', dict(id='c'*32, revision=0, name='Sample Touch Register', role='pos', app='pos', device='a'*32))[0] == 200
    assert f.call('admin/clock-pin', dict(name='Admin', pin='654321'))[0] == 200
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
        ctx = browser.new_context(viewport={'width':1920,'height':1080}, has_touch=True, reduced_motion='reduce')
        ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.nativeFocusCalls=0;window.pywebview={api:{kiosk_info:async()=>fixtureInfo,terminal_info:async()=>fixtureInfo,focus_pin:async()=>{nativeFocusCalls++;return {focused:true}}}};')
        p = ctx.new_page(); errors=[];p.on('pageerror', lambda e:errors.append(str(e)))
        origin = f'http://127.0.0.1:{f.port}'
        p.goto(origin+'/pos?kiosk=1')
        pin = p.locator('#deskPinForm [name=pin]')
        expect(pin).to_be_focused()
        p.wait_for_function('nativeFocusCalls > 0')
        # No click, fill(), or locator.press() that could focus the input for us.
        p.keyboard.type('654321');expect(pin).to_have_value('654321');p.keyboard.press('Enter')
        expect(p.locator('#posRoot')).to_be_visible()
        p.locator('[data-pos-product="'+product+'"]').tap();expect(p.locator('#posCart')).to_contain_text('$32.10')
        for width,height in [(1920,1080),(1366,768),(1024,768)]:
            p.set_viewport_size({'width':width,'height':height})
            for theme in ['classic-gray','midnight','glass-blue']:
                p.evaluate('(theme)=>document.body.dataset.retailTheme=theme',theme)
                p.locator('#deskCreditToggle').tap();expect(p.locator('#deskCreditChoices')).to_be_visible()
                issues=p.evaluate('''()=>{
                  const issues=[];
                  for(const id of ['creditOpen','cashAdvanceOpen']){
                    const el=document.getElementById(id),r=el.getBoundingClientRect();
                    if(r.left<0||r.top<0||r.right>innerWidth||r.bottom>innerHeight)issues.push(id+' outside viewport');
                    for(const x of [r.left+4,r.left+r.width/2,r.right-4])for(const y of [r.top+4,r.top+r.height/2,r.bottom-4]){
                      if(!el.contains(document.elementFromPoint(x,y)))issues.push(id+' covered at '+x+','+y);
                    }
                  }
                  return issues;
                }''')
                assert not issues,(width,height,theme,issues)
                if width==1920 and theme=='classic-gray':
                    p.screenshot(path=str(out/'DESK-Credit-Menu-1920.png'))
                    rect=p.locator('.receiptPane').bounding_box()
                    p.screenshot(path=str(out/'DESK-Credit-Menu-Detail.png'),clip={'x':rect['x']-6,'y':rect['y']-6,'width':width-rect['x'],'height':min(520,height-rect['y'])})
                p.keyboard.press('Escape');expect(p.locator('#deskCreditChoices')).to_be_hidden()
            p.locator('#deskCreditToggle').tap();p.locator('#creditOpen').tap();expect(p.locator('#creditDialog')).to_be_visible();expect(p.locator('#deskCreditChoices')).to_be_hidden();p.locator('#creditClose').tap()
            p.locator('#deskCreditToggle').tap();p.locator('#cashAdvanceOpen').tap();expect(p.locator('#cashAdvanceDialog')).to_be_visible();expect(p.locator('#deskCreditChoices')).to_be_hidden();p.locator('#cashAdvanceDialog .flowClose').tap();expect(p.locator('#cashAdvanceDialog')).to_have_count(0)
        p.set_viewport_size({'width':1920,'height':1080})
        p.locator('#deskCreditToggle').tap();p.emulate_media(media='print');expect(p.locator('#deskCreditChoices')).to_be_hidden();p.emulate_media(media='screen');p.locator('#posStatus').tap();expect(p.locator('#deskCreditChoices')).to_be_hidden()
        # Resize while open; the whole menu must remain reachable.
        p.locator('#deskCreditToggle').tap();p.set_viewport_size({'width':1366,'height':768})
        p.wait_for_function('()=>{const r=document.getElementById("deskCreditChoices").getBoundingClientRect();return r.right<=innerWidth&&r.bottom<=innerHeight}')
        p.keyboard.press('Escape')
        # Session expiry restores PIN input without mouse selection.
        ctx.clear_cookies();p.reload();expect(pin).to_be_focused()
        pin.evaluate('(e)=>e.blur()');p.keyboard.type('000000');p.keyboard.press('Enter')
        expect(p.locator('#deskPinError')).not_to_be_empty();expect(pin).to_be_focused()
        p.locator('#deskPasswordToggle').click();p.keyboard.type('Ad')
        p.evaluate('window.dispatchEvent(new Event("pywebviewready"));window.dispatchEvent(new Event("focus"))')
        expect(p.locator('#login [name=name]')).to_be_focused();expect(pin).to_have_value('')
        p.locator('#deskPasswordToggle').click();expect(pin).to_be_focused()
        # A modal owns its keys; automatic PIN focus must not steal them.
        p.evaluate('const d=document.createElement("dialog");d.id="focusFixture";d.innerHTML="<input>";document.body.append(d);d.showModal();window.dispatchEvent(new Event("focus"))')
        p.keyboard.type('123');expect(p.locator('#focusFixture input')).to_have_value('123');expect(pin).to_have_value('')
        p.evaluate('document.getElementById("focusFixture").remove();window.dispatchEvent(new Event("focus"))');expect(pin).to_be_focused()
        p.locator('#deskPinForm .deskKeypad button').filter(has_text='6').click()
        p.keyboard.type('54321');expect(pin).to_have_value('654321');p.keyboard.press('Enter');expect(p.locator('#posRoot')).to_be_visible()
        assert not errors,errors
        browser.close()
finally:
    f.close()
print('PASS unclicked keyboard sign-in, native-ready recovery, password/modal focus, touch/keyboard switching, full menu hit targets in 3 sizes and 3 themes, and both menu actions')
