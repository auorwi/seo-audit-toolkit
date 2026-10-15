#!/usr/bin/env node
/** Standalone TDK acquisition. No axe or other complete SEO audit is invoked. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {createRequire} from 'node:module';
import {createHash,randomUUID} from 'node:crypto';
import {collectMetadata} from './collect_metadata.mjs';
const require=createRequire(import.meta.url);let browser;
try{
  const {values}=parseArgs({options:Object.fromEntries(['url','config','runtime','browser-executable','output'].map(k=>[k,{type:'string',multiple:true}])),strict:true});
  const v=Object.fromEntries(Object.entries(values).map(([k,arr])=>[k,arr.at(-1)]));
  let target;try{target=new URL(v.url);}catch{throw new Error('unsupported_target');}
  if(!allowed(v.url))throw new Error('unsupported_target');
  const config=readinessConfig(v.config?JSON.parse(fs.readFileSync(v.config,'utf8')):{});
  if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof config[k]==='string'&&config[k].trim())||(config.identityRequired&&!config.expectedIdentity?.trim()))throw new Error('template_signals_required');
  for(const key of ['timeoutMs','stableWindowMs','sampleIntervalMs'])if(key in config&&(!Number.isFinite(config[key])||config[key]<=0))throw new Error('invalid_capture_budget');
  if('dynamicTitle' in config&&typeof config.dynamicTitle!=='boolean')throw new Error('invalid_dynamic_title');
  const output=path.resolve(v.output);if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
  const {chromium}=require(path.join(path.resolve(v.runtime),'node_modules/playwright-core'));
  browser=await chromium.launch({executablePath:v['browser-executable'],headless:true});const page=await browser.newPage();await protectPage(page);
  const response=await page.goto(target.href,{waitUntil:'domcontentloaded',timeout:30000});
  if(!allowed(page.url()))throw new Error('navigation_outside_site');
  const httpAt=new Date().toISOString();let initial=null,initialError=null;
  try{if(response)initial=await response.body();}catch(error){initialError=error.message;}
  const result=await collectMetadata(page,config);fs.mkdirSync(output,{recursive:true});
  const save=(name,value,raw=false)=>{const body=raw?Buffer.from(value):Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(output,name),body);return {path:name,bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')};};
  const evidence=save('dom.html',result.html,true);const capture={...result.capture,evidence,requested_url:target.href,
    environment:{browser:'isolated Chromium '+browser.version(),device:'desktop',login:'unauthenticated',network:'local egress; geography unverified'}};
  const captures=[capture];
  if(initial){const proof=save('initial.html',initial,true);captures.push({url:response.url(),snapshot_id:'tdk-http-'+randomUUID(),captured_at:httpAt,source:'same browser navigation main-document response body',representation:'initial_html',readiness:null,evidence:proof,document_sha256:proof.sha256,http_status:response.status(),state:response.ok()?'completed':'http_error'});}
  save('capture.json',capture);save('collection.json',{samples:result.samples,unmet:result.unmet,readiness_evidence:result.readiness_evidence,collection_ms:result.collection_ms,initial_error:initialError,template_signals:config});
  save('manifest.json',{schema_version:1,captures});save('urls.json',[capture.url]);
  console.log(JSON.stringify({status:capture.readiness,url:capture.url,output}));process.exitCode=capture.readiness==='ready'?0:2;
}catch(error){console.error(JSON.stringify({status:'error',reason:error.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
