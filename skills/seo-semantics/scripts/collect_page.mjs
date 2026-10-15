#!/usr/bin/env node
/** Public-page evidence CLI. Requires a caller-selected isolated browser runtime. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {collectSemantics} from './collect_semantics.mjs';

const require=createRequire(import.meta.url);
let browser;
try{
  const {values}=parseArgs({options:Object.fromEntries(['url','config','runtime','browser-executable','output','scope'].map(k=>[k,{type:'string'}])),strict:true});
  let target;
  try{target=new URL(values.url);}catch{throw new Error('unsupported_target');}
  if(!allowed(values.url))throw new Error('unsupported_target');
  if(values.scope){
    const scope=JSON.parse(fs.readFileSync(values.scope,'utf8'));
    if(scope.schema_version!==1||!Array.isArray(scope.targets)||scope.count!==scope.targets.length)throw new Error('invalid_scope_plan');
    const identity=url=>{const u=new URL(url);u.hash='';return u.href;};
    if(!scope.targets.some(row=>identity(row.url)===identity(values.url)))throw new Error('url_not_in_scope');
  }
  const config=readinessConfig(values.config?JSON.parse(fs.readFileSync(values.config,'utf8')):{});
  if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof config[k]==='string'&&config[k].trim())||(config.identityRequired&&!config.expectedIdentity?.trim()))throw new Error('template_signals_required');
  for(const key of ['timeoutMs','stableWindowMs','sampleIntervalMs'])if(key in config&&(!Number.isFinite(config[key])||config[key]<=0))throw new Error('invalid_capture_budget');
  const output=path.resolve(values.output);
  if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
  const runtime=path.resolve(values.runtime);
  const {chromium}=require(path.join(runtime,'node_modules/playwright-core'));
  const axe=require(path.join(runtime,'node_modules/axe-core'));
  browser=await chromium.launch({executablePath:values['browser-executable'],headless:true});
  const page=await browser.newPage();await protectPage(page);
  await page.goto(target.href,{waitUntil:'domcontentloaded',timeout:30000});
  if(!allowed(page.url()))throw new Error('navigation_outside_site');
  const result=await collectSemantics(page,{...config,axeSource:axe.source});
  const capture=result.capture;
  capture.environment={browser:'isolated Chromium '+browser.version(),device:'desktop',network:'local egress; geography unverified',login:'fresh unauthenticated context'};
  const record={tool:'axe',url:capture.url,checked_at:new Date().toISOString(),source:'isolated public browser + actual axe-core',
    capture_id:capture.snapshot_id+'-axe',document_sha256:result.document_sha256,input_sha256:result.axe_input_sha256,after_sha256:result.after_axe_sha256,
    checker_version:result.axe?.testEngine?.version??axe.version,representation:'rendered_dom',readiness:capture.readiness,
    state:result.axe?(result.document_sha256===result.axe_input_sha256&&result.after_axe_sha256===result.axe_input_sha256?'completed':'dom_changed_during_check'):'not_run',payload:result.axe??{}};
  fs.mkdirSync(output,{recursive:true});
  const save=(name,value,raw=false)=>{
    const body=Buffer.from(raw?value:JSON.stringify(value,null,2)+'\n','utf8');fs.writeFileSync(path.join(output,name),body);
    return {path:name,bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')};
  };
  const document=save('dom.html',result.html,true);
  const elements=save('elements.json',capture);const tool=save('axe.capture.json',record);
  save('axe.json',result.axe);save('collection.json',{requested_url:target.href,final_url:capture.url,scope_file:values.scope??null,document_sha256:result.document_sha256,axe_input_sha256:result.axe_input_sha256,after_axe_sha256:result.after_axe_sha256,unmet:result.unmet,readiness_samples:result.readiness_samples,collection_ms:result.collection_ms,template_signals:config});
  save('manifest.json',{schema_version:1,captures:[{kind:'rendered_elements',url:capture.url,snapshot_id:capture.snapshot_id,captured_at:capture.captured_at,source:capture.source,evidence:elements,document_evidence:document}],
    tool_reports:[{tool:'axe',url:record.url,capture_id:record.capture_id,checked_at:record.checked_at,evidence:tool,document_evidence:document}]});
  console.log(JSON.stringify({status:capture.readiness,axe_state:record.state,url:capture.url,output,manifest:path.join(output,'manifest.json')}));
  process.exitCode=capture.readiness==='ready'&&record.state==='completed'?0:2;
}catch(error){console.error(JSON.stringify({status:'error',reason:error.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
