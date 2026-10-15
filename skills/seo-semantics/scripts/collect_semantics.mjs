import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Collect from an already opened, isolated public page; never perform business actions. */
import {createHash,randomUUID} from 'node:crypto';

const digest=text=>createHash('sha256').update(text,'utf8').digest('hex');

export async function collectSemantics(page,options){
  options=readinessConfig(options);
  const timeoutMs=options.timeoutMs??30000, stableWindowMs=options.stableWindowMs??1000;
  const interval=options.sampleIntervalMs??250;
  const start=Date.now();let lastSignature=null, stableStart=null, stableCount=0, sampleCount=0;
  let state='unknown_timeout',unmet=[];
  while(Date.now()-start<=timeoutMs){
    const current=await page.evaluate(config=>{
      const main=document.querySelector(config.mainSelector);
      const identity=document.querySelector(config.identitySelector);
      const shown=element=>{const style=getComputedStyle(element);return style.display!=='none'&&style.visibility!=='hidden'&&style.visibility!=='collapse'&&element.getClientRects().length>0;};
      return {url:location.href,title:document.title,canonical:[...document.head.querySelectorAll('link[rel~="canonical"]')].map(x=>x.href),
        h1:[...document.querySelectorAll('h1')].map(x=>x.innerText),mainText:main?.innerText??'',identity:identity?.innerText??'',
        placeholders:[...document.querySelectorAll(config.placeholderSelector)].filter(shown).length,
        errors:[...document.querySelectorAll(config.errorSelector)].filter(shown).filter(x=>!config.errorText||x.innerText.includes(config.errorText)).map(x=>x.innerText)};
    },options);
    sampleCount++;unmet=[];
    if(!current.mainText.trim())unmet.push('main_content_missing');
    if(options.identityRequired&&current.identity.trim().toLocaleLowerCase()!==options.expectedIdentity.trim().toLocaleLowerCase())unmet.push('expected_identity_not_observed');
    if(current.placeholders)unmet.push('placeholders_present');
    if(current.errors.length){state='page_error';unmet.push('visible_page_error');break;}
    const signature=JSON.stringify([current.url,current.title,current.canonical,current.h1,current.identity]);
    if(!unmet.length&&signature===lastSignature){stableCount++;}
    else{stableStart=Date.now();stableCount=unmet.length?0:1;}
    lastSignature=signature;
    if(!unmet.length&&stableCount>=2&&Date.now()-stableStart>=stableWindowMs){state='ready';break;}
    if(!unmet.length)unmet.push('stable_samples_missing');
    await new Promise(resolve=>setTimeout(resolve,interval));
  }
  const captured=await page.evaluate(()=>{
    const all=[...document.querySelectorAll('*')];const ids=new Map(all.map((n,i)=>[n,'dom-'+(i+1)]));
    const path=el=>{
      if(el.id&&document.querySelectorAll('#'+CSS.escape(el.id)).length===1)return '#'+CSS.escape(el.id);
      const parts=[];let current=el;
      while(current){const tag=current.tagName.toLowerCase();const peers=current.parentElement?[...current.parentElement.children].filter(p=>p.tagName===current.tagName):[current];parts.unshift(tag+':nth-of-type('+(peers.indexOf(current)+1)+')');current=current.parentElement;}
      return parts.join(' > ');
    };
    const nodes=all.map(el=>{
      const style=getComputedStyle(el);const rects=el.getClientRects();
      let visibility=style.display==='contents'?'unknown':style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse'||!rects.length?'hidden':'visible';
      const tag=el.tagName.toLowerCase();const text=['script','style'].includes(tag)?'':el.textContent??'';
      const ancestors=[];let parent=el.parentElement;while(parent){ancestors.unshift(parent.tagName.toLowerCase());parent=parent.parentElement;}
      const attributes=Object.fromEntries([...el.attributes].filter(a=>a.name!=='value').map(a=>[a.name,a.value]));
      return {node_id:ids.get(el),tag,selector:path(el),attributes,text:text.slice(0,20000),text_truncated:text.length>20000,
        parent_id:ids.get(el.parentElement)??null,ancestor_tags:ancestors,visibility,accessible_name:null,
        snippet:el.outerHTML.slice(0,1000),snippet_truncated:el.outerHTML.length>1000};
    });
    return {url:location.href,captured_at:new Date().toISOString(),nodes};
  });
  const html=await page.content();const documentHash=digest(html);
  const capture={...captured,snapshot_id:'dom-'+randomUUID(),source:'isolated browser DOM evaluate; computed CSS/rect visibility; axe handles accessible-name checks',
    representation:'rendered_elements',identity_verified:false,readiness_basis:options.readinessBasis,readiness:state,scope:'document',document_sha256:documentHash,
    coverage:{nodes:'complete',visibility:captured.nodes.some(n=>n.visibility==='unknown')?'partial':'complete',accessible_names:'unknown'}};
  let axe=null,axeInputHash=null,afterHash=null;
  if(state==='ready'){
    await page.evaluate(options.axeSource);
    axeInputHash=digest(await page.content());
    axe=await page.evaluate(async()=>await window.axe.run());
    afterHash=digest(await page.content());
  }
  return {capture,html,document_sha256:documentHash,axe_input_sha256:axeInputHash,after_axe_sha256:afterHash,
    axe,unmet,readiness_samples:sampleCount,collection_ms:Date.now()-start};
}
