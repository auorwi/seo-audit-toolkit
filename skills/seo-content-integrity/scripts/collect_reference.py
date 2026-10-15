#!/usr/bin/env python3
"""Capture one official unauthenticated spot-symbol response, without trading."""
import argparse,json,hashlib
from pathlib import Path
from content_integrity.reference_fetch import fetch
from content_integrity.market_reference import review_response

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--symbol',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):raise ValueError('output_directory_not_empty')
    row=fetch(a.symbol);a.output.mkdir(parents=True,exist_ok=True);raw=(json.dumps(row,ensure_ascii=False,indent=2)+'\n').encode();(a.output/'reference.json').write_bytes(raw)
    proof={'path':'reference.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};(a.output/'reference-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    result=review_response(row,symbol=a.symbol,at=row['captured_at']);print(json.dumps({'state':result['state'],'reason':result.get('reason'),'status':row['status'],'output':str(a.output.resolve())}));return 2 if result['state']=='unknown' else 0
if __name__=='__main__':raise SystemExit(main())
