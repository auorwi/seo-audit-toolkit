#!/usr/bin/env python3
"""Audit explicit website link evidence and persist stable issue sightings."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from link_audit.adapters import load_manifest
from link_audit.audit import audit
from link_audit.report import write_report
from crawlability.ledger import record,history

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--supplement',type=Path,action='append',default=[]);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=168);p.add_argument('--depth-hint',type=int,default=4);p.add_argument('--parameter-variant-hint',type=int,default=100);p.add_argument('--expected-parameter',action='append',default=[]);args=p.parse_args()
    try:
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        inputs=load_manifest(args.manifest)
        for path in args.supplement:
            more=load_manifest(path)
            for key in ['captures','http_records','assets','pagination','language_expectations','gaps']:inputs[key]+=more[key]
            for name,urls in more['seeds'].items():
                if name in inputs['seeds'] and inputs['seeds'][name]!=urls:raise ValueError('conflicting_seed_group')
                inputs['seeds'][name]=urls
        result=audit(inputs,at=args.at,max_age_hours=args.max_age_hours,depth_hint=args.depth_hint,parameter_variant_hint=args.parameter_variant_hint,expected_parameters=args.expected_parameter)
        run=record(args.state/'issues.sqlite',result);write_report(args.output,result,history(args.state/'issues.sqlite'));partial=bool(result['gaps'] or result['pending_reviews'])
        print(json.dumps({'run_id':run,'status':'partial_review' if partial else 'completed_scoped_audit','findings':len(result['findings']),'edges':len(result['graph']['edges']),'output':str(args.output.resolve())},ensure_ascii=False));return 2 if partial else 0
    except (ValueError,KeyError,TypeError,OSError) as error:print('Internal links input/output error: '+str(error),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
