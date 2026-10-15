#!/usr/bin/env python3
"""Run local Nu on supplied original HTML and keep its collection time unchanged."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
from semantics_audit.shared import moment,url_id
from semantics_audit.nu_runner import run_nu
from semantics_audit.tool_reports import normalize_tool_report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('nu-executable','html','url','source','captured-at','output'):parser.add_argument('--'+key,required=True)
    parser.add_argument('--at',default=datetime.now(timezone.utc).isoformat());parser.add_argument('--timeout',type=float,default=30)
    args=parser.parse_args()
    try:
        moment(args.captured_at);url=url_id(args.url)
        if not args.source.strip():raise ValueError('source_required')
        output=Path(args.output)
        result=run_nu([args.nu_executable],args.html,url,output,at=args.at,timeout=args.timeout)
        body=(output/'nu.capture.json').read_bytes()
        tool_proof={'path':'nu.capture.json','bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
        snapshot='html-'+hashlib.sha256((url+'|'+args.captured_at+'|'+result['document_sha256']).encode()).hexdigest()[:24]
        manifest={'schema_version':1,'captures':[{'kind':'initial_html','url':url,'snapshot_id':snapshot,'captured_at':args.captured_at,
            'source':args.source,'evidence':result['document_evidence']}],
            'tool_reports':[{'tool':'nu','url':url,'capture_id':result['capture_id'],'checked_at':result['checked_at'],
                'evidence':tool_proof,'document_evidence':result['document_evidence']}]}
        (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        normalized=normalize_tool_report(result,at=args.at)
        print(json.dumps({'state':result['state'],'status':normalized['status'],'observations':len(normalized['observations']),
            'manifest':str((output/'manifest.json').resolve())},ensure_ascii=False))
        return 0 if normalized['status']=='usable' else 2
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('Nu input/output error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
