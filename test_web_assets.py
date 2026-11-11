import ast,base64,io,shutil,tempfile,unittest,zipfile
from pathlib import Path
from prepare_web_assets import prepare
import updater
from release_payload import release_bytes
class WebAssetTests(unittest.TestCase):
 def test_legacy_update_contains_offline_gif_and_shortcut_icons(self):
  source=Path(__file__).parent
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'assets').mkdir()
   for name in updater.FILES:
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
   for path in [source/'assets/home-icons.json',source/'assets/hr-reference-forms.json',source/'assets/hr-source-forms.json',*sorted((source/'assets').glob('plug-*.b64'))]:shutil.copyfile(path,root/'assets'/path.name)
   for name in ('pos.html','pos.js','pos.css','customer-office.js','customer-display.html','customer-display.js','customer-display.css','report-center.js','office-expansion.js','thrift-retail.js','retail-stores.js','fulfillment-print.js','pickup-followup.js','delivery-workspace.js','office-security.js','report-document.css','glass-theme.css','terminal-registration.js','terminal-registration.css','catalog-editor.js','cash-advances.js','office-updates.js','office-search.js','office-navigation.js','office-navigation.css','hr-browser.js','hr.html','hr.js','hr.css'):shutil.copyfile(source/'static'/name,root/'static'/name)
   shutil.copyfile(source/'customer_services.py',root/'customer_services.py')
   shutil.copyfile(source/'retail_reports.py',root/'retail_reports.py')
   shutil.copyfile(source/'computer_registry.py',root/'computer_registry.py')
   shutil.copyfile(source/'thrift_retail.py',root/'thrift_retail.py')
   for name in ('retail_stores.py','retail_fulfillment.py','catalog_setup.py','hr_onboarding.py','hr_browser.py'):shutil.copyfile(source/name,root/name)
   prepare(root)
   module=ast.parse((root/'server.py').read_text(encoding='utf-8'))
   assignment=next(node for node in module.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='WEB_ASSETS' for target in node.targets))
   assets=ast.literal_eval(assignment.value)
   self.assertEqual(assets['gif'],''.join(part.read_text() for part in sorted((source/'assets').glob('plug-*.b64'))))
   for size in ('180','192','512'):self.assertTrue(base64.b64decode(assets[size]).startswith(b'\x89PNG'))
   self.assertTrue(base64.b64decode(assets['ico']).startswith(b'\x00\x00\x01\x00'))
   self.assertEqual({k:assets[k] for k in ('180','192','512','ico')},__import__('json').loads((source/'assets/home-icons.json').read_text()))
   pos=next(node for node in module.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='POS_ASSETS' for target in node.targets))
   self.assertEqual(set(ast.literal_eval(pos.value)),{'pos.html','pos.js','pos.css','customer-display.html','customer-display.js','customer-display.css','hr.html','hr.js','hr.css'})
   self.assertIn('function thriftDesk()',ast.literal_eval(pos.value)['pos.js'])
   # Decode only the generated asset assignment: do not execute the server.
   packed_source=release_bytes(root,'server.py')
   packed_module=ast.parse(packed_source)
   packed_pos=next(node for node in packed_module.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='POS_ASSETS' for target in node.targets))
   import gzip,json
   decoded=eval(compile(ast.Expression(packed_pos.value),'<packaged assets>','eval'),{'json':json,'base64':base64,'_web_asset_gzip':gzip})
   self.assertEqual(decoded,ast.literal_eval(pos.value))
   self.assertIn((source/'static/office-navigation.js').read_text(encoding='utf-8'),decoded['pos.js'])
   self.assertIn((source/'static/office-navigation.css').read_text(encoding='utf-8'),decoded['pos.css'])
   self.assertEqual(release_bytes(root,'server.py'),packed_source)

   self.assertIn('nativeTerminalSetup',ast.literal_eval(pos.value)['pos.js'])
   self.assertIn((source/'static/cash-advances.js').read_text(encoding='utf-8'),ast.literal_eval(pos.value)['pos.js'])
   self.assertIn((source/'static/office-updates.js').read_text(encoding='utf-8'),ast.literal_eval(pos.value)['pos.js'])
   self.assertIn((source/'static/office-search.js').read_text(encoding='utf-8'),ast.literal_eval(pos.value)['pos.js'])
   self.assertIn('nativeTerminalSetup',(root/'static/app.js').read_text(encoding='utf-8'))
   self.assertIn('.computerSelectLabel input[type=checkbox]',ast.literal_eval(pos.value)['pos.css'])
   self.assertTrue(any(isinstance(node,ast.FunctionDef) and node.name=='thrift_init' for node in module.body))
   output=io.BytesIO()
   with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    for name in updater.FILES:archive.writestr(name,release_bytes(root,name))
   self.assertLess(len(output.getvalue()),updater.LIMIT)
   contents=updater.inspect(output.getvalue(),updater.current())
   import server
   for name in ('static/index.html','static/app.js','static/style.css'):
    packed=root/('packed-'+Path(name).name);packed.write_bytes(contents[name]);self.assertEqual(server.read_static_asset(packed),(root/name).read_bytes())
if __name__=='__main__':unittest.main()
