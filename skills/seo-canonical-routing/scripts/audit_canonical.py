#!/usr/bin/env python3
"""Standalone 004 canonical/routing audit; reads evidence without network or site writes."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
from canonical_routing.adapters import load_inventory,load_manifest
from canonical_routing.audit import audit
from canonical_routing.report import write_report
from crawlability.ledger import record,history

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--inventory',type=Path);source.add_argument('--manifest',type=Path)
    parser.add_argument('--supplement',action='append',type=Path,default=[])
    parser.add_argument('--url',action='append',default=[]);parser.add_argument('--urls',type=Path)
    parser.add_argument('--state',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat())
    parser.add_argument('--max-age-hours',type=float,default=168)
    parser.add_argument('--max-graph-depth',type=int,default=30)
    args=parser.parse_args()
    try:
        targets=[{'url':url} for url in args.url]
        if args.urls:
            loaded=json.loads(args.urls.read_text(encoding='utf-8'))
            if not isinstance(loaded,list):raise ValueError('urls_file_must_be_array')
            targets += [{'url':item} if isinstance(item,str) else item for item in loaded]
        if not targets:raise ValueError('explicit_nonempty_url_scope_required')
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        data=load_inventory(args.inventory,[t['url'] for t in targets],args.max_graph_depth) if args.inventory else load_manifest(args.manifest)
        for path in args.supplement:
            supplement=load_manifest(path)
            for key in data:data[key]+=supplement[key]
        result=audit(data['records'],targets,at=args.at,max_age_hours=args.max_age_hours,
            rendered=data['rendered'],facts=data['facts'],navigation=data['navigation'],
            engine_observations=data['engine_observations'],equivalences=data['equivalences'])
        result['input_gaps']=data['gaps']
        run_id=record(args.state/'issues.sqlite',result)
        write_report(args.output,result,history(args.state/'issues.sqlite'))
        partial=bool(data['gaps']) or any(f['classification']=='evidence_gap' for f in result['findings'])
        print(json.dumps({'run_id':run_id,'status':'partial' if partial else 'completed_scoped_audit',
            'urls':len(result['scope']),'findings':len(result['findings']),'output':str(args.output.resolve())},ensure_ascii=False))
        return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('Audit input/output error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
