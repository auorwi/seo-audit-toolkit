import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Passive media capture plus bounded decode probes for already-complete images. */
import {createHash,randomUUID} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {collectMetadata} from '../../seo-tdk/scripts/collect_metadata.mjs';
const collectorHash=createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex');
export async function installMediaObserver(page){
 await page.addInitScript(()=>{
  const errors=new WeakMap();Object.defineProperty(window,'__seoMediaErrors',{value:errors});
  window.addEventListener('error',e=>{if(e.target instanceof HTMLImageElement)errors.set(e.target,e.target.currentSrc||e.target.src);},true);
 });
}
export function observeResponses(page,{maxResponses=1500,maxPrefixBytes=4096,maxBodyBytes=65536}={}){
 const rows=[],pending=new Set();let stopped=false,omitted=0;
 const listener=response=>{
  if(stopped)return;
  const request=response.request(),kind=request.resourceType();
  if(!['image','media','document'].includes(kind))return;
  if(rows.length>=maxResponses){omitted++;return;}
  const row={url:response.url(),method:request.method(),status:response.status(),captured_at:new Date().toISOString(),
   source:'actual browser response',resource_type:kind,from_service_worker:response.fromServiceWorker(),
   body_complete:false,body_decoded:true,body_prefix_base64:null};rows.push(row);
  const task=(async()=>{
   try{
    const safe=new Set(['content-type','content-length','content-encoding','content-range','location','etag','last-modified','cache-control','retry-after','date','vary']);
    row.headers=(await response.headersArray()).filter(h=>safe.has(h.name.toLowerCase())).map(h=>[h.name.toLowerCase(),h.value]);
    const len=Number(await response.headerValue('content-length'));
    // Never read unbounded bodies or video payloads. Absence of a prefix stays a coverage gap.
    const encoding=(await response.headerValue('content-encoding')??'identity').toLowerCase();
    if(kind==='image'&&request.method()==='GET'&&Number.isSafeInteger(len)&&len>=0&&len<=maxBodyBytes&&await response.headerValue('content-length')!==null&&['','identity'].includes(encoding)){
     const data=await response.body();row.body_prefix_base64=data.subarray(0,maxPrefixBytes).toString('base64');row.body_complete=data.length<=maxPrefixBytes;row.received_body_bytes=data.length;
    }else row.body_unobserved_reason='body_not_within_image_budget';
   }catch(e){row.body_unobserved_reason=e.message;}
  })();pending.add(task);task.finally(()=>pending.delete(task));
 };
 page.on('response',listener);
 return {async finish(){stopped=true;page.off('response',listener);let timer;await Promise.race([Promise.allSettled([...pending]),new Promise(r=>{timer=setTimeout(r,5000);})]);clearTimeout(timer);if(omitted)rows.push({source:'collector_gap',reason:'response_limit_reached',omitted});return JSON.parse(JSON.stringify(rows));}};
}
export async function collectMedia(page,config){
  config=readinessConfig(config);
 const limits={maxImages:config.maxImages??300,maxCssElements:config.maxCssElements??3000,decodeTimeoutMs:config.decodeTimeoutMs??500};
 for(const [k,v] of Object.entries(limits))if(!Number.isInteger(v)||v<=0||v>({maxImages:1000,maxCssElements:10000,decodeTimeoutMs:5000}[k]))throw new Error('invalid_'+k);
 const base=await collectMetadata(page,config);
 const sample=await page.evaluate(async ({c,limits})=>{
  const gaps=[],media=[],all=[...document.querySelectorAll('*')];
  const slot=e=>{
   if(e.id&&document.querySelectorAll('#'+CSS.escape(e.id)).length===1)return e.localName+'#'+CSS.escape(e.id);
   const parts=[];for(let n=e;n&&n.nodeType===1;n=n.parentElement){const siblings=n.parentElement?[...n.parentElement.children].filter(x=>x.localName===n.localName):[n];parts.unshift(n.localName+':nth-of-type('+(siblings.indexOf(n)+1)+')');}return parts.join(' > ');
  };
  const geom=(e,pseudo=null)=>{const s=getComputedStyle(e,pseudo),r=e.getBoundingClientRect();const visible=e.checkVisibility({opacityProperty:true,visibilityProperty:true,contentVisibilityAuto:true})&&s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse'&&Number(s.opacity)!==0&&r.width>0&&r.height>0;return {visible,in_viewport:visible&&r.bottom>0&&r.right>0&&r.top<innerHeight&&r.left<innerWidth,rect:{x:r.x,y:r.y,width:r.width,height:r.height}};};
  const imgs=[...document.images];if(imgs.length>limits.maxImages)gaps.push('image_limit_reached');
  // Freeze each node's observed fields before probes; record source changes explicitly afterwards.
  const pairs=imgs.slice(0,limits.maxImages).map(e=>{const row={slot:slot(e),tag:'img',...geom(e),src_attribute:e.getAttribute('src'),src:e.src,current_src:e.currentSrc,
   srcset:e.getAttribute('srcset'),sizes:e.getAttribute('sizes'),alt_present:e.hasAttribute('alt'),alt:e.getAttribute('alt'),loading:e.loading,
   width_attribute:e.getAttribute('width'),height_attribute:e.getAttribute('height'),complete:e.complete,natural_width:e.naturalWidth,natural_height:e.naturalHeight,
   error_event_src:window.__seoMediaErrors?.get(e)??null,decode:{result:'not_attempted'}};media.push(row);return [e,row];});
  for(const e of document.querySelectorAll('video,iframe,embed,object')){
   if(media.length>=limits.maxImages+200){gaps.push('embed_limit_reached');break;}
   const row={slot:slot(e),tag:e.localName,...geom(e),src:e.localName==='object'?e.data:e.src,title:e.title,playback_verified:false};
   if(e.localName==='video')Object.assign(row,{current_src:e.currentSrc,poster:e.poster,ready_state:e.readyState,network_state:e.networkState,error_code:e.error?.code??null,
    paused:e.paused,current_time:e.currentTime,preload:e.preload,controls:e.controls,autoplay:e.autoplay,muted:e.muted,
    sources:[...e.querySelectorAll(':scope > source')].map(s=>({src:s.src,type:s.type,media:s.media}))});media.push(row);
  }
  if(all.length>limits.maxCssElements)gaps.push('css_scan_limit_reached');
  for(const e of all.slice(0,limits.maxCssElements))for(const pseudo of [null,'::before','::after']){
   const s=getComputedStyle(e,pseudo),bg=s.backgroundImage;if(!bg||bg==='none')continue;
   if(pseudo&&(s.content==='none'||s.content==='normal'))continue;
   const urls=[];const re=/url\(\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|([^)]*))\s*\)/g;let m;
   while((m=re.exec(bg))){const raw=(m[1]??m[2]??m[3]).trim();if(/\\[0-9a-fA-F]/.test(raw)){gaps.push('css_url_escape_unresolved');continue;}urls.push(raw.replace(/\\([\\"'])/g,'$1'));}
   if(urls.length)media.push({slot:slot(e)+(pseudo??'')+'::background',tag:'css',background_urls:urls,background_image:bg,...geom(e,pseudo)});
  }
  const html=(document.doctype?new XMLSerializer().serializeToString(document.doctype)+'\n':'')+document.documentElement.outerHTML;
  const captured_at=new Date().toISOString(),entity=document.querySelector(c.identitySelector),main=document.querySelector(c.mainSelector);
  const identity=entity&&geom(entity).visible?entity.innerText:'';
  const visible_main=main&&geom(main).visible?main.innerText.slice(0,10000):'';
  const identity_count=document.querySelectorAll(c.identitySelector).length,main_count=document.querySelectorAll(c.mainSelector).length;
  if((c.identityRequired&&identity_count!==1)||main_count!==1)gaps.push('ambiguous_readiness_selector');
  // No decode() on incomplete lazy images: calling it could initiate work that was not otherwise requested.
  await Promise.all(pairs.map(async ([e,row])=>{
   if(!row.complete||!row.current_src)return;
   let timer;const started=row.current_src;
   const result=await Promise.race([e.decode().then(()=> 'fulfilled',()=> 'rejected'),new Promise(r=>{timer=setTimeout(()=>r('timeout'),limits.decodeTimeoutMs);})]);clearTimeout(timer);
   row.decode={result,current_src:started,source_after_probe:e.currentSrc,completed_at:new Date().toISOString()};
   if(e.currentSrc!==started){row.decode.result='not_attempted';gaps.push('image_source_changed_during_probe:'+row.slot);}
  }));
  return {url:location.href,captured_at,html,entity:identity,visible_main,media,gaps,identity_count,main_count,
   viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio,scroll_x:scrollX,scroll_y:scrollY},
   totals:{images:imgs.length,dom_elements:all.length},phase:c.phase??'initial_no_scroll',
   readiness_same_capture:main_count===1&&(!c.identityRequired||(identity_count===1&&identity.trim().toLowerCase()===c.expectedIdentity.trim().toLowerCase()))&&!!visible_main.trim()};
 },{c:config,limits});
 for(const row of sample.media)row.captured_at=sample.captured_at;
 return {...sample,snapshot_id:'media-'+randomUUID(),document_sha256:createHash('sha256').update(sample.html).digest('hex'),
  identity_verified:false,readiness_basis:config.readinessBasis,readiness:base.capture.readiness==='ready'&&sample.readiness_same_capture?'ready':'unknown',readiness_gaps:base.unmet,
  source:'isolated Chromium actual DOM, currentSrc, computed CSS, load errors and bounded decode probes',collector_version:'1.0.0',collector_sha256:collectorHash,
  visibility_method:'checkVisibility opacity/visibility/content-visibility + rectangle viewport intersection; occlusion not verified',limits};
}
