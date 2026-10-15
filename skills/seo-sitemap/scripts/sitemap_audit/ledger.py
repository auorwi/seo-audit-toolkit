"""Stable issue history; absence from a later sample never closes an issue."""
import hashlib
import json
import sqlite3
from pathlib import Path
from .xmlrules import date

class Ledger:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=30);self.db.row_factory=sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,at TEXT,coverage TEXT);
        CREATE TABLE IF NOT EXISTS issues(id TEXT PRIMARY KEY,first_reported_at TEXT,last_reported_at TEXT,status TEXT,finding TEXT);
        CREATE TABLE IF NOT EXISTS observations(run_id TEXT,issue_id TEXT,finding TEXT,PRIMARY KEY(run_id,issue_id));''')

    def close(self):self.db.close()

    def record(self,result):
        at=date(result['at']).isoformat(timespec='seconds').replace('+00:00','Z')
        for row in result['findings']:
            if not isinstance(row,dict) or not all(row.get(k) for k in ('id','rule','url','category','certainty')):
                raise ValueError('invalid_finding')
        content=json.dumps({**{k:result[k] for k in ('findings','coverage')},'at':at},ensure_ascii=False,sort_keys=True)
        run_id='sitemap-'+hashlib.sha256(content.encode()).hexdigest()[:20]
        if self.db.execute('SELECT 1 FROM runs WHERE id=?',(run_id,)).fetchone():return {'run_id':run_id,'idempotent':True,'new_issues':0}
        new=0
        with self.db:
            self.db.execute('INSERT INTO runs VALUES(?,?,?)',(run_id,at,json.dumps(result['coverage'],ensure_ascii=False)))
            for row in result['findings']:
                packed=json.dumps(row,ensure_ascii=False,sort_keys=True)
                old=self.db.execute('SELECT * FROM issues WHERE id=?',(row['id'],)).fetchone()
                if old:
                    self.db.execute('UPDATE issues SET first_reported_at=MIN(first_reported_at,?),last_reported_at=MAX(last_reported_at,?),finding=? WHERE id=?',
                        (at,at,packed if date(at)>=date(old['last_reported_at']) else old['finding'],row['id']))
                else:
                    self.db.execute('INSERT INTO issues VALUES(?,?,?,?,?)',(row['id'],at,at,'open',packed));new+=1
                self.db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?)',(run_id,row['id'],packed))
        return {'run_id':run_id,'idempotent':False,'new_issues':new}

    def issues(self):
        latest=self.db.execute('SELECT id FROM runs ORDER BY at DESC,rowid DESC LIMIT 1').fetchone()
        result=[]
        for row in self.db.execute('SELECT * FROM issues ORDER BY first_reported_at,id'):
            value=dict(row);value['finding']=json.loads(value['finding'])
            value['observation_count']=self.db.execute('SELECT COUNT(*) FROM observations WHERE issue_id=?',(row['id'],)).fetchone()[0]
            value['seen_in_latest_run']=bool(latest and self.db.execute('SELECT 1 FROM observations WHERE run_id=? AND issue_id=?',(latest[0],row['id'])).fetchone())
            result.append(value)
        return result
