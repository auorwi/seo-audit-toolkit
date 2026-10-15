#!/usr/bin/env python3
"""Read one official field API response; preserve unavailable/auth/quota outcomes."""
import argparse,os,json,sys
from pathlib import Path
from cwv_audit.field_fetch import collect_field

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',choices=['crux_api','psi_api'],required=True);p.add_argument('--url',required=True);p.add_argument('--device',choices=['mobile','desktop'],required=True);p.add_argument('--scope',choices=['url','origin'],default='url');p.add_argument('--output',type=Path,required=True);p.add_argument('--key-env');p.add_argument('--timeout',type=float,default=30);args=p.parse_args()
    try:
        if not 0<args.timeout<=120:raise ValueError('invalid_request_timeout')
        name=args.key_env or ('CRUX_API_KEY' if args.source=='crux_api' else 'PAGESPEED_API_KEY');key=os.environ.get(name)
        r=collect_field(args.source,args.url,args.device,args.scope,args.output,key=key,timeout=args.timeout)
        print(json.dumps({'state':r['state'],'http_status':r['status'],'source':r['source'],'output':str(args.output.resolve())},ensure_ascii=False));return 0 if r['state']=='response_received' and r['status'] is not None and 200<=r['status']<300 else 2
    except (ValueError,KeyError,TypeError,OSError) as e:print('CWV field collection error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
