/** Explicit reloadable URL scope; live clients must additionally reject private DNS. */
import fs from 'node:fs';
import net from 'node:net';
import dns from 'node:dns/promises';
const sensitive=new Set('access_token refresh_token token id_token password passwd secret api_key apikey session sessionid authorization email auth_code client_secret cookie set-cookie appsecret'.split(' '));
function host(value){
 if(typeof value!=='string'||!value||value!==value.trim()||/[/?#@*\\]/.test(value)||value.endsWith('.'))throw Error('invalid_profile_hostname');
 if(!/^[\x00-\x7f]*$/.test(value))throw Error('Unicode hostnames are not supported; use explicit ASCII punycode A-labels');
 if(/^[0-9.]+$/.test(value)&&!net.isIP(value))throw Error('noncanonical_ip_literal');
 const h=value.toLowerCase();
 if(net.isIP(value))return value.toLowerCase();
 if(!h||h.length>253||h.split('.').some(v=>! /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(v)))throw Error('invalid_profile_hostname');return h;
}
function publicHost(h){
 const type=net.isIP(h);
 if(type===4){const a=h.split('.').map(Number);return !(a[0]===0||a[0]===10||a[0]===127||a[0]>=224||(a[0]===169&&a[1]===254)||(a[0]===172&&a[1]>=16&&a[1]<=31)||(a[0]===192&&a[1]===168)||(a[0]===100&&a[1]>=64&&a[1]<=127)||(a[0]===198&&(a[1]===18||a[1]===19))||(a[0]===192&&a[1]===0)||(a[0]===198&&a[1]===51&&a[2]===100)||(a[0]===203&&a[1]===0&&a[2]===113));}
 if(type===6)return /^[23]/.test(h)&&!h.startsWith('2001:db8:');
 return h.includes('.')&&!/(?:\.localhost|\.local|\.internal|\.test|\.invalid)$/.test(h);
}
function scoped(value,p){
 if(typeof value!=='string'||!value||/[\x00-\x20\x7f\\]/.test(value))return false;
 try{const u=new URL(value);const h=host(u.hostname.replace(/^\[|\]$/g,''));
 // WHATWG normalizes noncanonical IPv4; require the supplied authority to match host policy too.
 const authority=value.match(/^https?:\/\/([^/;?#]+)/i)?.[1];if(!authority||authority.includes('@'))return false;
 const rawHost=authority.startsWith('[')?authority.slice(1,authority.indexOf(']')):authority.split(':')[0];
 if(host(rawHost)!==h||!(p.allowed_schemes??['http','https']).includes(u.protocol.slice(0,-1))||u.username||u.password||!p.allowed_hosts.includes(h))return false;
 const loop=h==='localhost'||h==='::1'||/^127\./.test(h);
 if(loop&&p.test_only_allow_loopback){if(u.protocol!=='http:'||Number(u.port)!==p.fixture_port)return false;}
 else if(!publicHost(h)||u.port)return false;
 return ![...u.searchParams.keys()].some(k=>sensitive.has(k.toLowerCase()));
 }catch{return false;}
}
function noCredentials(value){
 if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){
  if(!Array.isArray(value)&&sensitive.has(key.toLowerCase().replaceAll('-','_')))throw Error('credentials_not_allowed_in_profile');
  noCredentials(item);
 }
}
export function getProfile(){
 if(!process.env.SEO_SITE_PROFILE)throw Error('SEO_SITE_PROFILE_required');
 const p=JSON.parse(fs.readFileSync(process.env.SEO_SITE_PROFILE,'utf8'));noCredentials(p);
 if(!p||typeof p!=='object'||Array.isArray(p))throw Error('invalid_site_profile');p.site=host(p.site);
 if(!Array.isArray(p.allowed_hosts)||!p.allowed_hosts.length)throw Error('profile_requires_allowed_hosts');p.allowed_hosts=p.allowed_hosts.map(host);
 if(!p.allowed_hosts.includes(p.site))throw Error('site_must_be_allowed');
 if(!['generic','bingx'].includes(p.business_profile??'generic'))throw Error('unknown_business_profile');
 if(typeof (p.brand??'')!=='string')throw Error('invalid_brand');
 if(typeof (p.test_only_allow_loopback??false)!=='boolean')throw Error('invalid_fixture_option');
 if(p.test_only_allow_loopback&&(!Number.isInteger(p.fixture_port)||p.fixture_port<1||p.fixture_port>65535))throw Error('fixture_port_required');
 if(typeof (p.allow_system_dns_alias??false)!=='boolean')throw Error('invalid_dns_alias_option');
 if(!Array.isArray(p.allowed_schemes??['http','https'])||!(p.allowed_schemes??['http','https']).length||(p.allowed_schemes??['http','https']).some(s=>!['http','https'].includes(s)))throw Error('invalid_allowed_schemes');
 for(const key of ['seeds','sitemaps'])if(!Array.isArray(p[key]??[])||(p[key]??[]).some(u=>!scoped(u,p)))throw Error('invalid_profile_'+key);
 if(!Array.isArray(p.excluded_path_patterns??[])||(p.excluded_path_patterns??[]).some(v=>typeof v!=='string'))throw Error('invalid_excluded_path_patterns');
 for(const pattern of p.excluded_path_patterns??[])new RegExp(pattern);
 if(!Number.isInteger(p.query_variants_per_path??2)||(p.query_variants_per_path??2)<0)throw Error('invalid_query_variant_limit');return p;
}
export function allowed(value){try{return scoped(value,getProfile());}catch{return false;}}
export function requireUrl(value){if(!allowed(value))throw Error('outside_configured_site_or_unsafe_url');return value;}

/** Generic readiness observes stable visible document text; it never verifies business identity. */
export function readinessConfig(value={}) {
 let profile={};try{profile=getProfile();}catch{}
 const required=value.identityRequired??(profile.readiness?.require_identity||Boolean(value.expectedIdentity?.trim())||Boolean(value.identitySelector?.trim()));
 return {mainSelector:'body',identitySelector:':root > __seo_identity_not_configured__',expectedIdentity:'',placeholderSelector:'[aria-busy="true"]',errorSelector:'[data-seo-page-error]',fieldSelectors:{},...value,identityRequired:required,identityVerified:false,readinessBasis:required?'caller_configured_identity_and_content':'generic_visible_content_and_stability; business identity unverified'};
}
/** Reject an out-of-scope navigation before any document request, including redirect hops. */
export async function protectPage(page) {
 // Playwright routing sees only the first URL of a redirected request. CDP Fetch
 // pauses every hop, so an allowed first response cannot send us outside scope.
 const session=await page.context().newCDPSession(page);
 session.on('Fetch.requestPaused',async event=>{
  const {requestId,request,resourceType}=event;
  const block=()=>session.send('Fetch.failRequest',{requestId,errorReason:'BlockedByClient'}).catch(()=>{});
  if(resourceType==='Document'&&!allowed(request.url))return block();
  try {
   const target=new URL(request.url);
   if(!['http:','https:'].includes(target.protocol))return block();
   const h=target.hostname.replace(/^\[|\]$/g,'');const profile=getProfile();
   const fixture=profile.test_only_allow_loopback&&allowed(target.href);
   if(!fixture){
    const addresses=net.isIP(h)?[{address:h}]:await dns.lookup(h,{all:true});
    if(!addresses.length||addresses.some(a=>!publicHost(a.address)))return block();
   }
   await session.send('Fetch.continueRequest',{requestId});
  } catch {return block();}
 });
 await session.send('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
 return session;
}
