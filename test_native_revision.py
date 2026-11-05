import tempfile,unittest
from pathlib import Path
from manager_cleanup import remove_standalone_manager

class CleanupTests(unittest.TestCase):
 def test_cleanup_keeps_server_data_and_uninstaller(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);install=root/'install';desktop=root/'desktop'
   install.mkdir();desktop.mkdir();(install/'data').mkdir()
   keep=['MGC YFC Operations Server.exe','unins000.exe','server.py','data/schedule.db']
   for name in keep:(install/name).write_bytes(b'preserve')
   for name in ['MGC YFC Operations Remote Manager.exe','Thrift Mart Dispatch Remote Manager.exe','Remote-Manager-README.txt']:(install/name).write_bytes(b'old manager')
   (desktop/'MGC YFC Operations Remote Manager.lnk').write_bytes(b'old')
   (desktop/'MGC YFC Operations Server.lnk').write_bytes(b'preserve')
   remove_standalone_manager(install,[desktop])
   for name in keep:self.assertEqual((install/name).read_bytes(),b'preserve')
   self.assertFalse((install/'MGC YFC Operations Remote Manager.exe').exists())
   self.assertFalse((desktop/'MGC YFC Operations Remote Manager.lnk').exists())
   self.assertEqual((desktop/'MGC YFC Operations Server.lnk').read_bytes(),b'preserve')
   remove_standalone_manager(install,[desktop])

if __name__=='__main__':unittest.main()
