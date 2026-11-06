"""Multi-browser handoff and shift autosave with simulated update/restart only."""
import os,time
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server

def run():
 f=CoordinatorFixture()
 try:
  people=f.call('workforce/team')[1]['people'];account=next(p['id'] for p in people if p['name']=='Employee')
  f.call('logout',{})
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));errors=[]
   def login(name):
    page=b.new_page(viewport={'width':1400,'height':1100},reduced_motion='reduce');page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{f.port}');page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
    if page.locator('#profileWelcomeSkip').is_visible():page.locator('#profileWelcomeSkip').click()
    return page
   admin=login('Admin');staff=login('Employee');second=login('Second')
   admin.evaluate("workOpen(false,'team')");expect(admin.locator('#workAddShift')).to_be_visible();admin.locator('#workAddShift').click()
   form=admin.locator('#workShiftForm');form.locator('[name=account]').select_option(account);form.locator('[name=start]').fill('2026-12-01T09:00');form.locator('[name=end]').fill('2026-12-01T17:00');form.locator('[name=notes]').fill('Automatically saved')
   expect(admin.locator('#shiftSaveStatus')).to_have_text('All changes saved.')
   with server.connect() as c:
    rows=c.execute('SELECT id,notes,revision FROM work_shifts').fetchall();assert len(rows)==1 and rows[0]['notes']=='Automatically saved';ident=rows[0]['id']
   # Drop a successful save response: retry must not repeat the mutation.
   first=[True]
   def lose_reply(route):
    response=route.fetch()
    if first[0]:first[0]=False;route.abort()
    else:route.fulfill(response=response)
   admin.route('**/api/workforce/shift',lose_reply)
   form.locator('[name=notes]').fill('Saved despite lost response');expect(admin.locator('#shiftSaveStatus')).to_contain_text('Not saved')
   admin.locator('#workShiftForm [type=submit]').click();expect(admin.locator('#workShiftDialog')).to_be_hidden()
   with server.connect() as c:
    row=c.execute('SELECT notes,revision FROM work_shifts WHERE id=?',(ident,)).fetchone();assert row['notes']=='Saved despite lost response' and row['revision']==2
   admin.unroute('**/api/workforce/shift')
   # Keep an employee request unfinished while the update notice arrives.
   staff.evaluate("workOpen(false,'requests')");expect(staff.locator('#workTimeOff')).to_be_visible();staff.locator('#workTimeOff').click()
   request=staff.locator('#workRequestForm');request.locator('[name=start]').fill('2026-12-03');request.locator('[name=end]').fill('2026-12-03')
   admin.route('**/api/update-check',lambda r:r.fulfill(json=dict(available=True,latest='99.0.0',current='0.39.2',notes='Test update')))
   admin.locator('#serverUpdateButton').click();expect(admin.locator('#updateStatus')).to_contain_text('99.0.0')
   admin.on('dialog',lambda d:d.accept());admin.locator('#requestCoordinatedUpdate').click()
   expect(admin.locator('#updateFlowDialog')).to_be_visible()
   staff.evaluate('pollUpdateFlow()');second.evaluate('pollUpdateFlow()')
   expect(staff.locator('#updateFlowDialog')).to_be_visible();staff.locator('#minimizeUpdateFlow').click();expect(staff.locator('#updatePendingBadge')).to_be_visible()
   staff.evaluate("tab('settings')");expect(staff.locator('#updateFlowDialog')).to_be_hidden();expect(request).to_be_visible()
   request.locator('button.primary').click();expect(request).to_be_hidden()
   staff.evaluate("tab('settings')");expect(staff.locator('#updateFlowDialog')).to_be_visible();expect(staff.locator('#minimizeUpdateFlow')).to_be_hidden()
   staff.keyboard.press('Escape');expect(staff.locator('#updateFlowDialog')).to_be_visible()
   staff.locator('#acknowledgeUpdateFlow').click();expect(staff.locator('#updateFlowTitle')).to_contain_text('Ready')
   assert not f.done.is_set()
   out=Path(os.environ.get('TEST_ARTIFACTS',f.tmp.name));out.mkdir(parents=True,exist_ok=True)
   admin.evaluate('pollUpdateFlow()');expect(admin.locator('#updateFlowPeople')).to_contain_text('Ready');admin.locator('#updateFlowDialog').screenshot(path=str(out/'coordinated-update.png'))
   second.locator('#acknowledgeUpdateFlow').click();expect(second.locator('#updateFlowTitle')).to_contain_text('Ready')
   assert f.done.wait(3)
   with server.connect() as c:
    assert c.execute('SELECT COUNT(*) FROM work_requests').fetchone()[0]==1
    assert c.execute('SELECT notes FROM work_shifts WHERE id=?',(ident,)).fetchone()[0]=='Saved despite lost response'
   with server.LOCK:server.UPDATE_FLOW=None;server.RESTART=False;server.SESSIONS.clear()
   with patch.object(server.updater,'current',return_value='99.0.0'):
    admin.evaluate('pollUpdateFlow()');expect(admin.locator('#updateFlowTitle')).to_have_text('Update complete');expect(admin.locator('#finishUpdateFlow')).to_be_visible()
   assert not errors,errors
   b.close()
 finally:f.close()
 print('PASS autosave and lost-response retry; finish-work notice, mandatory navigation acknowledgement, all-user wait, saved task preservation, and completion notice')
if __name__=='__main__':run()
