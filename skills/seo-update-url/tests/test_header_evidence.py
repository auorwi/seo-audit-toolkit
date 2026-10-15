import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import test_discover
from support import InventoryTest


class HeaderEvidenceTests(InventoryTest):
    def test_link_and_refresh_headers_survive_without_secret_query_values(self):
        net=self.module('network')
        headers=net.safe_header_pairs([('Link','<https://bingx.com/a?token=SECRET>; rel="canonical"'),('Refresh','0; url=https://bingx.com/b?token=SECRET')])
        self.assertEqual([k for k,v in headers],['link','refresh'])
        self.assertNotIn('SECRET',str(headers))

    def test_capture_declares_which_header_names_were_retained(self):
        net=self.module('network')
        self.assertIn('captured_header_names',net.Response.__dataclass_fields__)
        self.assertIn('link',net.CAPTURED_HEADERS)
        self.assertIn('refresh',net.CAPTURED_HEADERS)

    def test_capture_policy_is_persisted_and_old_policy_is_unknown(self):
        runner,store,_=test_discover.DiscoveryTests.setup_runner(self,{})
        net=self.module('network')
        self.assertIn('captured_header_names',net.Response.__dataclass_fields__)
        runner.fetch=lambda url:net.Response(url,200,{},b'OK',[],['link','refresh'])
        runner.run(max_requests=2)
        row=store.db.execute('SELECT captured_header_names FROM fetches LIMIT 1').fetchone()
        self.assertEqual(json.loads(row[0]),['link','refresh'])

    def test_wire_duplicate_headers_survive_capture_and_secrets_are_filtered(self):
        net = self.module('network')
        class Reply:
            status = 200
            def getheaders(self):
                return [('X-Robots-Tag', 'noindex'), ('X-Robots-Tag', 'nofollow'),
                        ('Set-Cookie', 'secret'), ('CF-Ray', 'public-request-id')]
            def read(self, limit): return b'OK'
        class Connection:
            def __init__(self, *a, **kw): pass
            def request(self, *a, **kw): pass
            def getresponse(self): return Reply()
            def close(self): pass
        with patch.object(net.socket, 'getaddrinfo', return_value=[(None,None,None,None,('8.8.8.8',443))]), patch.object(net.http.client,'HTTPSConnection',Connection):
            result = net.HttpClient(['bingx.com'], delay=0).get('https://bingx.com/en')
        self.assertTrue(hasattr(result, 'headers_all'), 'Repeated headers are not captured')
        self.assertEqual(result.headers_all[:2], [('x-robots-tag','noindex'),('x-robots-tag','nofollow')])
        self.assertNotIn('secret', str(result.headers_all))
        self.assertIn(('cf-ray','public-request-id'), result.headers_all)

    def test_old_database_gets_additive_header_column_without_losing_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'old.sqlite'
            db = sqlite3.connect(path)
            db.execute('CREATE TABLE fetches(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,status INTEGER,error TEXT,headers TEXT,evidence TEXT,checked_at TEXT)')
            db.execute("INSERT INTO fetches(id,url,status,headers) VALUES(7,'https://bingx.com/en',200,'{}')")
            db.commit(); db.close()
            store = self.module('store').Inventory(path,['bingx.com'])
            self.addCleanup(store.close)
            columns = {r[1] for r in store.db.execute('PRAGMA table_info(fetches)')}
            self.assertIn('headers_all',columns)
            row = store.db.execute('SELECT * FROM fetches WHERE id=7').fetchone()
            self.assertEqual(row['status'],200)
            self.assertIsNone(row['headers_all'])

    def test_duplicate_headers_persist_with_public_request_identifiers(self):
        runner, store, _ = test_discover.DiscoveryTests.setup_runner(self,{})
        net = self.module('network')
        self.assertIn('headers_all', net.Response.__dataclass_fields__)
        def fetch(url):
            return net.Response(url,200,{'content-type':'text/html'},b'OK',
                [('X-Robots-Tag','noindex'),('X-Robots-Tag','nofollow'),('Set-Cookie','secret'),('CF-Ray','trace')])
        runner.fetch=fetch
        runner.run(max_requests=2)
        rows=store.db.execute('SELECT headers_all FROM fetches').fetchall()
        self.assertEqual(len(rows),2)
        for row in rows:
            self.assertEqual(json.loads(row[0]),[['x-robots-tag','noindex'],['x-robots-tag','nofollow'],['cf-ray','trace']])

    def test_legacy_response_is_not_mislabeled_complete_header_capture(self):
        runner, store, _=test_discover.DiscoveryTests.setup_runner(self,{})
        runner.run(max_requests=1)
        self.assertIn('headers_all',{r[1] for r in store.db.execute('PRAGMA table_info(fetches)')})
        self.assertIsNone(store.db.execute('SELECT headers_all FROM fetches').fetchone()[0])
