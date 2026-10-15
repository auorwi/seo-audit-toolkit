#!/usr/bin/env python3
"""Replay evidence-bound content integrity checks without network access."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from content_integrity.adapters import load_manifest
from content_integrity.audit import audit
from content_integrity.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','state','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=24);args=p.parse_args()
    try:
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest,at=args.at,max_age_hours=args.max_age_hours);result=audit(inputs,at=args.at,max_age_hours=args.max_age_hours)
        run=record(args.state/'issues.sqlite',result);write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=not result['coverage']['declared_checks_complete'];print(json.dumps({'run_id':run,'status':'partial_review' if partial else 'completed_scoped_audit','findings':len(result['findings']),'coverage':result['coverage'],'output':str(args.output.resolve())},ensure_ascii=False));return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('Content audit error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
