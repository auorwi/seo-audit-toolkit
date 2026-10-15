#!/usr/bin/env node
/** Collect public international evidence; optional observed language switch. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';import path from 'node:path';import {parseArgs} from 'node:util';import {createRequire} from 'node:module';import {createHash,randomUUID} from 'node:crypto';
import {collectInternational,performLanguageSwitch} from './collect_international.mjs';
const require=createRequire(import.meta.url);let browser;

try{
 const names=['url','config','runtime','browser-executable','output','switch-selector','switch-config','switch-locale','switch-text','menu-selector'];
 const {values}=parseArgs({options:Object.fromEntries(names.map(k=>[k,{type:'string',multiple:true}])),strict:true});const v=Object.fromEntries(Object.entries(values).map(([k,a])=>[k,a.at(-1)]));
 if(!allowed(v.url))throw new Error('unsupported_target');
 const config=readinessConfig(v.config?JSON.parse(fs.readFileSync(v.config,'utf8')):{});
 const validate=c=>{if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof c[k]==='string'&&c[k].trim())||(c.identityRequired&&!c.expectedIdentity?.trim()))throw new Error('template_signals_required');for(const k of ['timeoutMs','stableWindowMs','sampleIntervalMs'])if(k in c&&(!Number.isFinite(c[k])||c[k]<=0))throw new Error('invalid_capture_budget');};validate(config);
 if(v['switch-selector']&&!['switch-config','switch-locale','switch-text'].every(k=>v[k]?.trim()))throw new Error('switch_options_required');
 const switchConfig=v['switch-selector']?readinessConfig(JSON.parse(fs.readFileSync(v['switch-config'],'utf8'))):null;if(switchConfig)validate(switchConfig);
 const output=path.resolve(v.output);if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
 const {chromium}=require(path.join(path.resolve(v.runtime),'node_modules/playwright-core'));browser=await chromium.launch({executablePath:v['browser-executable'],headless:true});
 fs.mkdirSync(output,{recursive:true});const captures=[],http_records=[],switches=[],collection=[];
 const save=(name,value,raw=false)=>{const b=raw?Buffer.from(value):Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(output,name),b);return {path:name,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};};
 const manifest=()=>save('manifest.json',{schema_version:1,captures,http_records,switches,body_reviews:[],asset_mappings:[]});
 async function initial(response,prefix){
  if(!response)return;const requests=[];for(let req=response.request();req;req=req.redirectedFrom())requests.unshift(req);
  for(let i=0;i<requests.length;i++){
   const req=requests[i],res=await req.response();if(!res)continue;
   const headers=(await res.headersArray()).filter(h=>['content-type','location','link','x-robots-tag','retry-after','content-language','vary'].includes(h.name.toLowerCase())).map(h=>[h.name.toLowerCase(),h.value]);
   const row={url:req.url(),status:res.status(),method:req.method(),headers,checked_at:new Date().toISOString(),source:'actual isolated-browser main-document response chain',state:'completed'};
   http_records.push({...row,evidence:save(prefix+'-http-hop-'+i+'.json',row),evidence_kind:'actual_response_metadata'});
  }
  try{const raw=await response.body(),evidence=save(prefix+'-initial.html',raw,true);captures.push({url:response.url(),snapshot_id:'intl-http-'+randomUUID(),document_sha256:evidence.sha256,captured_at:new Date().toISOString(),source:'same actual main-document response',representation:'initial_html',entry_mode:'direct',state:response.ok()?'completed':'http_error',evidence});}catch(e){collection.push({reason:'initial_body_unavailable',detail:e.message});}
 }
 function keep(r,prefix,requested){
  if(!allowed(r.capture.url))throw new Error('capture_outside_site');
  const row={...r.capture,requested_url:requested,evidence:save(prefix+'-dom.html',r.html,true),browser_evidence:save(prefix+'-browser.json',r.browser),environment:{browser:'isolated Chromium '+browser.version(),device:'desktop',login:'unauthenticated',network:'local egress; geography unverified'}};
  captures.push(row);collection.push({phase:prefix,capture:row,unmet:r.unmet,samples:r.samples});manifest();return row;
 }
 try{
  const page=await browser.newPage();await protectPage(page);const response=await page.goto(v.url,{waitUntil:'domcontentloaded',timeout:30000});await initial(response,'before');manifest();
  const before=await collectInternational(page,config);keep(before,'before',v.url);
  if(v['switch-selector']&&before.capture.readiness==='ready'){
   if(v['menu-selector'])await page.locator(v['menu-selector']).first().click();
   const r=await performLanguageSwitch(page,before,v['switch-selector'],switchConfig,{expectedText:v['switch-text'],expectedLocale:v['switch-locale']});keep(r.after,'after');switches.push(save('switch-action.json',r.action));manifest();
  }
 }catch(e){collection.push({reason:'collection_failed',detail:e.message});manifest();save('collection.json',{signals:config,observations:collection});throw e;}
 save('collection.json',{signals:config,observations:collection});manifest();
 const partial=captures.some(c=>c.representation==='rendered_html'&&c.readiness!=='ready');console.log(JSON.stringify({status:partial?'partial_capture':'ready',captures:captures.length,http_records:http_records.length,switches:switches.length,output}));process.exitCode=partial?2:0;
}catch(error){console.error(JSON.stringify({status:'error',reason:error.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
