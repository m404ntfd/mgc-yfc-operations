"""Isolated installer enrollment: authentication, repeat installs, MAC matches and retained data."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from types import SimpleNamespace

import server
from test_update_coordination import CoordinatorFixture
from installer_registration import SetupRegistration,SetupRequestError
from pos_kiosk import KioskStore
import computer_identity


class InstallerRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.f=CoordinatorFixture();self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.address=f'http://127.0.0.1:{self.f.port}'
        self.meta={'id':'1'*32,'hostname':'ORIGINAL-PC','macs':['00:11:22:33:44:55'],'os':'Windows fixture','active_mac':'02:AA:BB:CC:DD:10','active_adapter':'Ethernet','local_address':'192.0.2.50'}
        self.versions={'pos':'1.22.0','office':'1.19.0','ops':'1.6.0'};self.clients=[]
    def tearDown(self):
        for client in self.clients:client.close()
        self.f.close();self.temp.cleanup()
    def client(self,apps=('pos','office','ops'),meta=None,folder='current'):
        client=SetupRegistration(list(apps),self.versions,self.root/folder,copy.deepcopy(meta or self.meta));self.clients.append(client);return client
    def connect(self,client):return client.connect(self.address,'Admin','testpassword')
    def rows(self,table):
        with server.connect() as c:return [tuple(row) for row in c.execute('SELECT * FROM "'+table+'" ORDER BY rowid')]
    def test_reinstall_rename_and_network_changes_preserve_one_computer_and_checkout(self):
        client=self.client();self.connect(client)
        self.assertEqual(self.rows('retail_computers'),[],'Preview must not enroll a computer')
        first=client.register('Binopoly register','pos','binopoly');terminal=first['terminal']['id'];devices=copy.deepcopy(client.app_info)
        with server.connect() as c:
            before=dict(c.execute('SELECT * FROM retail_terminals WHERE id=?',(terminal,)).fetchone())
            self.assertEqual(c.execute('SELECT store FROM retail_terminal_stores WHERE terminal=?',(terminal,)).fetchone()[0],'binopoly')
        client.close()
        meta={**self.meta,'hostname':'RENAMED-PC','active_mac':'02:AA:BB:CC:DD:20','active_adapter':'Wi-Fi','local_address':'192.0.2.90'}
        again=self.client(meta=meta);preview=self.connect(again);self.assertTrue(preview['computer']['registered'])
        second=again.register('Binopoly renamed','pos','thrift-mart')
        self.assertEqual(second['computer']['id'],first['computer']['id']);self.assertEqual(second['terminal']['id'],terminal)
        self.assertEqual(again.app_info,devices);self.assertEqual(len(self.rows('retail_computers')),1)
        self.assertEqual(len(self.rows('retail_computer_apps')),3)
        with server.connect() as c:self.assertEqual(dict(c.execute('SELECT * FROM retail_terminals WHERE id=?',(terminal,)).fetchone()),before)
        self.assertEqual(self.rows('retail_computer_network')[0][1:4],('02:AA:BB:CC:DD:20','Wi-Fi','192.0.2.90'))
    def test_mac_match_adopts_original_registration_and_app_ids_only_after_confirmation(self):
        original=self.client();self.connect(original);first=original.register('Original checkout','pos','thrift-mart')
        original.close();client=self.client(meta={**self.meta,'id':'2'*32,'hostname':'REINSTALLED-PC'},folder='reinstalled')
        preview=self.connect(client);self.assertTrue(preview['matched_by_mac']);self.assertEqual(preview['terminal']['id'],first['terminal']['id'])
        with self.assertRaisesRegex(ValueError,'Confirm'):client.register('Original checkout','pos')
        self.assertEqual(len(self.rows('retail_computers')),1)
        result=client.register('Restored checkout','pos',reuse=True)
        self.assertEqual(result['computer']['id'],'1'*32);self.assertEqual(result['terminal']['id'],first['terminal']['id'])
        self.assertEqual(len(self.rows('retail_computers')),1);self.assertEqual(len(self.rows('retail_terminals')),1)
        self.assertEqual(len(self.rows('retail_computer_apps')),3)
        for app in client.app_info:self.assertEqual(KioskStore(client.settings_path(app['app'])).data['device'],app['device'])
        data={**client.app_info[0],'computer':{**client.identity,'active_mac':'02:AA:BB:CC:DD:30'}}
        code,state=self.f.call('computers/self',data);self.assertEqual(code,200,state);self.assertEqual(state['computer']['id'],'1'*32)
    def test_admin_only_failed_login_and_bad_server_leave_settings_and_database_untouched(self):
        client=self.client(('office',));path=client.settings_path('office');store=KioskStore(path);store.data.update(server='http://old-server:8080',printer='keep');store.save();before=path.read_bytes()
        for user,password in [('Admin','incorrect'),('Employee','testpassword')]:
            with self.assertRaises(ValueError):client.connect(self.address,user,password)
        with patch('installer_registration.probe_server',side_effect=ValueError('Wrong server')):
            with self.assertRaisesRegex(ValueError,'Wrong server'):self.connect(client)
        self.assertEqual(path.read_bytes(),before);self.assertEqual(self.rows('retail_computers'),[])
        staff=self.f.client('e');self.f.call('login',{'name':'Employee','password':'testpassword'},staff)
        self.assertEqual(self.f.call('computers/setup-preview',{'computer':self.meta,'apps':[]},staff)[0],403)
    def test_lost_reply_retries_once_and_preserves_non_server_settings(self):
        client=self.client(('office',));path=client.settings_path('office');store=KioskStore(path);store.data['custom']={'printer':'retained'};store.save()
        self.connect(client);call=client.call;dropped=[]
        def lose(path,data=None):
            result=call(path,data)
            if path=='computers/setup-register' and not dropped:dropped.append(True);raise SetupRequestError('Simulated lost reply')
            return result
        with patch.object(client,'call',side_effect=lose):
            with self.assertRaisesRegex(ValueError,'lost reply'):client.register('Office PC','office')
        request=client.pending['request'];result=client.register('Do not change pending choices','pos')
        self.assertEqual(result['computer']['name'],'Office PC');self.assertIsNone(client.pending)
        self.assertEqual(len(self.rows('retail_computer_setup_requests')),1);self.assertEqual(self.rows('retail_computer_setup_requests')[0][0],request)
        data=json.loads(path.read_text());self.assertEqual(data['custom'],{'printer':'retained'});self.assertEqual(data['device'],store.data['device']);self.assertEqual(data['server'],self.address)
    def test_registration_rolls_back_on_checkout_conflict_and_allows_correction(self):
        with server.connect() as c:c.execute("INSERT INTO retail_terminals VALUES('existing','Taken checkout',NULL,NULL,1,1,'')")
        client=self.client();self.connect(client)
        with self.assertRaisesRegex(ValueError,'unique name'):client.register('Taken checkout','pos','thrift-mart')
        self.assertIsNone(client.pending);self.assertEqual(self.rows('retail_computers'),[]);self.assertEqual(self.rows('retail_computer_apps'),[])
        result=client.register('Office computer','pos',terminal='existing')
        self.assertEqual(result['terminal']['id'],'existing');self.assertEqual(len(self.rows('retail_terminals')),1)
    def test_ambiguous_mac_does_not_merge_or_create_computers(self):
        for ident,folder in [('1'*32,'first'),('2'*32,'second')]:
            client=self.client(('office',),meta={**self.meta,'id':ident,'active_mac':'','macs':[]},folder=folder)
            self.connect(client);client.register(folder,'office');client.close()
        with server.connect() as c:c.execute('UPDATE retail_computers SET macs=?',(json.dumps([self.meta['active_mac']]),))
        before=self.rows('retail_computers');apps=self.rows('retail_computer_apps')
        client=self.client(('office',),meta={**self.meta,'id':'3'*32},folder='ambiguous')
        with self.assertRaisesRegex(ValueError,'more than one computer'):self.connect(client)
        self.assertEqual(self.rows('retail_computers'),before);self.assertEqual(self.rows('retail_computer_apps'),apps)
        self.assertEqual(self.rows('retail_computer_identity_aliases'),[])
    def test_local_save_failure_can_finish_the_same_registration(self):
        client=self.client(('office',));self.connect(client)
        with patch('installer_registration.write_json',side_effect=OSError('Disk unavailable')):
            with self.assertRaisesRegex(ValueError,'could not be saved'):client.register('Office PC','office')
        self.assertIsNotNone(client.pending);before=self.rows('retail_computers');receipts=self.rows('retail_computer_setup_requests')
        client.register('Office PC','office')
        self.assertEqual(self.rows('retail_computers'),before);self.assertEqual(self.rows('retail_computer_setup_requests'),receipts)
        self.assertEqual(json.loads(client.connection_path('office').read_text())['server'],self.address)
    def test_server_only_registration_and_business_data_are_preserved(self):
        with server.connect() as c:
            account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
            c.execute("INSERT INTO work_periods VALUES(901,?,100,NULL,'Office',NULL)",(account,));c.execute('INSERT INTO work_breaks VALUES(902,901,200,NULL)')
            c.execute("INSERT INTO jobs VALUES('fixture-reservation',8,?)",('{"type":"Delivery","notes":"Keep"}',));c.execute("INSERT INTO photos VALUES('fixture-reservation',0,?)",(b'keep-photo',))
            c.execute("INSERT INTO pos_products VALUES('fixture-item',?)",('{"name":"Fixture","price":1200,"active":true}',))
            c.execute("INSERT INTO pos_carts VALUES('fixture-cart',?,3,'paid',?,1000)",(account,'{"total":1200,"lines":[]}'));c.execute("INSERT INTO pos_sales VALUES(903,'fixture-cart',?,?)",(account,'{"total":1200,"lines":[]}'))
        names=['work_periods','work_breaks','jobs','photos','pos_products','pos_carts','pos_sales'];before={t:self.rows(t) for t in names}
        client=self.client(());self.connect(client);result=client.register('Server PC','server')
        self.assertTrue(result['computer']['registered']);self.assertEqual(result['computer']['role'],'server')
        self.assertEqual({t:self.rows(t) for t in names},before);self.assertEqual(len(self.rows('retail_computers')),1)
    def test_changing_protected_desk_server_requires_old_exit_passcode(self):
        client=self.client(('pos',));store=KioskStore(client.settings_path('pos'));store.data['server']='http://previous-server:8080';store.set_passcode('123456','123456')
        identity=store.data['device'];protection=copy.deepcopy(store.data['passcode']);self.connect(client)
        with self.assertRaisesRegex(ValueError,'exit passcode'):client.register('Checkout','pos',exit_code='000000')
        self.assertEqual(self.rows('retail_computers'),[])
        client.register('Checkout','pos',exit_code='123456');after=KioskStore(store.path).data
        self.assertEqual(after['device'],identity);self.assertEqual(after['passcode'],protection);self.assertEqual(after['server'],self.address)


class ActiveAdapterTests(unittest.TestCase):
    def test_uses_route_local_ip_to_select_adapter_instead_of_uuid_mac(self):
        connection=Mock();connection.__enter__=Mock(return_value=connection);connection.__exit__=Mock(return_value=False);connection.getsockname.return_value=('192.0.2.44',50000)
        with patch('computer_identity.platform.system',return_value='Windows'),patch('socket.create_connection',return_value=connection),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"mac":"02-AA-BB-CC-DD-11","name":"Ethernet 2"}')) as command:
            self.assertEqual(computer_identity.active_connection('https://ops.example'),{'active_mac':'02:AA:BB:CC:DD:11','active_adapter':'Ethernet 2','local_address':'192.0.2.44'})
            self.assertEqual(command.call_args.kwargs['env']['CY_SETUP_LOCAL_IP'],'192.0.2.44')
            self.assertIn('Get-NetAdapter -InterfaceIndex',command.call_args.args[0][-1])
    def test_loopback_and_unavailable_adapter_do_not_invent_a_mac(self):
        connection=Mock();connection.__enter__=Mock(return_value=connection);connection.__exit__=Mock(return_value=False);connection.getsockname.return_value=('127.0.0.1',50000)
        with patch('computer_identity.platform.system',return_value='Windows'),patch('socket.create_connection',return_value=connection),patch('subprocess.run') as command:
            self.assertNotIn('active_mac',computer_identity.active_connection('http://127.0.0.1:8080'));command.assert_not_called()


if __name__=='__main__':unittest.main()
