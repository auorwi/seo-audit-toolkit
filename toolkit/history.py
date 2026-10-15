"""Append quick-audit observations without silently resolving previous issues."""
import json
import sqlite3
from pathlib import Path


def record(path, report, output):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS runs (site TEXT, at TEXT, output TEXT, status TEXT, PRIMARY KEY(site,at,output))')
        db.execute('CREATE TABLE IF NOT EXISTS observations (site TEXT, issue_id TEXT, at TEXT, data TEXT, PRIMARY KEY(site,issue_id,at))')
        db.execute('INSERT OR IGNORE INTO runs VALUES (?,?,?,?)', (report['site'], report['at'], str(Path(output).resolve()), report['status']))
        for item in report['findings']:
            db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?)', (report['site'], item['issue_id'], item['observed_at'], json.dumps(item, ensure_ascii=False)))
