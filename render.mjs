import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {spawn,execFileSync} from 'node:child_process';
import {once} from 'node:events';

const opts={};
for(let i=2;i<process.argv.length;i+=2){
  if(!process.argv[i].startsWith('--')||process.argv[i+1]===undefined) throw Error('Use --name value pairs.');
  opts[process.argv[i].slice(2)]=process.argv[i+1];
}
for(const key of ['page','out']) if(!opts[key]) throw Error(`Missing --${key}`);
const pageFile=path.resolve(opts.page), audioFile=opts.audio?path.resolve(opts.audio):null, out=path.resolve(opts.out);
if(fs.existsSync(out)) throw Error('Output already exists; use a new filename.');
for(const f of [pageFile,audioFile].filter(Boolean)) if(!fs.existsSync(f)) throw Error(`Missing file: ${f}`);
if(opts['asset-group']&&!opts.assets) throw Error('--asset-group requires --assets.');
if(opts.assets){
  const checker=path.join(path.dirname(fileURLToPath(import.meta.url)),'verify_assets.py');
  const args=['-X','utf8',checker,path.resolve(opts.assets)];
  if(opts['asset-group'])args.push('--group',opts['asset-group']);
  execFileSync(process.env.VOX_PYTHON||'python',args,{stdio:'inherit'});
}
const root=path.dirname(pageFile), width=Number(opts.width||1280), height=width*9/16, fps=Number(opts.fps||30);
if(!Number.isInteger(width)||!Number.isInteger(height)||width%2||height%2||fps<=0||!Number.isFinite(fps)) throw Error('Use even 16:9 dimensions and positive fps.');
const candidates=[process.env.CHROME_PATH,'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','/usr/bin/google-chrome','/usr/bin/chromium','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
const executablePath=candidates.find(f=>f&&fs.existsSync(f));
if(!executablePath) throw Error('Set CHROME_PATH to your Chrome/Chromium executable.');
// The optional module path permits testing against an existing installation without changing it.
const mod=process.env.VOX_PUPPETEER_MODULE;
const {default:puppeteer}=await import(mod?pathToFileURL(path.resolve(mod)).href:'puppeteer-core');
const server=http.createServer((req,res)=>{
  try{
    const p=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
    if(p!==root&&!p.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
    if(!fs.existsSync(p)||!fs.statSync(p).isFile()){res.writeHead(404);return res.end();}
    res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.png':'image/png'})[path.extname(p)]||'application/octet-stream');
    fs.createReadStream(p).pipe(res);
  }catch{res.writeHead(400);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser,proc,completion;
try{
  browser=await puppeteer.launch({executablePath,headless:true,args:['--disable-background-timer-throttling']});
  const page=await browser.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.setViewport({width,height,deviceScaleFactor:1});
  await page.goto(`http://127.0.0.1:${server.address().port}/${encodeURIComponent(path.basename(pageFile))}`,{waitUntil:'networkidle0'});
  await page.waitForFunction('window.READY===true',{timeout:30000});
  await page.evaluate(()=>document.fonts.ready);
  const duration=await page.evaluate(()=>window.DUR);
  const start=Number(opts.start??0),end=Number(opts.end??duration);
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start||end>duration) throw Error('Invalid range.');
  fs.mkdirSync(path.dirname(out),{recursive:true});
  const audioArgs=audioFile?['-ss',String(start),'-i',audioFile]:['-f','lavfi','-i','anullsrc=r=48000:cl=stereo'];
  proc=spawn('ffmpeg',['-v','error','-n','-f','image2pipe','-vcodec','png','-framerate',String(fps),'-i','pipe:0',...audioArgs,'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',String(end-start),'-movflags','+faststart',out],{stdio:['pipe','ignore','pipe']});
  let errorText='';proc.stderr.on('data',s=>{errorText+=s});
  let pipeError;proc.stdin.on('error',e=>{pipeError=e});
  completion=new Promise((resolve,reject)=>{proc.on('error',reject);proc.on('close',code=>code===0?resolve():reject(Error(`FFmpeg ${code}: ${errorText}`)));});
  completion.catch(()=>{});
  const frames=Math.ceil((end-start)*fps);
  for(let i=0;i<frames;i++){
    if(pipeError)throw pipeError;
    const data=await page.evaluate(({t,width,height})=>{
      window.render(t);
      let target=window.exportCanvas;
      if(!target){target=window.exportCanvas=document.createElement('canvas');target.width=width;target.height=height;}
      target.getContext('2d').drawImage(document.querySelector('canvas'),0,0,width,height);
      return target.toDataURL('image/png').split(',')[1];
    },{t:start+i/fps,width,height});
    if(!proc.stdin.write(Buffer.from(data,'base64'))) await once(proc.stdin,'drain');
    if(i%Math.round(fps*2)===0)console.log(`${i}/${frames} frames`);
  }
  proc.stdin.end();await completion;
  if(errors.length)throw Error(errors.join('\n'));
  console.log(JSON.stringify({out,width,height,fps,duration:end-start,frames,visual_acceptance:'not_established_by_render'}));
}finally{
  if(proc&&proc.exitCode===null)proc.kill();
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
