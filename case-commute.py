"""Only the commute representative. Existing Vox easing and local render helpers reused."""
from pathlib import Path
import math,sys,subprocess
from PIL import Image,ImageDraw,ImageFilter
from PIL import ImageFont
import os
from functools import lru_cache
from verify_assets import main as check_assets
P=Path(__file__).resolve().parent; A=P/'素材'; O=P/'预览'
if __name__=='__main__':
    if check_assets([str(P/'ASSETS.json'),'--group','commute']): raise SystemExit(1)
O.mkdir(exist_ok=True)
W,H,FPS=1280,720,25; L=Image.Resampling.LANCZOS
def ease(e,p):
    p=max(0,min(p,1)); return p*p*(3-2*p) if e=='smooth' else 1-(1-p)**2
@lru_cache(None)
def font(n,bold=False):
    candidates=[os.environ.get('VOX_FONT',''), 'C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for f in candidates:
        if f and Path(f).is_file(): return ImageFont.truetype(f,n)
    raise RuntimeError('Set VOX_FONT to an installed Chinese font file.')
def put(im,obj,x,y,w=None,a=1):
    if w is not None: obj=obj.resize((max(1,round(w)),max(1,round(obj.height*w/obj.width))),L)
    if a<1:
        obj=obj.copy(); obj.putalpha(obj.getchannel('A').point(lambda v: round(v*a)))
    im.alpha_composite(obj,(round(x),round(y)))
def subtitle(im,text):
    d=ImageDraw.Draw(im); d.text((W/2,668),text,font=font(30,True),anchor='mt',fill='white',stroke_width=3,stroke_fill='#242029')


START,END=0,4.32
main=Image.open(A/'通勤城市主体-v4.png').convert('RGBA')
far=Image.open(A/'通勤远楼-v4.png').convert('RGBA').resize((2700,900),L)
parts=Image.open(A/'通勤车辆街沿-v4.png').convert('RGBA')
red=parts.crop((12,83,765,405));green=parts.crop((790,83,1536,405))
front=parts.crop((0,432,1536,1000))
legs=[[(225,606),(445,630),(655,631),(850,611)],[(850,611),(1080,624),(1290,631),(1450,619)]]

def camera(t):
    q=ease('smooth',(t-1.70)/1.38)
    return .80+.35*q,1200*q,100-130*q

def position(path,p):
    lengths=[math.dist(a,b) for a,b in zip(path,path[1:])];remaining=sum(lengths)*max(0,min(p,1))
    for i,(a,b,d) in enumerate(zip(path,path[1:],lengths)):
        if remaining<=d or i==len(lengths)-1:
            f=min(remaining/d,1);return (a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
        remaining-=d

def route(draw,path,p,col,s,dx,yoff):
    if p<=0:return
    points=[position(path,i/80*p) for i in range(81)]
    points=[(x*s-dx,y*s+yoff) for x,y in points]
    draw.line(points,fill='#f5e9cf',width=max(3,round(10*s)),joint='curve')
    draw.line(points,fill=col,width=max(2,round(5*s)),joint='curve')

def label(im,text,x,y,size=25):
    d=ImageDraw.Draw(im);d.text((x,y),text,font=font(size,True),fill='#223d36',stroke_width=3,stroke_fill='#f4ecd9')

def frame(t,captions=True):
    s,dx,yoff=camera(t)
    im=Image.new('RGBA',(W,H),'#d9ded6')
    put(im,far,-dx*.25,-155)
    # Continuous paper ground under the cutout, not a duplicated building strip.
    ground=Image.new('RGBA',(W,H));gd=ImageDraw.Draw(ground)
    gd.polygon([(0,530),(340,506),(720,535),(1040,502),(1280,540),(1280,720),(0,720)],fill='#c9c5b9')
    put(im,ground,0,0)
    put(im,main,-dx,yoff,main.width*s)
    d=ImageDraw.Draw(im)
    ps=[ease('out',(t-.12)/.83),ease('out',(t-.85)/.86)]
    for j,(path,p,col,bus) in enumerate(zip(legs,ps,['#aa4935','#285b50'],[red,green])):
        route(d,path,p,col,s,dx,yoff)
        if p>0:
            x,y=position(path,p);bw=164*s
            put(im,bus,x*s-dx-bw*.75,y*s+yoff-bw*bus.height/bus.width,bw)
    # The station is a single shared node. Both route endpoints move with buildings.
    x,y=legs[0][-1];sx,sy=x*s-dx,y*s+yoff
    d=ImageDraw.Draw(im);d.ellipse((sx-6,sy-6,sx+6,sy+6),fill='#f3e7d3',outline='#3b5f52',width=2)
    label(im,'合租',110*s-dx,320*s+yoff)
    label(im,'换乘',807*s-dx,500*s+yoff,23)
    label(im,'公司',1392*s-dx,345*s+yoff,26)
    # The option and its entire link are only visible after the pan reveals the area.
    if t>=2.77:
        a=ease('smooth',(t-2.77)/.18)
        near=Image.new('RGBA',(W,H));nd=ImageDraw.Draw(near)
        pts=[(1540,571),(1745,569),(1827,559)]
        for x in range(1540,1827,25):
            yy=571-(x-1540)*12/287
            nd.line([(x*s-dx,yy*s+yoff),((x+11)*s-dx,(yy-.5)*s+yoff)],fill='#f5e9cf',width=5)
        label(near,'可选择 · 单间',1810*s-dx,335*s+yoff,26)
        put(im,near,0,0,a=a)
    # A foreground curb crosses faster; a second piece stays at the reveal edge.
    fw=1770;fx=-130-dx*1.22;fy=540
    put(im,front,fx,fy,fw)
    if dx>600:put(im,front,1810-dx*1.22,588,1260)
    label(im,'通勤示意',30,28,22)
    if captions:subtitle(im,'原来合租要转两趟车' if t<2.40 else '现在可以换到公司附近的单间')
    return im.convert('RGB')

def render():
    out=O/'通勤视差-迁移验证.mp4'
    if out.exists(): raise FileExistsError(out)
    cmd=['ffmpeg','-v','error','-n','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','pipe:0','-ss',str(START),'-t',str(END-START),'-i',str(P/'input/original.wav'),'-map','0:v','-map','1:a','-c:v','libx264','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-t',str(END-START),'-movflags','+faststart',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(round((END-START)*FPS)):proc.stdin.write(frame(i/FPS).tobytes())
    finally:proc.stdin.close()
    assert proc.wait()==0;print(out)

if __name__=='__main__':
    assert legs[0][-1]==legs[1][0]
    assert position(legs[0],0)==legs[0][0] and position(legs[1],1)==legs[1][-1]
    for t in [0,.5,1,1.65,2,2.4,2.8,3.2,3.8,4.28]:frame(t).save(O/f'通勤v4静态-{t:.2f}.jpg',quality=96)
    if '--render' in sys.argv:render()
