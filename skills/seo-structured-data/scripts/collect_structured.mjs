import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Reuse only 007's readiness primitive, then bind stable structured markup and visible text. */
import {createHash,randomUUID} from 'node:crypto';
import {collectMetadata} from '../../seo-tdk/scripts/collect_metadata.mjs';
const hash=value=>createHash('sha256').update(value).digest('hex');
export async function collectStructured(page,config){
  config=readinessConfig(config);
  const started=Date.now(),limit=config.timeoutMs??30000,window=config.stableWindowMs??1000,interval=config.sampleIntervalMs??250;
  const base=await collectMetadata(page,config);let readiness=base.capture.readiness,unmet=[...base.unmet],last=null,stableStart=0,count=0,samples=0,observed;
  async function sample(){return await page.evaluate(c=>{
    const shown=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse'&&e.getClientRects().length>0;};
    const jsonld=[...document.querySelectorAll('script[type]')].filter(x=>x.type.split(';')[0].trim().toLowerCase()==='application/ld+json').map(x=>x.textContent);
    const microdata=[...document.querySelectorAll('[itemscope]')].map(x=>x.outerHTML);
    const rdfa=[...document.querySelectorAll('[typeof],[vocab]')].map(x=>x.outerHTML);
    const identity=document.querySelector(c.identitySelector),main=document.querySelector(c.mainSelector);
    const errors=[...document.querySelectorAll(c.errorSelector)].filter(shown).filter(x=>!c.errorText||x.innerText.includes(c.errorText)).length;
    const contentChecks=(c.contentChecks??[]).map(check=>{const e=document.querySelector(check.selector),text=e&&shown(e)?e.innerText:'';return {selector:check.selector,text,ready:!!text.trim()&&(!check.requiredText||text.includes(check.requiredText))&&(!check.forbiddenText||!text.includes(check.forbiddenText))};});
    return {contentChecks,url:location.href,title:document.title,entity:identity&&shown(identity)?identity.innerText:'',main:main?.innerText??'',errors,
      loading:[...document.querySelectorAll(c.placeholderSelector)].filter(shown).length,
      html:(document.doctype?new XMLSerializer().serializeToString(document.doctype)+'\n':'')+document.documentElement.outerHTML,
      visible_text:document.body.innerText,jsonld,microdata,rdfa,observed_at:new Date().toISOString()};
  },config);}
  if(readiness==='ready'){
    readiness='unknown_timeout';unmet=['structured_data_not_stable'];
    while(Date.now()-started<=limit){
      observed=await sample();samples++;
      if(observed.errors){readiness='page_error';unmet=['visible_page_error'];break;}
      const valid=observed.main.trim()&&(!config.identityRequired||observed.entity.trim().toLocaleLowerCase()===config.expectedIdentity.trim().toLocaleLowerCase())&&!observed.loading&&observed.contentChecks.every(x=>x.ready);
      unmet=observed.contentChecks.filter(x=>!x.ready).map(x=>'content_check_not_ready:'+x.selector);if(!unmet.length)unmet=['structured_data_not_stable'];
      const signature=hash(JSON.stringify([observed.url,config.dynamicTitle?null:observed.title,observed.entity,observed.jsonld,observed.microdata,observed.rdfa,observed.contentChecks]));
      if(valid&&signature===last)count++;else{count=valid?1:0;stableStart=Date.now();}
      last=signature;
      if(valid&&count>=2&&Date.now()-stableStart>=window){readiness='ready';unmet=[];break;}
      await new Promise(resolve=>setTimeout(resolve,interval));
    }
  }
  observed??=await sample();
  const document_sha256=hash(observed.html),snapshot_id='structured-dom-'+randomUUID();
  const capture={url:observed.url,snapshot_id,captured_at:observed.observed_at,document_sha256,source:'isolated browser serialized DOM + stable structured markup',representation:'rendered_html',identity_verified:false,readiness_basis:config.readinessBasis,readiness,entry_mode:config.entryMode??'direct'};
  return {capture,html:observed.html,visible:{url:observed.url,snapshot_id,captured_at:observed.observed_at,document_sha256,source:'same browser evaluate document.body.innerText',visible_text:observed.visible_text,scope:'current_document'},
    schema_samples:samples,unmet,structured_counts:{jsonld:observed.jsonld.length,microdata:observed.microdata.length,rdfa:observed.rdfa.length},
    readiness_evidence:{url:observed.url,entity:observed.entity,title:observed.title,content_checks:observed.contentChecks,loading:observed.loading,errors:observed.errors,observed_at:observed.observed_at},collection_ms:Date.now()-started};
}
