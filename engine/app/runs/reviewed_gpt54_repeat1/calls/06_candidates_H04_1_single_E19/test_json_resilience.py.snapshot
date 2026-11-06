import json
import tempfile
import unittest
from pathlib import Path
from agent_common import save,load,sha
from api_transport import parse_generated_response,OutputTruncatedError
from portfolio_chunks import build_portfolio

class JsonResilience(unittest.TestCase):
    def raw(self,text,tokens=16000):
        return dict(status='completed',usage=dict(output_tokens=tokens),output=[dict(type='message',content=[dict(type='output_text',text=text)])])
    def test_completed_flag_does_not_hide_truncation(self):
        with self.assertRaises(OutputTruncatedError):parse_generated_response(self.raw('{"claim":"cut'),dict(max_output_tokens=16000))
    def test_valid_json_at_limit_is_accepted(self):
        self.assertEqual(parse_generated_response(self.raw('{"ok":true}'),dict(max_output_tokens=16000)),dict(ok=True))
    def test_malformed_below_limit_is_not_classified_as_truncated(self):
        with self.assertRaises(json.JSONDecodeError):parse_generated_response(self.raw('{"bad":,}',12),dict(max_output_tokens=16000))
    def test_explicit_incomplete_is_rejected_even_with_valid_json(self):
        raw=self.raw('{"ok":true}');raw.update(status='incomplete',incomplete_details=dict(reason='max_output_tokens'))
        with self.assertRaises(OutputTruncatedError):parse_generated_response(raw,dict(max_output_tokens=16000))
    def test_refusal_at_limit_is_not_truncation(self):
        raw=self.raw('');raw['output'][0]['content']=[dict(type='refusal')]
        with self.assertRaisesRegex(ValueError,'Model refused'):parse_generated_response(raw,dict(max_output_tokens=16000))

class SplitPortfolio(unittest.TestCase):
    def build(self,root,corrupt=False):
        names=[]
        def stage(run,name,instruction,payload,schema,cap):
            names.append(name)
            if name=='05_split_hypotheses':
                value=dict(hypotheses=[dict(id=f'H{i:02}',question_id='Q1',claim='Testable claim',alternative='Alternative',evidence_ids=['EV001'],method_evidence_ids=[],platform_ids=['P01'],platform_and_comparator_choice='Choice',uncertainty='Uncertain') for i in range(1,5)],gaps=[])
            elif name.startswith('05_split_menu_'):
                value=dict(candidates=[dict(id=payload['reserved_experiment_ids'][0],hypothesis_id=payload['hypothesis']['id'],question_ids=['Q1'],candidate_type='intervention',title='Title',purpose='Purpose',method='Method',evidence_ids=['EV999' if corrupt else 'EV001'],distinct_information='Information',dependencies=[])],gaps=[])
            else:raise AssertionError('Unexpected stage: '+name)
            save(run/(name+'.json'),value)
            return value
        result=build_portfolio(root,{},[dict(id='P01',evidence_ids=['EV001'])],dict(selected_platform_ids=['P01']),dict(questions=[dict(question_id='Q1',mechanism_evidence_ids=['EV001'],method_evidence_ids=[])]),[dict(evidence_id='EV001')],stage)
        return result,names
    def test_combined_output_has_candidates_and_source_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);result,names=self.build(root)
            self.assertEqual([c['id'] for c in result['candidates']],['E01','E07','E13','E19'])
            self.assertEqual(len(names),5)
            provenance=load(root/'05_portfolio_assembly.json')
            self.assertEqual(provenance['output_sha256'],sha(root/'05_portfolio_blueprint.json'))
            for item in provenance['sources']:self.assertEqual(item['sha256'],sha(root/item['path']))
    def test_unknown_evidence_never_becomes_blueprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError,'Unknown evidence'):self.build(root,corrupt=True)
            self.assertFalse((root/'05_portfolio_blueprint.json').exists())

if __name__=='__main__':unittest.main()
