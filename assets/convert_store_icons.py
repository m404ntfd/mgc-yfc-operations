from PIL import Image
from pathlib import Path
import io,base64,json
root=Path(__file__).parent
for name in ('desk','office','store-ops'):
 Image.open(root/(name+'.png')).save(root/(name+'.ico'),sizes=[(n,n) for n in (16,20,24,32,48,64,128,256)])
web=Image.open(root/'store-ops.png');assets={}
for n in (180,192,512):
 buf=io.BytesIO();web.resize((n,n),Image.Resampling.LANCZOS).save(buf,format='PNG');assets[str(n)]=base64.b64encode(buf.getvalue()).decode()
assets['ico']=base64.b64encode((root/'store-ops.ico').read_bytes()).decode()
(root/'home-icons.json').write_text(json.dumps(assets),encoding='ascii')
