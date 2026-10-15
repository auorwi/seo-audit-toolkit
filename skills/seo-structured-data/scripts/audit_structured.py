#!/usr/bin/env python3
"""Audit explicit website structured-data captures and real external evidence."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from structured_audit.adapters import load_manifest
from structured_audit.audit import audit
from structured_audit.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--supplement',type=Path,action='append',default=[])
    p.add_argument('--urls',type=Path);p.add_argument('--url',action='append',default=[]);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=168);args=p.parse_args()
    try:
        targets=list(args.url)
        if args.urls:
            more=json.loads(args.urls.read_text())
            if not isinstance(more,list):raise ValueError('url_array_required')
            targets+=more
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in ['captures','engine_reports','gaps']:inputs[key]+=more[key]
            if more['vocabulary']:
                if inputs['vocabulary'] and inputs['vocabulary']!=more['vocabulary']:raise ValueError('conflicting_vocabulary_snapshots')
                inputs['vocabulary']=more['vocabulary']
        result=audit(inputs['captures'],targets,at=args.at,max_age_hours=args.max_age_hours,vocabulary=inputs['vocabulary'],engine_reports=inputs['engine_reports']);result['input_gaps']=inputs['gaps']
        run=record(args.state/'issues.sqlite',result);write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(result['gaps'] or result['input_gaps'] or result['pending_reviews'])
        print(json.dumps({'run_id':run,'status':'partial_review' if partial else 'completed_scoped_audit','urls':len(result['scope']),'findings':len(result['findings']),'examples':len(result['examples']),'output':str(args.output.resolve())},ensure_ascii=False));return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:print('Structured audit input/output error: '+str(error),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
