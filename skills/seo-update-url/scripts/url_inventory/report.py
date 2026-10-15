"""Machine-readable evidence and honest coverage summaries."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile

import csv
import io
import json
import os
from collections import defaultdict
from pathlib import Path


def _atomic(path, content):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _csv(rows, fields):
    stream = io.StringIO(newline="")
    stream.write("\ufeff")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        clean = {}
        for key in fields:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            clean[key] = value
        writer.writerow(clean)
    return stream.getvalue()


def latest_run(store):
    row = store.db.execute("SELECT * FROM runs ORDER BY started_at DESC,rowid DESC LIMIT 1").fetchone()
    if not row:
        return None
    result = dict(row)
    result["settings"] = json.loads(result["settings"])
    result["tasks"] = {r[0]: r[1] for r in store.db.execute("SELECT status,COUNT(*) FROM tasks WHERE run_id=? GROUP BY status", (row["id"],))}
    result["requests"] = store.db.execute("SELECT COUNT(*) FROM fetches WHERE run_id=?", (row["id"],)).fetchone()[0]
    return result


def snapshot(store):
    members = defaultdict(list)
    for row in store.db.execute("SELECT * FROM source_urls ORDER BY source_id,url"):
        members[row["url"]].append(dict(row))
    urls = []
    for row in store.db.execute("SELECT * FROM urls ORDER BY url"):
        value = dict(row)
        value["entities"] = json.loads(value["entities"])
        value["last_details"] = json.loads(value["last_details"]) if value["last_details"] else None
        value["source_memberships"] = members[value["url"]]
        value["sources"] = [r["source_id"] for r in members[value["url"]]]
        urls.append(value)
    summary = dict(store.summary(),configured_site=site_host())
    summary["latest_run"] = latest_run(store)
    return {"schema_version": 1, "summary": summary, "urls": urls,
            "sources": [dict(r) for r in store.db.execute("SELECT * FROM sources ORDER BY id")],
            "source_snapshots": [dict(r) for r in store.db.execute("SELECT * FROM snapshots ORDER BY captured_at,id")],
            "relations": [dict(r) for r in store.db.execute("SELECT * FROM relations ORDER BY source_url,target_url")],
            "changes": store.changes(), "exclusions": store.exclusions(),
            "tasks": [dict(r) for r in store.db.execute("SELECT * FROM tasks ORDER BY id")],
            "fetches": [dict(r) for r in store.db.execute("SELECT * FROM fetches ORDER BY id")]}


def write_report(store, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data = snapshot(store)
    summary = data["summary"]
    for name, value in [("summary.json", summary), ("snapshot.json", data)]:
        _atomic(output / name, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    inventory = []
    groups = defaultdict(lambda: {"url_count": 0, "locales": set(), "example_url": "", "classified": True})
    for row in data["urls"]:
        inventory.append({**row, "source_ids": row["sources"], "source_states": row["source_memberships"]})
        key = (row["host"], row["template"], row["kind"])
        group = groups[key]
        group["url_count"] += 1
        group["locales"].add(row["locale"])
        group["example_url"] = group["example_url"] or row["url"]
        group["classified"] &= bool(row["classified"])
    routes = [{"host": host, "template": template, "kind": kind, **g, "locales": sorted(g["locales"])}
              for (host, template, kind), g in sorted(groups.items())]
    languages = defaultdict(int)
    source_coverage = {r["id"]: {"source_id": r["id"], "discovered_url_count": 0,
        "observed_membership_count": 0, "missing_candidate_count": 0,
        "exclusive_discovered_url_count": 0} for r in data["sources"]}
    for row in data["urls"]:
        if row["kind"] == "page":
            languages[row["locale"]] += 1
        for member in row["source_memberships"]:
            source = source_coverage[member["source_id"]]
            source["discovered_url_count"] += 1
            source["observed_membership_count" if member["state"] == "observed" else "missing_candidate_count"] += 1
            source["exclusive_discovered_url_count"] += int(len(row["source_memberships"]) == 1)
    exports = {
        "inventory.csv": (inventory, ["url", "host", "locale", "template", "entities", "classified", "kind", "index_intent", "first_seen", "last_seen", "last_status", "last_checked", "source_ids", "source_states"]),
        "routes.csv": (routes, ["host", "template", "kind", "classified", "url_count", "locales", "example_url"]),
        "sources.csv": (data["sources"], ["id", "kind", "locator", "last_captured_at"]),
        "languages.csv": ([{"locale": key, "page_url_count": value} for key, value in sorted(languages.items())], ["locale", "page_url_count"]),
        "source-coverage.csv": (list(source_coverage.values()), ["source_id", "discovered_url_count", "observed_membership_count", "missing_candidate_count", "exclusive_discovered_url_count"]),
        "source-snapshots.csv": (data["source_snapshots"], ["id", "source_id", "run_id", "captured_at", "coverage", "accepted", "rejected", "ingested_at"]),
        "changes.csv": (data["changes"], ["run_id", "url", "source_id", "change", "before_value", "after_value", "changed_at"]),
        "exclusions.csv": (data["exclusions"], ["run_id", "source_id", "url", "reason"]),
        "relations.csv": (data["relations"], ["run_id", "source_url", "target_url", "relation"]),
        "tasks.csv": (data["tasks"], ["run_id", "url", "kind", "depth", "parent", "status", "reason"]),
        "fetches.csv": (data["fetches"], ["run_id", "url", "status", "error", "headers", "evidence", "checked_at"])}
    for name, (rows, fields) in exports.items():
        _atomic(output / name, _csv(rows, fields))
    run = summary["latest_run"] or {}
    lines = ["# "+site_host()+" URL 资产盘点", "", "生成时间：" + summary["generated_at"], "",
             "这是已发现资产的盘点，不是全站完整性证明，也不是 SEO 问题审查或索引确认。", "",
             "| 指标 | 数量／状态 |", "|---|---|",
             f"| 已发现 URL（含技术文件） | {summary['url_count']} |",
             f"| 页面 URL | {summary['page_url_count']} |",
             f"| 技术文件 URL | {summary['technical_url_count']} |",
             f"| 已识别的页面语言前缀数 | {summary['language_prefix_count']} |",
             f"| 已识别路由模板分组 | {summary['classified_route_family_count']} |",
             f"| 路由分组（含未分类的字面路径） | {summary['route_family_count']} |",
             f"| 尚未识别模板的页面 URL | {summary['unclassified_url_count']} |",
             f"| 有历史或本轮 HTTP 记录的 URL | {summary['http_checked_count']} |",
             f"| 最新记录为 HTTP 200 的 URL（不代表内容／索引正常） | {summary['http_200_count']} |",
             f"| 来源数 | {summary['source_count']} |", "| 全站真实 URL 总量 | 未知 |", "",
             f"尚无 HTTP 记录的页面：{summary['unverified_page_url_count']}。预期可索引规范 URL 与已确认退役 URL 总量均未知，需补充权威发布／退役状态和后续检查。", "",
             "## 最近运行", "", f"运行：`{run.get('id', '无')}`；状态：`{run.get('status', '无')}`。",
             f"该运行请求数：{run.get('requests', 0)}；任务状态：`{json.dumps(run.get('tasks', {}), ensure_ascii=False)}`。", "",
             "本表中的 HTTP 数量来自持久台账，不自动等于最近一次运行的检查量。请按 fetches.csv 的 run_id／checked_at 查看当次请求。", "",
             "## 阅读明细", "",
             "- inventory.csv：逐 URL、模板、语言、首次／最后发现、最近 HTTP 与来源。",
             "- routes.csv：模板与未分类路径分组；分组数不能称为确认的全站路由模板总数。",
             "- source-snapshots.csv：来源采集日期与 complete／sample／unknown 范围。",
             "- languages.csv：页面语言路由前缀分布；空值表示尚未识别。",
             "- source-coverage.csv：各来源历史发现数、当前来源状态及仅由该来源发现的 URL 数；不是全站覆盖率。",
             "- changes.csv：新增、来源中缺失候选、重新出现及状态变化。",
             "- relations.csv：canonical、hreflang、跳转和内链关系；它们没有修改 URL 身份。",
             "- tasks.csv／fetches.csv：已完成、未检查、延期、失败和受阻任务，以及证据路径与校验值。",
             "- exclusions.csv：越界、无效或含敏感参数等被排除的地址（已脱敏）。",
             "- snapshot.json：包含以上关系与来源的机器可读快照。", "",
             "## 判断边界", "",
             "来源 complete 仅指该来源此次导出／文件完整，不是全站完整。样例来源未出现某 URL 不构成下线证据。",
             "missing_candidate 仅表示完整来源中未再出现，不代表页面已删除；历史记录不会被删掉。",
             "普通 HTTP 不执行 JavaScript。客户端链接可通过 import-dom 补充；浏览器发现不冒充 HTTP 或搜索引擎检查。",
             "预期索引状态默认为 unknown，不能根据 noindex、Sitemap 或 200 响应自动推断业务意图。", ""]
    _atomic(output / "report.md", "\n".join(lines))
    return {"output": str(output.resolve()), "summary": summary, "files": ["report.md", "summary.json", "snapshot.json", *exports]}
