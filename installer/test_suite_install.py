"""Exercise the real role-selection installer in isolated directories on Windows."""
import hashlib,os,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
setup=root/'dist'/('CoastYouth-Retail-Computer-Setup-v'+(root/'VERSION').read_text().strip()+'.exe')
with tempfile.TemporaryDirectory(prefix='retail-suite-') as folder:
 base=Path(folder);server=base/'server';office=base/'office';desk=base/'desk';ops=base/'ops';appdata=base/'appdata';appdata.mkdir()
 sentinels=[]
 for path,body in [(server/'data/schedule.db',b'existing-timecards-and-reservations'),(server/'data/backup-settings.json',b'preserve-backup-settings'),(appdata/'MGCYFCPOS/settings.json',b'{"device":"existing-device","server":"http://existing-server","passcode":{"hash":"keep"}}'),(appdata/'CoastYouthRetailOffice/settings.json',b'{"server":"http://existing-server"}')]:
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body);sentinels.append((path,hashlib.sha256(body).hexdigest()))
 env={**os.environ,'APPDATA':str(appdata)}
 for selection in ('pos','office','server','custom'):
  args=[str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/TYPE='+selection,'/SERVERDIR='+str(server),'/OFFICEDIR='+str(office),'/POSDIR='+str(desk),'/OPSDIR='+str(ops)]
  if selection=='custom':args.append('/COMPONENTS=server,office,pos,ops')
  result=subprocess.run(args,env=env,timeout=240)
  assert result.returncode in (0,3010),(selection,result.returncode)
  for path,digest in sentinels:assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,(selection,path)
 for path in (server/'MGC YFC Operations Server.exe',office/'CoastYouth Retail OFFICE.exe',desk/'MGC YFC Point of Sale.exe',ops/'CoastYouth Retail STORE OPS.exe'):assert path.is_file(),path
 for exe in (office/'CoastYouth Retail OFFICE.exe',desk/'MGC YFC Point of Sale.exe',ops/'CoastYouth Retail STORE OPS.exe'):
  assert subprocess.run([str(exe),'--smoke-test'],env=env,timeout=60).returncode==0
print('PASS Server/OFFICE/POS/Custom suite installation and repeat installation preserve server data and both client settings')
