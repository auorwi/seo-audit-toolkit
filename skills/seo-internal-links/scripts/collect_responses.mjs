/** Observe actual browser redirect requests; retain only diagnostic response headers. */
export async function observeRedirectChain(response){
  const requests=[];let request=response?.request();const seen=new Set();
  while(request&&!seen.has(request)){seen.add(request);requests.unshift(request);request=request.redirectedFrom();}
  const rows=[];
  for(const request of requests){
    const current=await request.response();
    const headers=current?(await current.headersArray()).filter(x=>['content-type','location','x-robots-tag','retry-after'].includes(x.name.toLowerCase())).map(x=>[x.name.toLowerCase(),x.value]):[];
    rows.push({url:request.url(),status:current?.status()??null,method:request.method(),headers,checked_at:new Date().toISOString(),source:'actual isolated-browser main-document response chain',state:current?'completed':'unavailable'});
  }
  return rows;
}
