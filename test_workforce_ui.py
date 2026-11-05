"""Exercise the manager and staff views with simulated mobile geolocation."""
from playwright.sync_api import expect, sync_playwright
from test_server import Tests as Fixture


def run():
    Fixture.setUpClass()
    try:
        Fixture.call('setup', {'name':'Admin','password':'testpassword'})
        Fixture.call('user', {'name':'Staff','password':'testpassword'})
        origin=f'http://127.0.0.1:{Fixture.port}'
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch()
            errors=[]

            def open_workforce(name, width):
                context=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce')
                page=context.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(origin)
                expect(page.locator('#loginTimeClock')).to_be_visible()
                sign_in=page.locator('#login button.primary').bounding_box()
                shortcut=page.locator('#loginTimeClock').bounding_box()
                assert (sign_in['width'],sign_in['height'])==(shortcut['width'],shortcut['height'])
                page.locator('#login [name=name]').fill(name)
                page.locator('#login [name=password]').fill('testpassword')
                page.locator('#login button').click()
                expect(page.locator('#sectionChooser')).to_be_visible()
                page.locator('#sectionChooserForm button').click()
                page.locator('#storeMenuButton').click()
                page.locator('#workforceSection').click()
                expect(page.locator('#workClockState')).to_have_text('Clocked out')
                return page

            manager=open_workforce('Admin',1280)
            manager.locator('[data-work-view=sites]').click()
            expect(manager.locator('#workSiteList')).to_have_text('No work sites configured.')
            manager.locator('#workAddSite').click()
            form=manager.locator('#workSiteForm')
            for field,value in dict(name='Main Office',latitude='30.69',longitude='-88.04',radius='150').items():
                form.locator(f'[name={field}]').fill(value)
            form.get_by_role('button',name='Save work site').click()
            expect(manager.locator('#workSiteList')).to_contain_text('Main Office')

            manager.locator('[data-work-view=team]').click()
            expect(manager.locator('#workTeamShifts')).to_have_text('No shifts scheduled for this week.')
            week=manager.locator('#workWeekDate').input_value()
            manager.locator('#workAddShift').click()
            form=manager.locator('#workShiftForm')
            form.locator('[name=account]').select_option(label='Staff')
            form.locator('[name=start]').fill(week+'T08:00')
            form.locator('[name=end]').fill(week+'T16:00')
            form.locator('[name=location]').fill('Main Office')
            form.get_by_role('button',name='Save shift').click()
            expect(manager.locator('#workTeamShifts')).to_contain_text('Staff')
            assert manager.locator('#workforce .workHead').evaluate(
                "(element)=>getComputedStyle(element.closest('#workforce')).borderTopColor")=='rgb(203, 4, 207)'

            staff=open_workforce('Staff',390)
            expect(staff.locator('[data-work-view=team]')).to_be_hidden()
            expect(staff.locator('[data-work-view=sites]')).to_be_hidden()
            staff.locator('[data-work-view=mine]').click()
            expect(staff.locator('#workMyShifts')).to_contain_text('Main Office')
            staff.locator('[data-work-view=clock]').click()
            staff.context.grant_permissions(['geolocation'],origin=origin)
            staff.context.set_geolocation({'latitude':31,'longitude':-88.04,'accuracy':10})
            staff.locator('[data-work-punch=in]').click()
            expect(staff.locator('#workStatus')).to_contain_text('outside an approved work site')
            staff.context.set_geolocation({'latitude':30.69,'longitude':-88.04,'accuracy':10})
            staff.locator('[data-work-punch=in]').click()
            expect(staff.locator('#workClockState')).to_contain_text('Clocked in since')
            staff.context.clear_permissions()
            staff.locator('[data-work-punch=start_break]').click()
            expect(staff.locator('#workClockState')).to_contain_text('On break')
            staff.locator('[data-work-punch=end_break]').click()
            expect(staff.locator('#workClockState')).to_contain_text('Clocked in since')
            staff.context.grant_permissions(['geolocation'],origin=origin)
            staff.locator('[data-work-punch=out]').click()
            expect(staff.locator('#workClockState')).to_have_text('Clocked out')
            assert staff.evaluate('document.documentElement.scrollWidth<=innerWidth')
            staff.locator('#headerHome').click()
            expect(staff.locator('#currentSection')).to_have_text('Thrift Mart Dispatch')
            staff.locator('#headerClock').click()
            expect(staff.locator('#workClockState')).to_have_text('Clocked out')

            self_pin={'name':'Staff','pin':'714286'}
            assert Fixture.call('admin/clock-pin',self_pin)[0]==200
            kiosk=browser.new_context(viewport={'width':390,'height':900},reduced_motion='reduce')
            kiosk.grant_permissions(['geolocation'],origin=origin)
            kiosk.set_geolocation({'latitude':30.69,'longitude':-88.04,'accuracy':10})
            quick=kiosk.new_page()
            quick.on('pageerror',lambda error:errors.append(str(error)))
            quick.goto(origin)
            quick.locator('#loginTimeClock').click()
            quick.locator('#quickClockForm input').fill('000000')
            quick.locator('#quickClockForm button.primary').click()
            expect(quick.locator('#quickClockError')).to_contain_text('could not be used')
            quick.locator('#quickClockForm input').fill(self_pin['pin'])
            quick.locator('#quickClockForm button.primary').click()
            expect(quick.locator('#workClockState')).to_have_text('Clocked out')
            expect(quick.locator('[data-work-view=mine]')).to_be_hidden()
            assert quick.request.get(origin+'/api/workforce/team').status==401
            quick.locator('[data-work-punch=in]').click()
            expect(quick.locator('#loginTimeClock')).to_be_visible()
            assert quick.request.get(origin+'/api/workforce/quick').status==401
            staff.locator('#headerClock').click()
            expect(staff.locator('#workClockState')).to_contain_text('Clocked in since')
            assert not errors,errors
            browser.close()
    finally:
        Fixture.tearDownClass()


if __name__=='__main__':
    run()
