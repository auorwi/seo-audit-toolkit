#!/usr/bin/env python3
"""Copy verified, independently captured 001 HTTP baselines into a 005 manifest."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
from rendering_audit.baseline import prepare_inventory

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,required=True)
    parser.add_argument('--bindings',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat())
    parser.add_argument('--max-age-hours',type=float,default=168)
    args=parser.parse_args()
    try:
        bindings=json.loads(args.bindings.read_text(encoding='utf-8'))
        if not isinstance(bindings,list):raise ValueError('bindings_must_be_array')
        result=prepare_inventory(args.inventory,bindings,args.output,at=args.at,max_age_hours=args.max_age_hours)
        print(json.dumps({'snapshots':len(result['snapshots']),'gaps':result['gaps'],'manifest':str((args.output/'manifest.json').resolve())},ensure_ascii=False))
        return 2 if result['gaps'] else 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('Baseline preparation error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
