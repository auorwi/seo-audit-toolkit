#!/usr/bin/env python3
"""Retest selected original issue IDs against captured before/after evidence."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime,timezone
from recheck.evidence import load_plan
from recheck.audit import audit
from recheck.delivery import record,history,write_report

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['plan','state','output']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--at',default=datetime.now(timezone.utc).isoformat());p.add_argument('--max-age-hours',type=float,default=24);a=p.parse_args()
 try:
  if a.output.exists() and any(a.output.iterdir()):raise ValueError('output_not_empty')
  r=audit(load_plan(a.plan,at=a.at,max_age_hours=a.max_age_hours),at=a.at);run=record(a.state/'rechecks.sqlite',r);write_report(a.output,r,history(a.state/'rechecks.sqlite'));partial=not r['coverage']['complete'];print(json.dumps({'run_id':run,'status':'partial_review' if partial else 'completed_scoped_retest','verdicts':{x['issue_id']:x['status'] for x in r['rechecks']},'coverage':r['coverage'],'output':str(a.output.resolve())},ensure_ascii=False));return 2 if partial else 0
 except (ValueError,TypeError,KeyError,OSError,OverflowError) as ex:print('Recheck error: '+str(ex),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
