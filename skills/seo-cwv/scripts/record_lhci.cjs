/** Preserve every real LHCI run, including attempts hidden by its retry loop. */
const fs=require('node:fs');const path=require('node:path');const {randomUUID}=require('node:crypto');
const root=process.env.CWV_ATTEMPTS_DIR,runtime=process.env.CWV_RUNTIME;
if(!root||!runtime)throw new Error('CWV evidence environment required');
const Runner=require(path.join(runtime,'node_modules/@lhci/cli/src/collect/node-runner.js'));
const original=Runner.prototype.run;
Runner.prototype.run=async function(url,options){
 fs.mkdirSync(root,{recursive:true});const id=randomUUID(),meta=path.join(root,id+'.json');
 const record={run_id:id,url,state:'started',started_at:new Date().toISOString(),source:'actual pinned LHCI node runner invocation'};
 const write=()=>{fs.writeFileSync(meta+'.tmp',JSON.stringify(record,null,2)+'\n');fs.renameSync(meta+'.tmp',meta);};write();
 try{
  const raw=await original.call(this,url,options);record.lhr_file=id+'.lhr.json';fs.writeFileSync(path.join(root,record.lhr_file),raw);
  record.state='completed';record.finished_at=new Date().toISOString();write();return raw;
 }catch(error){
  record.state='failed';record.finished_at=new Date().toISOString();record.error={message:error.message};
  if(error.stdout){record.stdout_file=id+'.stdout.txt';fs.writeFileSync(path.join(root,record.stdout_file),error.stdout);}
  if(error.stderr){record.stderr_file=id+'.stderr.txt';fs.writeFileSync(path.join(root,record.stderr_file),error.stderr);}
  write();throw error;
 }
};
