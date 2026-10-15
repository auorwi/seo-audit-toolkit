#!/usr/bin/env python3
"""Audit evidence-bound international SEO and retain stable issue history."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from international_audit.adapters import load_manifest
from international_audit.audit import audit
from international_audit.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','state','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--supplement',type=Path,action='append',default=[]);p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=168);args=p.parse_args()
    try:
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in inputs:inputs[key]+=more[key]
        result=audit(inputs,at=args.at,max_age_hours=args.max_age_hours);run=record(args.state/'issues.sqlite',result);write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(result['gaps'] or result['pending_reviews']);print(json.dumps({'run_id':run,'status':'partial_review' if partial else 'completed_scoped_audit','findings':len(result['findings']),'coverage':result['coverage'],'output':str(args.output.resolve())},ensure_ascii=False));return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('International audit input/output error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
