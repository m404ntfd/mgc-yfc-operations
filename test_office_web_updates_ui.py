from test_ui_helpers import office_setting
"""OFFICE web/server updates: isolated database, mocked download/restart, no live install."""
import json,os,time
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright,expect
from test_computer_updates import ComputerTests
from test_theme_contrast import AUDIT
import server

def run():
 fixture=ComputerTests();fixture.setUp();f=fixture.f
 out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
 try:
  fixture.heartbeat();fixture.heartbeat('office','b'*32);fixture.register()
  with server.connect() as c:
   account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute('INSERT INTO work_periods VALUES(11,?,100,1000,?,?)',(account,'Office','Office'))
   c.execute('INSERT INTO work_periods VALUES(12,?,1200,NULL,?,NULL)',(account,'Office'))
   c.execute('INSERT INTO work_breaks VALUES(21,11,200,300)');c.execute('INSERT INTO work_breaks VALUES(22,12,1300,NULL)')
   c.execute("INSERT INTO work_time_card_audit VALUES(41,11,'Employee','Admin','2026-11-01','Keep audit history','{}','{}')")
   c.execute('INSERT INTO jobs VALUES(?,?,?)',('sample-delivery',8,json.dumps(dict(type='Delivery',customer='SAMPLE customer',notes='Keep reservation',start='2026-11-15T09:00',end='2026-11-15T10:00',status='Scheduled'))))
   c.execute('INSERT INTO photos VALUES(?,?,?)',('sample-delivery',0,b'original-sample-attachment'))
   c.execute('INSERT INTO pos_sales VALUES(?,?,?,?)',(801,'sample-cart',account,json.dumps(dict(total=1284,subtotal=1200,tax=84,tender=2000,change=716,lines=[]))))
  tables=['users','receipt_profiles','work_periods','work_breaks','work_time_card_audit','jobs','photos','pos_sales']
  def snapshot():
   with server.connect() as c:
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}
  before=snapshot();f.call('logout',{})
  release=dict(available=True,latest='99.0.0',current=server.updater.current(),notes='SAMPLE RELEASE — preview only.\nShared STORE OPS website and server improvements.')
  with patch.object(server.updater,'check',return_value=release),patch.object(server,'UPDATE_STATUS',{'available':False}),sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'))
   p=browser.new_page(viewport={'width':1440,'height':1100});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
   origin=f'http://127.0.0.1:{f.port}'
   def login(page,name):
    page.goto(origin+'/office');page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#officeTiles')).to_be_visible()
   def open_updates():
    p.locator('.computerUpdateSummary button').click();expect(p.locator('#officeWebCurrent')).to_have_text(release['current'])
   login(p,'Admin');open_updates()
   expect(p.locator('#officeWebNotify')).to_be_disabled();expect(p.locator('#officeWebActive')).to_have_text('0')
   p.locator('#officeWebCheck').click();expect(p.locator('#officeWebLatest')).to_have_text('99.0.0');expect(p.locator('#officeWebInstall')).to_be_enabled()
   expect(p.locator('#computerRollout button[type=submit]')).to_be_disabled()
   assert not server.UPDATE_FLOW and not f.done.is_set() and not f.stage.called
   # Failed checks must discard an older available release and block installation.
   with patch.object(server.updater,'check',side_effect=ValueError('Sample network unavailable')):
    p.locator('#officeWebCheck').click();expect(p.locator('#officeWebError')).to_contain_text('Sample network unavailable');expect(p.locator('#officeWebNotify')).to_be_disabled()
   p.locator('#officeWebCheck').click();expect(p.locator('#officeWebInstall')).to_be_enabled()
   p.route('**/api/admin/update-connections',lambda r:r.fulfill(status=503,json={'error':'Sample connection unavailable'}))
   p.evaluate('officeWebRelease=null');p.locator('#officeWebCheck').click();expect(p.locator('#officeWebError')).to_contain_text('Could not verify');expect(p.locator('#officeWebInstall')).to_be_disabled();expect(p.locator('#officeWebNotify')).to_be_disabled()
   p.unroute('**/api/admin/update-connections');p.locator('#officeWebCheck').click();expect(p.locator('#officeWebInstall')).to_be_enabled()
   # No managed launcher means no install, while release checking still works.
   p.route('**/api/updates',lambda r:r.fulfill(json={'current':release['current'],'launcher':False}))
   p.locator('#officeWebCheck').click();expect(p.locator('#officeWebStatus')).to_contain_text('Start the managed server');expect(p.locator('#officeWebNotify')).to_be_disabled()
   p.unroute('**/api/updates');p.locator('#officeWebCheck').click();expect(p.locator('#officeWebInstall')).to_be_enabled()
   # Existing staff is listed; the requesting session is excluded.
   staff=f.client('b');assert f.call('login',dict(name='Employee',password='testpassword'),staff)[0]==200
   p.locator('#officeWebCheck').click();expect(p.locator('#officeWebActive')).to_have_text('1');expect(p.locator('#officeWebInstall')).to_be_disabled();expect(p.locator('#officeWebNotify')).to_be_enabled()
   # Check-all covers both independent update packages, preserving selected PCs.
   p.route('**/api/computers/check',lambda r:r.fulfill(response=r.fetch(url=origin+'/api/computers/state',method='GET')))
   p.locator('[data-select-computer]').check();p.locator('#computerCheck').click();expect(p.locator('#officeWebLatest')).to_have_text('99.0.0');expect(p.locator('[data-select-computer]')).to_be_checked()
   p.locator('#computerRollout [name=seconds]').fill('150');p.locator('#officeWebNotify').click();expect(p.locator('#officeWebError')).to_contain_text('unfinished');assert not f.stage.called
   p.locator('dialog.computerDialog .flowClose').click();open_updates();p.locator('#officeWebCheck').click();expect(p.locator('#officeWebNotify')).to_be_enabled()
   themes=['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+x for x in ['blue','teal','violet','rose','graphite']]
   for theme in themes:
    for mode in ['light','dark']:
     p.evaluate('([t,m])=>{document.body.dataset.retailTheme=t;document.documentElement.dataset.theme=m}',[theme,mode]);p.wait_for_timeout(50)
     issues=p.evaluate(AUDIT);assert not issues,(theme,mode,issues)
   for width in [1000,1280,1440]:
    p.set_viewport_size({'width':width,'height':1100});assert p.locator('dialog.computerDialog').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1')
   p.evaluate("document.body.dataset.retailTheme='classic-gray';document.documentElement.dataset.theme='light';document.querySelector('.computerDialog').scrollTop=0")
   p.screenshot(path=str(out/'OFFICE-Application-Updates.png'))
   p.evaluate("document.body.dataset.retailTheme='glass-graphite';document.documentElement.dataset.theme='dark'");p.screenshot(path=str(out/'OFFICE-Application-Updates-Dark.png'))
   p.locator('#officeWebNotify').click();expect(p.locator('#updateDialog')).to_be_visible();expect(p.locator('#officeWebProgress')).to_contain_text('1 active user');expect(p.locator('#officeWebFlowCancel')).to_be_enabled();expect(p.locator('#updateReady')).to_be_hidden()
   assert not f.done.is_set();assert f.stage.call_count==1
   with server.connect() as c:assert c.execute('SELECT COUNT(*) FROM retail_computer_updates').fetchone()[0]==0
   p.screenshot(path=str(out/'OFFICE-Web-Update-Waiting.png'))
   p.locator('#officeWebFlowCancel').click();expect(p.locator('#updateTitle')).to_have_text('Update canceled');assert not f.done.is_set()
   p.locator('#updateDone').click();expect(p.locator('#officeTiles')).to_be_visible()
   # Direct-install precheck is race-safe: a new user still blocks the coordinator.
   assert f.call('logout',{},staff)[0]==200
   open_updates();p.locator('#officeWebCheck').click();expect(p.locator('#officeWebInstall')).to_be_enabled()
   def race(route):
    assert f.call('login',dict(name='Employee',password='testpassword'),staff)[0]==200
    route.continue_()
   p.route('**/api/update-flow/start',race);p.locator('#officeWebInstall').click();expect(p.locator('#officeWebFlowCancel')).to_be_enabled();expect(p.locator('#officeWebProgress')).to_contain_text('1 active user');assert not f.done.wait(.7)
   assert f.call('update-flow/acknowledge',dict(id=server.UPDATE_FLOW['id'],ready=True),staff)[0]==200
   assert f.done.wait(3);assert f.stage.call_count==2;assert snapshot()==before
   # Simulated restart invalidates sign-in; receipt still reports completion.
   with server.LOCK:server.UPDATE_FLOW=None;server.RESTART=False;server.SESSIONS.clear()
   with patch.object(server.updater,'current',return_value='99.0.0'):
    p.evaluate('pollFlow()');expect(p.locator('#updateTitle')).to_have_text('Update complete');expect(p.locator('#updateDone')).to_be_visible();expect(p.locator('#officeWebFlowCancel')).to_be_hidden()
   assert not errors,errors
   # Staff cannot see update controls or call the install endpoints.
   other=browser.new_page();login(other,'Employee');expect(office_setting(other,'computer-updates')).to_have_count(0);expect(other.locator('.computerUpdateSummary')).to_be_hidden()
   assert other.request.post(origin+'/api/update-flow/start',data={'version':'99.0.0','ready':True},headers={'X-Dispatch':'1'}).status==403
   assert snapshot()==before;browser.close()
 finally:fixture.tearDown()
 print('PASS OFFICE web/server check, failures, activity guards, unsaved entries, cancellation, late login, completion after restart, permissions, 20 theme combinations, and unchanged sample timecards/reservations/sales.')

if __name__=='__main__':run()
