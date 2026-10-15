#!/usr/bin/env python3
"""Standalone 003 audit; consumes evidence and never changes live configuration."""
import argparse
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
from crawlability.adapters import load_inventory,load_manifest
from crawlability.audit import audit
from crawlability.ledger import record,history
from crawlability.report import write_report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--inventory',type=Path);source.add_argument('--manifest',type=Path)
    parser.add_argument('--supplement',type=Path,action='append',default=[])
    parser.add_argument('--url',action='append',default=[])
    parser.add_argument('--urls',type=Path,help='JSON array of URL strings or objects with index_intent provenance')
    parser.add_argument('--agent',action='append')
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat())
    parser.add_argument('--max-age-hours',type=float,default=168)
    args=parser.parse_args()
    try:
        targets=[{'url':url} for url in args.url]
        if args.urls:
            loaded=json.loads(args.urls.read_text(encoding='utf-8'))
            if not isinstance(loaded,list):raise ValueError('urls_file_must_be_array')
            targets += [{'url':v} if isinstance(v,str) else v for v in loaded]
        if not targets:raise ValueError('explicit_nonempty_url_scope_required')
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_inventory(args.inventory,[t['url'] for t in targets]) if args.inventory else load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in inputs:inputs[key]+=more[key]
        result=audit(inputs['records'],targets,at=args.at,agents=args.agent,max_age_hours=args.max_age_hours,
            rendered=inputs['rendered'],observations=inputs['observations'])
        result['input_gaps']=inputs['gaps']
        run_id=record(args.state/'issues.sqlite',result)
        write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(inputs['gaps']) or any(f['classification']=='evidence_gap' for f in result['findings'])
        print(json.dumps({'run_id':run_id,'status':'partial' if partial else 'completed_scoped_audit',
            'urls':len(result['scope']),'findings':len(result['findings']),'output':str(args.output.resolve())},ensure_ascii=False))
        return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('Audit input/output error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
