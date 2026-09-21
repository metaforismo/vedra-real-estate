"""Isolate prominent sale ribbons before OCR; colour alone never proves a sale."""
import math


def ribbon_crop(image):
    from PIL import Image, ImageOps
    im=image.copy();im.thumbnail((900,900))
    small=im.copy();small.thumbnail((240,240))
    pixels=small.load()
    points={(x,y) for y in range(small.height) for x in range(small.width)
            if (lambda r,g,b:r>130 and r>g*1.6 and r>b*1.6)(*pixels[x,y])}
    largest=[]
    while points:
        queue=[points.pop()];component=[]
        while queue:
            x,y=queue.pop();component.append((x,y))
            for neighbour in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if neighbour in points:points.remove(neighbour);queue.append(neighbour)
        if len(component)>len(largest):largest=component
    if len(largest)<small.width*small.height*.04:return None
    mx=sum(x for x,y in largest)/len(largest);my=sum(y for x,y in largest)/len(largest)
    xx=sum((x-mx)**2 for x,y in largest);yy=sum((y-my)**2 for x,y in largest)
    xy=sum((x-mx)*(y-my) for x,y in largest)
    angle=math.degrees(.5*math.atan2(2*xy,xx-yy))
    mask=Image.new('L',small.size)
    for point in largest:mask.putpixel(point,255)
    mask=mask.resize(im.size).rotate(angle,expand=True)
    box=mask.getbbox()
    crop=im.rotate(angle,expand=True,fillcolor='white').crop(box)
    if not 2.5<crop.width/crop.height<12:return None
    crop.thumbnail((1000,130))
    # Discard rounded corners and invert white lettering for the single-line reader.
    crop=crop.crop((int(crop.width*.06),int(crop.height*.12),int(crop.width*.94),int(crop.height*.88)))
    crop=ImageOps.expand(crop.convert('L').point(lambda v:0 if v>210 else 255),border=15,fill=255)
    return crop,round(angle,2)
