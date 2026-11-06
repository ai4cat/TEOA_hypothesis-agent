import unittest,copy,tempfile,subprocess,sys,json
from agent_common import *
from workflow import validate_cards,atomic_revise,grounded,fts_query,CARD
from api_transport import parse_response,estimate_charge,reserved_charge

class Tests(unittest.TestCase):
    def card(self):
        c={k:'' for k in CARD['properties']};c.update(id='E01',hypothesis_id='H01',evidence_ids=['EV001'],groups=[dict(id='a',description='',factors=[dict(name='donor',value='x')]),dict(id='b',description='',factors=[dict(name='donor',value='y')])],comparisons=[dict(group_a='a',group_b='b',changed_factors=['donor'],inference='')],procedure=['pilot'],measurements=['signal'],feasibility='low_cost');return c
    def test_contrast_detects_wrong_factor(self):
        c=self.card();validate_cards([c],[dict(id='H01')],[dict(evidence_id='EV001')]);c['comparisons'][0]['changed_factors']=['light']
        with self.assertRaises(ValueError):validate_cards([c],[dict(id='H01')],[dict(evidence_id='EV001')])
    def test_atomic_rejects_missing_card(self):
        c=self.card();original=copy.deepcopy(c)
        with self.assertRaises(ValueError):atomic_revise([c],[],[dict(id='H01')],[dict(evidence_id='EV001')],['E01'])
        self.assertEqual(c,original)
    def test_final_phase(self):
        raw=dict(status='completed',output=[dict(type='message',phase='commentary',content=[dict(type='output_text',text='bad')]),dict(type='message',phase='final_answer',content=[dict(type='output_text',text='{"ok":true}')])])
        self.assertEqual(parse_response(raw),dict(ok=True))
    def test_redundant_closers_only(self):
        raw=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=' {"ok":true}]}')])])
        audit=[]
        self.assertEqual(parse_response(raw,audit),dict(ok=True))
        self.assertEqual(audit[0]['suffix'],']}')
        self.assertFalse(audit[0]['scientific_fields_changed'])
    def test_reject_ambiguous_or_truncated_json(self):
        for value in ('{"ok":true', '{"ok":true} {"second":1}', '{"ok":true} explanation', '{"ok":true,]}'):
            raw=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=value)])])
            with self.assertRaises(ValueError):parse_response(raw)
    def test_guard(self):
        code="from workflow import generation_guard,PACKAGE; generation_guard(); (PACKAGE/'unconfigured/input.json').read_text()"
        p=subprocess.run([sys.executable,'-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(p.returncode,0);self.assertIn('PermissionError',p.stderr)
    def test_quote(self):
        pool=[dict(evidence_id=f'EV{i}',paper_id='p',chunk_id='c',page=1,title='t',doi_candidates='',spans=[dict(id='S1',text='Exact source.',start=3,end=16)]) for i in range(4)]
        a=[dict(evidence_id=f'EV{i}',decision='include',span_ids=['S1']) for i in range(4)]
        self.assertEqual(grounded(pool,a)[0]['quotes'][0]['text'],'Exact source.')
        a[0]['span_ids']=['invented']
        with self.assertRaises(ValueError):grounded(pool,a)
    def test_cost(self):
        self.assertEqual(reserved_charge(dict(reserved_usd=1)),1)
        self.assertEqual(reserved_charge(dict(reserved_usd=1,settled_estimated_usd=.3)),.3)
        self.assertAlmostEqual(estimate_charge(1000,1000),.012)
    def test_query_escaping(self):
        self.assertEqual(fts_query([['Co','cobalt'],['"test"']]),'("Co" OR "cobalt") AND ("""test""")')
    def test_budget_blocks_without_network(self):
        from unittest.mock import patch
        from api_transport import call_api
        with tempfile.TemporaryDirectory() as tmp, patch('api_transport.get_api_key',return_value='test-not-a-key'), patch('api_transport.api_opener') as network:
            with self.assertRaisesRegex(RuntimeError,'Budget guard'):
                call_api(Path(tmp),'blocked','test',{},obj({}),dict(run_budget_usd=0,live_generation_enabled=True))
            network.assert_not_called()
    def test_concurrent_reservations_settle_by_call(self):
        from concurrent.futures import ThreadPoolExecutor
        from api_transport import reserve_call,settle_call
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger=root/'ledger.json'
            def run_one(i):
                base=root/'calls'/str(i)
                reserve_call(ledger,base,str(i),1,dict(run_budget_usd=20,max_calls_per_run=20))
                settle_call(ledger,base,i/100)
            with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run_one,range(12)))
            rows=load(ledger)['reservations']
            self.assertEqual(len(rows),12)
            self.assertEqual({r['name']:r['settled_estimated_usd'] for r in rows},{str(i):i/100 for i in range(12)})

if __name__=='__main__':unittest.main()
