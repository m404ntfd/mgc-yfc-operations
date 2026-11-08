import ast,base64,io,shutil,tempfile,unittest,zipfile
from pathlib import Path
from prepare_web_assets import prepare
import updater
class WebAssetTests(unittest.TestCase):
 def test_legacy_update_contains_offline_gif_and_shortcut_icons(self):
  source=Path(__file__).parent
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'assets').mkdir()
   for name in updater.FILES:
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
   for path in [source/'assets/home-icons.json',*sorted((source/'assets').glob('plug-*.b64'))]:shutil.copyfile(path,root/'assets'/path.name)
   for name in ('pos.html','pos.js','pos.css','customer-office.js','customer-display.html','customer-display.js','customer-display.css','report-center.js','office-expansion.js'):shutil.copyfile(source/'static'/name,root/'static'/name)
   shutil.copyfile(source/'customer_services.py',root/'customer_services.py')
   shutil.copyfile(source/'retail_reports.py',root/'retail_reports.py')
   prepare(root)
   module=ast.parse((root/'server.py').read_text(encoding='utf-8'))
   assignment=next(node for node in module.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='WEB_ASSETS' for target in node.targets))
   assets=ast.literal_eval(assignment.value)
   self.assertEqual(assets['gif'],''.join(part.read_text() for part in sorted((source/'assets').glob('plug-*.b64'))))
   for size in ('180','192','512'):self.assertTrue(base64.b64decode(assets[size]).startswith(b'\x89PNG'))
   self.assertTrue(base64.b64decode(assets['ico']).startswith(b'\x00\x00\x01\x00'))
   self.assertEqual({k:assets[k] for k in ('180','192','512','ico')},__import__('json').loads((source/'assets/home-icons.json').read_text()))
   pos=next(node for node in module.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='POS_ASSETS' for target in node.targets))
   self.assertEqual(set(ast.literal_eval(pos.value)),{'pos.html','pos.js','pos.css','customer-display.html','customer-display.js','customer-display.css'})
   output=io.BytesIO()
   with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    for name in updater.FILES:archive.write(root/name,name)
   self.assertLess(len(output.getvalue()),updater.LIMIT)
   updater.inspect(output.getvalue(),updater.current())
if __name__=='__main__':unittest.main()
