"""Exercise the manager and staff views with simulated mobile geolocation."""
import csv
import datetime

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
            manager.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
            manager.route('**/api/workforce/geocode?*',lambda route:route.fulfill(json={
                'matches':[{'address':'101 Main St, Mobile, AL','latitude':30.69,'longitude':-88.04}]
            }))
            form.locator('[name=name]').fill('Main Office')
            form.locator('[name=address]').fill('101 Main St, Mobile, AL')
            manager.locator('#workFindAddress').click()
            manager.locator('#workAddressMatches button').click()
            expect(manager.locator('#workSiteMap')).to_be_visible()
            assert len(manager.locator('#workMapBoundary').get_attribute('points').split())==64
            map_box=manager.locator('#workSiteMap').bounding_box()
            manager.locator('#workSiteMap').click(position={'x':map_box['width']/2,'y':map_box['height']/2})
            assert abs(float(form.locator('[name=longitude]').input_value())+88.04)<0.02
            # Set an exact center again before testing the geofence.
            form.locator('[name=latitude]').fill('30.69')
            form.locator('[name=longitude]').fill('-88.04')
            form.locator('[name=radius_unit]').select_option('ft')
            assert abs(float(form.locator('[name=radius]').input_value())-150/0.3048)<0.001
            form.locator('[name=radius]').fill('500')
            form.get_by_role('button',name='Save work site').click()
            expect(manager.locator('#workSiteList')).to_contain_text('500 ft radius')
            sites=manager.request.get(origin+'/api/workforce/sites').json()['sites']
            assert abs(sites[0]['radius']-152.4)<0.001
            assert sites[0]['address']=='101 Main St, Mobile, AL'

            manager.locator('#settingsTab').click()
            manager.get_by_role('button',name='Application Settings',exact=True).click()
            manager.locator('#settingsSubcategories').get_by_role('button',name='Users',exact=True).click()
            staff_row=manager.locator('#users .listRow').filter(has_text='Staff')
            expect(staff_row.get_by_role('button',name='Edit name',exact=True)).to_have_count(0)
            staff_row.get_by_role('button',name='Employee Profile',exact=True).click()
            employee_profile=manager.get_by_role('dialog',name='Employee Profile')
            expect(employee_profile.get_by_label('Login username')).to_have_value('Staff')
            employee_profile.get_by_role('button',name='Edit display name').click()
            expect(manager.locator('#renameUserName')).to_have_value('Staff')
            manager.locator('#renameUserCancel').click()
            manager.locator('[data-work-assignment=Staff]').click()
            assignments=manager.locator('#workAssignmentForm')
            expect(assignments.get_by_role('checkbox',name='Main Office')).to_be_visible()
            assignments.locator('[name=jobs]').fill('Host\nTrainer')
            assignments.locator('[name=primary_job]').select_option('Trainer')
            assignments.get_by_role('checkbox',name='Main Office').check()
            assignments.locator('[name=require_location]').check()
            assignments.get_by_role('button',name='Save assignments').click()
            expect(manager.locator('#workAssignmentForm')).to_be_hidden()
            manager.locator('#headerClock').click()
            manager.locator('[data-work-view=team]').click()
            expect(manager.locator('.workScheduleGrid')).to_be_visible()
            expect(manager.locator('.workScheduleGrid thead th').nth(2)).to_contain_text('Sun')
            week=manager.locator('#workWeekDate').input_value()
            manager.locator('#workAddShift').click()
            form=manager.locator('#workShiftForm')
            form.locator('[name=account]').select_option(label='Staff')
            form.locator('[name=start]').fill(week+'T08:00')
            form.locator('[name=end]').fill(week+'T16:00')
            expect(form.locator('[name=location]')).to_have_value('Main Office')
            expect(form.locator('[name=job]')).to_have_value('Trainer')
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
            staff.locator('[data-work-view=requests]').click()
            staff.locator('#workTimeOff').click()
            today=staff.request.get(origin+'/api/workforce/overview').json()['today']
            staff.locator('#workRequestForm [name=start]').fill(today)
            staff.locator('#workRequestForm [name=end]').fill(today)
            staff.get_by_role('button',name='Submit request').click()
            expect(staff.locator('#workMyRequests')).to_contain_text('pending')
            expect(manager.locator('#photoReviewCount')).to_have_text('1',timeout=10000)
            manager.locator('#photoNotifications').click()
            manager.locator('#scheduleNoticeOpen').click()
            manager.locator('#workReviewRequests').get_by_role('button',name='Approve').click()
            expect(manager.locator('#workReviewRequests')).to_contain_text('approved')
            manager.locator('[data-work-view=team]').click()
            expect(manager.locator('.workAbsence.timeOff')).to_have_text('Time off')
            staff.locator('[data-work-view=requests]').click()
            expect(staff.locator('#workMyRequests')).to_contain_text('approved')
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
            expect(staff.locator('[data-work-view=time-cards]')).to_be_hidden()
            manager.locator('[data-work-view=time-cards]').click()
            open_card=manager.locator('#workTimeCards article').filter(has_text='Open')
            open_card.get_by_role('button',name='Edit time card').click()
            card=manager.locator('#workCardForm')
            start=card.locator('[name=start]').input_value()
            card.locator('[name=end]').fill(start)
            card.locator('[name=reason]').fill('Correct missing clock-out')
            card.get_by_role('button',name='Save correction').click()
            expect(manager.locator('#workCardDialog')).to_be_hidden()
            manager.locator('#workAddCard').click()
            card.locator('[name=account]').select_option(label='Admin')
            first=datetime.datetime.fromisoformat(start)-datetime.timedelta(hours=2)
            card.locator('[name=start]').fill(first.isoformat(timespec='seconds'))
            card.locator('[name=end]').fill((first+datetime.timedelta(hours=1)).isoformat(timespec='seconds'))
            card.locator('[name=reason]').fill('Enter a missed shift')
            card.get_by_role('button',name='Save time card').click()
            expect(manager.locator('#workCardDialog')).to_be_hidden()
            manager.locator('[data-work-view=time-card-audit]').click()
            expect(manager.locator('#workTimeAudit')).to_contain_text('Correct missing clock-out')
            expect(manager.locator('#workTimeAudit')).to_contain_text('No entry existed.')
            expect(manager.locator('#workTimeAudit')).to_contain_text('Before')
            expect(manager.locator('#workTimeAudit')).to_contain_text('After')
            manager.locator('[data-work-view=payroll]').click()
            manager.route('**/api/workforce/payroll?*',lambda route:route.fulfill(json={
                'start':'2025-01-05','end':'2025-01-11','unlinked':0,
                'employees':[{'account':'staff','name':'Staff','gross':162000,'net':154800,'open_punch':False,
                                           'issues':[{'kind':'no-break-recorded','at':'2025-01-07T08:00'}]},
                             {'account':'open','name':'Incomplete','gross':1800,'net':1800,'open_punch':True}]
            }))
            payroll=manager.locator('#workPayrollForm')
            pay_start=payroll.locator('[name=start]')
            pay_start.fill('2025-01-06')
            assert pay_start.evaluate('(input)=>input.validity.stepMismatch')
            pay_start.fill('2025-01-05')
            expect(payroll.locator('#workPayrollRange')).to_contain_text('Sunday')
            expect(payroll.locator('#workPayrollRange')).to_contain_text('Saturday')
            expect(payroll.locator('[name=threshold]')).to_have_value('40')
            expect(payroll.locator('[name=break_after]')).to_have_value('5.5')
            expect(payroll.locator('[name=breaks]')).to_have_value('exclude')
            payroll.get_by_role('button',name='Preview hours').click()
            manager.get_by_role('checkbox',name='Include Staff',exact=True).check()
            manager.get_by_label('Overtime treatment for Staff').select_option('overtime')
            expect(manager.locator('[data-payroll-account=staff] [data-regular]')).to_have_text('40.00')
            expect(manager.locator('[data-payroll-account=staff] [data-overtime]')).to_have_text('3.00')
            expect(manager.locator('#workPayrollRows')).to_contain_text('No break recorded')
            expect(manager.locator('#workPayrollDownload')).to_be_hidden()
            manager.get_by_role('checkbox',name='Reviewed flags for Staff').check()
            expect(manager.locator('#workPayrollDownload')).to_be_visible()
            manager.get_by_role('checkbox',name='Include Incomplete').check()
            manager.get_by_label('Overtime treatment for Incomplete').select_option('regular')
            expect(manager.locator('#workPayrollDownload')).to_be_hidden()
            manager.get_by_role('checkbox',name='Include Incomplete').uncheck()
            with manager.expect_download() as exported:
                manager.locator('#workPayrollDownload').click()
            with exported.value.path().open(newline='',encoding='utf-8') as file:
                rows=list(csv.DictReader(file))
            assert len(rows)==1 and rows[0]['Employee']=='Staff'
            assert rows[0]['Pay Period Start']=='2025-01-05' and rows[0]['Pay Period End']=='2025-01-11'
            assert rows[0]['Regular Hours']=='40.00' and rows[0]['Overtime Hours']=='3.00'
            payroll.locator('[name=threshold]').fill('41')
            payroll.locator('[name=break_after]').fill('6')
            payroll.locator('[name=breaks]').select_option('include')
            with manager.expect_request('**/api/workforce/payroll?*break_after=6'):
                payroll.get_by_role('button',name='Preview hours').click()
            expect(manager.locator('[data-payroll-account=staff] [data-regular]')).to_have_text('41.00')
            expect(manager.locator('[data-payroll-account=staff] [data-overtime]')).to_have_text('4.00')
            assert not errors,errors
            browser.close()
    finally:
        Fixture.tearDownClass()


if __name__=='__main__':
    run()
