"""Compile the real suite wrapper around harmless fixtures; exercise failure paths.

No production installer is run, no application directory is installed, and the
fixtures do not register uninstall entries or create shortcuts.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile


def run():
    root = Path(__file__).resolve().parents[1]
    compiler = Path(os.environ.get('INNO_COMPILER', r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'))
    if not compiler.is_file():
        raise RuntimeError('Set INNO_COMPILER to the Inno Setup compiler.')
    version = (root/'VERSION').read_text().strip()
    source = (root/'installer/suite.iss').read_text(encoding='utf-8')
    files = re.findall(r'Source: "\.\.\\dist\\([^"]+)"', source)
    files = [name.replace('{#AppVersion}', version) for name in files]
    assert len(files) == 4
    roles = ['server', 'office', 'desk', 'ops']
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    def compile_file(script):
        result = subprocess.run([str(compiler), '/Q', f'/DAppVersion={version}', str(script)],
                                capture_output=True, text=True, timeout=90, creationflags=flags)
        assert result.returncode == 0, result.stdout + result.stderr

    with tempfile.TemporaryDirectory(prefix='retail-suite-error-check-') as temp:
        base = Path(temp)
        (base/'installer').mkdir()
        (base/'dist').mkdir()
        sentinels = []
        for name in ('data/schedule.db', 'data/sales.json', 'client/settings.json'):
            p = base/'existing'/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'preserve-existing-test-data')
            sentinels.append((p, hashlib.sha256(p.read_bytes()).hexdigest()))
        for role, filename in zip(roles, files):
            fixture = base/'installer'/f'{role}.iss'
            fixture.write_text(f'''[Setup]
AppName=Installer diagnostics fixture {role}
AppVersion=1.0
DefaultDirName={{tmp}}\\unused
PrivilegesRequired=lowest
CreateAppDir=no
Uninstallable=no
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=yes
OutputDir=..\\dist
OutputBaseFilename={Path(filename).stem}
[Code]
function GetCustomSetupExitCode: Integer;
begin
 SaveStringToFile(GetEnv('CY_TEST_MARKER'), '{role}' + #13#10, True);
 if GetEnv('CY_TEST_FAIL_COMPONENT') = '{role}' then
  Result := StrToIntDef(GetEnv('CY_TEST_FAIL_CODE'), 0)
 else Result := 0;
end;
''', encoding='utf-8')
            compile_file(fixture)
        wrapper = base/'installer/suite.iss'
        wrapper.write_text(source, encoding='utf-8')
        compile_file(wrapper)
        suite = base/'dist'/f'CoastYouth-Retail-Computer-Setup-v{version}.exe'

        def invoke(label, role='', code=0, expected=('server', 'office', 'desk', 'ops'), failed=False):
            marker = base/f'{label}-started.txt'
            logs = base/f'{label} logs'
            result = subprocess.run([str(suite), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                     '/TYPE=custom', '/COMPONENTS=server,office,pos,ops',
                                     '/SETUPLOGDIR='+str(logs), '/LOG='+str(base/f'{label}-parent.log')],
                                    env={**os.environ, 'CY_TEST_MARKER':str(marker),
                                         'CY_TEST_FAIL_COMPONENT':role, 'CY_TEST_FAIL_CODE':str(code)},
                                    timeout=90, creationflags=flags)
            started = marker.read_text().splitlines() if marker.exists() else []
            assert started == list(expected), (label, started)
            assert (result.returncode != 0) == failed, (label, result.returncode)
            summary = (logs/'components.txt').read_bytes().decode('utf-8-sig')
            for p, digest in sentinels:
                assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, (label, p)
            if failed:
                assert 'Remaining applications were not started.' in summary
                assert 'Keep the existing application data folders.' in summary
            return logs, summary

        invoke('success')
        for code in (2, 5, 7):
            logs, summary = invoke(f'office-exit-{code}', 'office', code,
                                   expected=('server', 'office'), failed=True)
            assert 'CoastYouth Retail OFFICE did not finish.' in summary
            assert f'Exit code {code}:' in summary
            assert 'Completed before this stop: Operations server and controller.' in summary
            assert (logs/Path(files[1]).with_suffix('.log')).is_file()
        _, summary = invoke('server-failure', 'server', 7, expected=('server',), failed=True)
        assert 'Completed before this stop: None.' in summary
        invoke('restart-required', 'office', 3010)

        # A missing child reproduces Windows refusing to launch an installer.
        missing = source.replace("'CoastYouth-Retail-OFFICE-Setup-v", "'Missing-OFFICE-Setup-v")
        assert missing != source
        wrapper.write_text(missing, encoding='utf-8')
        compile_file(wrapper)
        _, summary = invoke('launch-failure', expected=('server',), failed=True)
        assert 'Windows could not start the installer. Error ' in summary
        assert 'CoastYouth Retail OFFICE did not finish.' in summary
    print('PASS suite success, cancellation, fatal exit, launch failure, stop order, retained logs and data sentinels')


if __name__ == '__main__':
    run()
