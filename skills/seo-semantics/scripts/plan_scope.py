#!/usr/bin/env python3
"""Prepare a complete, local-only preflight list. This does not visit any page."""
import argparse,csv,json,sys
from pathlib import Path
from datetime import datetime,timezone
from semantics_audit.scope import build_plan
from crawlability.report import csv_file,md

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',required=True,choices=['single','subset','all'])
    p.add_argument('--input',type=Path);p.add_argument('--url',action='append',default=[]);p.add_argument('--id',action='append',default=[])
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.output.exists() and any(args.output.iterdir()):raise ValueError('output_directory_not_empty')
        rows=[]
        if args.input:
            if args.input.suffix.lower()=='.csv':
                with args.input.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            else:rows=json.loads(args.input.read_text(encoding='utf-8'))
        plan=build_plan(rows,mode=args.mode,source=str(args.input.resolve()) if args.input else 'explicit_user_urls',
            at=datetime.now(timezone.utc).isoformat(),urls=args.url,ids=args.id)
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/'scope.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        (args.output/'urls.json').write_text(json.dumps(plan['targets'],ensure_ascii=False,indent=2)+'\n')
        csv_file(args.output/'scope.csv',plan['targets'],['id','url','page_type','family','locale','required_tools'])
        lines=['# 本轮待检查页面','',f"模式：{args.mode}；页面数：{plan['count']}；来源：{md(plan['source'])}",'',
            '以下为本轮完整 URL 清单。每页将使用真实浏览器；全量仅指这份清单，不代表全站权威全集。','',
            '| 序号 | ID | 页面类型 | 语言 | URL |','|---|---|---|---|---|']
        for i,r in enumerate(plan['targets'],1):lines.append('| '+ ' | '.join(md(str(v)) for v in [i,r.get('id',''),r['page_type'],r['locale'],r['url']])+' |')
        if plan['excluded']:
            lines+=['','## 不在本轮范围内','']
            lines += ['- '+md(r['url'])+'：'+md(r['reason']) for r in plan['excluded']]
        lines+=['','须先向用户展示此清单，再采集；生成文件本身不代表已告知用户。','']
        (args.output/'scope-preview.md').write_text('\n'.join(lines))
        print(json.dumps({'scope_id':plan['scope_id'],'count':plan['count'],'mode':args.mode,'preview':str((args.output/'scope-preview.md').resolve()),'scope':str((args.output/'scope.json').resolve())},ensure_ascii=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('Scope error: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
