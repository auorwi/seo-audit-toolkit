#!/usr/bin/env python3
"""Run actual local extruct Microdata/RDFa extraction against preserved HTML."""
import argparse,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
from importlib.metadata import version
from urllib.parse import urlsplit

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--html',type=Path,required=True);p.add_argument('--url',required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.output.exists():raise ValueError('output_already_exists')
        if not urlsplit(args.url).netloc.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
        body=args.html.read_bytes()
        if len(body)>8*1024*1024:raise ValueError('html_size_limit')
        result={'tool':'extruct','url':args.url,'source':'actual local extruct extraction from saved HTML','checked_at':datetime.now(timezone.utc).isoformat(),
            'document_sha256':hashlib.sha256(body).hexdigest(),'input_sha256':hashlib.sha256(body).hexdigest(),'syntaxes':['microdata','rdfa'],
            'state':'unavailable','checker_version':None,'payload':{},'coverage':{'engine_validation':False,'schema_semantic_validation':False,'rdfa_library_status':'experimental'}}
        try:
            import extruct
            result['checker_version']=version('extruct')
            payload={};errors=[]
            for syntax in result['syntaxes']:
                try:payload[syntax]=extruct.extract(body,base_url=args.url,syntaxes=[syntax],uniform=False)[syntax]
                except Exception as error:errors.append({'syntax':syntax,'reason':str(error)})
            result.update(payload=payload,errors=errors,state='completed' if not errors else 'partial_extraction')
        except ImportError as error:result['errors']=[{'reason':str(error)}]
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'state':result['state'],'output':str(args.output.resolve())}));return 0 if result['state']=='completed' else 2
    except (ValueError,OSError) as error:print(str(error),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
