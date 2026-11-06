import os
from unittest.mock import patch
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from remote.client import Client

def run():
 with patch.dict(os.environ,{'DISPATCH_CONTROL_TOKEN':'ui-controller-secret'}):
  f=CoordinatorFixture()
  try:
   native=Client(f'http://127.0.0.1:{f.port}',local_control='ui-controller-secret');native.login('Admin','testpassword');f.call('logout',{})
   with sync_playwright() as pw:
    b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
    p=b.new_page(viewport={'width':1400,'height':1100},reduced_motion='reduce');errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.goto(f'http://127.0.0.1:{f.port}');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
    expect(p.locator('#sectionChooser')).to_be_visible();p.locator('#sectionChooserForm button').click()
    if p.locator('#profileWelcomeSkip').is_visible():p.locator('#profileWelcomeSkip').click()
    p.locator('#settingsTab').click();p.get_by_role('button',name='Connection Activity',exact=True).click()
    expect(p.locator('#activitySettingsForm [name=inactive_minutes]')).to_have_value('5')
    p.locator('#activitySettingsForm [name=inactive_minutes]').fill('2');p.locator('#activitySettingsForm [type=submit]').click();expect(p.locator('#activitySettingsStatus')).to_contain_text('2 minutes')
    assert native.request('admin/update-connections',activity=False)['inactive_minutes']==2
    rows=native.request('admin/update-connections',activity=False)['connections'];assert len(rows)==1 and rows[0]['kind']=='Browser'
    request=native.request('update-flow/start',dict(version='99.0.0',ready=True));p.evaluate('pollUpdateFlow()')
    expect(p.locator('#updateFlowDialog')).to_be_visible();p.locator('#minimizeUpdateFlow').click();expect(p.locator('#updatePendingBadge')).to_be_visible()
    p.locator('#headerClock').click();expect(p.locator('#updateFlowDialog')).to_be_visible();expect(p.locator('#minimizeUpdateFlow')).to_be_hidden()
    p.locator('#acknowledgeUpdateFlow').click();assert f.done.wait(3);assert not errors,errors;b.close()
  finally:f.close()
 print('PASS configurable activity, excluded native controller, native-to-browser popup and navigation acknowledgement')
if __name__=='__main__':run()
