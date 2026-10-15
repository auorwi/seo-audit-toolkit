#!/usr/bin/env python3
"""Serial, resumable CWV-only LHCI measurement grid. Does not upload reports."""
import argparse,json,hashlib,platform,time,sys,os
from pathlib import Path
from datetime import datetime,timezone
from cwv_audit.runner import build_collect_config,run_lhci_cell,PerformanceLock
from cwv_audit.shared import url_id
from cwv_audit.environment import preflight

def proof(path,root):
    raw=path.read_bytes();return {'path':str(path.relative_to(root)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['urls-file','runtime','chrome','output','lock']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--device',choices=['mobile','desktop'],action='append');p.add_argument('--runs',type=int,default=3);p.add_argument('--plan-only',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--budget-seconds',type=int,default=7200);p.add_argument('--cell-timeout-seconds',type=int,default=900);p.add_argument('--network-location',default='local-egress-geography-unverified');args=p.parse_args()
    try:
        if args.budget_seconds<1 or args.cell_timeout_seconds<1:raise ValueError('invalid_collection_budget')
        raw=json.loads(args.urls_file.read_text());raw=raw.get('urls') if isinstance(raw,dict) else raw
        if not isinstance(raw,list) or not raw:raise ValueError('url_array_required')
        urls=list(dict.fromkeys(url_id(x['url'] if isinstance(x,dict) else x) for x in raw));devices=list(dict.fromkeys(args.device or ['mobile','desktop']));runtime=args.runtime.resolve();output=args.output.resolve()
        versions={}
        for package in ['@lhci/cli','lighthouse']:
            file=runtime/'node_modules'/package/'package.json';versions[package]=json.loads(file.read_text()).get('version') if file.is_file() else None
        context={'runner':'lhci','host_id':hashlib.sha256((platform.node()+'|'+platform.platform()+'|'+platform.machine()).encode()).hexdigest()[:20],'network_location':args.network_location,'entry_mode':'direct','login':'unauthenticated','cache_mode':'cold_storage_reset','cpu_model':platform.processor() or platform.machine(),'source':'actual local LHCI collection','versions':versions}
        cells=[{'id':f'{i:03d}-{device}','url':url,'device':device,'config':build_collect_config(url,device,args.chrome,runs=args.runs)} for i,url in enumerate(urls,1) for device in devices]
        plan={'schema_version':1,'runtime':str(runtime),'chrome':str(args.chrome.resolve()),'context':context,'cells':cells};plan_hash=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest();plan['plan_hash']=plan_hash
        if output.exists() and any(output.iterdir()):
            if not args.resume:raise ValueError('output_directory_not_empty')
            previous=json.loads((output/'plan.json').read_text())
            if previous.get('plan_hash')!=plan_hash:raise ValueError('resume_plan_mismatch')
        else:output.mkdir(parents=True,exist_ok=True);(output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        def manifest():
            rows=[];statuses=[]
            for cell in cells:
                root=output/'cells'/cell['id'];saved=root/'cell.json'
                if not saved.is_file():statuses.append({'id':cell['id'],'state':'pending'});continue
                result=json.loads(saved.read_text());statuses.append({'id':cell['id'],'state':'attempted','exit_code':result['exit_code'],'timed_out':result['timed_out']})
                for a in result['attempts']:
                    row={k:a[k] for k in ['run_id','url','state','started_at','finished_at','source','error'] if k in a}
                    for kind in ['attempt','lhr','stdout','stderr']:
                        old=a.get(kind+'_evidence')
                        if old:row[kind+'_evidence']=proof(root/old['path'],output)
                    row['context_evidence']=proof(saved,output);rows.append(row)
            data={'schema_version':1,'lab_runs':rows,'field_records':[],'expected_cells':[{'url':c['url'],'device':c['device'],'minimum_valid_runs':3} for c in cells],'collection_status':statuses,'plan_hash':plan_hash,'collection_events':[proof(p,output) for p in sorted((output/'collection-events').glob('*.json'))]}
            (output/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');return data
        manifest()
        if args.plan_only:print(json.dumps({'status':'planned_only','cells':len(cells),'requested_runs':sum(c['config']['ci']['collect']['numberOfRuns'] for c in cells),'output':str(output)}));return 0
        if versions.get('@lhci/cli')!='0.15.1' or versions.get('lighthouse')!='12.6.1':raise ValueError('unvalidated_runtime_version')
        if not args.chrome.is_file():raise ValueError('chrome_executable_missing')
        started=time.monotonic()
        with PerformanceLock(args.lock):
            for cell in cells:
                root=output/'cells'/cell['id']
                if (root/'cell.json').exists():continue
                remaining=args.budget_seconds-(time.monotonic()-started)
                if remaining<5:break
                if root.exists() and any(root.iterdir()):raise ValueError('interrupted_cell_requires_review: '+str(root))
                quality=preflight();events=output/'collection-events';events.mkdir(exist_ok=True)
                event={'source':'host_preflight','observed_at':datetime.now(timezone.utc).isoformat(),'cell_id':cell['id'],'url':cell['url'],'device':cell['device'],'state':'ready_to_collect' if quality['suitable_for_regression'] else 'collection_paused','quality':quality}
                (events/(f'{len(list(events.glob("*.json")))+1:04d}.json')).write_text(json.dumps(event,ensure_ascii=False,indent=2)+'\n')
                if not quality['suitable_for_regression']:
                    manifest();print(json.dumps({'status':'collection_paused','reason':quality['status'],'cell':cell['id'],'pending_scope_preserved':True},ensure_ascii=False),flush=True);break
                print(json.dumps({'status':'measuring','cell':cell['id'],'url':cell['url'],'device':cell['device']},ensure_ascii=False),flush=True)
                r=run_lhci_cell(root,cell['config'],runtime,Path(__file__).with_name('record_lhci.cjs'),context,timeout_seconds=min(args.cell_timeout_seconds,remaining));manifest()
                print(json.dumps({'status':'cell_saved','cell':cell['id'],'exit_code':r['exit_code'],'attempts':len(r['attempts'])},ensure_ascii=False),flush=True)
        result=manifest();pending=sum(x['state']=='pending' for x in result['collection_status']);failed=sum(x.get('exit_code',0)!=0 for x in result['collection_status']);print(json.dumps({'status':'collection_finished','pending_cells':pending,'failed_cells':failed,'output':str(output)},ensure_ascii=False));return 2 if pending or failed else 0
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as e:print('CWV collection error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
