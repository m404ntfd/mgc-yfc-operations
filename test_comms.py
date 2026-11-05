"""Exercise communication membership, unread state, and attachment privacy."""
import base64
import http.cookiejar
import unittest
import urllib.error
import urllib.request

import test_server



class CommunicationTests(unittest.TestCase):
    def test_private_conversations_and_preferences(self):
        Fixture = test_server.Tests
        Fixture.setUpClass()
        self.addCleanup(Fixture.tearDownClass)
        call = Fixture.call
        self.assertEqual(call('comms/status')[0], 401)
        password = 'testpassword'
        self.assertEqual(call('setup', dict(name='Admin', password=password))[0], 200)

        def login(name):
            client = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            self.assertEqual(call('login', dict(name=name, password=password), client)[0], 200)
            return client

        for name in ('Alex', 'Blair', 'Casey'):
            self.assertEqual(call('user', dict(name=name, password=password))[0], 200)
        alex, blair, casey = map(login, ('Alex', 'Blair', 'Casey'))
        directory = call('comms/inbox', client=alex)[1]
        people = {p['name']: p['id'] for p in directory['team']}
        self.assertNotIn('Alex', people)
        dm = dict(kind='dm', members=[people['Blair']])
        thread = call('comms/create', dm, alex)[1]['id']
        self.assertEqual(call('comms/create', dm, alex)[1]['id'], thread)
        message = call('comms/send', dict(thread=thread, text='Volunteer schedule',
            filename='schedule.txt', file=base64.b64encode(b'Tuesday').decode()), alex)[1]['id']
        self.assertEqual(call('comms/status', client=alex)[1]['unread'], [])
        self.assertEqual(call('comms/status', client=blair)[1]['unread'],
                         [dict(id=thread, unread=1, latest=message)])
        self.assertEqual(call('comms/inbox', client=casey)[1]['threads'], [])
        self.assertEqual(call(f'comms/messages?thread={thread}', client=casey)[0], 404)
        self.assertEqual(call('comms/send', dict(thread=thread, text='Intrusion'), casey)[0], 404)
        self.assertEqual(call('comms/save', dict(id=message, save=True), casey)[0], 404)
        url = f'http://127.0.0.1:{Fixture.port}/api/comms/file/{message}'
        with blair.open(url) as response:
            self.assertEqual(response.read(), b'Tuesday')
            self.assertEqual(response.headers['Content-Disposition'], 'attachment')
        with self.assertRaises(urllib.error.HTTPError) as denied:
            casey.open(url)
        self.assertEqual(denied.exception.code, 404)
        denied.exception.close()
        self.assertEqual(call('comms/save', dict(id=message, save=True), blair)[0], 200)
        self.assertEqual(call('comms/saved', client=blair)[1]['messages'][0]['id'], message)
        self.assertEqual(call('comms/saved', client=alex)[1]['messages'], [])
        self.assertEqual(call('comms/files', client=casey)[1]['messages'], [])
        call('comms/read', dict(thread=thread, id=message), blair)
        self.assertEqual(call('comms/status', client=blair)[1]['unread'], [])
        prefs = dict(direct=False, order='unread', dm='all', group='all', alerts=False)
        self.assertEqual(call('comms/preferences', prefs, blair), (200, prefs))
        self.assertEqual(call('comms/send', dict(thread=thread, text='Blocked'), alex)[0], 403)
        group = call('comms/create', dict(kind='group', title='Volunteers',
            members=[people['Blair'], people['Casey']]), alex)[1]['id']
        self.assertEqual(call('comms/send', dict(thread=group, text='Group update'), alex)[0], 200)
        self.assertEqual(call('comms/status', client=blair)[1]['alerts'], False)
        self.assertEqual(call('comms/status', client=casey)[1]['unread'][0]['id'], group)
        self.assertEqual(call(f'comms/messages?thread={group}')[0], 404)
        rename = dict(name='Blair', new_name='Blair Morgan')
        self.assertEqual(call('admin/rename-user', rename, alex)[0], 403)
        role = call('roles', dict(name='Name editor', grants={'rename_users': True}))[1]['id']
        self.assertEqual(call('admin/user-role', dict(name='Alex', role_id=role))[0], 200)
        self.assertEqual(call('admin/users', client=alex)[0], 200)
        self.assertEqual(call('admin/rename-user', dict(name='Admin', new_name='Admin 2'), alex)[0], 403)
        self.assertEqual(call('admin/rename-user', dict(name='Blair', new_name='Casey'), alex)[0], 409)
        self.assertEqual(call('admin/rename-user', rename, alex)[0], 200)
        self.assertEqual(call('session', client=blair)[1]['user']['name'], 'Blair Morgan')
        self.assertEqual(call('comms/inbox', client=login('Blair Morgan'))[1]['account'], people['Blair'])
        self.assertEqual(call('comms/saved', client=blair)[1]['messages'][0]['id'], message)
        self.assertEqual(call('comms/inbox', client=blair)[1]['preferences'], prefs)
        # A reused name does not inherit the old account's conversations.
        self.assertEqual(call('admin/remove-user', dict(name='Casey'))[0], 200)
        self.assertEqual(call('user', dict(name='Casey', password=password))[0], 200)
        self.assertEqual(call('comms/inbox', client=login('Casey'))[1]['threads'], [])


if __name__ == '__main__':
    unittest.main()
