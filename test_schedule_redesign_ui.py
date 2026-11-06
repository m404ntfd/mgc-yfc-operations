"""Desktop/mobile acceptance checks against an isolated test database."""
import datetime as dt
import os
import json
import sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_server import Tests as Fixture


def run():
    Fixture.setUpClass()
    try:
        call=Fixture.call
        call('setup',dict(name='Admin',password='testpassword'))
        call('user',dict(name='Staff',password='testpassword'))
        people=call('workforce/team')[1]['people'];staff_id=next(p['id'] for p in people if p['name']=='Staff')
        call('workforce/assignment',dict(name='Staff',jobs=['Host','Trainer'],primary_job='Host',sites=[],primary_site=None,require_location=False))
        week=call('workforce/overview')[1]['week']
        target=(dt.date.fromisoformat(week)+dt.timedelta(days=7)).isoformat()
        call('workforce/jobs',dict(jobs=['Host','Trainer','Driver']))
        with sqlite3.connect(Path(Fixture.tmp.name)/'schedule.db') as db:
            for kind,hour in [('Pickup','10:00'),('Delivery','14:00')]:
                db.execute('INSERT INTO jobs VALUES(?,?,?)',(kind,1,json.dumps(dict(type=kind,start=target+'T'+hour,status='Scheduled'))))
        db.close()
        call('workforce/shift',dict(account=staff_id,start=week+'T09:00',end=week+'T17:00',job='Host',location='Main Office'))
        origin=f'http://127.0.0.1:{Fixture.port}'
        artifacts=Path(os.environ.get('TEST_ARTIFACTS',Fixture.tmp.name))
        artifacts.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));errors=[]
            def open_page(name,width):
                page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce')
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(origin)
                page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
                expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
                if page.locator('#profileWelcomeSkip').is_visible(): page.locator('#profileWelcomeSkip').click()
                page.locator('#headerClock').click();expect(page.locator('#workClockState')).to_have_text('Clocked out')
                return page
            def choose(page,view,menu):
                page.locator(menu+' summary').click();page.locator('[data-work-view="'+view+'"]').click()
            manager=open_page('Admin',1500)
            choose(manager,'team','#workManagerMenu')
            expect(manager.locator('[data-job-section="Host"] .workShiftCard:not(.workGhost)')).to_have_count(1)
            expect(manager.locator('[data-job-section="Driver"]')).to_be_visible()
            expect(manager.locator('[data-job-section="Trainer"] .workGhost')).to_have_count(1)
            expect(manager.locator('[data-job-section="Trainer"] .workGhost')).to_contain_text('other job')
            manager.locator('[data-job-section="Trainer"] [data-grid-account]').first.click()
            expect(manager.locator('#workShiftForm [name=job]')).to_have_value('Trainer');manager.locator('#workCancelShift').click()
            manager.locator('#workCopyWeek').click();manager.locator('#workCopyForm button.primary').click()
            expect(manager.locator('#workWeekDate')).to_have_value(target)
            expect(manager.locator('[data-job-section="Host"] .workShiftCard:not(.workGhost)')).to_have_count(1)
            expect(manager.locator('.workDispatch.typePickup')).to_contain_text('10:00 AM Pickup')
            expect(manager.locator('.workDispatch.typeDelivery')).to_contain_text('2:00 PM Delivery')
            expect(manager.locator('[data-work-panel=team]')).to_be_visible()
            manager.evaluate('window.scrollTo(0,0)')
            manager.set_viewport_size({'width':1500,'height':1300})
            manager.screenshot(path=str(artifacts/'manager-schedule.png'))
            manager.set_viewport_size({'width':390,'height':844})
            expect(manager.locator('[data-work-panel=mine]')).to_be_visible()
            expect(manager.locator('[data-work-view=team]')).to_be_hidden()
            staff=open_page('Staff',390)
            choose(staff,'mine','.workDropdown:has([data-work-view=mine])')
            expect(staff.locator('.workPersonalShift')).to_have_count(1)
            expect(staff.locator('#workScheduledCount')).to_have_text('1')
            expect(staff.locator('#workScheduledHours')).to_have_text('8')
            expect(staff.locator('.workDay')).to_have_count(7)
            assert staff.evaluate('document.documentElement.scrollWidth<=innerWidth')
            staff.evaluate('window.scrollTo(0,0)')
            staff.screenshot(path=str(artifacts/'employee-schedule.png'))
            choose(staff,'availability','.workDropdown:has([data-work-view=mine])')
            expect(staff.locator('#workAvailabilityEdit')).to_be_visible()
            choose(staff,'requests','.workDropdown:has([data-work-view=mine])')
            staff.locator('#workTimeOff').click()
            form=staff.locator('#workRequestForm');form.locator('[name=start]').fill(target);form.locator('[name=end]').fill(target)
            form.locator('[name=from_time]').fill('09:00');form.locator('[name=until_time]').fill('11:00');form.locator('button.primary').click()
            expect(staff.locator('#workMyRequests')).to_contain_text('09:00')
            choose(staff,'my-cards','.workDropdown:has([data-work-view=mine])')
            expect(staff.locator('#workOwnCards')).to_contain_text('No timecards')
            staff.locator('.headerMenu summary').click();expect(staff.locator('#appearanceMenu')).to_be_visible()
            manager.set_viewport_size({'width':1500,'height':1000})
            manager.locator('.headerMenu summary').click();manager.locator('#appearanceMenu').click()
            manager.get_by_role('button',name='Application Settings',exact=True).click()
            manager.locator('#settingsSubcategories').get_by_role('button',name='Jobs',exact=True).click()
            expect(manager.locator('#workJobsForm textarea')).to_contain_text('')
            expect(manager.locator('#workJobsForm textarea')).to_have_value('Driver\nHost\nTrainer')
            manager.locator('#workJobsForm textarea').fill('Driver\nHost\nTrainer\nCashier')
            manager.locator('#workJobsForm button').click();expect(manager.locator('#workJobsStatus')).to_have_text('Jobs saved.')
            assert not errors,errors
            browser.close()
    finally: Fixture.tearDownClass()

if __name__=='__main__': run()
