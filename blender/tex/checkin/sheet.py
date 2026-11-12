import sys
from PIL import Image
fs=sys.argv[2:]; ims=[Image.open(f).convert("RGB") for f in fs]
h=int(sys.argv[1]); ims=[i.resize((int(i.width*h/i.height),h)) for i in ims]
S=Image.new("RGB",(sum(i.width for i in ims),h)); x=0
for i in ims: S.paste(i,(x,0)); x+=i.width
S.save(r"D:\gimli3d\render\checkin_final\sheet.jpg",quality=88)
