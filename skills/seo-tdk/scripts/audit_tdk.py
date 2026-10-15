#!/usr/bin/env python3
"""Audit scoped website metadata from preserved source/browser evidence."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from tdk_audit.adapters import load_manifest
from tdk_audit.audit import audit
from tdk_audit.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--supplement',type=Path,action='append',default=[])
    p.add_argument('--urls',type=Path);p.add_argument('--url',action='append',default=[])
    p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=168)
    args=p.parse_args()
    try:
        urls=list(args.url)
        if args.urls:
            extra=json.loads(args.urls.read_text())
            if not isinstance(extra,list):raise ValueError('url_array_required')
            urls+=extra
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in inputs:inputs[key]+=more[key]
        result=audit(inputs['captures'],urls,at=args.at,max_age_hours=args.max_age_hours);result['input_gaps']=inputs['gaps']
        run=record(args.state/'issues.sqlite',result);write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(result['gaps'] or inputs['gaps'] or any(r['topics'] for r in result['pending_reviews']))
        print(json.dumps({'run_id':run,'status':'partial_review' if partial else 'completed_scoped_audit','urls':len(result['scope']),'findings':len(result['findings']),'drafts':len(result['drafts']),'output':str(args.output.resolve())},ensure_ascii=False))
        return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('TDK audit input/output error: '+str(error),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
