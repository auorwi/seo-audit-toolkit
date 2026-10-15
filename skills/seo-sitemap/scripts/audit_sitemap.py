#!/usr/bin/env python3
"""002 Sitemap: inspect acquired evidence without changing production files."""
import argparse
import fcntl
import json
import sqlite3
import sys
from datetime import datetime,timezone
from pathlib import Path
from sitemap_audit.adapters import from_inventory,from_manifest,validate_expected
from sitemap_audit.audit import audit
from sitemap_audit.ledger import Ledger
from sitemap_audit.report import write_report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--inventory',type=Path,help='001 inventory.sqlite, opened read-only')
    inputs.add_argument('--manifest',type=Path,help='JSON evidence manifest with local body hashes')
    parser.add_argument('--root',action='append',required=True)
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected',type=Path)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'))
    parser.add_argument('--max-age-hours',type=float,default=168)
    parser.add_argument('--cross-site-host',action='append',default=[],help='Only when cross-site submission is independently verified')
    args=parser.parse_args(argv)
    try:
        data=from_inventory(args.inventory) if args.inventory else from_manifest(args.manifest)
        expected=validate_expected(json.loads(args.expected.read_text(encoding='utf-8-sig'))) if args.expected else None
        result=audit(data['documents'],data.get('pages',{}),args.root,args.at,expected,args.max_age_hours,args.cross_site_host)
        result['input']={'inventory':str(args.inventory.resolve()) if args.inventory else None,'manifest':str(args.manifest.resolve()) if args.manifest else None,
            'expected_source':expected.get('source_id') if expected else None,'max_age_hours':args.max_age_hours}
        c=result['coverage']
        result['status']='partial' if not c['sitemap_set_read_complete'] or c['unverified_page_urls'] or any(f['certainty']=='unknown' for f in result['findings']) else 'completed_selected_scope'
        args.state.mkdir(parents=True,exist_ok=True)
        with (args.state/'.sitemap.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as e:raise ValueError('sitemap_state_locked') from e
            store=Ledger(args.state/'issues.sqlite')
            try:
                result['ledger']=store.record(result)
                output=write_report(result,store.issues(),args.output)
            finally:store.close()
        print(json.dumps({'status':result['status'],'output':output,'issues':len(result['findings']),'coverage':c,'ledger':result['ledger']},ensure_ascii=False,indent=2))
        return 2 if result['status']=='partial' else 0
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
