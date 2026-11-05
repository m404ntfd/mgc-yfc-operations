"""Build the native YFC rings + office-building application icon at tray sizes."""
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).parent
im=Image.new('RGBA',(512,512));d=ImageDraw.Draw(im)
red='#ea4520'
# Linked YFC circles, laid out top / lower-left / lower-right.
for box in [(36,172,272,408),(164,282,372,490),(132,24,388,280)]:
 d.ellipse(box,outline='white',width=50)
 inner=tuple(v+6 if i<2 else v-6 for i,v in enumerate(box))
 d.ellipse(inner,outline=red,width=34)
# The office-building glyph is in front of the rings on the right, like 🏢.
d.rounded_rectangle((278,216,494,492),radius=9,fill='#334c60',outline='white',width=8)
d.rectangle((290,228,480,480),fill='#b8c7d2')
d.rectangle((430,228,480,480),fill='#8fa5b5')
d.rectangle((305,204,464,230),fill='#667e90')
for y in (248,295,342,389):
 for x in (306,350,394,438):
  d.rectangle((x,y,x+25,y+29),fill='#286584')
  d.line((x+3,y+3,x+21,y+3),fill='#9ed9ef',width=3)
d.rectangle((365,437,411,480),fill='#334c60')
d.line((388,439,388,480),fill='#b8c7d2',width=3)
d.rounded_rectangle((270,480,501,501),radius=5,fill='#536e82')
im.save(root/'dispatch.png')
im.save(root/'dispatch.ico',sizes=[(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(128,128),(256,256)])
