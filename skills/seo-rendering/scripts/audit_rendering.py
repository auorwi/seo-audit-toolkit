#!/usr/bin/env python3
"""Standalone rendering audit: consume observed evidence, never execute page actions."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
from rendering_audit.adapters import load_manifest
from rendering_audit.audit import audit
from rendering_audit.report import write_report
from crawlability.ledger import record,history

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--supplement',type=Path,action='append',default=[])
    parser.add_argument('--url',action='append',default=[]);parser.add_argument('--urls',type=Path)
    parser.add_argument('--state',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat())
    parser.add_argument('--max-age-hours',type=float,default=168)
    args=parser.parse_args()
    try:
        targets=[{'url':url} for url in args.url]
        if args.urls:
            extra=json.loads(args.urls.read_text(encoding='utf-8'))
            if not isinstance(extra,list):raise ValueError('urls_file_must_be_array')
            targets += [{'url':v} if isinstance(v,str) else v for v in extra]
        if not targets:raise ValueError('explicit_nonempty_url_scope_required')
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in inputs:inputs[key]+=more[key]
        result=audit(inputs['snapshots'],targets,at=args.at,max_age_hours=args.max_age_hours,interactions=inputs['interactions'])
        result['input_gaps']=inputs['gaps']
        run_id=record(args.state/'issues.sqlite',result)
        write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(inputs['gaps']) or any(f['classification']=='evidence_gap' for f in result['findings'])
        print(json.dumps({'run_id':run_id,'status':'partial' if partial else 'completed_scoped_audit',
            'urls':len(result['scope']),'ready_paths':result['coverage']['ready_paths'],
            'findings':len(result['findings']),'output':str(args.output.resolve())},ensure_ascii=False))
        return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('Audit input/output error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
