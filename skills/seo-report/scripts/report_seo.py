#!/usr/bin/env python3
"""Consolidate selected sources. Publishing is an explicit separate command."""
import argparse,json,pathlib,sys
from seo_report.core import load_manifest,aggregate,parse
from seo_report.delivery import write_outputs
from seo_report.publish import Lark,publish_all,adopt

def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
 b=s.add_parser('build');b.add_argument('--manifest',required=True);b.add_argument('--state',required=True);b.add_argument('--output',required=True)
 b=s.add_parser('publish');b.add_argument('--report-dir',required=True);b.add_argument('--state',required=True)
 b=s.add_parser('adopt');b.add_argument('--key',required=True);b.add_argument('--url',required=True);b.add_argument('--state',required=True)
 args=p.parse_args()
 try:
  if args.command=='build':
   if pathlib.Path(args.output).exists():raise ValueError('new output directory required')
   result=aggregate(load_manifest(args.manifest),args.state);write_outputs(result,args.output);print(json.dumps({'issues':len(result['issues']),'counts':result['counts'],'mode':result['mode']},ensure_ascii=False))
  elif args.command=='publish':
   d=pathlib.Path(args.report_dir);r=parse((d/'report.json').read_bytes());docs=parse((d/'publication.json').read_bytes())
   # Publication must be exactly the generated content, not separately edited XML.
   from seo_report.delivery import documents
   if docs!=documents(r):raise ValueError('publication differs from report; rebuild first')
   result=publish_all(docs,r['run_id'],args.state,Lark(pathlib.Path(args.state)/'private-logs'));(d/'feishu-links.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result))
  else:print(adopt(args.key,args.url,args.state,Lark(pathlib.Path(args.state)/'private-logs')))
  return 0
 except (ValueError,OSError,KeyError,TypeError) as e:print(type(e).__name__+': '+str(e),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
