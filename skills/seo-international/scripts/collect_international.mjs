import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Capture actual visible main and multilingual declarations as one document observation. */
import {createHash,randomUUID} from 'node:crypto';
import {collectMetadata} from '../../seo-tdk/scripts/collect_metadata.mjs';
const hash=s=>createHash('sha256').update(s).digest('hex');
export async function collectInternational(page,config){
  config=readinessConfig(config);
 const start=Date.now(),limit=config.timeoutMs??30000,window=config.stableWindowMs??1000,interval=config.sampleIntervalMs??250;
 const base=await collectMetadata(page,config);let readiness=base.capture.readiness,unmet=[...base.unmet],sample,last=null,count=0,stableAt=0,samples=0;
 const observe=()=>page.evaluate(c=>{
  const shown=e=>{if(!e)return false;const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse'&&e.getClientRects().length>0;};
  const main=document.querySelector(c.mainSelector),entity=document.querySelector(c.identitySelector);
  return {url:location.href,html_lang:document.documentElement.lang,visible_main:shown(main)?main.innerText:'',entity:shown(entity)?entity.innerText:'',
   declarations:[...document.querySelectorAll('link[hreflang],link[rel="canonical" i]')].map(e=>e.outerHTML),
   visible_fields:Object.fromEntries(Object.entries(c.fieldSelectors??{}).map(([name,selector])=>[name,[...document.querySelectorAll(selector)].some(shown)])),
   loading:[...document.querySelectorAll(c.placeholderSelector)].filter(shown).length,
   errors:[...document.querySelectorAll(c.errorSelector)].filter(shown).filter(e=>!c.errorText||e.innerText.includes(c.errorText)).length,
   html:(document.doctype?new XMLSerializer().serializeToString(document.doctype)+'\n':'')+document.documentElement.outerHTML,at:new Date().toISOString()};
 },config);
 if(readiness==='ready'){
  readiness='unknown_timeout';
  while(Date.now()-start<=limit){
   sample=await observe();samples++;unmet=[];
   if(sample.errors){readiness='page_error';unmet=['visible_page_error'];break;}
   if(!sample.visible_main.trim()||config.identityRequired&&sample.entity.trim().toLocaleLowerCase()!==config.expectedIdentity.trim().toLocaleLowerCase())unmet.push('entity_or_main_not_ready');
   if(sample.loading)unmet.push('placeholders_present');
   if(config.expectedHtmlLang&&sample.html_lang.toLowerCase()!==config.expectedHtmlLang.toLowerCase())unmet.push('expected_html_lang_not_observed');
   if(config.requiredText&&!sample.visible_main.includes(config.requiredText))unmet.push('required_business_text_missing');
   const signature=hash(JSON.stringify([sample.url,sample.html_lang,sample.entity,sample.declarations,sample.visible_fields]));
   if(!unmet.length&&last===signature)count++;else{count=unmet.length?0:1;stableAt=Date.now();}last=signature;
   if(!unmet.length&&count>=2&&Date.now()-stableAt>=window){readiness='ready';break;}
   if(!unmet.length)unmet.push('international_samples_not_stable');
   await new Promise(r=>setTimeout(r,interval));
  }
 }
 sample??=await observe();const document_sha256=hash(sample.html),snapshot_id='intl-dom-'+randomUUID();
 const capture={url:sample.url,snapshot_id,document_sha256,captured_at:sample.at,representation:'rendered_html',identity_verified:false,readiness_basis:config.readinessBasis,readiness,state:'completed',source:'isolated browser stable multilingual DOM',entry_mode:config.entryMode??'direct'};
 return {capture,html:sample.html,browser:{url:sample.url,snapshot_id,document_sha256,captured_at:sample.at,source:'same actual DOM evaluate',visible_main:sample.visible_main,main_selector:config.mainSelector,visible_fields:sample.visible_fields,html_lang:sample.html_lang},unmet,samples,collection_ms:Date.now()-start};
}

export async function performLanguageSwitch(page,before,selector,config,{expectedText,expectedLocale}){
 if(before.capture.readiness!=='ready')throw new Error('switch_before_not_ready');
 if(!expectedText?.trim()||!expectedLocale?.trim())throw new Error('switch_expectations_required');
 const control=page.locator(selector).first();await control.waitFor({state:'visible',timeout:10000});
 const observed=await control.evaluate(e=>({text:(e.innerText||e.getAttribute('aria-label')||'').trim(),href:e.getAttribute('href'),tag:e.localName,html:e.outerHTML,disabled:e.matches(':disabled')||e.getAttribute('aria-disabled')==='true'}));
 if(observed.text!==expectedText.trim())throw new Error('switch_label_mismatch');
 if(observed.disabled)throw new Error('switch_disabled');
 const clicked_at=new Date().toISOString();await control.click();const after=await collectInternational(page,{...config,entryMode:'language_switch'});
 const action={source:'actual isolated-browser language switch click',selector,control:observed,clicked_at,expected_locale:expectedLocale,before_snapshot:before.capture.snapshot_id,after_snapshot:after.capture.snapshot_id,before_sha256:before.capture.document_sha256,after_sha256:after.capture.document_sha256,before_url:before.capture.url,after_url:after.capture.url};
 return {after,action};
}
