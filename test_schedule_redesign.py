"""Integration checks for schedule copying and private employee views."""
import datetime as dt
import http.cookiejar
import urllib.request
import unittest
from test_server import Tests as Fixture


class ScheduleRedesignTests(unittest.TestCase):
    def test_copy_is_atomic_permission_checked_and_single_shift_per_employee(self):
        Fixture.setUpClass();self.addCleanup(Fixture.tearDownClass)
        call=Fixture.call
        call('setup',dict(name='Admin',password='testpassword'))
        call('user',dict(name='Staff',password='testpassword'))
        client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        call('login',dict(name='Staff',password='testpassword'),client)
        team=call('workforce/team')[1]
        employee=next(p['id'] for p in team['people'] if p['name']=='Staff')
        call('workforce/assignment',dict(name='Staff',jobs=['Host','Trainer'],primary_job='Host',sites=[],primary_site=None,require_location=False))
        self.assertEqual(call('workforce/jobs',dict(jobs=['Host','Trainer','Driver']))[0],200)
        self.assertIn('Driver',call('workforce/team')[1]['jobs'])
        self.assertEqual(call('workforce/jobs',dict(jobs=['Trainer']))[0],409)
        self.assertEqual(call('workforce/jobs',dict(jobs=['Host','Trainer']),client)[0],403)
        source=call('workforce/overview')[1]['week']
        target=(dt.date.fromisoformat(source)+dt.timedelta(days=7)).isoformat()
        for job,start,end in [('Host','08:00','12:00'),('Trainer','13:00','17:00')]:
            self.assertEqual(call('workforce/shift',dict(account=employee,start=source+'T'+start,end=source+'T'+end,job=job))[0],200)
        self.assertEqual(call('workforce/copy-week',dict(source=source,target=target),client)[0],403)
        # The first candidate would succeed, but the second conflicts: rollback both.
        call('workforce/shift',dict(account=employee,start=target+'T14:00',end=target+'T15:00',job='Trainer'))
        self.assertEqual(call('workforce/copy-week',dict(source=source,target=target))[0],409)
        destination=call('workforce/team?week='+target)[1]['shifts']
        self.assertEqual(len(destination),1)
        call('workforce/shift',dict(id=destination[0]['id'],revision=destination[0]['revision'],remove=True))
        status,result=call('workforce/copy-week',dict(source=source,target=target))
        self.assertEqual((status,result['copied']),(200,2))
        self.assertEqual(call('workforce/copy-week',dict(source=source,target=target))[0],409)
        own=call('workforce/overview?week='+target,client=client)[1]['shifts']
        self.assertEqual(len(own),2)
        self.assertEqual({s['job'] for s in own},{'Host','Trainer'})
        self.assertEqual(call('workforce/copy-week',dict(source=source,target=source))[0],400)
        # Partial-day requests remain pending until reviewed and preserve their hours.
        self.assertEqual(call('workforce/request',dict(kind='time-off',start=target,end=target,from_time='09:00',until_time='11:00'),client)[0],200)
        pending=call('workforce/team?week='+target)[1]['pending_absences']
        self.assertEqual(pending[0]['start'],'09:00')
        self.assertEqual(call('workforce/team?week='+target)[1]['absences'],[])
        request=call('workforce/requests',client=client)[1]['requests'][0]
        self.assertEqual(call('workforce/review-request',dict(id=request['id'],decision='approved'))[0],200)
        self.assertEqual(call('workforce/team?week='+target)[1]['absences'][0]['end'],'11:00')
        self.assertEqual(call('workforce/request',dict(kind='time-off',start=target,end=target,from_time='12:00',until_time='09:00'),client)[0],400)
        # A staff member cannot request another employee's cards through the self endpoint.
        admin_id=next(p['id'] for p in team['people'] if p['name']=='Admin')
        call('workforce/add-time-card',dict(account=admin_id,start='2025-01-06T09:00',end='2025-01-06T10:00',reason='Test'))
        self.assertEqual(call('workforce/my-time-cards?week=2025-01-05&account='+admin_id,client=client)[1]['cards'],[])
        self.assertEqual(len(call('workforce/my-time-cards?week=2025-01-05')[1]['cards']),1)


if __name__=='__main__': unittest.main()
