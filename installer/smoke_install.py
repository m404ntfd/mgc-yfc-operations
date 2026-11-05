"""Verify an installed server runs with bundled Python and the manager connects."""
import os,sys,subprocess,tempfile,socket,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'remote'))
from client import Client
root=Path(sys.argv[1])
with tempfile.TemporaryDirectory() as data:
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 p=subprocess.Popen([str(root/'runtime/python.exe'),str(root/'launcher.py')],cwd=root,env={**os.environ,'DISPATCH_DATA':data,'DISPATCH_PORT':str(port)})
 try:
  c=Client(f'127.0.0.1:{port}')
  for i in range(60):
   try:c.probe();break
   except Exception:time.sleep(.25)
  else:raise AssertionError('Installed server did not start')
  c.request('setup',{'name':'SmokeAdmin','password':'TestPasswordOnly'})
  assert c.login('SmokeAdmin','TestPasswordOnly')['name']=='MGC YFC Operations Server'
  c.request('admin/restart',{})
  time.sleep(2)
  assert c.probe()['application']=='thrift-mart-dispatch'
  print('Bundled server, administrator connection and restart passed.')
 finally:
  subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
  p.wait()

# Test the installed GUI host, real Windows tray, hide/show behavior, and safe exit.
with tempfile.TemporaryDirectory() as data:
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 p=subprocess.Popen([str(root/'MGC YFC Operations Server.exe'),'--smoke-test'],cwd=root,env={**os.environ,'DISPATCH_DATA':data,'DISPATCH_PORT':str(port)})
 try:
  assert p.wait(timeout=75)==0, 'Tray host smoke test failed'
  c=Client(f'127.0.0.1:{port}')
  try:c.probe()
  except Exception:pass
  else:raise AssertionError('Tray Exit left the server running')
  print('YFC-icon GUI, tray minimize/restore, continued access and graceful exit passed.')
 finally:
  if p.poll() is None:
   subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait()

# Use the classic console host so Windows Terminal tabs do not own the window.
with tempfile.TemporaryDirectory() as data:
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 command=[str(Path(os.environ['SystemRoot'])/'System32/conhost.exe'),str(root/'MGC YFC Operations Server Console.exe'),'--console','--smoke-test']
 p=subprocess.Popen(command,cwd=root,env={**os.environ,'DISPATCH_DATA':data,'DISPATCH_PORT':str(port)})
 try:
  assert p.wait(timeout=75)==0,'Console tray smoke test failed'
  # Log proves the child actually ran; conhost must not silently fail to start it.
  assert (Path(data)/'server-console.log').exists(),'Console did not start server'
  assert json.loads((Path(data)/'tray-smoke.json').read_text())=={'passed':True,'console':True},'Console assertions were not completed'
  c=Client(f'127.0.0.1:{port}')
  try:c.probe()
  except Exception:pass
  else:raise AssertionError('Console tray Exit left server running')
  print('Command window YFC icons, actual minimize-to-tray, restore and graceful exit passed.')
 finally:
  if p.poll() is None:
   subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait()
