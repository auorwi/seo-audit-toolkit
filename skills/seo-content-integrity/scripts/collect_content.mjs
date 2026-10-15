import {readinessConfig} from '../../seo-crawlability/scripts/site.mjs';
/** Read-only public content evidence; edits only explicitly chosen calculator inputs. */
import {createHash,randomUUID} from 'node:crypto';
import {collectMetadata} from '../../seo-tdk/scripts/collect_metadata.mjs';
const hash=s=>createHash('sha256').update(s).digest('hex');
export async function collectContent(page,config){
  config=readinessConfig(config);
 const started=Date.now();
 const base=await collectMetadata(page,config);
 const observe=()=>page.evaluate(c=>{
  const shown=e=>{if(!e)return false;const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse'&&e.getClientRects().length>0;};
  const main=document.querySelector(c.mainSelector),entity=document.querySelector(c.identitySelector);
  const fields=Object.fromEntries(Object.entries(c.fieldSelectors??{}).map(([name,selector])=>{
   const els=[...document.querySelectorAll(selector)],el=els[0];
   return [name,{selector,present:!!el,count:els.length,visible:shown(el),text:shown(el)?(el.innerText??el.textContent??''):null,
    value:el&&['input','textarea','select'].includes(el.localName)&&el.type!=='password'&&shown(el)?el.value:null}];
  }));
  return {url:location.href,captured_at:new Date().toISOString(),entity:shown(entity)?entity.innerText:'',
   visible_main:shown(main)?main.innerText:'',fields,
   loading:[...document.querySelectorAll(c.placeholderSelector)].some(shown),
   html:(document.doctype?new XMLSerializer().serializeToString(document.doctype)+'\n':'')+document.documentElement.outerHTML};
 },config);
 let sample,readiness=base.capture.readiness,last=null,stableAt=0,unmet=[];
 do{
  sample=await observe();unmet=[];
  if(config.identityRequired&&sample.entity.trim().toLowerCase()!==config.expectedIdentity.trim().toLowerCase()||sample.loading||!sample.visible_main.trim())unmet.push('entity_main_or_loading');
  for(const [name,rule] of Object.entries(config.requiredFields??{})){
   const f=sample.fields[name],value=f?.value??f?.text;
   if(!f?.present||!f.visible||f.count!==1||typeof value!=='string'||(rule.nonEmpty&&!value.trim())||(rule.pattern&&!new RegExp(rule.pattern).test(value)))unmet.push('business_field_not_ready:'+name);
  }
  if(base.capture.readiness!=='ready')break;
  if(!Object.keys(config.requiredFields??{}).length&&!unmet.length)break;
  const signature=JSON.stringify(Object.keys(config.requiredFields??{}).map(k=>sample.fields[k]));
  if(signature!==last||unmet.length){stableAt=Date.now();last=signature;}
  if(!unmet.length&&Date.now()-stableAt>=(config.stableWindowMs??1000))break;
  if(!unmet.length)unmet.push('business_fields_not_stable');
  await new Promise(r=>setTimeout(r,config.sampleIntervalMs??250));
 }while(Date.now()-started<(config.timeoutMs??30000));
 if(unmet.length)readiness='unknown_timeout';
 return {...sample,snapshot_id:'content-'+randomUUID(),document_sha256:hash(sample.html),identity_verified:false,readiness_basis:config.readinessBasis,readiness,
  source:'isolated Chromium same-evaluate public DOM and visible fields',unmet:[...base.unmet,...unmet],
  signals:{...config},readiness_samples:base.samples};
}

export async function performTrial(page,config,{inputSelector,quantity,direction}){
 const before=await collectContent(page,config);
 const action={action_id:'calculator-'+randomUUID(),source:'actual browser fill; no submit',status:'failed',
  input_selector:inputSelector,requested_input:quantity,direction,started_at:new Date().toISOString(),before_snapshot:before.snapshot_id};
 try{
  if(before.readiness!=='ready')throw new Error('before_not_ready');
  if(!['asset_to_quote','quote_to_asset'].includes(direction)||!/^\d+(\.\d+)?$/.test(quantity))throw new Error('invalid_trial');
  const control=page.locator(inputSelector);
  if(await control.count()!==1)throw new Error('input_selector_not_unique');
  const meta=await control.evaluate(e=>({tag:e.localName,type:e.type,readonly:e.readOnly,disabled:e.disabled}));action.control=meta;
  if(meta.tag!=='input'||!['text','number','tel'].includes(meta.type)||meta.readonly||meta.disabled)throw new Error('control_not_editable_public_calculator');
  await control.fill(quantity,{timeout:5000});
  action.applied_input=await control.inputValue();
  // Minimum dwell plus stable readiness capture. This is bounded UI evidence, not proof all requests finished.
  await new Promise(r=>setTimeout(r,config.interactionDwellMs??750));
  action.status='completed';
 }catch(e){action.reason=e.message;}
 const after=await collectContent(page,config);action.finished_at=new Date().toISOString();action.after_snapshot=after.snapshot_id;
 action.before_sha256=before.document_sha256;action.after_sha256=after.document_sha256;
 action.settlement='minimum dwell plus readiness samples; asynchronous work beyond window remains possible';
 return {before,after,action};
}

export async function performScenario(page,config,{inputSelector,growthPercent}){
 const before=await collectContent(page,config);
 const action={action_id:'forecast-'+randomUUID(),source:'actual browser forecast growth fill; no submit',status:'failed',
  input_selector:inputSelector,growth_percent:growthPercent,started_at:new Date().toISOString(),before_snapshot:before.snapshot_id};
 try{
  if(before.readiness!=='ready')throw new Error('before_not_ready');
  if(typeof growthPercent!=='string'||!/^[-+]?\d+(\.\d+)?$/.test(growthPercent)||Number(growthPercent)<-100||Number(growthPercent)>1000)throw new Error('growth_outside_declared_range');
  const control=page.locator(inputSelector);
  if(await control.count()!==1)throw new Error('input_selector_not_unique');
  const meta=await control.evaluate(e=>({tag:e.localName,type:e.type,readonly:e.readOnly,disabled:e.disabled}));action.control=meta;
  if(meta.tag!=='input'||!['text','number'].includes(meta.type)||meta.readonly||meta.disabled)throw new Error('growth_control_not_editable');
  const original=await control.inputValue();action.requested_raw_input=growthPercent+(original.trim().endsWith('%')?'%':'');
  await control.fill(action.requested_raw_input,{timeout:5000});await control.blur();
  await new Promise(r=>setTimeout(r,config.interactionDwellMs??750));
  action.applied_input=await control.inputValue();
  const applied=action.applied_input.trim().replace(/%$/,'').trim();
  if(!/^[-+]?\d+(\.\d+)?$/.test(applied)||Number(applied)!==Number(growthPercent))throw new Error('growth_input_not_applied');
  action.status='completed';
 }catch(e){action.reason=e.message;}
 const after=await collectContent(page,config);action.finished_at=new Date().toISOString();action.after_snapshot=after.snapshot_id;
 action.before_sha256=before.document_sha256;action.after_sha256=after.document_sha256;
 return {before,after,action};
}
