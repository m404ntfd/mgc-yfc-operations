"""Startup checks use real release validation and an isolated installer handoff."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import desktop_startup as startup
import pos_updater


def published(app='pos', target='1.20.0'):
    name=startup.APPS[app][1]+target+'.exe'
    return {'draft':False,'prerelease':False,'assets':[{'name':name,'digest':'sha256:'+'a'*64,
        'browser_download_url':'https://github.com/'+startup.REPO+'/releases/download/v0.60.0/'+name}]}


class StartupTests(unittest.TestCase):
    def check(self, release, app='pos', current='1.16.0'):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock()
        response.read.return_value=json.dumps(release).encode()
        with patch.object(startup,'urlopen',return_value=response):return startup.check_release(app,current)

    def test_each_application_and_semantic_version(self):
        for app in startup.APPS:
            with self.subTest(app=app):
                self.assertEqual(self.check(published(app,'1.20.0'),app,'1.9.0')['version'],'1.20.0')
                self.assertIsNone(self.check(published(app,'1.20.0'),app,'1.20.0'))
                self.assertIsNone(self.check(published(app,'1.20.0'),app,'2.0.0'))

    def test_untrusted_or_incomplete_release_never_offered(self):
        for change in ('draft','prerelease','digest','url','asset'):
            release=published()
            if change in ('draft','prerelease'):release[change]=True
            elif change=='digest':release['assets'][0]['digest']=''
            elif change=='url':release['assets'][0]['browser_download_url']='https://example.com/setup.exe'
            else:release['assets']=[]
            with self.subTest(change=change),self.assertRaises(ValueError):self.check(release)

    def test_offline_check_does_not_start_an_installer(self):
        with patch.object(startup,'urlopen',side_effect=OSError('Offline')),patch.object(startup.subprocess,'Popen') as launch:
            with self.assertRaises(OSError):startup.check_release('office','1.13.0')
            launch.assert_not_called()

    def test_staging_and_handoff_keep_settings_and_records(self):
        for app in ('pos','office','ops','remote'):
            with self.subTest(app=app),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);settings=root/'settings.json';settings.write_bytes(b'original device, passcode and server')
                db=root/'schedule.db';db.write_bytes(b'existing timecards reservations sales')
                exe=root/'application.exe';exe.write_bytes(b'original program')
                offer=self.check(published(app),app,'1.0.0');raw=b'verified public installer';digest=hashlib.sha256(raw).hexdigest()
                with patch.object(pos_updater,'verified_installer',return_value=(raw,digest)),patch.object(startup.sys,'executable',str(exe)),patch.object(startup.sys,'frozen',True,create=True),patch.object(startup.subprocess,'Popen') as launch:
                    path,checksum=startup.stage_installer(offer,settings)
                    launch.assert_not_called()
                    startup.launch_installer(offer,settings,path,checksum)
                    command=launch.call_args.args[0]
                    self.assertEqual(command[1],'--apply-pos-update')
                    manifest=json.loads(Path(command[2]).read_text())
                    self.assertEqual(manifest['exe'],str(exe.resolve()))
                    self.assertEqual(manifest.get('install_type'),'remote' if app=='remote' else None)
                self.assertEqual(settings.read_bytes(),b'original device, passcode and server')
                self.assertEqual(db.read_bytes(),b'existing timecards reservations sales')

    def test_checksum_failure_never_launches(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(pos_updater,'verified_installer',return_value=(b'wrong','a'*64)),patch.object(startup.subprocess,'Popen') as launch:
            offer=self.check(published())
            with self.assertRaisesRegex(ValueError,'verification'):startup.stage_installer(offer,Path(tmp)/'settings.json')
            launch.assert_not_called()

    def test_installed_server_admin_does_not_offer_its_own_release_again(self):
        from remote.remote_manager import VERSION as installed
        target=(Path(__file__).parent/'VERSION').read_text().strip()
        release={'assets':[{'name':'MGC-YFC-Operations-Setup-v'+target+'.exe'}]}
        with patch.object(startup,'urlopen') as fetch:
            fetch.return_value.__enter__.return_value.read.return_value=json.dumps(release).encode()
            self.assertIsNone(startup.check_release('remote',installed))

    def test_shared_server_cannot_use_desktop_handoff(self):
        with self.assertRaisesRegex(ValueError,'administrator'):
            startup.stage_installer({'app':'server'},Path('unused'))
        with tempfile.TemporaryDirectory() as tmp,patch.object(startup.sys,'executable',str(Path(tmp)/'admin.exe')):
            (Path(tmp)/'server.py').write_text('existing server')
            with self.assertRaisesRegex(ValueError,'combined server'):
                startup.stage_installer({'app':'remote'},Path(tmp)/'settings.json')

    def test_helper_uses_noninterrupting_installer_and_preserves_configuration(self):
        for kind,exit_code in ((None,0),('remote',0),(None,3010),(None,5)):
            with self.subTest(kind=kind,exit_code=exit_code),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);exe=root/'app.exe';exe.write_bytes(b'existing app');installer=root/'installer.exe';installer.write_bytes(b'verified installer')
                settings=root/'settings.json';settings.write_text('retained');db=root/'schedule.db';db.write_text('unchanged')
                meta={'exe':str(exe),'installer':str(installer),'sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'settings':str(settings),'pid':0,'version':'1.20.0'}
                if kind:meta['install_type']=kind
                manifest=root/'install.json';manifest.write_text(json.dumps(meta))
                kernel=Mock();kernel.OpenProcess.return_value=None
                with patch('ctypes.WinDLL',return_value=kernel,create=True),patch.object(pos_updater.subprocess,'run',return_value=Mock(returncode=exit_code)) as run,patch.object(pos_updater.subprocess,'Popen') as launch:
                    pos_updater.apply_update(manifest)
                    command=run.call_args.args[0]
                    self.assertIn('/NOCLOSEAPPLICATIONS',command);self.assertIn('/NORESTARTAPPLICATIONS',command)
                    self.assertEqual('/TYPE=remote' in command,kind=='remote')
                    launch.assert_called_once_with([str(exe)],creationflags=getattr(pos_updater.subprocess,'CREATE_NO_WINDOW',0))
                result=json.loads((root/'pos-update-result.json').read_text())
                self.assertEqual(result['ok'],exit_code==0)
                self.assertEqual(settings.read_text(),'retained');self.assertEqual(db.read_text(),'unchanged')
                self.assertEqual((root/'settings-backup.json').read_text(),'retained')

    def test_server_accept_waits_for_admin_and_uses_coordinated_flow(self):
        from remote.remote_manager import App
        panel=App.__new__(App);panel.startup_version=None;panel.client=None;panel.status=Mock();panel.busy=False;panel.root=Mock()
        panel.run=Mock();panel.request_startup_update('0.60.0');panel.run.assert_not_called()
        self.assertIn('administrator',panel.status.set.call_args.args[0])
        client=Mock();client.request.return_value={'available':True,'latest':'0.60.0'};panel.client=client
        panel.run=lambda work,done:done(work());panel.start_flow=Mock()
        panel.resume_startup_update()
        client.request.assert_called_once_with('update-check',{})
        panel.start_flow.assert_called_once_with(confirmed=True)
        self.assertIsNone(panel.startup_version)

    def test_server_changed_release_requires_new_consent(self):
        from remote.remote_manager import App
        panel=App.__new__(App);panel.startup_version='0.60.0';panel.client=Mock();panel.status=Mock();panel.busy=False
        panel.client.request.return_value={'available':True,'latest':'0.61.0'}
        panel.run=lambda work,done:done(work());panel.start_flow=Mock()
        panel.resume_startup_update();panel.start_flow.assert_not_called()


if __name__=='__main__':unittest.main()
