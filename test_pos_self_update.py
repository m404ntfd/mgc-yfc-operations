"""Run the real POS installer through the update helper against an isolated installation."""
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch,Mock
import pos_updater

def run():
 root=Path(__file__).parent;setup=root/'dist/MGC-YFC-POS-Setup-v1.1.0.exe'
 with tempfile.TemporaryDirectory() as tmp:
  target=Path(tmp)/'installed';target.mkdir();exe=target/'MGC YFC Point of Sale.exe';shutil.copy2(root/'dist/MGC YFC Point of Sale.exe',exe)
  settings=Path(tmp)/'settings.json';settings.write_text('{"device":"retain","passcode":{"hash":"retain-existing-hash"},"server":"http://unchanged"}')
  data=target/'data';data.mkdir();(data/'schedule.db').write_bytes(b'preserve-operational-data');before=settings.read_bytes()
  manifest=Path(tmp)/'install.json';manifest.write_text(json.dumps({'installer':str(setup),'sha256':hashlib.sha256(setup.read_bytes()).hexdigest(),'exe':str(exe),'pid':0,'version':'1.1.0','settings':str(settings)}))
  kernel=Mock();kernel.OpenProcess.return_value=None
  original_popen=subprocess.Popen;restarted=[]
  def launch(command,*args,**kwargs):
   if command==[str(exe)]:restarted.append(command);return Mock()
   return original_popen(command,*args,**kwargs)
  with patch('ctypes.WinDLL',return_value=kernel),patch.object(pos_updater.subprocess,'Popen',side_effect=launch):
   pos_updater.apply_update(manifest)
  assert restarted==[[str(exe)]]
  result=json.loads((settings.parent/'pos-update-result.json').read_text());assert result['ok'],result
  assert settings.read_bytes()==before;assert (Path(tmp)/'settings-backup.json').read_bytes()==before
  assert (data/'schedule.db').read_bytes()==b'preserve-operational-data'
  process=subprocess.run([str(exe),'--smoke-test'],timeout=60);assert process.returncode==0
 print('PASS real POS self-update installer, retained device settings/data and installed runtime startup')
if __name__=='__main__':run()
