#!/usr/bin/env python3
"""Audit supplied performance evidence and maintain stable issue history."""
import argparse,json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
from cwv_audit.adapters import load_manifest
from cwv_audit.audit import audit
from cwv_audit.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','state','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--supplement',type=Path,action='append',default=[]);p.add_argument('--baseline',type=Path);p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=168);args=p.parse_args()
    try:
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in inputs:inputs[key]+=more[key]
        baseline=None;proof=None
        if args.baseline:
            raw=args.baseline.read_bytes();baseline=json.loads(raw)
            if not isinstance(baseline,dict) or baseline.get('skill')!='011':raise ValueError('invalid_baseline_report')
            proof={'path':str(args.baseline.resolve()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        result=audit(inputs,at=args.at,max_age_hours=args.max_age_hours,baseline=baseline);result['baseline_evidence']=proof;run=record(args.state/'issues.sqlite',result);write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(result['gaps'] or result['pending_reviews']);print(json.dumps({'status':'partial_review' if partial else 'completed_scoped_audit','run_id':run,'findings':len(result['findings']),'coverage':result['coverage'],'output':str(args.output.resolve())},ensure_ascii=False));return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('CWV input/output error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
