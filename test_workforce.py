from contextlib import closing
import http.cookiejar
import sqlite3
import unittest
import urllib.request

import server
import test_server


class WorkforceTests(unittest.TestCase):
    def test_employee_isolation_management_and_location_checks(self):
        fixture=test_server.Tests
        fixture.setUpClass()
        self.addCleanup(fixture.tearDownClass)
        call=fixture.call
        call('setup',dict(name='Admin',password='testpassword'))
        clients={}
        for name in ('Manager','Staff','Other'):
            call('user',dict(name=name,password='testpassword'))
            client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            self.assertEqual(call('login',dict(name=name,password='testpassword'),client)[0],200)
            clients[name]=client
        manager,staff,other=(clients[name] for name in ('Manager','Staff','Other'))
        role=call('roles',dict(name='Scheduler',grants={'manage_staff_schedule':True}))[1]['id']
        self.assertEqual(call('admin/user-role',dict(name='Manager',role_id=role))[0],200)
        self.assertEqual(call('workforce/team',client=staff)[0],403)
        self.assertEqual(call('workforce/sites',client=manager)[0],403)

        team=call('workforce/team',client=manager)[1]
        staff_id=next(person['id'] for person in team['people'] if person['name']=='Staff')
        overview=call('workforce/overview',client=staff)[1]
        week=overview['week']
        shift=dict(account=staff_id,start=week+'T08:00',end=week+'T16:00',location='Main Office',notes='Open office')
        self.assertEqual(call('workforce/shift',shift,staff)[0],403)
        self.assertEqual(call('workforce/shift',shift,manager)[0],200)
        self.assertEqual(call('workforce/shift',shift,manager)[0],409)
        own=call('workforce/overview',client=staff)[1]['shifts']
        self.assertEqual([s['location'] for s in own],['Main Office'])
        self.assertEqual(call('workforce/overview',client=other)[1]['shifts'],[])
        edited=dict(shift,id=own[0]['id'],revision=own[0]['revision'],end=week+'T16:30')
        self.assertEqual(call('workforce/shift',edited,manager)[0],200)
        self.assertEqual(call('workforce/shift',edited,manager)[0],409)

        request=dict(kind='availability',blocks=[dict(day=0,start='08:00',end='12:00')])
        self.assertEqual(call('workforce/request',request,staff)[0],200)
        own_request=call('workforce/requests',client=staff)[1]['requests'][0]
        self.assertEqual(call('workforce/requests',client=other)[1]['requests'],[])
        self.assertEqual(call('workforce/review-requests',client=other)[0],403)
        review=dict(id=own_request['id'],decision='approved')
        self.assertEqual(call('workforce/review-request',review,other)[0],403)
        self.assertEqual(call('admin/user-role',dict(name='Other',role_id=role))[0],200)
        self.assertEqual(call('workforce/request',request,other)[0],200)
        peer=call('workforce/requests',client=other)[1]['requests'][0]
        self.assertEqual([row['id'] for row in call('workforce/review-requests',client=manager)[1]['requests']],[own_request['id']])
        self.assertEqual(call('workforce/review-request',dict(id=peer['id'],decision='approved'),manager)[0],403)
        self.assertEqual(call('comms/status',client=manager)[1]['pending_schedule'],1)
        self.assertEqual(call('comms/status')[1]['pending_schedule'],2)
        self.assertEqual(call('workforce/review-request',review,manager)[0],200)
        self.assertEqual(call('workforce/review-request',dict(id=peer['id'],decision='declined'))[0],200)
        today=overview['today']
        self.assertEqual(call('workforce/request',dict(kind='time-off',start=today,end=today))[0],200)
        self.assertEqual(call('workforce/requests')[1]['requests'][0]['status'],'approved')
        self.assertEqual(call('workforce/request',dict(kind='time-off',start=today,end=today),manager)[0],200)
        manager_request=call('workforce/review-requests',client=manager)[1]['requests'][0]
        self.assertEqual(manager_request['status'],'pending')
        self.assertEqual(call('comms/status',client=manager)[1]['pending_schedule'],1)
        self.assertEqual(call('workforce/review-request',dict(id=manager_request['id'],decision='approved'),manager)[0],200)
        self.assertEqual(call('workforce/requests',client=manager)[1]['requests'][0]['status'],'approved')
        self.assertEqual(call('comms/status')[1]['pending_schedule'],0)
        self.assertEqual(call('workforce/review-request',review)[0],409)
        import datetime
        next_week=(datetime.date.fromisoformat(week)+datetime.timedelta(days=7)).isoformat()
        absences=call('workforce/team?week='+next_week,client=manager)[1]['absences']
        self.assertEqual(datetime.date.fromisoformat(week).weekday(),6)
        monday=(datetime.date.fromisoformat(next_week)+datetime.timedelta(days=1)).isoformat()
        self.assertEqual(absences,[dict(account=staff_id,day=monday,kind='availability',start='08:00',end='12:00')])

        self.assertFalse(call('workforce/overview',client=staff)[1]['require_location'])
        site=dict(name='Main Office',latitude=30.69,longitude=-88.04,radius=150)
        self.assertEqual(call('workforce/site',site,manager)[0],403)
        self.assertEqual(call('workforce/site',site)[0],200)
        self.assertEqual(call('workforce/site',dict(site,name='Other Office',latitude=31.00))[0],200)
        sites=call('workforce/sites')[1]['sites']
        primary=next(site['id'] for site in sites if site['name']=='Main Office')
        assignments=dict(name='Staff',jobs=['Host','Trainer'],sites=[primary],primary_job='Trainer',
                         primary_site=primary,require_location=True)
        self.assertEqual(call('workforce/assignment',assignments,staff)[0],403)
        self.assertEqual(call('workforce/assignment',assignments,manager)[0],200)
        self.assertFalse(call('workforce/overview',client=other)[1]['require_location'])
        self.assertEqual(call('workforce/punch',dict(action='in'),other)[0],200)
        self.assertEqual(call('workforce/punch',dict(action='out'),other)[0],200)
        self.assertEqual(call('workforce/shift',dict(account=staff_id,start=week+'T18:00',end=week+'T20:00'),manager)[0],200)
        new_shift=call('workforce/overview',client=staff)[1]['shifts'][-1]
        self.assertEqual((new_shift['location'],new_shift['job']),('Main Office','Trainer'))
        self.assertEqual(call('workforce/punch',dict(action='in'),staff)[0],403)
        near=dict(latitude=30.69,longitude=-88.04,accuracy=10)
        far=dict(latitude=31.00,longitude=-88.04,accuracy=10)
        self.assertEqual(call('workforce/punch',dict(action='in',position=far),staff)[0],403)
        self.assertEqual(call('workforce/punch',dict(action='in',position=dict(near,accuracy=151)),staff)[0],403)
        self.assertEqual(call('workforce/punch',dict(action='in',position=near),staff)[0],200)
        self.assertEqual(call('workforce/punch',dict(action='in',position=near),staff)[0],409)
        self.assertEqual(call('workforce/punch',dict(action='start_break'),staff)[0],200)
        self.assertEqual(call('workforce/overview',client=staff)[1]['clock']['state'],'break')
        self.assertEqual(call('workforce/punch',dict(action='end_break'),staff)[0],200)
        self.assertEqual(call('workforce/punch',dict(action='out',position=far),staff)[0],403)
        self.assertEqual(call('workforce/punch',dict(action='out',position=near),staff)[0],200)
        self.assertEqual(call('workforce/overview',client=staff)[1]['clock']['state'],'out')
        self.assertEqual(call('admin/rename-user',dict(name='Staff',new_name='Staff Updated'))[0],200)
        self.assertEqual(call('workforce/overview',client=staff)[1]['shifts'][0]['name'],'Staff Updated')
        with closing(sqlite3.connect(fixture.tmp.name+'/schedule.db')) as db:
            self.assertEqual(db.execute('SELECT account,site_in,site_out FROM work_periods WHERE account=?',(staff_id,)).fetchone(),
                             (staff_id,'Main Office','Main Office'))

    def test_elapsed_and_net_time_are_clipped_to_the_selected_period(self):
        c=sqlite3.connect(':memory:')
        self.addCleanup(c.close)
        c.row_factory=sqlite3.Row
        server.init_workforce(c)
        c.execute("INSERT INTO work_periods VALUES(1,'staff',100,300,NULL,NULL)")
        c.execute("INSERT INTO work_periods VALUES(2,'staff',400,NULL,NULL,NULL)")
        c.execute('INSERT INTO work_breaks VALUES(1,1,140,200)')
        c.execute('INSERT INTO work_breaks VALUES(2,2,450,NULL)')
        self.assertEqual(server.work_hours(c,'staff',(160,800),500),(240,150))
        self.assertEqual(server.work_hours(c,'staff',(0,420),500),(220,160))
        self.assertEqual(server.work_hours(c,'other',(0,800),500),(0,0))


if __name__=='__main__':
    unittest.main()
