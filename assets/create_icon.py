"""Build the native YFC rings + computer server icon at tray sizes."""
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
rings=im.copy()
# Bold monitor silhouette, with a white edge for dark and light Windows trays.
# Keep the screen simple so it remains recognizable at 16 and 20 pixels.
d.rounded_rectangle((202,252,504,438),radius=18,fill='#263c50',outline='white',width=12)
d.rounded_rectangle((225,276,481,405),radius=6,fill='#8ed5ee')
d.polygon([(225,276),(481,276),(225,366)],fill='#c6edf7')
d.rectangle((326,438,380,472),fill='#263c50')
d.rounded_rectangle((280,465,427,497),radius=12,fill='#263c50',outline='white',width=7)
im.save(root/'dispatch.png')
im.save(root/'dispatch.ico',sizes=[(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(128,128),(256,256)])

# TV remote emoji-style handset in front of the YFC rings.
im=rings;d=ImageDraw.Draw(im)
d.rounded_rectangle((322,170,486,500),radius=45,fill='#273746',outline='white',width=9)
d.rounded_rectangle((341,186,467,480),radius=28,fill='#455767')
d.ellipse((392,201,427,236),fill='#ef4936')
d.rounded_rectangle((355,254,452,285),radius=6,fill='#9ce0ec')
d.ellipse((369,304,443,378),fill='#162b3b')
d.ellipse((392,327,420,355),fill='#b8c7d2')
for y in (398,425,452):
 for x in (355,390,425):d.rounded_rectangle((x,y,x+23,y+15),radius=4,fill='#dae4ea')
im.save(root/'remote.png')
im.save(root/'remote.ico',sizes=[(16,16),(20,20),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
