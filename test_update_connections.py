import datetime as dt
import http.cookiejar
import sqlite3
import time
import unittest
import urllib.request
from types import SimpleNamespace
from unittest.mock import patch

import server
import test_server


class ConnectionTests(unittest.TestCase):
    def test_own_tab_idle_unconfirmed_expired_and_pin_connections(self):
        now=time.time();key='a'*32
        handler=SimpleNamespace(headers={'X-Dispatch-Connection':key})
        current=dict(name='Admin',expires=now+3600,login_day=dt.date.today().isoformat(),last_active=now)
        other=dict(name='Staff',expires=now+3600,login_day=dt.date.today().isoformat(),last_active=now-800)
        expired=dict(name='Expired',expires=now-1,login_day=dt.date.today().isoformat())
        with sqlite3.connect(':memory:') as c,patch.object(server,'SESSIONS',{'admin-secret':current,'staff-secret':other,'expired-secret':expired}),patch.object(server,'CLOCK_SESSIONS',{}):
            c.row_factory=sqlite3.Row
            c.execute('CREATE TABLE receipt_profiles(name,profile_id)')
            c.execute("INSERT INTO receipt_profiles VALUES('PIN staff','pin-staff')")
            server.record_connection(handler,current)
            self.assertEqual(server.update_connection_rows(handler,c,current)['other_connections'],0)
            server.record_connection(SimpleNamespace(headers={'X-Dispatch-Connection':'b'*32}),current)
            server.record_connection(SimpleNamespace(headers={}),other)
            server.record_connection(SimpleNamespace(headers={}),expired)
            rows=server.update_connection_rows(handler,c,current)
            self.assertEqual(rows['other_connections'],2)
            self.assertNotIn('admin-secret',str(rows));self.assertNotIn('staff-secret',str(rows))
            self.assertEqual(next(r['status'] for r in rows['connections'] if r['name']=='Staff'),'idle')
            other['connections']['legacy']['last_seen']=now-120
            rows=server.update_connection_rows(handler,c,current)
            self.assertEqual(next(r['status'] for r in rows['connections'] if r['name']=='Staff'),'not-seen')
            with self.assertRaises(server.Problem) as error:server.ensure_update_connections_clear(handler,c,current)
            self.assertEqual(error.exception.status,409)
            current['connections'].pop('b'*32);other['connections'].clear()
            server.ensure_update_connections_clear(handler,c,current)
            server.CLOCK_SESSIONS['pin-secret']=('pin-staff',now+60,'hash')
            self.assertEqual(server.update_connection_rows(handler,c,current)['other_connections'],1)
            server.CLOCK_SESSIONS['pin-secret']=('pin-staff',now-1,'hash')
            server.ensure_update_connections_clear(handler,c,current)
        c.close()

    def test_admin_only_visibility_and_server_install_guard(self):
        fixture=test_server.Tests;fixture.setUpClass();self.addCleanup(fixture.tearDownClass)
        call=fixture.call
        call('setup',dict(name='Admin',password='testpassword'))
        call('user',dict(name='Staff',password='testpassword'))
        staff=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        call('login',dict(name='Staff',password='testpassword'),staff)
        self.assertEqual(call('admin/update-connections',client=staff)[0],403)
        self.assertEqual(call('admin/update-connections')[1]['other_connections'],1)
        status,result=call('update-install',dict(version='0.39.1'))
        self.assertEqual(status,409);self.assertIn('other signed-in',result['error'])
        self.assertEqual(call('account/connection',dict(closing=True),staff)[0],200)
        self.assertEqual(call('admin/update-connections')[1]['other_connections'],0)
        # Any later request from that connection is seen again.
        call('account/connection',dict(closing=False),staff)
        self.assertEqual(call('admin/update-connections')[1]['other_connections'],1)
        call('logout',{},staff)
        self.assertEqual(call('admin/update-connections')[1]['other_connections'],0)
        # With no other users, the existing launcher requirement still applies.
        self.assertEqual(call('update-install',dict(version='0.39.1'))[0],400)


if __name__=='__main__':unittest.main()
