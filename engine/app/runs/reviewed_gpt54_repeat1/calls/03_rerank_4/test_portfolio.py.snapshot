import unittest
from research_workflow import validate_plan,FAMILIES
from workflow import derive_literal_contrasts
class GuardChecks(unittest.TestCase):
    def plan(self):
        return dict(queries=[dict(id=q+c,question_id=q,channel=c,question='test',term_groups=[['TEOA','triethanolamine'],['cobalt'] ] if c=='teoa_system' else [['spectroscopy'],['cobalt']]) for q in FAMILIES for c in ('teoa_system','method')])
    def test_method_need_not_name_teoa(self):validate_plan(self.plan(),True)
    def test_authorized_mixed_teoa_group_warns(self):
        p=self.plan();p['queries'][0]['term_groups'][0]=['TEOA','cobalt']
        with self.assertWarnsRegex(RuntimeWarning,'USER_AUTHORIZED_QUERY_WARNING'):validate_plan(p,True)
    def test_missing_family_channel_rejected(self):
        p=self.plan();p['queries'].pop()
        with self.assertRaises(ValueError):validate_plan(p,True)
    def test_phrase_not_a_whole_token(self):
        p=self.plan();p['queries'][1]['term_groups']=[['electron transfer']]
        with self.assertRaises(ValueError):validate_plan(p,True)
    def test_derived_diff_does_not_rewrite_science(self):
        c=dict(id='C01',purpose='An uncertain proposal',groups=[dict(id='G1',factors=[dict(name='donor',value='TEOA'),dict(name='dose',value='low')]),dict(id='G2',factors=[dict(name='donor',value='TEA'),dict(name='dose',value='high')])],comparisons=[dict(group_a='G1',group_b='G2',changed_factors=['donor'],inference='A claim requiring scientific review')])
        result,audit=derive_literal_contrasts([c])
        self.assertEqual(result[0]['comparisons'][0]['changed_factors'],['donor','dose'])
        self.assertEqual(c['comparisons'][0]['changed_factors'],['donor'])
        self.assertEqual(result[0]['comparisons'][0]['inference'],c['comparisons'][0]['inference'])
        self.assertEqual(result[0]['groups'],c['groups']);self.assertEqual(len(audit),1)
if __name__=='__main__':unittest.main()
