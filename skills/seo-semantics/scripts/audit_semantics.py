#!/usr/bin/env python3
"""Run specialist 006 against explicit, locally verified evidence."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
from semantics_audit.adapters import load_manifest
from semantics_audit.audit import audit
from semantics_audit.report import write_report
from semantics_audit.scope import validate_plan
from crawlability.ledger import record,history

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--supplement',type=Path,action='append',default=[])
    parser.add_argument('--urls',type=Path);parser.add_argument('--url',action='append',default=[])
    parser.add_argument('--scope',type=Path,help='Frozen preflight scope; cannot be combined with --urls/--url')
    parser.add_argument('--state',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat());parser.add_argument('--max-age-hours',type=float,default=168)
    args=parser.parse_args()
    try:
        plan=None
        if args.scope:
            if args.urls or args.url:raise ValueError('scope_plan_cannot_be_overridden')
            plan=validate_plan(json.loads(args.scope.read_text(encoding='utf-8')))
        targets=list(args.url)
        if plan:targets=list(plan['targets'])
        if args.urls:
            extra=json.loads(args.urls.read_text(encoding='utf-8'))
            if not isinstance(extra,list):raise ValueError('url_array_required')
            targets+=extra
        if not targets:raise ValueError('explicit_nonempty_url_scope_required')
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in inputs:inputs[key]+=more[key]
        result=audit(inputs['captures'],inputs['tool_reports'],targets,at=args.at,max_age_hours=args.max_age_hours)
        result['input_gaps']=inputs['gaps']
        if plan:result['scope_plan']=plan
        run_id=record(args.state/'issues.sqlite',result)
        write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(result['gaps'] or result['input_gaps'] or any(r['topics'] for r in result['pending_reviews']))
        print(json.dumps({'run_id':run_id,'status':'partial_review' if partial else 'completed_scoped_audit','urls':len(result['scope']),
            'findings':len(result['findings']),'handoffs':len(result['handoffs']),'output':str(args.output.resolve())},ensure_ascii=False))
        return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('Semantic audit input/output error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
