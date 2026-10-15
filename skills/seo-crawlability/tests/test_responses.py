from support import CrawlTest, AT

ROOT='https://bingx.com/robots.txt'
PAGE='https://bingx.com/en'
def response(url=ROOT,status=200,body=b'User-agent: *\nDisallow: /en',at=AT,headers=None,**kw):
    return {'url':url,'status':status,'body':body,'checked_at':at,'headers':headers or [],**kw}

class ResponseTests(CrawlTest):
    def evaluate(self,records,target=PAGE,agent='Googlebot',**kw):
        return self.module('responses').evaluate_response(records,target,agent,AT,**kw)

    def test_200_rules_are_engine_model_not_actual_bot_access(self):
        data=self.evaluate([response()])
        self.assertFalse(data['allowed'])
        self.assertEqual(data['actual_bot_access'],'unknown')

    def test_google_4xx_except_429_has_no_restrictions(self):
        for status in [401,403,404,410]:
            with self.subTest(status=status):
                data=self.evaluate([response(status=status)])
                self.assertTrue(data['allowed'])
                self.assertEqual(data['reason'],'google_4xx_no_restrictions')

    def test_429_and_5xx_need_cache_and_timing_not_allow_all(self):
        for status in [429,500,503]:
            with self.subTest(status=status):
                data=self.evaluate([response(status=status)])
                self.assertIsNone(data['allowed'])
                self.assertEqual(data['reason'],'robots_access_unverified')

    def test_google_error_policy_not_silently_applied_to_bing_or_yandex(self):
        for agent in ['Bingbot','YandexBot']:
            self.assertIsNone(self.evaluate([response(status=403)],agent=agent)['allowed'])

    def test_subdomain_needs_own_robots(self):
        data=self.evaluate([response()],target='https://blog.bingx.com/en')
        self.assertIsNone(data['allowed'])
        self.assertEqual(data['reason'],'robots_missing_evidence')

    def test_latest_failed_attempt_cannot_fall_back_to_old_good_response(self):
        records=[response(at='2026-09-16T11:00:00Z'),response(status=None,error='TimeoutError')]
        data=self.evaluate(records)
        self.assertIsNone(data['allowed'])
        self.assertEqual(data['chain'][-1]['error'],'TimeoutError')

    def test_stale_robots_is_not_current_proof(self):
        data=self.evaluate([response(at='2025-01-01T00:00:00Z')])
        self.assertIsNone(data['allowed']);self.assertEqual(data['reason'],'robots_stale')

    def test_complete_redirect_chain_applies_rules_to_original_origin(self):
        target='https://blog.bingx.com/robots-main.txt'
        records=[response(status=301,headers=[('Location',target)]),response(url=target)]
        data=self.evaluate(records)
        self.assertFalse(data['allowed'])
        self.assertEqual(len(data['chain']),2)
        self.assertEqual(data['final_url'],target)

    def test_redirect_gap_loop_and_budget_are_unknown(self):
        record=response(status=302,headers={'location':'/rules.txt'})
        data=self.evaluate([record]);self.assertIsNone(data['allowed'])
        self.assertEqual(data['reason'],'redirect_missing_evidence')
        data=self.evaluate([record,response(url='https://bingx.com/rules.txt',status=302,headers={'location':ROOT})])
        self.assertEqual(data['reason'],'redirect_loop')
        data=self.evaluate([record],max_redirects=0)
        self.assertEqual(data['reason'],'redirect_limit')

    def test_robot_html_misconfiguration_and_rule_decision_are_separate(self):
        data=self.evaluate([response(body=b'<html>Login required</html>',headers={'content-type':'text/html'})])
        self.assertTrue(data['allowed'])
        self.assertIn('robots_html_response',data['warnings'])

    def test_redirect_with_ambiguous_locations_is_not_guessed(self):
        data=self.evaluate([response(status=302,headers=[('Location','/a'),('Location','/b')])])
        self.assertIsNone(data['allowed']);self.assertEqual(data['reason'],'redirect_location_ambiguous')

    def test_headers_only_response_without_verified_body_is_unknown(self):
        record=response();record.pop('body')
        data=self.evaluate([record])
        self.assertIsNone(data['allowed']);self.assertEqual(data['reason'],'robots_body_missing')
