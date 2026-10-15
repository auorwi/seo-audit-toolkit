#!/usr/bin/env python3
"""Replay website media evidence and update an idempotent local issue history."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from media_audit.adapters import load_manifest
from media_audit.audit import audit
from media_audit.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('manifest','state','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=24);a=p.parse_args()
    try:
        if a.output.exists() and any(a.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(a.manifest,at=a.at,max_age_hours=a.max_age_hours);result=audit(inputs,at=a.at,max_age_hours=a.max_age_hours)
        run=record(a.state/'issues.sqlite',result);write_report(a.output,result,history(a.state/'issues.sqlite'))
        partial=not result['coverage']['declared_checks_complete'];print(json.dumps({'status':'partial_review' if partial else 'completed_scoped_audit','run_id':run,'findings':len(result['findings']),'gaps':len(result['gaps']),'coverage':result['coverage'],'output':str(a.output.resolve())},ensure_ascii=False));return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('Media audit error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
