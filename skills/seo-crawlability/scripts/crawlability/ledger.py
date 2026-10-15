"""Idempotent sightings. A missing finding is never proof of a repair."""
import hashlib
import json
import sqlite3
from pathlib import Path
from .common import moment

def packed(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))

def connect(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=30);db.row_factory=sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,at TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS issues(issue_id TEXT PRIMARY KEY,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sightings(run_id TEXT,issue_id TEXT,at TEXT,payload TEXT,PRIMARY KEY(run_id,issue_id));
    ''')
    return db

def record(path,result):
    at=moment(result['at']).isoformat().replace('+00:00','Z')
    for issue in result['findings']:
        if not issue.get('issue_id'):raise ValueError('issue_identity_required')
    payload=packed(result);run_id='crawl-run-'+hashlib.sha256(payload.encode()).hexdigest()[:24]
    db=connect(path)
    try:
        with db:
            db.execute('INSERT OR IGNORE INTO runs VALUES(?,?,?)',(run_id,at,payload))
            for issue in result['findings']:
                encoded=packed(issue);key=issue['issue_id']
                db.execute('INSERT OR IGNORE INTO sightings VALUES(?,?,?,?)',(run_id,key,at,encoded))
                old=db.execute('SELECT * FROM issues WHERE issue_id=?',(key,)).fetchone()
                if old:
                    first=min(old['first_seen'],at,key=moment);last=max(old['last_seen'],at,key=moment)
                    newest=encoded if moment(at)>=moment(old['last_seen']) else old['payload']
                    db.execute('UPDATE issues SET first_seen=?,last_seen=?,payload=? WHERE issue_id=?',(first,last,newest,key))
                else:db.execute('INSERT INTO issues VALUES(?,?,?,?,?)',(key,at,at,'open',encoded))
        return run_id
    finally:db.close()

def history(path):
    db=connect(path)
    try:
        result=[]
        for row in db.execute('SELECT i.*,COUNT(s.issue_id) AS sightings FROM issues i LEFT JOIN sightings s ON s.issue_id=i.issue_id GROUP BY i.issue_id ORDER BY i.issue_id'):
            item=dict(row);item['payload']=json.loads(item['payload']);result.append(item)
        return result
    finally:db.close()
