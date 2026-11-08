"""Package the approved icon artwork for Windows and web use."""
import base64, io, json
from pathlib import Path
from PIL import Image
root=Path(__file__).parent
sizes=[(n,n) for n in (16,20,24,32,40,48,64,128,256)]
def square(name):
    original=Image.open(root/'approved-icons'/name).convert('RGBA')
    canvas=Image.new('RGBA',(max(original.size),)*2)
    canvas.alpha_composite(original,((canvas.width-original.width)//2,(canvas.height-original.height)//2))
    return canvas
for source,target in [('server.png','dispatch'),('admin.png','remote')]:
    icon=square(source).resize((512,512),Image.Resampling.LANCZOS)
    icon.save(root/(target+'.png'))
    icon.save(root/(target+'.ico'),sizes=sizes)
web=square('operations.png')
assets={}
for n in (180,192,512):
    out=io.BytesIO();web.resize((n,n),Image.Resampling.LANCZOS).save(out,format='PNG')
    assets[str(n)]=base64.b64encode(out.getvalue()).decode('ascii')
out=io.BytesIO();web.resize((512,512),Image.Resampling.LANCZOS).save(out,format='ICO',sizes=sizes)
assets['ico']=base64.b64encode(out.getvalue()).decode('ascii')
(root/'home-icons.json').write_text(json.dumps(assets,separators=(',',':')),encoding='ascii')
