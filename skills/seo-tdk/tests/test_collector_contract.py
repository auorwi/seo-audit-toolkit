import json,subprocess
from support import TdkTest,ROOT,URL
class CollectorContractTests(TdkTest):
    def test_readiness_result_keeps_actual_observed_entity_and_time(self):
        js='''const {collectMetadata}=await import(process.argv[1]);
const page={evaluate:async()=>({url:'https://bingx.com/en/price',title:'SOLV',descriptions:['Actual description'],main:'SOLV actual main',entity:'SOLV',loading:0,errors:0}),content:async()=>'<html><head><title>SOLV</title></head><body>SOLV</body></html>',url:()=> 'https://bingx.com/en/price'};
const result=await collectMetadata(page,{expectedIdentity:'SOLV',timeoutMs:100,stableWindowMs:2,sampleIntervalMs:2});console.log(JSON.stringify(result));'''
        r=subprocess.run(['node','--input-type=module','-e',js,(ROOT/'scripts/collect_metadata.mjs').as_uri()],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);data=json.loads(r.stdout)
        self.assertEqual(data['readiness_evidence']['entity'],'SOLV');self.assertEqual(data['readiness_evidence']['descriptions'],['Actual description']);self.assertTrue(data['readiness_evidence']['observed_at'])
