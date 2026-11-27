"""Shared policy validation, authorization, persistence and additive upgrade checks."""
from contextlib import closing
import sqlite3
import unittest
import server
from test_update_coordination import CoordinatorFixture


class ConnectionSettingsTests(unittest.TestCase):
    def setUp(self):self.f=CoordinatorFixture();self.addCleanup(self.f.close)

    def test_default_and_authenticated_sync_without_guest_policy(self):
        self.assertEqual(self.f.call('connection-settings'),(200,{'timeout_seconds':10,'revision':0}))
        guest=self.f.client('g')
        self.assertEqual(self.f.call('connection-settings',client=guest)[0],401)
        self.assertIsNone(self.f.call('session',client=guest)[1]['connection_settings'])
        code,settings=self.f.call('connection-settings',{'timeout_seconds':25,'revision':0})
        self.assertEqual((code,settings),(200,{'timeout_seconds':25,'revision':1}))
        code,login=self.f.call('login',{'name':'Employee','password':'testpassword'},guest)
        self.assertEqual(code,200);self.assertEqual(login['connection_settings'],settings)
        self.assertEqual(self.f.call('session',client=guest)[1]['connection_settings'],settings)
        self.assertEqual(self.f.call('connection-settings',{'timeout_seconds':5,'revision':1},guest)[0],403)
        self.assertEqual(self.f.call('connection-settings')[1],settings)
        self.assertEqual(self.f.call('admin/clock-pin',{'name':'Employee','pin':'654321'})[0],200)
        code,pin=self.f.call('pos-pin-login',{'pin':'654321'},self.f.client('p'))
        self.assertEqual(code,200);self.assertEqual(pin['connection_settings'],settings)

    def test_invalid_or_stale_edits_do_not_replace_policy(self):
        for value in (None,0,121,1.5,True,'20'):
            self.assertEqual(self.f.call('connection-settings',{'timeout_seconds':value,'revision':0})[0],400)
        self.assertEqual(self.f.call('connection-settings',{'timeout_seconds':20,'revision':0})[0],200)
        self.assertEqual(self.f.call('connection-settings',{'timeout_seconds':30,'revision':0})[0],409)
        self.assertEqual(self.f.call('connection-settings',{'timeout_seconds':30})[0],409)
        self.assertEqual(self.f.call('connection-settings')[1],{'timeout_seconds':20,'revision':1})

    def test_setting_survives_repeat_initialization_and_backup(self):
        with closing(sqlite3.connect(server.DB)) as c:
            before=list(c.execute('SELECT name,salt,hash,admin FROM users ORDER BY name'))
        self.f.call('connection-settings',{'timeout_seconds':30,'revision':0})
        server.init()
        self.assertEqual(self.f.call('connection-settings')[1],{'timeout_seconds':30,'revision':1})
        with closing(sqlite3.connect(server.DB)) as c,closing(sqlite3.connect(':memory:')) as backup:
            self.assertEqual(list(c.execute('SELECT name,salt,hash,admin FROM users ORDER BY name')),before)
            c.backup(backup)
            self.assertEqual(backup.execute('SELECT timeout_seconds,revision FROM application_connection_settings').fetchone(),(30,1))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE action='Changed application connection timeout'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
