#!/usr/bin/env node
/** Public website capture with optional explicitly configured calculator input trials. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';import path from 'node:path';import {parseArgs} from 'node:util';import {createRequire} from 'node:module';import {createHash} from 'node:crypto';
import {collectContent,performTrial,performScenario} from './collect_content.mjs';
const require=createRequire(import.meta.url);let browser;

try{
 const {values:v}=parseArgs({options:Object.fromEntries(['url','config','runtime','browser-executable','output'].map(k=>[k,{type:'string'}])),strict:true});
 if(!allowed(v.url))throw new Error('unsupported_target');
 const config=readinessConfig(v.config?JSON.parse(fs.readFileSync(v.config,'utf8')):{});
 if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof config[k]==='string'&&config[k].trim())||(config.identityRequired&&!config.expectedIdentity?.trim())||!config.fieldSelectors||typeof config.fieldSelectors!=='object')throw new Error('template_signals_required');
 for(const key of ['timeoutMs','stableWindowMs','sampleIntervalMs','interactionDwellMs'])if(key in config&&(!Number.isFinite(config[key])||config[key]<=0||config[key]>60000))throw new Error('invalid_capture_budget');
 if(config.trials&&!Array.isArray(config.trials))throw new Error('trial_array_required');
 for(const trial of config.trials??[])if(!trial.inputSelector||!['asset_to_quote','quote_to_asset'].includes(trial.direction)||typeof trial.quantity!=='string'||!/^\d+(\.\d+)?$/.test(trial.quantity))throw new Error('invalid_trial');
 const output=path.resolve(v.output);if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
 const {chromium}=require(path.join(path.resolve(v.runtime),'node_modules/playwright-core'));browser=await chromium.launch({executablePath:v['browser-executable'],headless:true});
 fs.mkdirSync(output,{recursive:true});const manifest={schema_version:1,scope:[{url:v.url,kinds:config.kinds??['pair']}],captures:[],actions:[],reviews:[]};const events=[];
 const save=(name,value)=>{const b=Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(output,name),b);return {path:name,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};};
 const keep=c=>{if(!allowed(c.url))throw new Error('capture_outside_site');manifest.captures.push(save(c.snapshot_id+'.json',{...c,requested_url:v.url,environment:{browser:browser.version(),login:'unauthenticated',geography:'unverified',device:'desktop'}}));};
 const persist=()=>{save('manifest.json',manifest);save('collection.json',{events,config});};
 try{
  const page=await browser.newPage();await protectPage(page);const response=await page.goto(v.url,{waitUntil:'domcontentloaded',timeout:30000});
  events.push({type:'navigation',requested_url:v.url,url:page.url(),status:response?.status()??null,at:new Date().toISOString()});
  const initial=await collectContent(page,config);keep(initial);persist();
  for(const trial of config.trials??[]){
   const result=await performTrial(page,{...config,fieldSelectors:trial.fieldSelectors??config.fieldSelectors},trial);keep(result.before);keep(result.after);manifest.actions.push(save(result.action.action_id+'.json',result.action));persist();
  }
  for(const scenario of config.scenarioTrials??[]){
   const result=await performScenario(page,config,scenario);keep(result.before);keep(result.after);manifest.actions.push(save(result.action.action_id+'.json',result.action));persist();
  }
  try{await page.screenshot({path:path.join(output,'final-viewport.png'),timeout:10000});}catch(e){events.push({type:'screenshot_unavailable',reason:e.message});}
  persist();console.log(JSON.stringify({status:'captured_pending_semantic_review',captures:manifest.captures.length,actions:manifest.actions.length,output}));
  if(initial.readiness!=='ready')process.exitCode=2;
 }catch(e){events.push({type:'collection_failed',reason:e.message,at:new Date().toISOString()});persist();throw e;}
}catch(e){console.error(JSON.stringify({status:'error',reason:e.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
