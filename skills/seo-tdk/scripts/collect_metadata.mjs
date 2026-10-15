import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Read actual metadata readiness from an already opened public page. */
import {createHash,randomUUID} from 'node:crypto';
export async function collectMetadata(page,config){
  config=readinessConfig(config);
  const started=Date.now();let lastSample=null,last=null,stableStart=0,count=0,samples=0,unmet=[],readiness='unknown_timeout';
  const timeout=config.timeoutMs??30000,window=config.stableWindowMs??1000,interval=config.sampleIntervalMs??250;
  while(Date.now()-started<=timeout){
    const sample=await page.evaluate(c=>{
      const shown=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse'&&e.getClientRects().length>0;};
      const main=document.querySelector(c.mainSelector),entity=document.querySelector(c.identitySelector);
      return {url:location.href,title:document.title,descriptions:[...document.head.querySelectorAll('meta[name="description" i]')].map(x=>x.content),
        main:main?.innerText??'',entity:entity&&shown(entity)?entity.innerText:'',
        loading:[...document.querySelectorAll(c.placeholderSelector)].filter(shown).length,
        errors:[...document.querySelectorAll(c.errorSelector)].filter(shown).filter(x=>!c.errorText||x.innerText.includes(c.errorText)).length};
    },config);
    lastSample={...sample,main:sample.main.slice(0,2000),main_truncated:sample.main.length>2000,observed_at:new Date().toISOString()};
    samples++;unmet=[];
    if(!sample.main.trim())unmet.push('main_content_missing');
    if(config.identityRequired&&sample.entity.trim().toLocaleLowerCase()!==config.expectedIdentity.trim().toLocaleLowerCase())unmet.push('entity_not_observed');
    if(sample.loading)unmet.push('placeholders_present');
    if(sample.errors){readiness='page_error';unmet.push('visible_page_error');break;}
    // Price-bearing titles may change; explicit dynamicTitle skips only this stability component.
    const signature=JSON.stringify([sample.url,config.dynamicTitle?null:sample.title,sample.descriptions,sample.entity]);
    if(!unmet.length&&signature===last)count++;else{stableStart=Date.now();count=unmet.length?0:1;}
    last=signature;
    if(!unmet.length&&count>=2&&Date.now()-stableStart>=window){readiness='ready';break;}
    if(!unmet.length)unmet.push('stable_samples_missing');
    await new Promise(resolve=>setTimeout(resolve,interval));
  }
  const html=await page.content(),document_sha256=createHash('sha256').update(html).digest('hex');
  return {capture:{url:page.url(),snapshot_id:'tdk-dom-'+randomUUID(),captured_at:new Date().toISOString(),document_sha256,
    source:'isolated browser actual serialized DOM; stable title/description/entity checks',representation:'rendered_html',identity_verified:false,readiness_basis:config.readinessBasis,readiness},
    html,samples,unmet,readiness_evidence:lastSample,collection_ms:Date.now()-started};
}
