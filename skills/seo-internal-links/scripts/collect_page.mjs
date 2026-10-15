#!/usr/bin/env node
/** Collect one public page and optionally an observed pagination control plus direct destination. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';import path from 'node:path';import {parseArgs} from 'node:util';import {createRequire} from 'node:module';import {createHash,randomUUID} from 'node:crypto';
import {collectLinks} from './collect_links.mjs';
import {observeRedirectChain} from './collect_responses.mjs';
const require=createRequire(import.meta.url);let browser;

try{
 const {values}=parseArgs({options:Object.fromEntries(['url','config','runtime','browser-executable','output','pagination-selector'].map(k=>[k,{type:'string',multiple:true}])),strict:true});
 const v=Object.fromEntries(Object.entries(values).map(([k,a])=>[k,a.at(-1)]));if(!allowed(v.url))throw new Error('unsupported_target');
 const config=readinessConfig(v.config?JSON.parse(fs.readFileSync(v.config,'utf8')):{});
 if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof config[k]==='string'&&config[k].trim())||(config.identityRequired&&!config.expectedIdentity?.trim()))throw new Error('template_signals_required');
 for(const k of ['timeoutMs','stableWindowMs','sampleIntervalMs'])if(k in config&&(!Number.isFinite(config[k])||config[k]<=0))throw new Error('invalid_capture_budget');
 if(v['pagination-selector']&&!config.itemSelector)throw new Error('pagination_items_required');
 if(v['pagination-selector']&&!(typeof config.paginationControlText==='string'&&config.paginationControlText.trim()))throw new Error('pagination_control_text_required');
 const output=path.resolve(v.output);if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
 const {chromium}=require(path.join(path.resolve(v.runtime),'node_modules/playwright-core'));browser=await chromium.launch({executablePath:v['browser-executable'],headless:true});
 fs.mkdirSync(output,{recursive:true});
 const save=(name,value,raw=false)=>{const b=raw?Buffer.from(value):Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(output,name),b);return {path:name,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};};
 const captures=[],http_records=[],pagination=[],collection=[];
 async function initial(response,prefix){
  if(!response)return;const at=new Date().toISOString();
  const hops=await observeRedirectChain(response);
  for(let i=0;i<hops.length;i++){const proof=save(prefix+'-http-hop-'+i+'.json',hops[i]);http_records.push({...hops[i],evidence:proof,evidence_kind:'actual_response_metadata'});}
  try{const raw=await response.body();const evidence=save(prefix+'-initial.html',raw,true),url=response.url();

   captures.push({url,snapshot_id:'links-http-'+randomUUID(),document_sha256:evidence.sha256,captured_at:at,source:'same actual browser main-document response',representation:'initial_html',entry_mode:prefix==='before'?'direct':'direct_verification',state:response.ok()?'completed':'http_error',evidence});
  }catch(e){collection.push({phase:prefix,reason:'initial_response_body_unavailable',detail:e.message});}
 }
 async function capture(page,prefix,options={}){
  if(!allowed(page.url()))throw new Error('navigation_outside_site');
  const r=await collectLinks(page,{...config,...options});if(!allowed(r.capture.url))throw new Error('capture_outside_site');
  const row={...r.capture,evidence:save(prefix+'-dom.html',r.html,true),browser_evidence:save(prefix+'-browser.json',r.browser),environment:{browser:'isolated Chromium '+browser.version(),device:'desktop',login:'unauthenticated',network:'local egress; geography unverified'}};
  if(options.previousItemKeys)row.discovery_mode='interaction_only';if(options.requestedUrl)row.requested_url=options.requestedUrl;
  captures.push(row);collection.push({phase:prefix,capture:row,samples:r.samples,unmet:r.unmet,collection_ms:r.collection_ms});return {...r,row};
 }
 const page=await browser.newPage();await protectPage(page);const response=await page.goto(v.url,{waitUntil:'domcontentloaded',timeout:30000});await initial(response,'before');const before=await capture(page,'before');
 if(v['pagination-selector']&&before.capture.readiness==='ready'){
  const control=page.locator(v['pagination-selector']).first();await control.waitFor({state:'visible',timeout:10000});
  const observed=await control.evaluate(e=>({tag:e.localName.toLowerCase(),text:(e.innerText||e.getAttribute('aria-label')||'').trim(),href:e.getAttribute('href'),disabled:e.matches(':disabled')||e.getAttribute('aria-disabled')==='true',html:e.outerHTML}));
  if(observed.text!==config.paginationControlText.trim())throw new Error('pagination_control_text_mismatch');
  if(observed.disabled)collection.push({phase:'pagination',status:'disabled_control',observed});
  else{
   const clickedAt=new Date().toISOString();await control.click();const after=await capture(page,'after',{entryMode:'pagination',previousItemKeys:before.browser.item_keys});
   const action={source:'actual isolated-browser pagination click',selector:v['pagination-selector'],control:observed,before_snapshot:before.capture.snapshot_id,after_snapshot:after.capture.snapshot_id,before_document_sha256:before.capture.document_sha256,after_document_sha256:after.capture.document_sha256,clicked_at:clickedAt};
   const item={before:before.capture.snapshot_id,after:after.capture.snapshot_id,action_evidence:save('pagination-action.json',action)};pagination.push(item);
   let directUrl=after.capture.url;
   if(observed.tag==='a'&&observed.href){const candidate=new URL(observed.href,before.capture.url).href;if(allowed(candidate))directUrl=candidate;}
   if(allowed(directUrl)){
    const directPage=await browser.newPage();await protectPage(directPage);const directResponse=await directPage.goto(directUrl,{waitUntil:'domcontentloaded',timeout:30000});await initial(directResponse,'direct');const direct=await capture(directPage,'direct',{entryMode:'direct_verification',requestedUrl:directUrl});item.direct=direct.capture.snapshot_id;
   }
  }
 }
 const assets=[...new Set(captures.map(c=>c.url))];save('collection.json',{observations:collection,signals:config});save('manifest.json',{schema_version:1,captures,http_records,pagination,assets,seeds:{requested_entry:[v.url]}});
 const partial=captures.some(c=>c.representation==='rendered_html'&&c.readiness!=='ready');console.log(JSON.stringify({status:partial?'partial_capture':'ready',captures:captures.length,http_records:http_records.length,pagination:pagination.length,output}));process.exitCode=partial?2:0;
}catch(error){console.error(JSON.stringify({status:'error',reason:error.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
