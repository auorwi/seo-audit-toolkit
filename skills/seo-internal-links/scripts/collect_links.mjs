import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Bind observed links, visibility and list identities to the same serialized document. */
import {createHash,randomUUID} from 'node:crypto';
import {collectMetadata} from '../../seo-tdk/scripts/collect_metadata.mjs';
const hash=s=>createHash('sha256').update(s).digest('hex');
export async function collectLinks(page,config){
  config=readinessConfig(config);
  const start=Date.now(),limit=config.timeoutMs??30000,window=config.stableWindowMs??1000,interval=config.sampleIntervalMs??250;
  const base=await collectMetadata(page,config);let ready=base.capture.readiness,unmet=[...base.unmet],sample,count=0,stableAt=0,last=null,samples=0;
  const observe=()=>page.evaluate(c=>{
    const shown=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse'&&e.getClientRects().length>0;};
    const nodes=[...document.querySelectorAll('a,button,[role="link" i]')];
    const links=nodes.map((e,i)=>({tag:e.localName.toLowerCase(),locator:e.localName.toLowerCase()+'[observed-index='+i+']',href:e.getAttribute('href'),visible:shown(e),inner_text:e.innerText??e.textContent??''})).filter(e=>e.tag==='a');
    const item_keys=c.itemSelector?[...document.querySelectorAll(c.itemSelector)].filter(shown).map(e=>c.itemAttribute?e.getAttribute(c.itemAttribute):e.innerText).filter(x=>typeof x==='string'&&x.trim()).map(x=>x.trim()):[];
    const identity=document.querySelector(c.identitySelector),main=document.querySelector(c.mainSelector);
    return {url:location.href,links,item_keys,entity:identity&&shown(identity)?identity.innerText:'',main:main?.innerText??'',
      loading:[...document.querySelectorAll(c.placeholderSelector)].filter(shown).length,
      errors:[...document.querySelectorAll(c.errorSelector)].filter(shown).filter(e=>!c.errorText||e.innerText.includes(c.errorText)).length,
      html:(document.doctype?new XMLSerializer().serializeToString(document.doctype)+'\n':'')+document.documentElement.outerHTML,at:new Date().toISOString()};
  },config);
  if(ready==='ready'){
    ready='unknown_timeout';
    while(Date.now()-start<=limit){
      sample=await observe();samples++;unmet=[];
      if(sample.errors){ready='page_error';unmet=['visible_page_error'];break;}
      if(!sample.main.trim()||config.identityRequired&&sample.entity.trim().toLocaleLowerCase()!==config.expectedIdentity.trim().toLocaleLowerCase())unmet.push('entity_not_ready');
      if(sample.loading)unmet.push('placeholders_present');
      if(config.itemSelector&&!sample.item_keys.length)unmet.push('items_not_observed');
      if(config.previousItemKeys&&JSON.stringify([...new Set(config.previousItemKeys)].sort())===JSON.stringify([...new Set(sample.item_keys)].sort()))unmet.push('items_not_changed');
      const signature=hash(JSON.stringify([sample.url,sample.links,sample.item_keys,sample.entity]));
      if(!unmet.length&&signature===last)count++;else{count=unmet.length?0:1;stableAt=Date.now();}
      last=signature;
      if(!unmet.length&&count>=2&&Date.now()-stableAt>=window){ready='ready';break;}
      if(!unmet.length)unmet.push('link_samples_not_stable');
      await new Promise(r=>setTimeout(r,interval));
    }
  }
  sample??=await observe();const document_sha256=hash(sample.html),snapshot_id='links-dom-'+randomUUID();
  const capture={url:sample.url,snapshot_id,document_sha256,captured_at:sample.at,representation:'rendered_html',identity_verified:false,readiness_basis:config.readinessBasis,readiness:ready,source:'isolated browser serialized DOM and stable link observations',entry_mode:config.entryMode??'direct'};
  return {capture,html:sample.html,browser:{url:sample.url,snapshot_id,document_sha256,captured_at:sample.at,source:'same browser evaluate of actual DOM',links:sample.links,item_keys:sample.item_keys,item_selector:config.itemSelector??null,item_attribute:config.itemAttribute??null},unmet,samples,collection_ms:Date.now()-start};
}
