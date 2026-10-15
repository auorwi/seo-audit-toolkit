#!/usr/bin/env node
/** Standalone public structured-data capture; optional observed internal anchor entry. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';import path from 'node:path';import {parseArgs} from 'node:util';import {createRequire} from 'node:module';import {createHash,randomUUID} from 'node:crypto';
import {collectStructured} from './collect_structured.mjs';
const require=createRequire(import.meta.url);let browser;

try{
  const {values}=parseArgs({options:Object.fromEntries(['url','config','runtime','browser-executable','output','entry-origin','entry-link'].map(k=>[k,{type:'string',multiple:true}])),strict:true});
  const v=Object.fromEntries(Object.entries(values).map(([k,a])=>[k,a.at(-1)]));if(!allowed(v.url))throw new Error('unsupported_target');
  if(Boolean(v['entry-origin'])!==Boolean(v['entry-link']))throw new Error('entry_contract_required');
  if(v['entry-origin']&&!allowed(v['entry-origin']))throw new Error('unsupported_entry_origin');
  const config=readinessConfig(v.config?JSON.parse(fs.readFileSync(v.config,'utf8')):{});
  if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof config[k]==='string'&&config[k].trim())||(config.identityRequired&&!config.expectedIdentity?.trim()))throw new Error('template_signals_required');
  for(const key of ['timeoutMs','stableWindowMs','sampleIntervalMs'])if(key in config&&(!Number.isFinite(config[key])||config[key]<=0))throw new Error('invalid_capture_budget');
  if('contentChecks' in config&&(!Array.isArray(config.contentChecks)||!config.contentChecks.every(c=>c&&typeof c.selector==='string'&&c.selector.trim()&&['requiredText','forbiddenText'].some(k=>typeof c[k]==='string'&&c[k].trim())&&['requiredText','forbiddenText'].every(k=>!(k in c)||(typeof c[k]==='string'&&c[k].trim())))))throw new Error('invalid_content_checks');
  const output=path.resolve(v.output);if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
  const {chromium}=require(path.join(path.resolve(v.runtime),'node_modules/playwright-core'));
  browser=await chromium.launch({executablePath:v['browser-executable'],headless:true});const page=await browser.newPage();await protectPage(page);
  let response=null,navigation={entry_mode:'direct',requested_url:v.url},initial=null,initialAt=null,initialError=null;
  if(v['entry-origin']){
    await page.goto(v['entry-origin'],{waitUntil:'domcontentloaded',timeout:30000});
    const link=page.locator(v['entry-link']).first();await link.waitFor({state:'visible',timeout:30000});
    const observed=await link.evaluate(el=>({tag:el.tagName,href:el.href,html:el.outerHTML}));
    if(observed.tag!=='A'||new URL(observed.href).href!==new URL(v.url).href)throw new Error('entry_link_does_not_match_requested_target');
    navigation={entry_mode:'internal',origin:page.url(),requested_url:v.url,observed_link:observed,clicked_at:new Date().toISOString()};
    await Promise.all([page.waitForURL(v.url,{timeout:30000}),link.click()]);
  }else{
    response=await page.goto(v.url,{waitUntil:'domcontentloaded',timeout:30000});initialAt=new Date().toISOString();
    try{if(response)initial=await response.body();}catch(error){initialError=error.message;}
  }
  if(!allowed(page.url()))throw new Error('navigation_outside_site');
  const result=await collectStructured(page,{...config,entryMode:navigation.entry_mode});
  if(!allowed(result.capture.url))throw new Error('capture_outside_site');
  fs.mkdirSync(output,{recursive:true});
  const save=(name,value,raw=false)=>{const b=raw?Buffer.from(value):Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(output,name),b);return {path:name,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};};
  const proof=save('dom.html',result.html,true),visible=save('visible.json',result.visible);
  const capture={...result.capture,evidence:proof,visible_evidence:visible,environment:{browser:'isolated Chromium '+browser.version(),device:'desktop',login:'unauthenticated',network:'local egress; geography unverified'}};
  const captures=[capture];
  if(initial){const evidence=save('initial.html',initial,true);captures.push({url:response.url(),snapshot_id:'structured-http-'+randomUUID(),captured_at:initialAt,document_sha256:evidence.sha256,source:'same direct browser navigation main-document response',representation:'initial_html',readiness:null,entry_mode:'direct',evidence,http_status:response.status(),state:response.ok()?'completed':'http_error'});}
  save('navigation.json',{...navigation,final_url:capture.url});save('collection.json',{schema_samples:result.schema_samples,unmet:result.unmet,structured_counts:result.structured_counts,readiness_evidence:result.readiness_evidence,collection_ms:result.collection_ms,initial_error:initialError,template_signals:config});
  save('manifest.json',{schema_version:1,captures});save('urls.json',[{url:capture.url,entries:[capture.entry_mode]}]);
  console.log(JSON.stringify({status:capture.readiness,url:capture.url,entry_mode:capture.entry_mode,structured_counts:result.structured_counts,output}));process.exitCode=capture.readiness==='ready'?0:2;
}catch(error){console.error(JSON.stringify({status:'error',reason:error.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
