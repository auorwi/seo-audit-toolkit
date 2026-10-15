/** Real Chrome + localhost fixture; never live BingX evidence. */
import assert from 'node:assert/strict';import http from 'node:http';import {createRequire} from 'node:module';import {createHash} from 'node:crypto';import {gzipSync} from 'node:zlib';
import {installMediaObserver,collectMedia,observeResponses} from '../scripts/collect_media.mjs';
const require=createRequire(import.meta.url),{chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');
const html=`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>fixture</title><main><h1>Media fixture</h1>
<picture><source media="(max-width: 500px)" srcset="/mobile.svg"><img id="responsive" src="/desktop.svg" alt="diagram"></picture>
<img id="density" src="/one.svg" srcset="/one.svg 1x, /two.svg 2x" alt="density">
<img id="broken" src="/gone.svg" alt="broken"><img id="html-image" src="/player.html" alt="wrong bytes">
<img id="empty-svg" src="/empty.svg" alt=""><img id="hidden" hidden src="/one.svg">
<img id="compressed" src="/compressed.svg" alt="compressed">
<div style="opacity:0"><img id="transparent-parent" src="/one.svg"></div>
<div style="content-visibility:hidden"><img id="content-hidden" src="/one.svg"></div>
<div id="css-hero" style="width:120px;height:50px;background-image:url('/mobile.svg')">background</div>
<iframe id="frame" src="/player.html" title="auxiliary"></iframe><video id="video" preload="metadata" src="/bad-video.mp4"></video>
<div style="height:15000px">spacer</div><img id="lazy" loading="lazy" src="/lazy.svg" width="40" height="40" alt="later"></main>`;
const server=http.createServer((req,res)=>{
 if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html'});res.end(html);return;}
 let body,type='image/svg+xml',status=200;
 if(req.url==='/gone.svg'){status=404;body='missing';type='text/plain';}
 else if(req.url==='/player.html'){body='<html><body>Player document, not playback evidence</body></html>';type='text/html';}
 else if(req.url==='/bad-video.mp4'){body='not video bytes';type='video/mp4';}
 else body='<svg xmlns="http://www.w3.org/2000/svg"'+(req.url==='/empty.svg'?'':' width="40" height="40"')+'><rect width="40" height="40" fill="blue"/></svg>';
 const extra={'Set-Cookie':'fixture_secret=never-store'};
 if(req.url==='/compressed.svg'){body=gzipSync(body);extra['Content-Encoding']='gzip';}
 res.writeHead(status,{'Content-Type':type,'Content-Length':Buffer.byteLength(body),...extra});res.end(body);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const url='http://127.0.0.1:'+server.address().port+'/';
let browser;const tests=[];const test=(name,fn)=>{try{fn();tests.push({name,status:'passed'});}catch(e){tests.push({name,status:'failed',reason:e.message});}};
try{
 browser=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});
 const config={mainSelector:'main',identitySelector:'h1',expectedIdentity:'Media fixture',placeholderSelector:'.loading',errorSelector:'.error',timeoutMs:3500,stableWindowMs:150,sampleIntervalMs:50,maxImages:100,maxCssElements:300,decodeTimeoutMs:600};
 const desk=await browser.newContext({viewport:{width:1280,height:720},deviceScaleFactor:1});const p=await desk.newPage();await installMediaObserver(p);const net=observeResponses(p);await p.goto(url,{waitUntil:'load'});const a=await collectMedia(p,config);const responses=await net.finish();
 const get=(r,id)=>r.media.find(x=>x.slot==='img#'+id);
 test('desktop picture currentSrc is actual desktop',()=>assert.ok(get(a,'responsive').current_src.endsWith('/desktop.svg')));
 test('1x responsive selected actual source',()=>assert.ok(get(a,'density').current_src.endsWith('/one.svg')));
 test('broken complete is true but captured error and decode failure',()=>{const x=get(a,'broken');assert.equal(x.complete,true);assert.equal(x.natural_width,0);assert.ok(x.error_event_src.endsWith('/gone.svg'));assert.equal(x.decode.result,'rejected');});
 test('HTML document is not valid image decode',()=>assert.equal(get(a,'html-image').decode.result,'rejected'));
 test('SVG without explicit width decodes',()=>assert.equal(get(a,'empty-svg').decode.result,'fulfilled'));
 test('hidden image visibility retained',()=>assert.equal(get(a,'hidden').visible,false));
 test('transparent ancestor is not visible',()=>assert.equal(get(a,'transparent-parent').visible,false));
 test('content visibility hidden ancestor is not visible',()=>assert.equal(get(a,'content-hidden').visible,false));
 test('lazy distant image not force-loaded by decode',()=>{const x=get(a,'lazy');assert.equal(x.complete,false);assert.equal(x.decode.result,'not_attempted');assert.equal(x.in_viewport,false);});
 test('actual CSS URL captured',()=>assert.ok(a.media.some(x=>x.tag==='css'&&x.slot.startsWith('div#css-hero')&&x.background_urls.some(u=>u.endsWith('/mobile.svg')))));
 test('iframe source not labelled playback',()=>{const f=a.media.find(x=>x.tag==='iframe');assert.ok(f.src.endsWith('/player.html'));assert.equal(f.playback_verified,false);});
 test('video actual unsupported resource error captured',()=>assert.equal(a.media.find(x=>x.tag==='video').error_code,4));
 test('network records real 404 and bounded prefix',()=>{assert.ok(responses.some(r=>r.url.endsWith('/gone.svg')&&r.status===404));assert.ok(responses.every(r=>!r.body_prefix_base64||Buffer.from(r.body_prefix_base64,'base64').length<=4096));});
 test('compressed body skipped because encoded length is not decoded budget',()=>{const r=responses.find(x=>x.url.endsWith('/compressed.svg'));assert.equal(r.body_prefix_base64,null);assert.equal(get(a,'compressed').decode.result,'fulfilled');});
 test('response cookie headers excluded',()=>assert.ok(responses.every(r=>!(r.headers??[]).some(h=>(h.name??h[0]).toLowerCase()==='set-cookie'))));
 test('same snapshot HTML hash matches',()=>assert.equal(a.document_sha256,createHash('sha256').update(a.html).digest('hex')));
 test('readiness is actual expected entity',()=>assert.equal(a.readiness,'ready'));
 await p.locator('#lazy').scrollIntoViewIfNeeded();await p.waitForFunction(()=>document.querySelector('#lazy').complete);const scrolled=await collectMedia(p,{...config,phase:'after_explicit_scroll'});
 test('lazy after explicit scroll is distinct observation',()=>{assert.equal(scrolled.phase,'after_explicit_scroll');assert.equal(get(scrolled,'lazy').decode.result,'fulfilled');assert.notEqual(scrolled.snapshot_id,a.snapshot_id);});
 const mob=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true});const m=await mob.newPage();await installMediaObserver(m);await m.goto(url,{waitUntil:'load'});const b=await collectMedia(m,config);
 test('mobile picture and 2x differ from desktop',()=>{assert.ok(get(b,'responsive').current_src.endsWith('/mobile.svg'));assert.ok(get(b,'density').current_src.endsWith('/two.svg'));assert.equal(b.viewport.dpr,2);});
 const bounded=await collectMedia(p,{...config,maxImages:1,maxCssElements:1});
 test('bounded capture reports omitted media',()=>{assert.equal(bounded.media.filter(x=>x.tag==='img').length,1);assert.ok(bounded.gaps.includes('image_limit_reached'));assert.ok(bounded.gaps.includes('css_scan_limit_reached'));});
 await p.evaluate(()=>document.querySelector('main').append(document.querySelector('h1').cloneNode(true)));const duplicate=await collectMedia(p,config);
 test('ambiguous entity selector cannot become ready',()=>assert.equal(duplicate.readiness,'unknown'));
 console.log(JSON.stringify({tests,passed:tests.filter(x=>x.status==='passed').length,failed:tests.filter(x=>x.status==='failed').length},null,2));if(tests.some(x=>x.status==='failed'))process.exitCode=1;
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
