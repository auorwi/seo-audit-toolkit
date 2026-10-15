#!/usr/bin/env node
/** Isolated read-only public website media collection. No clicks, forms or playback. */
import {allowed,readinessConfig,protectPage} from '../../seo-crawlability/scripts/site.mjs';
import fs from 'node:fs';import path from 'node:path';import {parseArgs} from 'node:util';import {createRequire} from 'node:module';import {createHash} from 'node:crypto';
import {installMediaObserver,observeResponses,collectMedia} from './collect_media.mjs';
const require=createRequire(import.meta.url);let browser;

try{
 const {values:v}=parseArgs({options:Object.fromEntries(['url','device','config','runtime','browser-executable','output'].map(k=>[k,{type:'string'}])),strict:true});
 if(!allowed(v.url))throw new Error('unsupported_target');if(!['desktop','mobile'].includes(v.device))throw new Error('device_required');
 const config=readinessConfig(v.config?JSON.parse(fs.readFileSync(v.config,'utf8')):{});
 if(!['mainSelector','identitySelector','placeholderSelector','errorSelector'].every(k=>typeof config[k]==='string'&&config[k].trim())||(config.identityRequired&&!config.expectedIdentity?.trim()))throw new Error('template_signals_required');
 for(const [key,max] of Object.entries({maxImages:1000,maxCssElements:10000,decodeTimeoutMs:5000,timeoutMs:60000,stableWindowMs:10000,sampleIntervalMs:5000}))if(key in config&&(!Number.isInteger(config[key])||config[key]<=0||config[key]>max))throw new Error('invalid_'+key);
 const output=path.resolve(v.output);if(fs.existsSync(output)&&fs.readdirSync(output).length)throw new Error('output_directory_not_empty');
 const {chromium}=require(path.join(path.resolve(v.runtime),'node_modules/playwright-core'));browser=await chromium.launch({executablePath:v['browser-executable'],headless:true});
 fs.mkdirSync(output,{recursive:true});const manifest={schema_version:1,scope:[{url:v.url,devices:[v.device]}],captures:[],reviews:[]},events=[];
 const keep=(name,data)=>{const bytes=Buffer.isBuffer(data)?data:Buffer.from(JSON.stringify(data,null,2)+'\n');fs.writeFileSync(path.join(output,name),bytes);return {path:name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')};};
 const persist=()=>{keep('manifest.json',manifest);keep('collection.json',{events,config});};
 try{
  const opts=v.device==='mobile'?{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,userAgent:'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'+browser.version()+' Mobile Safari/537.36'}:{viewport:{width:1440,height:900},deviceScaleFactor:1};
  const context=await browser.newContext({...opts,locale:'en-US'}),page=await context.newPage();await protectPage(page);await installMediaObserver(page);const network=observeResponses(page);
  const response=await page.goto(v.url,{waitUntil:'domcontentloaded',timeout:30000});events.push({type:'navigation',requested_url:v.url,url:page.url(),status:response?.status()??null,at:new Date().toISOString()});
  if(!allowed(page.url()))throw new Error('landing_outside_site');
  const capture=await collectMedia(page,config);if(!allowed(capture.url))throw new Error('capture_outside_site');
  capture.responses=await network.finish();capture.requested_url=v.url;capture.device=v.device;
  capture.environment={browser:browser.version(),emulated:true,context:opts,locale:'en-US',login:'unauthenticated',geography:'unverified'};
  try{capture.screenshot=keep('viewport.png',await page.screenshot({timeout:10000}));capture.screenshot_captured_at=new Date().toISOString();}
  catch(e){capture.gaps.push('screenshot_unavailable');events.push({type:'screenshot_error',reason:e.message});}
  manifest.captures.push(keep(capture.snapshot_id+'.json',capture));persist();
  if(config.scrollSelector&&capture.readiness==='ready'){
   const target=page.locator(config.scrollSelector);if(await target.count()!==1)throw new Error('scroll_target_not_unique');
   const scrolledNetwork=observeResponses(page),started_at=new Date().toISOString();await target.scrollIntoViewIfNeeded({timeout:5000});
   const after=await collectMedia(page,{...config,phase:'after_explicit_scroll'});if(!allowed(after.url))throw new Error('capture_outside_site');
   after.responses=await scrolledNetwork.finish();after.requested_url=v.url;after.device=v.device;after.environment=capture.environment;
   after.scroll_action={selector:config.scrollSelector,started_at,finished_at:new Date().toISOString(),action:'scroll only; no playback or clicks'};
   try{after.screenshot=keep('scrolled-viewport.png',await page.screenshot({timeout:10000}));after.screenshot_captured_at=new Date().toISOString();}catch(e){after.gaps.push('screenshot_unavailable');}
   manifest.captures.push(keep(after.snapshot_id+'.json',after));persist();if(after.readiness!=='ready')process.exitCode=2;
  }
  console.log(JSON.stringify({status:'captured_pending_purpose_review',device:v.device,readiness:capture.readiness,captures:manifest.captures.length,media:capture.media.length,responses:capture.responses.length,output}));if(capture.readiness!=='ready')process.exitCode=2;
 }catch(e){events.push({type:'collection_failed',reason:e.message,at:new Date().toISOString()});persist();throw e;}
}catch(e){console.error(JSON.stringify({status:'error',reason:e.message}));process.exitCode=1;}
finally{if(browser)await browser.close();}
